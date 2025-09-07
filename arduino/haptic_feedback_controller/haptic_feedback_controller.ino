/*
 * Haptic Feedback Controller for Arduino Uno R4 WiFi
 * 
 * This sketch controls a vibration module via HTTP REST API
 * Compatible with the Python vibration_agent system
 * 
 * Hardware:
 * - Arduino Uno R4 WiFi
 * - Vibration module connected to pin 9 (PWM)
 * 
 * API Endpoints:
 * - GET /status - Get device status
 * - POST /pattern - Execute vibration pattern
 * - POST /stop - Stop vibration
 */

#include <WiFiS3.h>
#include <ArduinoJson.h>

// Pin configuration
const int VIBRATION_PIN = 9;  // PWM pin for vibration control

// WiFi credentials - Create config.h with your credentials
#include "config.h"
// config.h should contain:
// #define WIFI_SSID "your_wifi_ssid"
// #define WIFI_PASSWORD "your_wifi_password"

// Server configuration
WiFiServer server(80);

// Vibration controller class
class VibrationController {
private:
  struct VibrationStep {
    int intensity;      // 0-100 (percentage)
    unsigned long duration;  // milliseconds
  };
  
  static const int MAX_STEPS = 10;
  VibrationStep pattern[MAX_STEPS];
  int numSteps;
  int currentStep;
  unsigned long stepStartTime;
  unsigned long intervalTime;
  int repeatCount;
  int currentRepeat;
  bool isRunning;
  
public:
  VibrationController() {
    reset();
    pinMode(VIBRATION_PIN, OUTPUT);
  }
  
  void reset() {
    numSteps = 0;
    currentStep = 0;
    stepStartTime = 0;
    intervalTime = 0;
    repeatCount = 0;
    currentRepeat = 0;
    isRunning = false;
    analogWrite(VIBRATION_PIN, 0);
  }
  
  bool setPattern(JsonDocument& doc) {
    reset();
    
    JsonArray steps = doc["steps"];
    if (!steps || steps.size() == 0) {
      return false;
    }
    
    numSteps = min((int)steps.size(), MAX_STEPS);
    
    for (int i = 0; i < numSteps; i++) {
      pattern[i].intensity = steps[i]["intensity"] | 0;
      pattern[i].duration = steps[i]["duration"] | 100;
      
      // Validate intensity
      pattern[i].intensity = constrain(pattern[i].intensity, 0, 100);
    }
    
    intervalTime = doc["interval"] | 50;
    repeatCount = doc["repeat_count"] | 1;
    currentRepeat = 0;
    
    return true;
  }
  
  void startVibration() {
    if (numSteps > 0) {
      isRunning = true;
      currentStep = 0;
      currentRepeat = 0;
      stepStartTime = millis();
      applyStep(0);
    }
  }
  
  void stopVibration() {
    isRunning = false;
    analogWrite(VIBRATION_PIN, 0);
  }
  
  bool isVibrating() {
    return isRunning;
  }
  
  void update() {
    if (!isRunning || numSteps == 0) return;
    
    unsigned long currentTime = millis();
    unsigned long elapsed = currentTime - stepStartTime;
    
    // Check if current step is complete
    if (elapsed >= pattern[currentStep].duration) {
      // Turn off vibration during interval
      analogWrite(VIBRATION_PIN, 0);
      
      // Check if interval period is complete
      if (elapsed >= pattern[currentStep].duration + intervalTime) {
        currentStep++;
        
        // Check if pattern is complete
        if (currentStep >= numSteps) {
          currentRepeat++;
          
          if (currentRepeat >= repeatCount) {
            // Pattern complete
            stopVibration();
            return;
          } else {
            // Repeat pattern
            currentStep = 0;
          }
        }
        
        // Start next step
        stepStartTime = currentTime;
        applyStep(currentStep);
      }
    }
  }
  
private:
  void applyStep(int stepIndex) {
    if (stepIndex < numSteps) {
      int pwmValue = map(pattern[stepIndex].intensity, 0, 100, 0, 255);
      analogWrite(VIBRATION_PIN, pwmValue);
    }
  }
};

// Global instances
VibrationController vibrationController;
String currentLine = "";

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("Haptic Feedback Controller Starting...");
  
  // Initialize vibration pin
  pinMode(VIBRATION_PIN, OUTPUT);
  analogWrite(VIBRATION_PIN, 0);
  
  // Connect to WiFi
  connectToWiFi();
  
  // Start server
  server.begin();
  Serial.print("Server started at http://");
  Serial.print(WiFi.localIP());
  Serial.println("/");
}

