"""
Vibration Sensor Controller for Arduino Integration via WiFi HTTP REST API
Based on patterns from https://github.com/FujiiNoritsugu/try_openai_agent
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Optional, List, Callable
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
import time


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


class VibrationSensorControllerWiFi(BaseController):
    """Controller for Arduino vibration sensor via WiFi HTTP REST API"""
    
    def __init__(self, device_id: str, host: str, port: int = 80, timeout: float = 5.0):
        super().__init__(device_id)
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        self.session: Optional[aiohttp.ClientSession] = None
        self.sensor_threshold = 100  # Default threshold for vibration detection
        self.callbacks: List[Callable] = []
        self._monitoring_task = None
        self._running = False
        
    async def connect(self) -> bool:
        """Establish connection to Arduino vibration sensor via WiFi"""
        try:
            # Create HTTP session
            timeout_config = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout_config)
            
            # Test connection with status request
            async with self.session.get(f"{self.base_url}/status") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "online":
                        self.is_connected = True
                        self._running = True
                        self.logger.info(f"Connected to vibration sensor {self.device_id} at {self.host}:{self.port}")
                        self.logger.info(f"Device info: {data}")
                        return True
                else:
                    self.logger.error(f"Failed to connect: HTTP {response.status}")
                    await self.session.close()
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to connect to sensor {self.device_id}: {e}")
            if self.session:
                await self.session.close()
            self.is_connected = False
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from Arduino"""
        self._running = False
        
        # Cancel monitoring task if running
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
                
        # Close HTTP session
        if self.session:
            await self.session.close()
            
        self.session = None
        self.is_connected = False
        self.logger.info(f"Disconnected from sensor {self.device_id}")
        
    async def send_command(self, command: Dict) -> Optional[Dict]:
        """Send command to Arduino via HTTP"""
        if not self.is_connected or not self.session:
            self.logger.error("Not connected to sensor")
            return None
            
        try:
            action = command.get("action")
            
            if action == "status":
                return await self._get_status()
            elif action == "read_sensor":
                return await self._read_sensor()
            elif action == "calibrate":
                return await self._calibrate()
            elif action == "set_threshold":
                return await self._set_threshold(command.get("value", 100))
            elif action == "start_monitoring":
                return await self._start_monitoring(command.get("interval", 100))
            elif action == "stop_monitoring":
                return await self._stop_monitoring()
            else:
                self.logger.error(f"Unknown action: {action}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to send command: {e}")
            return None
            
    async def _get_status(self) -> Optional[Dict]:
        """Get device status"""
        try:
            async with self.session.get(f"{self.base_url}/status") as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
        return None
        
    async def _read_sensor(self) -> Optional[Dict]:
        """Read sensor data"""
        try:
            async with self.session.get(f"{self.base_url}/sensor") as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            self.logger.error(f"Failed to read sensor: {e}")
        return None
        
    async def _calibrate(self) -> Optional[Dict]:
        """Calibrate sensor"""
        try:
            async with self.session.post(f"{self.base_url}/calibrate") as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            self.logger.error(f"Failed to calibrate: {e}")
        return None
        
    async def _set_threshold(self, threshold: int) -> Optional[Dict]:
        """Set threshold value"""
        try:
            data = {"value": threshold}
            async with self.session.post(
                f"{self.base_url}/threshold",
                json=data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        self.sensor_threshold = threshold
                    return result
        except Exception as e:
            self.logger.error(f"Failed to set threshold: {e}")
        return None
        
    async def _start_monitoring(self, interval: int) -> Optional[Dict]:
        """Start monitoring"""
        # Cancel existing monitoring task if any
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
                
        # Start new monitoring task
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        
        return {"success": True, "message": "Monitoring started", "interval": interval}
        
    async def _stop_monitoring(self) -> Optional[Dict]:
        """Stop monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            
        return {"success": True, "message": "Monitoring stopped"}
        
    async def _monitor_loop(self) -> None:
        """Long polling loop for continuous monitoring"""
        while self._running and self.is_connected:
            try:
                # Use long polling endpoint
                async with self.session.get(
                    f"{self.base_url}/monitor",
                    timeout=aiohttp.ClientTimeout(total=35)  # Slightly longer than server timeout
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        await self._handle_sensor_broadcast(data)
                    elif response.status == 204:
                        # No new data, continue polling
                        pass
                    else:
                        self.logger.warning(f"Monitor request failed: HTTP {response.status}")
                        await asyncio.sleep(1)
                        
            except asyncio.TimeoutError:
                # Normal timeout, continue polling
                pass
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(1)
                
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
                    
    async def read_sensor_data(self) -> Optional[Dict]:
        """Read current vibration sensor data"""
        if not self.is_connected or not self.session:
            return None
            
        try:
            result = await self._read_sensor()
            
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
        result = await self._set_threshold(threshold)
        return result is not None and result.get("success", False)
        
    async def calibrate_sensor(self) -> bool:
        """Calibrate the vibration sensor"""
        result = await self._calibrate()
        return result is not None and result.get("success", False)
        
    def add_vibration_callback(self, callback: Callable) -> None:
        """Add callback for vibration events"""
        self.callbacks.append(callback)
        
    async def start_monitoring(self, interval: float = 0.1) -> None:
        """Start continuous monitoring of vibration sensor"""
        self.logger.info(f"Starting vibration monitoring")
        
        # Start monitoring with specified interval
        result = await self._start_monitoring(int(interval * 1000))
        
        if not result or not result.get("success"):
            self.logger.error("Failed to start monitoring")
            return
            
        # Keep the method running
        while self.is_connected and self._monitoring_task and not self._monitoring_task.done():
            await asyncio.sleep(1)
            
    async def stop_monitoring(self) -> None:
        """Stop continuous monitoring"""
        await self._stop_monitoring()


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


class VibrationSensorManagerWiFi:
    """Manager for multiple vibration sensors and actuators via WiFi"""
    
    def __init__(self):
        self.sensors: Dict[str, VibrationSensorControllerWiFi] = {}
        self.actuators: Dict[str, BaseController] = {}
        self.pattern_generator = VibrationPatternGenerator()
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def add_sensor(self, sensor_id: str, host: str, port: int = 80) -> bool:
        """Add a new vibration sensor via WiFi"""
        sensor = VibrationSensorControllerWiFi(sensor_id, host, port)
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
    manager = VibrationSensorManagerWiFi()
    
    # Add vibration sensor via WiFi
    # Replace with your Arduino's IP address
    await manager.add_sensor("sensor1", "192.168.1.100")  # Example IP
    
    # Add haptic actuator (example)
    # actuator = HapticActuator("actuator1", "192.168.1.101")
    # await manager.add_actuator(actuator)
    
    # Start monitoring
    try:
        await manager.start_monitoring_all()
    except KeyboardInterrupt:
        await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main()