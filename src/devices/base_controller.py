"""
Base controller classes for device communication
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List, Callable
from datetime import datetime
import aiohttp


class BaseController(ABC):
    """Abstract base class for device controllers"""
    
    def __init__(self, device_id: str, base_url: str, retry_count: int = 3, timeout: float = 5.0):
        self.device_id = device_id
        self.base_url = base_url
        self.retry_count = retry_count
        self.timeout = timeout
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{device_id}")
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False
        
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the device"""
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the device"""
        pass
        
    @abstractmethod
    async def send_pattern(self, pattern: Dict[str, Any]) -> bool:
        """Send a vibration pattern to the device"""
        pass
        
    @abstractmethod
    async def stop(self) -> bool:
        """Stop any ongoing vibration"""
        pass
        
    @abstractmethod
    async def get_status(self) -> Optional[Dict[str, Any]]:
        """Get device status"""
        pass
        
    async def _create_session(self) -> None:
        """Create HTTP session with timeout"""
        if not self.session or self.session.closed:
            timeout_config = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout_config)
            
    async def _close_session(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def _retry_request(self, method: str, url: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
        """Execute HTTP request with retry logic"""
        last_error = None
        
        for attempt in range(self.retry_count):
            try:
                if not self.session:
                    await self._create_session()
                    
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status < 500:  # Don't retry client errors
                        return response
                    last_error = f"HTTP {response.status}"
                    
            except asyncio.TimeoutError:
                last_error = "Timeout"
            except Exception as e:
                last_error = str(e)
                
            if attempt < self.retry_count - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {last_error}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                
        self.logger.error(f"Request failed after {self.retry_count} attempts: {last_error}")
        return None


class BaseControllerManager:
    """Manages multiple device controllers"""
    
    def __init__(self):
        self.controllers: Dict[str, BaseController] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def add_controller(self, controller: BaseController) -> bool:
        """Add a controller and connect to it"""
        try:
            if await controller.connect():
                self.controllers[controller.device_id] = controller
                self.logger.info(f"Added controller: {controller.device_id}")
                return True
            else:
                self.logger.error(f"Failed to connect to controller: {controller.device_id}")
                return False
        except Exception as e:
            self.logger.error(f"Error adding controller {controller.device_id}: {e}")
            return False
            
    async def remove_controller(self, device_id: str) -> None:
        """Remove and disconnect a controller"""
        if device_id in self.controllers:
            await self.controllers[device_id].disconnect()
            del self.controllers[device_id]
            self.logger.info(f"Removed controller: {device_id}")
            
    async def send_pattern_to_all(self, pattern: Dict[str, Any]) -> Dict[str, bool]:
        """Send pattern to all connected controllers"""
        results = {}
        
        tasks = []
        for device_id, controller in self.controllers.items():
            tasks.append(self._send_pattern_with_id(controller, pattern))
            
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for (device_id, _), result in zip(
            [(c.device_id, c) for c in self.controllers.values()], 
            responses
        ):
            if isinstance(result, Exception):
                self.logger.error(f"Error sending to {device_id}: {result}")
                results[device_id] = False
            else:
                results[device_id] = result
                
        return results
        
    async def _send_pattern_with_id(self, controller: BaseController, pattern: Dict[str, Any]) -> bool:
        """Helper to send pattern and track device ID"""
        return await controller.send_pattern(pattern)
        
    async def stop_all(self) -> Dict[str, bool]:
        """Stop all controllers"""
        results = {}
        
        for device_id, controller in self.controllers.items():
            try:
                results[device_id] = await controller.stop()
            except Exception as e:
                self.logger.error(f"Error stopping {device_id}: {e}")
                results[device_id] = False
                
        return results
        
    async def get_all_status(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get status from all controllers"""
        results = {}
        
        for device_id, controller in self.controllers.items():
            try:
                results[device_id] = await controller.get_status()
            except Exception as e:
                self.logger.error(f"Error getting status from {device_id}: {e}")
                results[device_id] = None
                
        return results
        
    async def disconnect_all(self) -> None:
        """Disconnect all controllers"""
        for controller in list(self.controllers.values()):
            await self.remove_controller(controller.device_id)
            
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect_all()