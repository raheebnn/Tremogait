import os
import sys
import time
from flask import Flask, request, jsonify
import joblib
import pandas as pd
import numpy as np

# --- Application Setup ---
app = Flask(__name__)

# --- Global State Management ---
# WARNING: Using global variables makes this server NOT thread-safe. It will only
# work correctly with a single user at a time.

# Dictionaries to hold the most recent data from each leg sensor.
left_leg_data = {'ax': None, 'ay': None, 'az': None}
right_leg_data = {'ax': None, 'ay': None, 'az': None}

# Variables to track predictions over a series of strides.
stride_count = 0
stride_predictions = []

# The number of strides to collect before making a final, aggregated decision.
PREDICTION_THRESHOLD = 10

# --- Configurable Parameters ---
SCALING_FACTOR = 1.0

# Thresholds to detect if the user is stationary (~1g due to gravity).
STATIONARY_MAGNITUDE_MIN = 1.03
STATIONARY_MAGNITUDE_MAX = 1.06
LEFT_MAGNITUDE_MIN_THRESHOLD = 1.07
LEFT_MAGNITUDE_MAX_THRESHOLD = 1.30
RIGHT_MAGNITUDE_MIN_THRESHOLD = 1.07
RIGHT_MAGNITUDE_MAX_THRESHOLD = 1.30

# Asymmetry Index (ASI) threshold. If the model predicts "Normal" but the
# asymmetry between legs is higher than this value, it will be overridden to "Abnormal".
ASI_THRESHOLD = 15.0  # Represents a 15% difference

# --- Load Trained Machine Learning Model ---
# Looks in, in order: $TREMOGAIT_GAIT_MODEL, ../models/, then the current directory.
MODEL_FILENAME = 'knn_model_with_scaler22.pkl'
_here = os.path.dirname(os.path.abspath(__file__))
_candidates = [
    os.environ.get('TREMOGAIT_GAIT_MODEL', ''),
    os.path.join(_here, '..', 'models', MODEL_FILENAME),
    MODEL_FILENAME,
]
model_file_path = next((p for p in _candidates if p and os.path.isfile(p)), MODEL_FILENAME)
model = None

try:
    print(f"Loading model from: {model_file_path}...")
    loaded_object = joblib.load(model_file_path)

    if isinstance(loaded_object, dict):
        model = loaded_object.get('model') or loaded_object.get('pipeline')
    else:
        model = loaded_object

    if model:
        print("✅ Model loaded successfully.")
    else:
        raise ValueError("No valid model found in the loaded file.")

except FileNotFoundError:
    print(f"❌ Error: Model file not found at '{model_file_path}'.")
    print("Put it in models/ or set TREMOGAIT_GAIT_MODEL to its path.")
    sys.exit(1)
except Exception as e:
    print(f"❌ An error occurred while loading the model: {e}")
    sys.exit(1)

# --- User Gender Input (Once at Startup) ---
def get_user_gender():
    """
    Prompts the user to enter their gender at startup.
    Returns: int: 1 for male, 0 for female.
    Set TREMOGAIT_GENDER=m or f to skip the prompt (e.g. when run as a service).
    """
    env_gender = os.environ.get('TREMOGAIT_GENDER', '').strip().lower()
    if env_gender in ('m', 'f'):
        print(f"Gender set from TREMOGAIT_GENDER: {'Male' if env_gender == 'm' else 'Female'}")
        return 1 if env_gender == 'm' else 0

    while True:
        try:
            gender_input = input("Please enter your gender (m/f): ").strip().lower()
            if gender_input == 'm':
                print("Gender set to: Male")
                return 1
            elif gender_input == 'f':
                print("Gender set to: Female")
                return 0
            else:
                print("Invalid input. Please enter 'm' or 'f'.")
        except Exception as e:
            print(f"An error occurred: {e}. Please try again.")

GENDER = get_user_gender()

# --- Flask Endpoint: Health Check ---
@app.route('/health', methods=['GET'])
def health_check():
    """A simple endpoint to confirm that the server is running."""
    return jsonify({'status': 'Server is running'}), 200

# Most recent completed session, served by GET /result.
last_result = None

@app.route('/result', methods=['GET'])
def get_result():
    """Returns the final decision from the most recently completed session."""
    return jsonify({
        'last_result': last_result,          # None until a session completes
        'current_stride': stride_count,
        'strides_needed': PREDICTION_THRESHOLD
    }), 200

