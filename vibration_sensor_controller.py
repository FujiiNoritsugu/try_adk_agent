"""
Vibration Sensor Controller for Arduino Integration via Serial Communication
Based on patterns from https://github.com/FujiiNoritsugu/try_openai_agent
"""

import asyncio
import serial
import serial.tools.list_ports
import json
import logging
from typing import Dict, Optional, List, Callable
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
import time
from asyncio import Queue


class VibrationLevel(Enum):
    """Vibration intensity levels"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    EXTREME = 4


class BaseController(ABC):
    """Abstract base controller for device communication"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{device_id}")
        self.is_connected = False
        
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to device"""
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from device"""
        pass
        
    @abstractmethod
    async def send_command(self, command: Dict) -> Optional[Dict]:
        """Send command to device"""
        pass


class VibrationSensorController(BaseController):
    """Controller for Arduino vibration sensor via Serial"""
    
    def __init__(self, device_id: str, port: str = None, baudrate: int = 115200, timeout: float = 1.0):
        super().__init__(device_id)
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection: Optional[serial.Serial] = None
        self.sensor_threshold = 100  # Default threshold for vibration detection
        self.callbacks: List[Callable] = []
        self._read_queue = Queue()
        self._read_task = None
        self._running = False
        
    async def connect(self) -> bool:
        """Establish connection to Arduino vibration sensor via Serial"""
        try:
            # Auto-detect Arduino port if not specified
            if not self.port:
                self.port = self._find_arduino_port()
                if not self.port:
                    self.logger.error("No Arduino found. Please specify port manually.")
                    return False
                    
            # Open serial connection
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            
            # Wait for Arduino to reset
            await asyncio.sleep(2)
            
            # Clear any initial data
            self.serial_connection.reset_input_buffer()
            
            # Send status request to verify connection
            await self._send_serial_command({"action": "status"})
            
            # Wait for response
            response = await self._read_serial_response()
            if response and response.get("status") == "online":
                self.is_connected = True
                self._running = True
                # Start background task to read serial data
                self._read_task = asyncio.create_task(self._serial_read_loop())
                self.logger.info(f"Connected to vibration sensor {self.device_id} on {self.port}")
                self.logger.info(f"Sensor status: {response}")
                return True
            else:
                self.logger.error(f"Invalid response from sensor: {response}")
                self.serial_connection.close()
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to sensor {self.device_id}: {e}")
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            self.is_connected = False
            return False
            
    def _find_arduino_port(self) -> Optional[str]:
        """Auto-detect Arduino port"""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # Check for common Arduino identifiers
            if "Arduino" in port.description or "CH340" in port.description or "USB" in port.description:
                self.logger.info(f"Found Arduino on port: {port.device}")
                return port.device
        return None
        
    async def _send_serial_command(self, command: Dict) -> None:
        """Send command to Arduino via serial"""
        if not self.serial_connection or not self.serial_connection.is_open:
            raise Exception("Serial connection not open")
            
        # Convert to JSON and add newline delimiter
        message = json.dumps(command) + '\n'
        self.serial_connection.write(message.encode('utf-8'))
        self.serial_connection.flush()
        
    async def _read_serial_response(self, timeout: float = 2.0) -> Optional[Dict]:
        """Read response from serial with timeout"""
        try:
            response = await asyncio.wait_for(self._read_queue.get(), timeout=timeout)
            return response
        except asyncio.TimeoutError:
            return None
            
    async def _serial_read_loop(self) -> None:
        """Background task to continuously read serial data"""
        buffer = ""
        
        while self._running and self.serial_connection and self.serial_connection.is_open:
            try:
                # Read available bytes
                if self.serial_connection.in_waiting > 0:
                    data = self.serial_connection.read(self.serial_connection.in_waiting).decode('utf-8', errors='ignore')
                    buffer += data
                    
                    # Process complete messages (newline delimited)
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line:
                            try:
                                message = json.loads(line)
                                await self._read_queue.put(message)
                                
                                # Handle sensor data broadcasts
                                if message.get("type") == "sensor_data":
                                    await self._handle_sensor_broadcast(message)
                                    
                            except json.JSONDecodeError:
                                self.logger.warning(f"Invalid JSON received: {line}")
                                
                await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
                
            except Exception as e:
                self.logger.error(f"Error in serial read loop: {e}")
                await asyncio.sleep(0.1)
                
    async def _handle_sensor_broadcast(self, data: Dict) -> None:
        """Handle broadcasted sensor data"""
        sensor_data = {
            "timestamp": datetime.now().isoformat(),
            "device_id": self.device_id,
            "vibration_value": data.get("value", 0),
            "vibration_level": self._calculate_vibration_level(data.get("value", 0)),
            "raw_data": data
        }
        
        # Trigger callbacks if threshold exceeded
        if sensor_data["vibration_value"] > self.sensor_threshold:
            for callback in self.callbacks:
                if asyncio.iscoroutinefunction(callback):
                    await callback(sensor_data)
                else:
                    callback(sensor_data)
            
    async def disconnect(self) -> None:
        """Disconnect from Arduino"""
        self._running = False
        
        # Cancel read task
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
                
        # Close serial connection
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            
        self.serial_connection = None
        self.is_connected = False
        self.logger.info(f"Disconnected from sensor {self.device_id}")
        
    async def send_command(self, command: Dict) -> Optional[Dict]:
        """Send command to Arduino via Serial"""
        if not self.is_connected or not self.serial_connection:
            self.logger.error("Not connected to sensor")
            return None
            
        try:
            # Clear any pending responses
            while not self._read_queue.empty():
                self._read_queue.get_nowait()
                
            # Send command
            await self._send_serial_command(command)
            
            # Wait for response
            response = await self._read_serial_response()
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to send command: {e}")
            return None
            
    async def read_sensor_data(self) -> Optional[Dict]:
        """Read current vibration sensor data"""
        if not self.is_connected or not self.serial_connection:
            return None
            
        try:
            # Request sensor data
            result = await self.send_command({"action": "read_sensor"})
            
            if result and "value" in result:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "device_id": self.device_id,
                    "vibration_value": result.get("value", 0),
                    "vibration_level": self._calculate_vibration_level(result.get("value", 0)),
                    "raw_data": result
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to read sensor data: {e}")
            return None
            
    def _calculate_vibration_level(self, value: int) -> VibrationLevel:
        """Calculate vibration level from raw sensor value"""
        if value < 50:
            return VibrationLevel.NONE
        elif value < 200:
            return VibrationLevel.LOW
        elif value < 500:
            return VibrationLevel.MEDIUM
        elif value < 800:
            return VibrationLevel.HIGH
        else:
            return VibrationLevel.EXTREME
            
    async def set_threshold(self, threshold: int) -> bool:
        """Set vibration detection threshold"""
        result = await self.send_command({
            "action": "set_threshold",
            "value": threshold
        })
        if result and result.get("success"):
            self.sensor_threshold = threshold
            return True
        return False
        
    async def calibrate_sensor(self) -> bool:
        """Calibrate the vibration sensor"""
        result = await self.send_command({"action": "calibrate"})
        return result is not None and result.get("success", False)
        
    def add_vibration_callback(self, callback: Callable) -> None:
        """Add callback for vibration events"""
        self.callbacks.append(callback)
        
    async def start_monitoring(self, interval: float = 0.1) -> None:
        """Start continuous monitoring of vibration sensor"""
        self.logger.info(f"Starting vibration monitoring")
        
        # Send command to start continuous monitoring on Arduino
        result = await self.send_command({
            "action": "start_monitoring",
            "interval": int(interval * 1000)  # Convert to milliseconds
        })
        
        if not result or not result.get("success"):
            self.logger.error("Failed to start monitoring on Arduino")
            return
            
        # The Arduino will now broadcast sensor data automatically
        # Callbacks will be triggered by _handle_sensor_broadcast in the read loop
        
        # Keep the method running
        while self.is_connected:
            await asyncio.sleep(1)
            
    async def stop_monitoring(self) -> None:
        """Stop continuous monitoring"""
        await self.send_command({"action": "stop_monitoring"})


