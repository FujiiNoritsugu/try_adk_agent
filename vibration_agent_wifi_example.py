#!/usr/bin/env python3
"""
Example script for using vibration agent with WiFi-based Arduino communication
"""

import asyncio
import logging
from vibration_sensor_controller_wifi import VibrationSensorManagerWiFi, VibrationSensorControllerWiFi

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_wifi_connection():
    """Test basic WiFi connection to Arduino"""
    # Replace with your Arduino's IP address
    ARDUINO_IP = "192.168.1.100"  # Change this to your Arduino's IP
    
    controller = VibrationSensorControllerWiFi("test_sensor", ARDUINO_IP)
    
    print(f"Connecting to Arduino at {ARDUINO_IP}...")
    connected = await controller.connect()
    
    if connected:
        print("✓ Connected successfully!")
        
        # Get status
        print("\nGetting device status...")
        status = await controller.send_command({"action": "status"})
        print(f"Status: {status}")
        
        # Read sensor
        print("\nReading sensor data...")
        sensor_data = await controller.read_sensor_data()
        print(f"Sensor data: {sensor_data}")
        
        # Calibrate
        print("\nCalibrating sensor...")
        calibrated = await controller.calibrate_sensor()
        print(f"Calibration result: {calibrated}")
        
        # Set threshold
        print("\nSetting threshold to 150...")
        threshold_set = await controller.set_threshold(150)
        print(f"Threshold set: {threshold_set}")
        
        # Disconnect
        await controller.disconnect()
        print("\n✓ Disconnected successfully!")
    else:
        print("✗ Failed to connect!")

async def test_continuous_monitoring():
    """Test continuous monitoring with callbacks"""
    # Replace with your Arduino's IP address
    ARDUINO_IP = "192.168.1.100"  # Change this to your Arduino's IP
    
    manager = VibrationSensorManagerWiFi()
    
    # Define callback for vibration events
    async def vibration_callback(data):
        print(f"\n🔔 Vibration detected: Level={data['vibration_level'].name}, Value={data['vibration_value']}")
    
    # Add sensor
    print(f"Adding sensor at {ARDUINO_IP}...")
    added = await manager.add_sensor("sensor1", ARDUINO_IP)
    
    if added:
        print("✓ Sensor added successfully!")
        
        # Add custom callback
        manager.sensors["sensor1"].add_vibration_callback(vibration_callback)
        
        # Start monitoring
        print("\nStarting continuous monitoring (press Ctrl+C to stop)...")
        try:
            await manager.start_monitoring_all()
        except KeyboardInterrupt:
            print("\n\nStopping monitoring...")
            await manager.shutdown()
            print("✓ Shutdown complete!")
    else:
        print("✗ Failed to add sensor!")

async def test_pattern_sending():
    """Test sending vibration patterns"""
    # Replace with your Arduino's IP address
    ARDUINO_IP = "192.168.1.100"  # Change this to your Arduino's IP
    
    controller = VibrationSensorControllerWiFi("test_sensor", ARDUINO_IP)
    
    print(f"Connecting to Arduino at {ARDUINO_IP}...")
    connected = await controller.connect()
    
    if connected:
        print("✓ Connected successfully!")
        
        # Test different patterns
        patterns = [
            ("pulse", 0.7, 1000, 3),
            ("wave", 0.8, 1500, 2),
            ("burst", 0.9, 500, 5),
            ("fade", 0.6, 2000, 1)
        ]
        
        for pattern_type, intensity, duration, repeat in patterns:
            print(f"\nSending {pattern_type} pattern...")
            
            # Create pattern
            if pattern_type == "pulse":
                steps = [
                    {"intensity": intensity, "duration_ms": duration // 2},
                    {"intensity": 0.0, "duration_ms": duration // 2}
                ]
            elif pattern_type == "wave":
                steps = [
                    {"intensity": intensity * 0.3, "duration_ms": duration // 3},
                    {"intensity": intensity * 0.7, "duration_ms": duration // 3},
                    {"intensity": intensity, "duration_ms": duration // 3}
                ]
            elif pattern_type == "burst":
                steps = [
                    {"intensity": intensity, "duration_ms": 100},
                    {"intensity": 0.0, "duration_ms": 50}
                ]
            else:  # fade
                steps = [
                    {"intensity": intensity, "duration_ms": duration // 2},
                    {"intensity": intensity * 0.5, "duration_ms": duration // 4},
                    {"intensity": intensity * 0.2, "duration_ms": duration // 4}
                ]
            
            pattern = {
                "steps": steps,
                "interval_ms": 50,
                "repeat_count": repeat
            }
            
            result = await controller.send_command({
                "action": "vibrate",
                "pattern": pattern
            })
            
            print(f"Result: {result}")
            await asyncio.sleep(3)  # Wait between patterns
        
        await controller.disconnect()
        print("\n✓ Disconnected successfully!")
    else:
        print("✗ Failed to connect!")

async def main():
    """Main function to run examples"""
    print("=== Vibration Agent WiFi Example ===\n")
    print("Make sure to:")
    print("1. Upload VibrationSensorArduinoWiFi.ino to your ESP8266/ESP32")
    print("2. Update WiFi credentials in the Arduino sketch")
    print("3. Update ARDUINO_IP in this script with your Arduino's IP address")
    print("4. Ensure your computer and Arduino are on the same network\n")
    
    while True:
        print("\nSelect an option:")
        print("1. Test basic WiFi connection")
        print("2. Test continuous monitoring")
        print("3. Test vibration patterns")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == "1":
            await test_wifi_connection()
        elif choice == "2":
            await test_continuous_monitoring()
        elif choice == "3":
            await test_pattern_sending()
        elif choice == "4":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    asyncio.run(main())