# Gait server API

`raspberry_pi/gait_server.py` — Flask, port `8080`.

| Method | Path | Body | Purpose |
|---|---|---|---|
| `GET` | `/health` | — | Liveness check |
| `POST` | `/receive_left_gait` | form: `ax`, `ay`, `az` (g) | Left-leg reading (used by the firmware) |
| `POST` | `/receive_right_gait` | form: `ax`, `ay`, `az` (g) | Right-leg reading (used by the firmware) |
| `POST` | `/receive_data` | form: `leg` (`left`/`right`), `ax`, `ay`, `az` | Generic endpoint |
| `GET` | `/result` | — | Last completed session + current stride count |

A stride is processed once one reading from each leg has arrived.

**Per-stride response**
```json
{"stride": 3, "stride_prediction": "Normal", "reason": "...", "left_magnitude": 1.12, "right_magnitude": 1.15}
```

**Final response (after 10 strides)** — the server then resets and is ready for a new session.
```json
{"final_prediction": "Abnormal", "normal_count": 3, "abnormal_count": 7, "strides": 10}
```

## Test with curl

```bash
curl -X POST -d "ax=0.31&ay=0.92&az=0.55" http://localhost:8080/receive_left_gait
curl -X POST -d "ax=0.28&ay=0.95&az=0.51" http://localhost:8080/receive_right_gait
curl http://localhost:8080/result
```
