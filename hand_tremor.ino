#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <MPU9250_asukiaaa.h>

// === Wi-Fi Credentials ===
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// === Server URL (replace with your Pi IP) ===
const char* serverURL = "http://YOUR_SERVER_IP:8080/receive_tremor";

// === MPU Setup ===
MPU9250_asukiaaa mySensor;

void setup() {
  Serial.begin(115200);
  Wire.begin();

  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");

  // Initialize MPU9250
  mySensor.setWire(&Wire);
  mySensor.beginAccel();
  mySensor.beginGyro();
}

void loop() {
  mySensor.accelUpdate();
  mySensor.gyroUpdate();

  float ax = mySensor.accelX();
  float ay = mySensor.accelY();
  float az = mySensor.accelZ();
  float gx = mySensor.gyroX();
  float gy = mySensor.gyroY();
  float gz = mySensor.gyroZ();

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverURL);
    http.addHeader("Content-Type", "application/json");

    String jsonPayload = "{\"ax\":" + String(ax, 6) +
                         ",\"ay\":" + String(ay, 6) +
                         ",\"az\":" + String(az, 6) +
                         ",\"gx\":" + String(gx, 6) +
                         ",\"gy\":" + String(gy, 6) +
                         ",\"gz\":" + String(gz, 6) + "}";

    int httpResponseCode = http.POST(jsonPayload);
    Serial.println("POST response: " + String(httpResponseCode));
    http.end();
  }

  delay(500); // Send data every 500ms
}