class VibrationPatternGenerator:
    """Generate vibration patterns based on sensor input"""
    
    @staticmethod
    def create_response_pattern(vibration_level: VibrationLevel) -> Dict:
        """Create haptic response pattern based on detected vibration level"""
        patterns = {
            VibrationLevel.NONE: {
                "steps": [],
                "interval_ms": 0,
                "repeat_count": 0
            },
            VibrationLevel.LOW: {
                "steps": [
                    {"intensity": 0.3, "duration_ms": 100},
                    {"intensity": 0.0, "duration_ms": 200}
                ],
                "interval_ms": 50,
                "repeat_count": 2
            },
            VibrationLevel.MEDIUM: {
                "steps": [
                    {"intensity": 0.6, "duration_ms": 150},
                    {"intensity": 0.0, "duration_ms": 100},
                    {"intensity": 0.4, "duration_ms": 100}
                ],
                "interval_ms": 50,
                "repeat_count": 3
            },
            VibrationLevel.HIGH: {
                "steps": [
                    {"intensity": 0.9, "duration_ms": 200},
                    {"intensity": 0.0, "duration_ms": 50},
                    {"intensity": 0.7, "duration_ms": 150}
                ],
                "interval_ms": 30,
                "repeat_count": 4
            },
            VibrationLevel.EXTREME: {
                "steps": [
                    {"intensity": 1.0, "duration_ms": 300},
                    {"intensity": 0.0, "duration_ms": 50},
                    {"intensity": 1.0, "duration_ms": 300}
                ],
                "interval_ms": 20,
                "repeat_count": 5
            }
        }
        
        return patterns.get(vibration_level, patterns[VibrationLevel.NONE])
        
    @staticmethod
    def create_alert_pattern(alert_type: str) -> Dict:
        """Create specific alert patterns"""
        alerts = {
            "earthquake": {
                "steps": [
                    {"intensity": 1.0, "duration_ms": 500},
                    {"intensity": 0.0, "duration_ms": 100},
                    {"intensity": 1.0, "duration_ms": 500}
                ],
                "interval_ms": 10,
                "repeat_count": 10
            },
            "machine_fault": {
                "steps": [
                    {"intensity": 0.8, "duration_ms": 100},
                    {"intensity": 0.0, "duration_ms": 100}
                ],
                "interval_ms": 50,
                "repeat_count": 20
            },
            "proximity_warning": {
                "steps": [
                    {"intensity": 0.5, "duration_ms": 200},
                    {"intensity": 0.7, "duration_ms": 200},
                    {"intensity": 1.0, "duration_ms": 200}
                ],
                "interval_ms": 100,
                "repeat_count": 3
            }
        }
        
        return alerts.get(alert_type, alerts["proximity_warning"])


