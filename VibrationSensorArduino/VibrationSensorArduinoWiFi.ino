/*
 * Vibration Sensor Arduino Sketch - WiFi HTTP REST API Version
 * 
 * This sketch reads data from a vibration sensor and communicates via WiFi HTTP REST API
 * with the Python vibration_agent
 * 
 * Hardware Setup:
 * - ESP8266 (NodeMCU, Wemos D1 Mini) or ESP32 board
 * - Vibration sensor module connected to analog pin A0
 * - Optional: LED on pin 13 for visual feedback
 * 
 * HTTP REST API:
 * - GET /status - Get device status
 * - GET /sensor - Read current sensor value
 * - POST /calibrate - Calibrate sensor
 * - POST /threshold - Set threshold value
 * - GET /monitor - Get continuous monitoring data (long polling)
 */

#ifdef ESP32
  #include <WiFi.h>
  #include <WebServer.h>
  WebServer server(80);
#else
  #include <ESP8266WiFi.h>
  #include <ESP8266WebServer.h>
  ESP8266WebServer server(80);
#endif

#include <ArduinoJson.h>

// WiFi credentials - CHANGE THESE!
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Pin definitions
#ifdef ESP32
  const int VIBRATION_SENSOR_PIN = 34;  // ESP32 ADC pin
  const int LED_PIN = 2;                 // Built-in LED
  const int CALIBRATION_LED = 4;         // External LED
#else
  const int VIBRATION_SENSOR_PIN = A0;   // ESP8266 ADC pin
  const int LED_PIN = LED_BUILTIN;       // Built-in LED
  const int CALIBRATION_LED = D4;        // External LED
#endif

// Sensor variables
int baselineValue = 0;      // Baseline reading (calibrated zero)
int threshold = 100;        // Detection threshold
int currentValue = 0;       // Current sensor reading
bool isCalibrating = false; // Calibration flag
unsigned long lastReadTime = 0;
const int READ_INTERVAL = 50; // Read sensor every 50ms

// Monitoring variables
bool hasNewData = false;
unsigned long monitorTimeout = 30000; // 30 second timeout for long polling

// Calibration settings
const int CALIBRATION_SAMPLES = 100;
const int CALIBRATION_DELAY = 10;

// Device info
String deviceId = "vibration_sensor_wifi_01";
String firmwareVersion = "3.0.0";

void setup() {
  Serial.begin(115200);
  delay(100);
  
  // Initialize pins
  pinMode(VIBRATION_SENSOR_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(CALIBRATION_LED, OUTPUT);
  
  digitalWrite(LED_PIN, LOW);
  digitalWrite(CALIBRATION_LED, LOW);
  
  // Connect to WiFi
  connectToWiFi();
  
  // Setup HTTP routes
  setupHTTPRoutes();
  
  // Start HTTP server
  server.begin();
  Serial.println("HTTP server started");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  
  // Initial calibration
  calibrateSensor();
}

void loop() {
  // Handle HTTP requests
  server.handleClient();
  
  // Read sensor periodically
  unsigned long currentTime = millis();
  if (currentTime - lastReadTime >= READ_INTERVAL) {
    lastReadTime = currentTime;
    int rawValue = analogRead(VIBRATION_SENSOR_PIN);
    currentValue = abs(rawValue - baselineValue);
    hasNewData = true;
    
    // Visual feedback if vibration detected
    if (currentValue > threshold) {
      digitalWrite(LED_PIN, HIGH);
    } else {
      digitalWrite(LED_PIN, LOW);
    }
  }
}

void connectToWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    digitalWrite(LED_PIN, !digitalRead(LED_PIN)); // Blink LED while connecting
  }
  
  Serial.println("");
  Serial.println("WiFi connected");
  digitalWrite(LED_PIN, LOW);
}

void setupHTTPRoutes() {
  // GET /status - Device status
  server.on("/status", HTTP_GET, handleStatus);
  
  // GET /sensor - Current sensor reading
  server.on("/sensor", HTTP_GET, handleSensorRead);
  
  // POST /calibrate - Calibrate sensor
  server.on("/calibrate", HTTP_POST, handleCalibrate);
  
  // POST /threshold - Set threshold
  server.on("/threshold", HTTP_POST, handleSetThreshold);
  
  // GET /monitor - Long polling for continuous data
  server.on("/monitor", HTTP_GET, handleMonitor);
  
  // Handle 404
  server.onNotFound(handleNotFound);
  
  // Enable CORS
  server.on("/", HTTP_OPTIONS, []() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
    server.send(200);
  });
}

