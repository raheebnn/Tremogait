# Models

Trained models are not committed (`*.pkl` is git-ignored). Put them here:

| File | Used by | Produced by |
|---|---|---|
| `svm_model_with_scaler.pkl` | `raspberry_pi/tremor_detection.py` | `notebooks/tremor_model_training.ipynb` |
| `knn_model_with_scaler22.pkl` | `raspberry_pi/gait_server.py` | `notebooks/gait_model_training.ipynb` (exports `knn_model_with_scaler.pkl` — rename it) |

The scripts look here automatically. To use another location set `TREMOGAIT_TREMOR_MODEL` / `TREMOGAIT_GAIT_MODEL`.
