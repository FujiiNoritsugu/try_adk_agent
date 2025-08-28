/*
 * Vibration Sensor Arduino Sketch - Serial Communication Version
 * 
 * This sketch reads data from a vibration sensor and communicates via Serial/USB
 * with the Python vibration_agent
 * 
 * Hardware Setup:
 * - Any Arduino board (Uno, Nano, Mega, etc.)
 * - Vibration sensor module connected to analog pin A0
 * - Optional: LED on pin 13 for visual feedback
 * 
 * Serial Protocol:
 * - JSON messages delimited by newline
 * - Commands: status, read_sensor, calibrate, set_threshold, start_monitoring, stop_monitoring
 */

#include <ArduinoJson.h>

// Pin definitions
const int VIBRATION_SENSOR_PIN = A0;  // Analog input for vibration sensor
const int LED_PIN = 13;               // Built-in LED for feedback
const int CALIBRATION_LED = 12;       // LED for calibration mode

// Sensor variables
int baselineValue = 0;      // Baseline reading (calibrated zero)
int threshold = 100;        // Detection threshold
int currentValue = 0;       // Current sensor reading
bool isCalibrating = false; // Calibration flag
bool isMonitoring = false;  // Continuous monitoring flag
unsigned long lastReadTime = 0;
unsigned long monitorInterval = 100; // Monitoring interval in ms
const int READ_INTERVAL = 50; // Read sensor every 50ms

// Calibration settings
const int CALIBRATION_SAMPLES = 100;
const int CALIBRATION_DELAY = 10;

// Serial communication
String inputBuffer = "";

void setup() {
  Serial.begin(115200);
  delay(100);
  
  // Initialize pins
  pinMode(VIBRATION_SENSOR_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(CALIBRATION_LED, OUTPUT);
  
  digitalWrite(LED_PIN, LOW);
  digitalWrite(CALIBRATION_LED, LOW);
  
  // Send initial status
  delay(1000); // Wait for serial to stabilize
  sendStatus();
  
  // Initial calibration
  calibrateSensor();
}

void loop() {
  // Handle serial commands
  handleSerialInput();
  
  // Read sensor periodically
  unsigned long currentTime = millis();
  if (currentTime - lastReadTime >= READ_INTERVAL) {
    lastReadTime = currentTime;
    int rawValue = analogRead(VIBRATION_SENSOR_PIN);
    currentValue = abs(rawValue - baselineValue);
    
    // Visual feedback if vibration detected
    if (currentValue > threshold) {
      digitalWrite(LED_PIN, HIGH);
    } else {
      digitalWrite(LED_PIN, LOW);
    }
    
    // Send data if monitoring
    if (isMonitoring && (currentTime - lastReadTime >= monitorInterval)) {
      sendSensorData();
    }
  }
}

// Handle serial input
void handleSerialInput() {
  while (Serial.available()) {
    char c = Serial.read();
    
    if (c == '\n') {
      // Process complete message
      if (inputBuffer.length() > 0) {
        processCommand(inputBuffer);
        inputBuffer = "";
      }
    } else if (c != '\r') {
      inputBuffer += c;
    }
  }
}

// Process JSON command
void processCommand(String jsonStr) {
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, jsonStr);
  
  if (error) {
    sendError("Invalid JSON");
    return;
  }
  
  String action = doc["action"];
  
  if (action == "status") {
    sendStatus();
  } else if (action == "read_sensor") {
    sendSensorReading();
  } else if (action == "calibrate") {
    calibrateSensor();
    sendSuccess("Calibration completed", baselineValue);
  } else if (action == "set_threshold") {
    threshold = doc["value"];
    sendSuccess("Threshold updated", threshold);
  } else if (action == "start_monitoring") {
    monitorInterval = doc["interval"] | 100;
    isMonitoring = true;
    sendSuccess("Monitoring started", monitorInterval);
  } else if (action == "stop_monitoring") {
    isMonitoring = false;
    sendSuccess("Monitoring stopped", 0);
  } else {
    sendError("Unknown action: " + action);
  }
}

// Send status response
void sendStatus() {
  StaticJsonDocument<200> doc;
  doc["status"] = "online";
  doc["device_id"] = "vibration_sensor_01";
  doc["firmware_version"] = "2.0.0";
  doc["protocol"] = "serial";
  doc["baseline"] = baselineValue;
  doc["threshold"] = threshold;
  doc["uptime"] = millis();
  
  serializeJson(doc, Serial);
  Serial.println();
}

// Send sensor reading
void sendSensorReading() {
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
  
  serializeJson(doc, Serial);
  Serial.println();
}

// Send sensor data (for monitoring)
void sendSensorData() {
  int rawValue = analogRead(VIBRATION_SENSOR_PIN);
  int adjustedValue = abs(rawValue - baselineValue);
  
  StaticJsonDocument<200> doc;
  doc["type"] = "sensor_data";
  doc["value"] = adjustedValue;
  doc["raw_value"] = rawValue;
  doc["detected"] = (adjustedValue > threshold);
  doc["timestamp"] = millis();
  
  serializeJson(doc, Serial);
  Serial.println();
}

// Send success response
void sendSuccess(String message, int value) {
  StaticJsonDocument<200> doc;
  doc["success"] = true;
  doc["message"] = message;
  doc["value"] = value;
  
  serializeJson(doc, Serial);
  Serial.println();
}

// Send error response
void sendError(String error) {
  StaticJsonDocument<200> doc;
  doc["success"] = false;
  doc["error"] = error;
  
  serializeJson(doc, Serial);
  Serial.println();
}

// Calibrate sensor by taking average of multiple readings
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

