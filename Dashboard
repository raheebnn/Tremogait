# Snippets from the dashboard app (Flask). Needs: from flask import jsonify; import requests
# and your own log_event(), tremor_result, gait_result, test_state globals.

def get_final_result():
    global tremor_result, gait_result, test_state

    final = ''
    normal = ''
    abnormal = ''

    # Tremor conclusion
    if tremor_result == "Normal":
        normal += "✔️ Tremor: Normal\n"
    elif tremor_result == "Abnormal":
        abnormal += "⚠️ Tremor: Abnormal\n"

    # Gait conclusion
    if gait_result == "Normal":
        normal += "✔️ Gait: Normal\n"
    elif gait_result == "Abnormal":
        abnormal += "⚠️ Gait: Abnormal\n"

    # Combined Final Decision
    if tremor_result and gait_result:
        if tremor_result == "Abnormal" and gait_result == "Abnormal":
            final = "🔄 Strong indication of Parkinson's symptoms. Please consult a neurologist."
        elif tremor_result == "Abnormal" or gait_result == "Abnormal":
            final = "⚠️ Early signs of Parkinson's symptoms detected."
        else:
            final = "✅ Fine - no Parkinson's symptoms detected"

    return jsonify({
        'final': final,
        'normal': normal,
        'abnormal': abnormal,
        'tremor_result': tremor_result,
        'gait_result': gait_result
    })


# ---------------- ThingSpeak ----------------
import os
THINGSPEAK_API_KEY = os.environ.get("THINGSPEAK_API_KEY", "")  # set via environment variable
THINGSPEAK_URL = f"https://api.thingspeak.com/update?api_key={THINGSPEAK_API_KEY}"

def send_to_thingspeak(tremor_mag, left_mag, right_mag):
    try:
        payload = {
            'field1': tremor_mag,
            'field2': left_mag,
            'field3': right_mag
        }
        response = requests.get(THINGSPEAK_URL, params=payload)
        if response.status_code == 200:
            log_event(f"Data sent to ThingSpeak: Tremor={tremor_mag:.2f}, Left={left_mag:.2f}, Right={right_mag:.2f}", "INFO")
        else:
            log_event(f"ThingSpeak upload failed: {response.status_code} {response.text}", "ERROR")
    except Exception as e:
        log_event(f"Error sending to ThingSpeak: {str(e)}", "ERROR")