# --- Flask Endpoint: Data Receiver and Predictor ---
# /receive_left_gait and /receive_right_gait match the URLs used by
# firmware/leg_gait/leg_gait.ino; /receive_data expects a 'leg' form field.
@app.route('/receive_left_gait', methods=['POST'], defaults={'route_leg': 'left'})
@app.route('/receive_right_gait', methods=['POST'], defaults={'route_leg': 'right'})
@app.route('/receive_data', methods=['POST'], defaults={'route_leg': None})
def receive_data(route_leg):
    """
    Receives accelerometer data for a leg, processes a full stride when data
    for both legs is available, and returns a gait prediction.
    """
    global left_leg_data, right_leg_data, stride_count, stride_predictions, last_result

    try:
        # --- 1. Get and Scale Data from the POST Request ---
        leg = route_leg or request.form.get('leg', '').strip().lower()
        ax = float(request.form.get('ax', '0')) * SCALING_FACTOR
        ay = float(request.form.get('ay', '0')) * SCALING_FACTOR
        az = float(request.form.get('az', '0')) * SCALING_FACTOR

        if leg == 'left':
            left_leg_data.update({'ax': ax, 'ay': ay, 'az': az})
        elif leg == 'right':
            right_leg_data.update({'ax': ax, 'ay': ay, 'az': az})
        else:
            return jsonify({'error': f"Invalid leg identifier: '{leg}'"}), 400

        # --- 2. Wait for a Complete Stride (Data from Both Legs) ---
        if left_leg_data['ax'] is None or right_leg_data['ax'] is None:
            return jsonify({'message': 'Data received. Waiting for the other leg.'}), 200

        # --- 3. Process the Complete Stride Data ---
        left_mag = np.sqrt(left_leg_data['ax']**2 + left_leg_data['ay']**2 + left_leg_data['az']**2)
        right_mag = np.sqrt(right_leg_data['ax']**2 + right_leg_data['ay']**2 + right_leg_data['az']**2)

        # --- 4. Prediction Logic (Rule-Based and ML) ---
        gait_status_for_stride = None
        reason = ""

        # STEP 1: Check if the person is stationary.
        if (STATIONARY_MAGNITUDE_MIN <= left_mag <= STATIONARY_MAGNITUDE_MAX and
                STATIONARY_MAGNITUDE_MIN <= right_mag <= STATIONARY_MAGNITUDE_MAX):
            gait_status_for_stride = "Abnormal"
            reason = "Stationary position detected (magnitudes are near 1g)."

        # STEP 2: Check if magnitudes are in a predefined 'normal' range.
        elif (LEFT_MAGNITUDE_MIN_THRESHOLD <= left_mag <= LEFT_MAGNITUDE_MAX_THRESHOLD and
              RIGHT_MAGNITUDE_MIN_THRESHOLD <= right_mag <= RIGHT_MAGNITUDE_MAX_THRESHOLD):
            gait_status_for_stride = "Normal"
            reason = "Magnitudes are within the predefined normal walking range."

        # STEP 3: If neither of the above, use the ML model.
        else:
            feature_data = pd.DataFrame([{
                'L Accel X (g)': left_leg_data['ax'],
                'L Accel Y (g)': left_leg_data['ay'],
                'L Accel Z (g)': left_leg_data['az'],
                'R Accel X (g)': right_leg_data['ax'],
                'R Accel Y (g)': right_leg_data['ay'],
                'R Accel Z (g)': right_leg_data['az'],
                'Gender': GENDER
            }])

            model_prediction = model.predict(feature_data)[0]

            if model_prediction == 0:  # Assuming 0 corresponds to "Normal"
                # If model says Normal, perform an Asymmetry Index check.
                # ASI = |L-R| / ((L+R)/2) * 100
                if (left_mag + right_mag) > 0:
                    asi = (np.abs(left_mag - right_mag) / ((left_mag + right_mag) / 2.0)) * 100
                else:
                    asi = 0

                if asi <= ASI_THRESHOLD:
                    gait_status_for_stride = "Normal"
                    reason = f"ML Model predicted Normal and ASI ({asi:.1f}%) is within threshold."
                else:
                    gait_status_for_stride = "Abnormal"
                    reason = f"ML Model predicted Normal, but ASI ({asi:.1f}%) is too high."
            else:  # Model predicts Abnormal
                gait_status_for_stride = "Abnormal"
                reason = "ML Model predicted Abnormal."

        # --- 5. Accumulate Stride Prediction and Reset for Next Stride ---
        stride_count += 1
        stride_predictions.append(gait_status_for_stride)

        print(f"\n--- STRIDE {stride_count}/{PREDICTION_THRESHOLD} ---")
        print(f"Left Mag: {left_mag:.2f}g | Right Mag: {right_mag:.2f}g")
        print(f"Prediction: {gait_status_for_stride} | Reason: {reason}")
        print("------------------------------")

        left_leg_data = {'ax': None, 'ay': None, 'az': None}
        right_leg_data = {'ax': None, 'ay': None, 'az': None}

        # --- 6. Determine Response (Intermediate or Final) ---
        if stride_count < PREDICTION_THRESHOLD:
            return jsonify({
                'stride': stride_count,
                'stride_prediction': gait_status_for_stride,
                'reason': reason,
                'left_magnitude': round(left_mag, 2),
                'right_magnitude': round(right_mag, 2)
            }), 200
        else:
            normal_count = stride_predictions.count("Normal")
            abnormal_count = stride_predictions.count("Abnormal")
            final_prediction = "Normal" if normal_count >= abnormal_count else "Abnormal"

            print(f"\n✅ FINAL DECISION after {PREDICTION_THRESHOLD} strides: {final_prediction}")
            print(f"   Normal count: {normal_count}, Abnormal count: {abnormal_count}")
            print("====================================")

            final_response = {
                'final_prediction': final_prediction,
                'normal_count': normal_count,
                'abnormal_count': abnormal_count,
                'strides': PREDICTION_THRESHOLD
            }
            last_result = final_response

            # Reset so a new session can start without restarting the server.

            stride_count = 0
            stride_predictions = []

            return jsonify(final_response), 200

    except Exception as e:
        print(f"❌ An error occurred in /receive_data: {e}")
        left_leg_data = {'ax': None, 'ay': None, 'az': None}
        right_leg_data = {'ax': None, 'ay': None, 'az': None}
        stride_count = 0
        stride_predictions = []
        return jsonify({'error': 'An internal server error occurred'}), 500

# --- Start Server ---
if __name__ == '__main__':
    # host='0.0.0.0' makes the server reachable from other devices on the local network.
    app.run(host='0.0.0.0', port=8080)
