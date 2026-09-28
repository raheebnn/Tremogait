#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <MPU6050.h>

// Wi-Fi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// ===== Set this to "left" or "right" before flashing each board =====
#define LEG "left"

// Server IP and endpoint (endpoint is chosen from LEG automatically)
const String serverName = String("http://YOUR_SERVER_IP:8080/receive_") + LEG + "_gait";

// MPU6050 I2C address
MPU6050 mpu;

// Scaling factor for ±2g range of MPU6050 (16384 counts)
const float SCALING_FACTOR = 16384.0;

void setup() {
  Serial.begin(115200);
  Wire.begin();

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");

  // Initialize MPU6050
  mpu.initialize();
}

void loop() {
  // Read acceleration data from MPU6050
  int16_t ax, ay, az;
  mpu.getAcceleration(&ax, &ay, &az);

  // Scale the raw values to 'g' (since MPU6050 has a ±2g range)
  float ax_scaled = ax / SCALING_FACTOR;
  float ay_scaled = ay / SCALING_FACTOR;
  float az_scaled = az / SCALING_FACTOR;

  // Print the scaled acceleration values
  Serial.print(LEG); Serial.print(" leg - X: "); Serial.print(ax_scaled);
  Serial.print(" Y: "); Serial.print(ay_scaled);
  Serial.print(" Z: "); Serial.println(az_scaled);

  // Send the scaled data to Raspberry Pi
  HTTPClient http;
  http.begin(serverName);

  // Prepare the payload
  String payload = String("leg=") + LEG + "&ax=" + String(ax_scaled) + "&ay=" + String(ay_scaled) + "&az=" + String(az_scaled);
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");

  // Send POST request
  int httpResponseCode = http.POST(payload);

  if (httpResponseCode > 0) {
    Serial.println(String(LEG) + " leg data sent to Raspberry Pi");
  } else {
    Serial.println("Error sending data to Raspberry Pi");
  }

  http.end();
  delay(1000); // Delay before next reading
}
