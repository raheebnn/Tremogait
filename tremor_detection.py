import os
import sys
import smbus2
import time
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# --- Configuration ---
MPU6050_ADDR = 0x68
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43

# Calibration offsets (measure these in stable position)
CALIB_OFFSETS = {
    'ax': -120, 'ay': 50, 'az': 1000,   # Accelerometer offsets
    'gx': 40, 'gy': -20, 'gz': 10       # Gyroscope offsets
}

# Tremor classification thresholds (adjust based on testing)
TREMOR_THRESHOLDS = {
    'small': 9000,
    'medium': 12000,
    'large': 16500
}

# Stability check limits (customizable for both accelerometer and gyroscope)
STABLE_LIMIT_ACCEL = 7500  # Custom threshold for accelerometer data stability check
STABLE_LIMIT_GYRO = 2000   # Custom threshold for gyroscope data stability check
CONFIDENCE_THRESHOLD = 0.7  # Only classify if model is 70%+ confident

# --- Initialize ---
print("🟢 Tremor Detection System (Confidence-Based)")
bus = smbus2.SMBus(1)
bus.write_byte_data(MPU6050_ADDR, PWR_MGMT_1, 0)

# Load model
try:
    _here = os.path.dirname(os.path.abspath(__file__))
    _candidates = [os.environ.get('TREMOGAIT_TREMOR_MODEL', ''),
                   os.path.join(_here, '..', 'models', 'svm_model_with_scaler.pkl'),
                   'svm_model_with_scaler.pkl']
    model_path = next((p for p in _candidates if p and os.path.isfile(p)), 'svm_model_with_scaler.pkl')
    model_bundle = joblib.load(model_path)
    model = model_bundle['model']
    scaler = model_bundle['scaler']
    print("✅ Model loaded successfully")
except Exception as e:
    print(f"❌ Model loading failed: {str(e)}")
    sys.exit(1)

def read_raw_data(addr):
    high = bus.read_byte_data(MPU6050_ADDR, addr)
    low = bus.read_byte_data(MPU6050_ADDR, addr + 1)
    value = (high << 8) | low
    return value - 65536 if value >= 32768 else value

def get_calibrated_data():
    """Returns sensor data with calibration offsets applied"""
    raw = [
        (read_raw_data(ACCEL_XOUT_H)/3),
        (read_raw_data(ACCEL_XOUT_H + 2)/3),
        (read_raw_data(ACCEL_XOUT_H + 4)/3),
        (read_raw_data(GYRO_XOUT_H)/2),
        (read_raw_data(GYRO_XOUT_H + 2)/2),
        (read_raw_data(GYRO_XOUT_H + 4)/2)
    ]
    calibrated = [
        raw[0] - CALIB_OFFSETS['ax'],
        raw[1] - CALIB_OFFSETS['ay'],
        raw[2] - CALIB_OFFSETS['az'],
        raw[3] - CALIB_OFFSETS['gx'],
        raw[4] - CALIB_OFFSETS['gy'],
        raw[5] - CALIB_OFFSETS['gz']
    ]
    return calibrated

def is_stable(sensor_data):
    """Check if the sensor data is stable based on custom limits for accelerometer and gyroscope"""
    accel_data = sensor_data[:3]  # Accelerometer data
    gyro_data = sensor_data[3:]   # Gyroscope data

    # Check if both accelerometer and gyroscope data are within their stable limits
    accel_stable = all(abs(x) < STABLE_LIMIT_ACCEL for x in accel_data)
    gyro_stable = all(abs(x) < STABLE_LIMIT_GYRO for x in gyro_data)

    return accel_stable and gyro_stable

def classify_tremor(magnitude):
    if magnitude < TREMOR_THRESHOLDS['small']:
        return "SMALL TREMOR"
    elif magnitude < TREMOR_THRESHOLDS['medium']:
        return "MEDIUM TREMOR"
    else:
        return "LARGE TREMOR"

def get_tremor_magnitude(data):
    """Calculates combined tremor magnitude using both accelerometer and gyroscope data."""

    # Gyroscope data (angular velocity)
    gx, gy, gz = data[3], data[4], data[5]

    # Accelerometer data (linear acceleration)
    ax, ay, az = data[0], data[1], data[2]

    # Euclidean norm combining both accelerometer and gyroscope data
    gyro_magnitude = np.sqrt(gx**2 + gy**2 + gz**2)
    accel_magnitude = np.sqrt(ax**2 + ay**2 + az**2)

    # Combine both magnitudes (you can adjust the weight if needed)
    combined_magnitude = np.sqrt(gyro_magnitude**2 + accel_magnitude**2)

    return combined_magnitude

# --- Real-Time Plotting Setup ---
fig, ax = plt.subplots(2, 1, figsize=(10, 6))
accel_data = {'ax': [], 'ay': [], 'az': []}
gyro_data = {'gx': [], 'gy': [], 'gz': []}

# Global variables for classification logic (to persist across frames)
start_time = datetime.now()
stable_count = 0
tremor_count = 0

def update_plot(frame):
    """Function to update the plot with new data and perform classification"""
    global start_time, stable_count, tremor_count  # Declare as global

    # Get new sensor data
    sensor_data = get_calibrated_data()

    # Append the data to the corresponding lists
    accel_data['ax'].append(sensor_data[0])
    accel_data['ay'].append(sensor_data[1])
    accel_data['az'].append(sensor_data[2])
    gyro_data['gx'].append(sensor_data[3])
    gyro_data['gy'].append(sensor_data[4])
    gyro_data['gz'].append(sensor_data[5])

    # Limit the lists to the latest 100 values
    if len(accel_data['ax']) > 100:
        for key in accel_data:
            accel_data[key] = accel_data[key][1:]
        for key in gyro_data:
            gyro_data[key] = gyro_data[key][1:]

    # Clear and plot accelerometer data
    ax[0].cla()
    ax[0].plot(accel_data['ax'], label="ax")
    ax[0].plot(accel_data['ay'], label="ay")
    ax[0].plot(accel_data['az'], label="az")
    ax[0].set_title("Accelerometer Data (Real-Time)")
    ax[0].legend(loc="upper right")
    ax[0].set_xlabel("Time (frames)")
    ax[0].set_ylabel("Acceleration (m/s²)")
    ax[0].set_ylim([-5000, 5000])

    # Clear and plot gyroscope data
    ax[1].cla()
    ax[1].plot(gyro_data['gx'], label="gx")
    ax[1].plot(gyro_data['gy'], label="gy")
    ax[1].plot(gyro_data['gz'], label="gz")
    ax[1].set_title("Gyroscope Data (Real-Time)")
    ax[1].legend(loc="upper right")
    ax[1].set_xlabel("Time (frames)")
    ax[1].set_ylabel("Angular Velocity (°/s)")
    ax[1].set_ylim([-5000, 5000])

    plt.tight_layout()

    # --- Tremor Classification Logic (moved into update_plot) ---
    if is_stable(sensor_data):
        stable_count += 1
    else:
        tremor_count += 1

    # The animation interval is 500ms, so 40 frames = 20 seconds
    if frame % 40 == 0 and frame != 0:
        if stable_count > tremor_count:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🟢 Not Parkinson's Disease (Stable)")
        else:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚨 Potential Parkinson's Disease (Tremor detected)")
        stable_count, tremor_count = 0, 0  # Reset counters
        start_time = datetime.now()        # Reset for next 20 sec interval

# --- Main Execution ---
try:
    ani = FuncAnimation(fig, update_plot, interval=500, cache_frame_data=False)
    plt.show()
except KeyboardInterrupt:
    print("🛑 Detection stopped.")
