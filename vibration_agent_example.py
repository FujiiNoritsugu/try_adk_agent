"""
Example usage of the vibration agent system
Demonstrates how to integrate vibration sensors with haptic feedback devices
"""

import asyncio
import logging
from vibration_sensor_controller import (
    VibrationSensorController, 
    VibrationSensorManager,
    VibrationPatternGenerator,
    VibrationLevel
)


# Example haptic actuator controller (implements same interface)
class HapticActuator(VibrationSensorController):
    """Example haptic feedback device controller"""
    
    async def send_vibration_pattern(self, pattern: dict) -> bool:
        """Send vibration pattern to haptic device"""
        return await self.send_command({
            "action": "vibrate",
            "pattern": pattern
        })


async def example_basic_usage():
    """Basic example: Connect to sensor and read data via Serial"""
    print("=== Basic Vibration Sensor Usage (Serial) ===")
    
    # Create sensor controller (auto-detect port)
    sensor = VibrationSensorController(
        device_id="sensor1"
        # port="/dev/ttyUSB0"  # Specify port if needed (Linux)
        # port="COM3"          # Specify port if needed (Windows)
    )
    
    # Connect to sensor
    if await sensor.connect():
        print("Connected to vibration sensor via Serial!")
        
        # Read sensor data
        for i in range(10):
            data = await sensor.read_sensor_data()
            if data:
                print(f"Vibration: {data['vibration_value']} - Level: {data['vibration_level'].name}")
            await asyncio.sleep(1)
            
        # Calibrate sensor
        print("\nCalibrating sensor...")
        if await sensor.calibrate_sensor():
            print("Calibration successful!")
            
        # Set threshold
        if await sensor.set_threshold(150):
            print("Threshold set to 150")
            
        await sensor.disconnect()
    else:
        print("Failed to connect to sensor")


async def example_vibration_monitoring():
    """Example: Monitor vibrations and trigger alerts"""
    print("\n=== Vibration Monitoring Example (Serial) ===")
    
    sensor = VibrationSensorController("sensor1")  # Auto-detect port
    
    # Define callback for vibration events
    async def vibration_detected(data):
        level = data["vibration_level"]
        value = data["vibration_value"]
        
        print(f"⚠️  Vibration detected! Level: {level.name}, Value: {value}")
        
        if level == VibrationLevel.EXTREME:
            print("🚨 EXTREME VIBRATION - Possible earthquake!")
        elif level == VibrationLevel.HIGH:
            print("⚡ HIGH VIBRATION - Machine fault detected!")
            
    # Add callback and connect
    sensor.add_vibration_callback(vibration_detected)
    
    if await sensor.connect():
        print("Starting vibration monitoring (press Ctrl+C to stop)...")
        try:
            await sensor.start_monitoring(interval=0.1)
        except KeyboardInterrupt:
            print("\nStopping monitoring...")
            
        await sensor.disconnect()


async def example_sensor_actuator_system():
    """Example: Complete system with sensors and haptic feedback"""
    print("\n=== Sensor-Actuator System Example (Serial) ===")
    
    # Create manager
    manager = VibrationSensorManager()
    
    # Add vibration sensors
    sensors = [
        {"id": "floor_sensor"},  # Auto-detect
        {"id": "machine_sensor", "port": "/dev/ttyUSB1"},  # Specific port
    ]
    
    for sensor_config in sensors:
        success = await manager.add_sensor(
            sensor_config["id"], 
            sensor_config.get("port")
        )
        if success:
            print(f"✓ Added sensor: {sensor_config['id']}")
            
    # Add haptic actuators (example)
    actuator = HapticActuator("haptic_glove", "/dev/ttyUSB2")
    if await manager.add_actuator(actuator):
        print("✓ Added haptic actuator: haptic_glove")
        
    # Custom event handler
    original_handler = manager.handle_vibration_event
    
    async def enhanced_handler(sensor_data):
        # Call original handler
        await original_handler(sensor_data)
        
        # Add custom logic
        if sensor_data["device_id"] == "machine_sensor":
            level = sensor_data["vibration_level"]
            if level in [VibrationLevel.HIGH, VibrationLevel.EXTREME]:
                print(f"🔧 Machine sensor alert! Sending maintenance notification...")
                # Here you could send alerts, log to database, etc.
                
    # Replace handler
    manager.handle_vibration_event = enhanced_handler
    
    # Start monitoring
    print("\nStarting sensor-actuator system (press Ctrl+C to stop)...")
    try:
        await manager.start_monitoring_all()
    except KeyboardInterrupt:
        print("\nShutting down system...")
        
    await manager.shutdown()


async def example_custom_patterns():
    """Example: Using custom vibration patterns"""
    print("\n=== Custom Vibration Patterns Example ===")
    
    generator = VibrationPatternGenerator()
    
    # Show different vibration levels
    print("Vibration patterns by level:")
    for level in VibrationLevel:
        pattern = generator.create_response_pattern(level)
        print(f"\n{level.name}:")
        print(f"  Steps: {len(pattern['steps'])}")
        print(f"  Repeat: {pattern['repeat_count']} times")
        if pattern['steps']:
            print(f"  Intensity range: {min(s['intensity'] for s in pattern['steps'])} - "
                  f"{max(s['intensity'] for s in pattern['steps'])}")
            
    # Show alert patterns
    print("\n\nAlert patterns:")
    alerts = ["earthquake", "machine_fault", "proximity_warning"]
    for alert in alerts:
        pattern = generator.create_alert_pattern(alert)
        print(f"\n{alert.upper()}:")
        print(f"  Duration: {sum(s['duration_ms'] for s in pattern['steps'])}ms per cycle")
        print(f"  Cycles: {pattern['repeat_count']}")
        print(f"  Total duration: ~{sum(s['duration_ms'] for s in pattern['steps']) * pattern['repeat_count']}ms")


async def example_websocket_client():
    """Example: Connect to WebSocket server for real-time data"""
    print("\n=== WebSocket Client Example ===")
    
    # This would connect to the websocket server
    # See vibration_websocket_server.py for the server implementation
    print("WebSocket client example - see vibration_websocket_server.py")
    print("Run the server with: python vibration_websocket_server.py")
    print("Then use the test_client() function in that file")


async def main():
    """Run all examples"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run examples
    examples = [
        example_basic_usage,
        example_vibration_monitoring,
        example_sensor_actuator_system,
        example_custom_patterns,
        example_websocket_client
    ]
    
    for example in examples:
        try:
            await example()
        except Exception as e:
            print(f"Error in {example.__name__}: {e}")
        print("\n" + "="*50 + "\n")
        
    print("All examples completed!")


if __name__ == "__main__":
    # Run specific example or all
    import sys
    
    if len(sys.argv) > 1:
        example_name = sys.argv[1]
        examples_map = {
            "basic": example_basic_usage,
            "monitoring": example_vibration_monitoring,
            "system": example_sensor_actuator_system,
            "patterns": example_custom_patterns,
            "websocket": example_websocket_client
        }
        
        if example_name in examples_map:
            asyncio.run(examples_map[example_name]())
        else:
            print(f"Unknown example: {example_name}")
            print(f"Available: {', '.join(examples_map.keys())}")
    else:
        asyncio.run(main())