void handleStatus() {
  StaticJsonDocument<400> doc;
  doc["status"] = "online";
  doc["device_id"] = deviceId;
  doc["firmware_version"] = firmwareVersion;
  doc["protocol"] = "http";
  doc["ip_address"] = WiFi.localIP().toString();
  doc["mac_address"] = WiFi.macAddress();
  doc["baseline"] = baselineValue;
  doc["threshold"] = threshold;
  doc["uptime"] = millis();
  doc["wifi_strength"] = WiFi.RSSI();
  
  String response;
  serializeJson(doc, response);
  
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", response);
}

void handleSensorRead() {
  int rawValue = analogRead(VIBRATION_SENSOR_PIN);
  int adjustedValue = abs(rawValue - baselineValue);
  
  StaticJsonDocument<300> doc;
  doc["value"] = adjustedValue;
  doc["raw_value"] = rawValue;
  doc["baseline"] = baselineValue;
  doc["threshold"] = threshold;
  doc["detected"] = (adjustedValue > threshold);
  doc["timestamp"] = millis();
  
  // Add vibration intensity classification
  if (adjustedValue < 50) {
    doc["level"] = "none";
  } else if (adjustedValue < 200) {
    doc["level"] = "low";
  } else if (adjustedValue < 500) {
    doc["level"] = "medium";
  } else if (adjustedValue < 800) {
    doc["level"] = "high";
  } else {
    doc["level"] = "extreme";
  }
  
  String response;
  serializeJson(doc, response);
  
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", response);
}

void handleCalibrate() {
  calibrateSensor();
  
  StaticJsonDocument<200> doc;
  doc["success"] = true;
  doc["message"] = "Calibration completed";
  doc["baseline"] = baselineValue;
  
  String response;
  serializeJson(doc, response);
  
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", response);
}

void handleSetThreshold() {
  if (server.hasArg("plain")) {
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, server.arg("plain"));
    
    if (!error && doc.containsKey("value")) {
      threshold = doc["value"];
      
      StaticJsonDocument<200> response_doc;
      response_doc["success"] = true;
      response_doc["message"] = "Threshold updated";
      response_doc["threshold"] = threshold;
      
      String response;
      serializeJson(response_doc, response);
      
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(200, "application/json", response);
    } else {
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(400, "application/json", "{\"error\":\"Invalid request\"}");
    }
  } else {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(400, "application/json", "{\"error\":\"No data received\"}");
  }
}

void handleMonitor() {
  // Long polling implementation
  unsigned long startTime = millis();
  
  // Wait for new data or timeout
  while (!hasNewData && (millis() - startTime < monitorTimeout)) {
    server.handleClient();
    delay(10);
  }
  
  if (hasNewData) {
    hasNewData = false;
    
    int rawValue = analogRead(VIBRATION_SENSOR_PIN);
    int adjustedValue = abs(rawValue - baselineValue);
    
    StaticJsonDocument<200> doc;
    doc["type"] = "sensor_data";
    doc["value"] = adjustedValue;
    doc["raw_value"] = rawValue;
    doc["detected"] = (adjustedValue > threshold);
    doc["timestamp"] = millis();
    
    String response;
    serializeJson(doc, response);
    
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(200, "application/json", response);
  } else {
    // Timeout - send empty response
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(204); // No content
  }
}

void handleNotFound() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(404, "application/json", "{\"error\":\"Not found\"}");
}

void calibrateSensor() {
  Serial.println("Starting calibration...");
  digitalWrite(CALIBRATION_LED, HIGH);
  isCalibrating = true;
  
  long sum = 0;
  for (int i = 0; i < CALIBRATION_SAMPLES; i++) {
    sum += analogRead(VIBRATION_SENSOR_PIN);
    delay(CALIBRATION_DELAY);
    
    // Blink calibration LED
    if (i % 10 == 0) {
      digitalWrite(CALIBRATION_LED, !digitalRead(CALIBRATION_LED));
    }
  }
  
  baselineValue = sum / CALIBRATION_SAMPLES;
  isCalibrating = false;
  digitalWrite(CALIBRATION_LED, LOW);
  
  Serial.print("Calibration complete. Baseline: ");
  Serial.println(baselineValue);
}