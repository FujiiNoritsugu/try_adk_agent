"""
Arduino haptic feedback controller implementation
"""

import asyncio
import json
import logging
from typing import Dict, Optional, Any
import aiohttp

from .base_controller import BaseController
from .vibration_patterns import VibrationPattern


class ArduinoController(BaseController):
    """Controller for Arduino-based haptic feedback device"""
    
    def __init__(self, device_id: str, host: str, port: int = 80, 
                 retry_count: int = 3, timeout: float = 5.0):
        """
        Initialize Arduino controller
        
        Args:
            device_id: Unique identifier for the device
            host: IP address or hostname of Arduino
            port: HTTP port (default 80)
            retry_count: Number of retry attempts
            timeout: Request timeout in seconds
        """
        base_url = f"http://{host}:{port}"
        super().__init__(device_id, base_url, retry_count, timeout)
        self.host = host
        self.port = port
        
    async def connect(self) -> bool:
        """Connect to Arduino device"""
        try:
            await self._create_session()
            
            # Test connection with status endpoint
            status = await self.get_status()
            if status and status.get("status") == "ready":
                self.is_connected = True
                self.logger.info(f"Connected to Arduino at {self.host}:{self.port}")
                return True
            else:
                self.logger.error(f"Arduino not ready: {status}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Arduino: {e}")
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from Arduino device"""
        if self.is_connected:
            # Stop any ongoing vibration
            try:
                await self.stop()
            except Exception as e:
                self.logger.warning(f"Failed to stop vibration during disconnect: {e}")
            
        await self._close_session()
        self.is_connected = False
        self.logger.info("Disconnected from Arduino")
        
    async def send_pattern(self, pattern: Dict[str, Any]) -> bool:
        """
        Send vibration pattern to Arduino
        
        Args:
            pattern: Pattern dictionary or VibrationPattern object
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            self.logger.error("Not connected to Arduino")
            return False
            
        try:
            # Ensure session exists
            if not self.session or self.session.closed:
                await self._create_session()
                
            # Convert VibrationPattern to dict if needed
            if isinstance(pattern, VibrationPattern):
                pattern = pattern.to_dict()
                
            # Send pattern via POST request
            url = f"{self.base_url}/pattern"
            
            async with self.session.post(url, json=pattern) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "ok":
                        self.logger.debug(f"Pattern sent successfully: {pattern}")
                        return True
                    else:
                        self.logger.error(f"Pattern rejected: {data}")
                        return False
                else:
                    self.logger.error(f"HTTP error {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to send pattern: {e}")
            return False
            
    async def stop(self) -> bool:
        """Stop any ongoing vibration"""
        if not self.is_connected:
            return False
            
        try:
            # Ensure session exists
            if not self.session or self.session.closed:
                await self._create_session()
                
            url = f"{self.base_url}/stop"
            
            async with self.session.post(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "stopped":
                        self.logger.debug("Vibration stopped")
                        return True
                        
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to stop vibration: {e}")
            return False
            
    async def get_status(self) -> Optional[Dict[str, Any]]:
        """Get device status"""
        try:
            if not self.session:
                await self._create_session()
                
            url = f"{self.base_url}/status"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    self.logger.error(f"Status request failed: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
            return None
            
    async def send_vibration_command(self, command: str) -> bool:
        """
        Send raw vibration command (for compatibility)
        
        Args:
            command: Command string (e.g., "PULSE:128,2.0,500")
            
        Returns:
            True if successful
        """
        if not self.is_connected:
            return False
            
        try:
            # Parse command format: PATTERN:intensity,frequency,duration
            parts = command.split(':')
            if len(parts) != 2:
                self.logger.error(f"Invalid command format: {command}")
                return False
                
            pattern_type = parts[0].lower().replace('mixed_', '')
            params = parts[1].split(',')
            
            if len(params) != 3:
                self.logger.error(f"Invalid parameters: {parts[1]}")
                return False
                
            intensity = int(params[0]) / 255.0  # Convert from 0-255 to 0.0-1.0
            frequency = float(params[1])
            duration = int(params[2])
            
            # Create pattern based on command
            if pattern_type == "pulse":
                pattern = {
                    "steps": [
                        {"intensity": int(intensity * 100), "duration": duration // 2},
                        {"intensity": 0, "duration": duration // 2}
                    ],
                    "interval": 50,
                    "repeat_count": int(frequency)
                }
            elif pattern_type == "wave":
                pattern = {
                    "steps": [
                        {"intensity": int(intensity * 30), "duration": duration // 3},
                        {"intensity": int(intensity * 70), "duration": duration // 3},
                        {"intensity": int(intensity * 100), "duration": duration // 3}
                    ],
                    "interval": 50,
                    "repeat_count": int(frequency)
                }
            elif pattern_type == "burst":
                pattern = {
                    "steps": [
                        {"intensity": int(intensity * 100), "duration": 100},
                        {"intensity": 0, "duration": 50}
                    ],
                    "interval": 30,
                    "repeat_count": int(frequency * 3)
                }
            elif pattern_type == "fade":
                pattern = {
                    "steps": [
                        {"intensity": int(intensity * 100), "duration": duration // 2},
                        {"intensity": int(intensity * 50), "duration": duration // 4},
                        {"intensity": int(intensity * 20), "duration": duration // 4}
                    ],
                    "interval": 50,
                    "repeat_count": int(frequency)
                }
            else:
                # Default pattern
                pattern = {
                    "steps": [
                        {"intensity": int(intensity * 100), "duration": duration}
                    ],
                    "interval": 0,
                    "repeat_count": 1
                }
                
            return await self.send_pattern(pattern)
            
        except Exception as e:
            self.logger.error(f"Failed to send command: {e}")
            return False


class ArduinoManager(BaseController):
    """Manager for multiple Arduino devices"""
    
    def __init__(self):
        self.controllers: Dict[str, ArduinoController] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def add_arduino(self, device_id: str, host: str, port: int = 80) -> bool:
        """Add and connect to an Arduino device"""
        controller = ArduinoController(device_id, host, port)
        
        if await controller.connect():
            self.controllers[device_id] = controller
            self.logger.info(f"Added Arduino: {device_id} at {host}:{port}")
            return True
        else:
            self.logger.error(f"Failed to add Arduino: {device_id}")
            return False
            
    async def remove_arduino(self, device_id: str) -> None:
        """Remove and disconnect Arduino device"""
        if device_id in self.controllers:
            await self.controllers[device_id].disconnect()
            del self.controllers[device_id]
            self.logger.info(f"Removed Arduino: {device_id}")
            
    async def send_pattern_to_all(self, pattern: Dict[str, Any]) -> Dict[str, bool]:
        """Send pattern to all connected Arduinos"""
        results = {}
        
        for device_id, controller in self.controllers.items():
            results[device_id] = await controller.send_pattern(pattern)
            
        return results
        
    async def stop_all(self) -> Dict[str, bool]:
        """Stop all Arduinos"""
        results = {}
        
        for device_id, controller in self.controllers.items():
            results[device_id] = await controller.stop()
            
        return results
        
    async def disconnect_all(self) -> None:
        """Disconnect all Arduinos"""
        for device_id in list(self.controllers.keys()):
            await self.remove_arduino(device_id)