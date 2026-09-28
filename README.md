 TremoGait

> 📄 **Accepted at IEEE TENCON 2026** — the paper describing this system has been accepted at the IEEE Region 10 Conference (TENCON) 2026.

An IoT + machine-learning system for **screening Parkinson's-related symptoms** by combining two signals:

- **Hand tremor**: an ESP32 + IMU on the hand streams accelerometer and gyroscope data.
- **Gait**: two ESP32 + MPU6050 units (left and right leg) stream acceleration data.

A Raspberry Pi / Flask server classifies each signal with a trained model, and a dashboard combines the two results into a single screening outcome. Readings can also be pushed to ThingSpeak for live plotting.

> ⚠️ **Disclaimer:** This is an academic/prototype project. It is **not a medical device** and must not be used for diagnosis. Consult a qualified neurologist for any health concern.

---

## How it works

```
 ┌────────────────┐   HTTP POST (JSON)    ┌──────────────────────┐
 │ ESP32 + IMU    │ ────────────────────► │                      │
 │ (hand tremor)  │                       │   Raspberry Pi /     │      ┌────────────┐
 └────────────────┘                       │   Flask server       │ ───► │ Dashboard  │
 ┌────────────────┐   HTTP POST (form)    │   - SVM  (tremor)    │      │ + ensemble │
 │ 2× ESP32 +     │ ────────────────────► │   - KNN  (gait)      │      │ decision   │
 │ MPU6050 (legs) │                       │   - rule checks      │      └─────┬──────┘
 └────────────────┘                       └──────────────────────┘            │
                                                                        ThingSpeak
```

### Tremor pipeline
- Features: `aX, aY, aZ, gX, gY, gZ`
- Models compared: Logistic Regression, Random Forest, SVM (RBF)
- The **SVM + StandardScaler** bundle is used for deployment (`svm_model_with_scaler.pkl`).
- On the Pi, `tremor_detection.py` reads an MPU6050 over I²C, applies calibration offsets, plots live data, and every ~20 s decides *stable* vs *tremor detected* using stability thresholds.

### Gait pipeline
- Features: `Gender, L Accel X/Y/Z (g), R Accel X/Y/Z (g)`
- Dataset balanced by gender × status (60,356 samples per group after balancing)
- Models compared: Random Forest, Logistic Regression, Naive Bayes, KNN, XGBoost
- The **KNN + StandardScaler** bundle is used for deployment (`knn_model_with_scaler22.pkl`).
- `gait_server.py` waits for one reading from each leg, then decides per stride:
  1. Both magnitudes ≈ 1 g → stationary → *Abnormal*
  2. Both magnitudes in the normal-walking range → *Normal*
  3. Otherwise → ML model, followed by an **Asymmetry Index** check (ASI > 15 % overrides "Normal")
- After 10 strides, a majority vote gives the final gait result.

### Final decision (dashboard)
| Tremor | Gait | Result |
|---|---|---|
| Abnormal | Abnormal | Strong indication of Parkinson's symptoms |
| Abnormal | Normal (or vice versa) | Early signs detected |
| Normal | Normal | No symptoms detected |

---

## Results (from the notebooks)

**Tremor** (80/20 stratified split)

| Model | Train acc. | Test acc. |
|---|---|---|
| Logistic Regression | 0.768 | 0.758 |
| Random Forest | 1.000 | 0.998 |
| **SVM (RBF)** *(deployed)* | 0.977 | 0.982 |

**Gait** (70/5/15-ish train/val/test split)

| Model | Test acc. |
|---|---|
| Random Forest | 0.882 |
| XGBoost | 0.825 |
| **KNN** *(deployed)* | 0.846 |
| Logistic Regression / Naive Bayes | ~0.57 |

> Random Forest reaches 100 % train accuracy in both notebooks, which suggests overfitting. Results should be validated on data from **new subjects**, not just a random row split.

---

## Repository structure

```
TremoGait/
├── firmware/
│   ├── hand_tremor/hand_tremor.ino   # ESP32 + MPU9250 → POST JSON every 500 ms
│   └── leg_gait/leg_gait.ino         # ESP32 + MPU6050 → POST form data every 1 s
├── notebooks/
│   ├── tremor_model_training.ipynb   # tremor model training/evaluation
│   └── gait_model_training.ipynb     # gait dataset balancing + model training
├── raspberry_pi/
│   ├── tremor_detection.py           # live MPU6050 reading + tremor classification
│   └── gait_server.py                # Flask server for leg data + gait prediction
├── dashboard/
│   └── ensemble_and_thingspeak.py    # combined result + ThingSpeak upload (snippets)
├── models/                           # put trained .pkl files here (git-ignored)
├── data/                             # put datasets here (git-ignored)
└── requirements.txt
```

## Hardware

- 3× ESP32 (1 hand, 2 legs)
- 1× MPU9250 (hand) and 2× MPU6050 (legs)
- Raspberry Pi (server + optional direct MPU6050 tremor sensing)
- Wi-Fi network shared by all devices

## Setup

### 1. Python environment
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Train the models
Open the notebooks and update the dataset paths (they currently point to local `J:\...` folders), then run all cells. The last cells export:
- `svm_model_with_scaler.pkl` (tremor)
- `knn_model_with_scaler.pkl` → rename to `knn_model_with_scaler22.pkl` (gait), or change the filename in `gait_server.py`

Place both files in `models/` (or next to the scripts).

**Expected dataset columns**
- Tremor CSV: `aX, aY, aZ, gX, gY, gZ, Result`
- Gait CSV: `Gender, L Accel X (g), L Accel Y (g), L Accel Z (g), R Accel X (g), R Accel Y (g), R Accel Z (g), Status`

### 3. Flash the ESP32s
Install these Arduino libraries: `MPU6050` (I2Cdevlib), `MPU9250_asukiaaa`.
In each `.ino` file, replace the placeholders:
```cpp
const char* ssid     = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
// server URL: http://YOUR_SERVER_IP:8080/...
```
For the two legs, flash the same sketch twice, changing `leg=left` to `leg=right` on the second board.

### 4. Run the server (Raspberry Pi)
```bash
cd raspberry_pi
python gait_server.py            # asks for gender (m/f), listens on port 8080
python tremor_detection.py       # live tremor detection with plots
```

### 5. ThingSpeak (optional)
Never commit your API key. Set it as an environment variable:
```bash
export THINGSPEAK_API_KEY="your_write_key"
```

---

## Citation

If you use this work, please cite our paper:

```bibtex
@inproceedings{tremogait2026,
  title     = {YOUR PAPER TITLE},
  author    = {Nazmul, Raheeb Bin and OTHER AUTHORS},
  booktitle = {Proceedings of the IEEE Region 10 Conference (TENCON)},
  year      = {2026},
  note      = {Accepted}
}
```

> Replace the title and author list with the final details from the paper. Add the DOI once the paper is published in IEEE Xplore.

## Known limitations / TODO

- The ESP32 leg firmware posts to `/receive_left_gait`, but `gait_server.py` exposes `/receive_data`. Make the endpoint names match before running end to end.
- `gait_server.py` calls `os._exit(0)` after 10 strides, so the server stops after one session.
- Global state in the server means it supports **one user at a time**.
- Dashboard code is provided as snippets; the full Flask app is not included yet.
- Datasets and trained models are not included.

## License

Released under the [MIT License](LICENSE). Datasets may have their own terms.
