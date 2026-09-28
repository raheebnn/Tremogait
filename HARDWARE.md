# Hardware & wiring

## Bill of materials

| Qty | Part | Role |
|---|---|---|
| 3 | ESP32 dev board | 1 × hand, 2 × legs |
| 1 | MPU9250 | Hand tremor (accel + gyro) |
| 2 | MPU6050 | Left and right leg acceleration |
| 1 | Raspberry Pi (3B+/4/5) | Flask server, optional direct tremor sensing |
| 3 | Battery pack / power bank | Power for each wearable |
| — | Straps or bands | Mounting on wrist and shins |

All devices must be on the same Wi-Fi network.

## ESP32 ↔ IMU (I²C)

Both sketches call `Wire.begin()` with the ESP32 default pins.

| IMU pin | ESP32 pin |
|---|---|
| VCC | 3V3 |
| GND | GND |
| SDA | GPIO 21 |
| SCL | GPIO 22 |

## Raspberry Pi ↔ MPU6050 (optional, for `tremor_detection.py`)

| MPU6050 | Raspberry Pi |
|---|---|
| VCC | 3.3 V (pin 1) |
| GND | GND (pin 6) |
| SDA | GPIO 2 (pin 3) |
| SCL | GPIO 3 (pin 5) |

Enable I²C with `sudo raspi-config` → Interface Options → I2C. The sensor should show up at `0x68` in `i2cdetect -y 1`.

## Mounting tips

- Fix each leg sensor in the same orientation on both shins — the asymmetry check compares the two directly.
- Strap sensors tightly; loose mounting adds vibration that looks like tremor.
- Keep the hand sensor on the back of the hand or wrist, same place every session.