class VibrationSensorManager:
    """Manager for multiple vibration sensors and actuators"""
    
    def __init__(self):
        self.sensors: Dict[str, VibrationSensorController] = {}
        self.actuators: Dict[str, BaseController] = {}
        self.pattern_generator = VibrationPatternGenerator()
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def add_sensor(self, sensor_id: str, port: str = None, baudrate: int = 115200) -> bool:
        """Add a new vibration sensor via serial port"""
        sensor = VibrationSensorController(sensor_id, port, baudrate)
        if await sensor.connect():
            self.sensors[sensor_id] = sensor
            # Add callback for vibration events
            sensor.add_vibration_callback(self.handle_vibration_event)
            return True
        return False
        
    async def add_actuator(self, actuator: BaseController) -> bool:
        """Add a haptic actuator device"""
        if await actuator.connect():
            self.actuators[actuator.device_id] = actuator
            return True
        return False
        
    async def handle_vibration_event(self, sensor_data: Dict) -> None:
        """Handle vibration detection event"""
        self.logger.info(f"Vibration detected: {sensor_data}")
        
        # Generate response pattern based on vibration level
        pattern = self.pattern_generator.create_response_pattern(
            sensor_data["vibration_level"]
        )
        
        # Send pattern to all connected actuators
        await self.send_pattern_to_actuators(pattern)
        
    async def send_pattern_to_actuators(self, pattern: Dict) -> None:
        """Send vibration pattern to all connected actuators"""
        tasks = []
        for actuator in self.actuators.values():
            if actuator.is_connected:
                tasks.append(actuator.send_command({
                    "action": "vibrate",
                    "pattern": pattern
                }))
                
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Failed to send pattern: {result}")
                    
    async def start_monitoring_all(self) -> None:
        """Start monitoring all connected sensors"""
        tasks = []
        for sensor in self.sensors.values():
            tasks.append(sensor.start_monitoring())
            
        await asyncio.gather(*tasks)
        
    async def shutdown(self) -> None:
        """Shutdown all connections"""
        # Disconnect sensors
        for sensor in self.sensors.values():
            await sensor.disconnect()
            
        # Disconnect actuators
        for actuator in self.actuators.values():
            await actuator.disconnect()


# Example usage
async def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create manager
    manager = VibrationSensorManager()
    
    # Add vibration sensor (auto-detect port or specify like "COM3" or "/dev/ttyUSB0")
    await manager.add_sensor("sensor1")  # Auto-detect
    # await manager.add_sensor("sensor1", "COM3")  # Windows
    # await manager.add_sensor("sensor1", "/dev/ttyUSB0")  # Linux
    
    # Add haptic actuator (example)
    # actuator = HapticActuator("actuator1", "/dev/ttyUSB1")
    # await manager.add_actuator(actuator)
    
    # Start monitoring
    try:
        await manager.start_monitoring_all()
    except KeyboardInterrupt:
        await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())