void loop() {
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected, reconnecting...");
    connectToWiFi();
  }
  
  // Handle client requests
  WiFiClient client = server.available();
  if (client) {
    handleClient(client);
  }
  
  // Update vibration controller
  vibrationController.update();
}

void connectToWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void handleClient(WiFiClient& client) {
  String method = "";
  String path = "";
  String body = "";
  bool isPost = false;
  int contentLength = 0;
  
  while (client.connected()) {
    if (client.available()) {
      String line = client.readStringUntil('\n');
      line.trim();
      
      // Parse request line
      if (method == "") {
        int firstSpace = line.indexOf(' ');
        int secondSpace = line.indexOf(' ', firstSpace + 1);
        
        if (firstSpace > 0 && secondSpace > firstSpace) {
          method = line.substring(0, firstSpace);
          path = line.substring(firstSpace + 1, secondSpace);
          isPost = (method == "POST");
        }
      }
      
      // Parse headers
      if (line.startsWith("Content-Length:")) {
        contentLength = line.substring(15).toInt();
      }
      
      // Empty line indicates end of headers
      if (line.length() == 0) {
        // Read body for POST requests
        if (isPost && contentLength > 0) {
          char* buffer = new char[contentLength + 1];
          client.readBytes(buffer, contentLength);
          buffer[contentLength] = '\0';
          body = String(buffer);
          delete[] buffer;
        }
        
        // Process request
        processRequest(client, method, path, body);
        break;
      }
    }
  }
  
  client.stop();
}

void processRequest(WiFiClient& client, String& method, String& path, String& body) {
  Serial.print("Request: ");
  Serial.print(method);
  Serial.print(" ");
  Serial.println(path);
  
  if (path == "/status" && method == "GET") {
    handleStatus(client);
  } else if (path == "/pattern" && method == "POST") {
    handlePattern(client, body);
  } else if (path == "/stop" && method == "POST") {
    handleStop(client);
  } else {
    send404(client);
  }
}

void handleStatus(WiFiClient& client) {
  StaticJsonDocument<200> doc;
  doc["status"] = "ready";
  doc["is_vibrating"] = vibrationController.isVibrating();
  doc["wifi_connected"] = (WiFi.status() == WL_CONNECTED);
  doc["ip_address"] = WiFi.localIP().toString();
  doc["firmware_version"] = "1.0.0";
  
  sendJsonResponse(client, doc);
}

void handlePattern(WiFiClient& client, String& body) {
  StaticJsonDocument<1024> doc;
  DeserializationError error = deserializeJson(doc, body);
  
  if (error) {
    sendError(client, "Invalid JSON: " + String(error.c_str()));
    return;
  }
  
  if (!vibrationController.setPattern(doc)) {
    sendError(client, "Invalid pattern format");
    return;
  }
  
  vibrationController.startVibration();
  
  StaticJsonDocument<64> response;
  response["status"] = "ok";
  sendJsonResponse(client, response);
}

void handleStop(WiFiClient& client) {
  vibrationController.stopVibration();
  
  StaticJsonDocument<64> doc;
  doc["status"] = "stopped";
  sendJsonResponse(client, doc);
}

void sendJsonResponse(WiFiClient& client, JsonDocument& doc) {
  String response;
  serializeJson(doc, response);
  
  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: application/json");
  client.println("Connection: close");
  client.println("Access-Control-Allow-Origin: *");
  client.print("Content-Length: ");
  client.println(response.length());
  client.println();
  client.print(response);
}

void sendError(WiFiClient& client, String message) {
  StaticJsonDocument<128> doc;
  doc["status"] = "error";
  doc["message"] = message;
  
  String response;
  serializeJson(doc, response);
  
  client.println("HTTP/1.1 400 Bad Request");
  client.println("Content-Type: application/json");
  client.println("Connection: close");
  client.println("Access-Control-Allow-Origin: *");
  client.print("Content-Length: ");
  client.println(response.length());
  client.println();
  client.print(response);
}

void send404(WiFiClient& client) {
  client.println("HTTP/1.1 404 Not Found");
  client.println("Content-Type: text/plain");
  client.println("Connection: close");
  client.println();
  client.println("404 Not Found");
}