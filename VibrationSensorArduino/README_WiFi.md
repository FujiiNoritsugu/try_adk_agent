# Vibration Sensor Arduino WiFi Setup

This guide explains how to use the vibration sensor with WiFi communication instead of Serial/USB.

## Hardware Requirements

- **ESP8266** (NodeMCU, Wemos D1 Mini, etc.) or **ESP32** board
- Vibration sensor module
- LEDs (optional)

## Software Requirements

- Arduino IDE with ESP8266/ESP32 board support
- Python 3.8+ with required packages (`aiohttp`, `asyncio`)

## Arduino Setup

1. **Install Board Support**
   - For ESP8266: Add `http://arduino.esp8266.com/stable/package_esp8266com_index.json` to Board Manager URLs
   - For ESP32: Add `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`

2. **Install Libraries**
   - ArduinoJson (via Library Manager)

3. **Configure WiFi Credentials**
   Open `VibrationSensorArduinoWiFi.ino` and update:
   ```cpp
   const char* ssid = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";
   ```

4. **Upload Sketch**
   - Select your board (e.g., "NodeMCU 1.0" or "ESP32 Dev Module")
   - Upload the sketch
   - Open Serial Monitor to see the IP address

## Python Setup

1. **Install Dependencies**
   ```bash
   pip install aiohttp asyncio
   ```

2. **Update IP Address**
   In your Python scripts, update the Arduino IP address:
   ```python
   ARDUINO_IP = "192.168.1.100"  # Your Arduino's IP
   ```

## HTTP REST API Endpoints

The Arduino provides these HTTP endpoints:

- **GET /status** - Get device status and information
- **GET /sensor** - Read current sensor value
- **POST /calibrate** - Calibrate the sensor
- **POST /threshold** - Set detection threshold
  ```json
  {"value": 150}
  ```
- **GET /monitor** - Long polling for continuous data

## Usage Examples

### Basic Connection Test
```python
from vibration_sensor_controller_wifi import VibrationSensorControllerWiFi

controller = VibrationSensorControllerWiFi("sensor1", "192.168.1.100")
await controller.connect()
status = await controller.send_command({"action": "status"})
print(status)
```

### With MCP Server
Update `agent_mcp/agent.py` to use the WiFi version:
```python
# Use WiFi-based vibration server
"vibration_agent": {
    "command": "python",
    "args": ["-m", "mcp_servers.vibration_server_wifi"],
    "env": {}
}
```

### Initialize Arduino in MCP
```python
# In your agent, initialize with IP address
result = await mcp.call_tool(
    "vibration_agent",
    "initialize_arduino",
    arguments={"host": "192.168.1.100", "port": 80}
)
```

## Troubleshooting

1. **Cannot Connect**
   - Check WiFi credentials
   - Ensure Arduino and computer are on same network
   - Try pinging the Arduino IP
   - Check firewall settings

2. **Slow Response**
   - WiFi signal strength (check RSSI in status)
   - Network congestion
   - Increase timeout values

3. **Connection Drops**
   - Add WiFi reconnection logic
   - Check power supply stability
   - Monitor heap memory on ESP8266

## Advantages of WiFi over Serial

- Wireless operation
- Multiple device support
- Remote monitoring
- No USB cable required
- Can be accessed from multiple clients

## Limitations

- Requires WiFi network
- Higher latency than Serial
- Power consumption
- Limited by network bandwidth

## Security Note

This implementation uses HTTP without encryption. For production use, consider:
- Using HTTPS with SSL/TLS
- Adding authentication
- Restricting network access
- Using a dedicated IoT network