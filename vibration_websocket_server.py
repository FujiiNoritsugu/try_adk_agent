"""
WebSocket server for real-time vibration sensor data streaming
"""

import asyncio
import websockets
import json
import logging
from typing import Set, Dict, Optional, List
from datetime import datetime
from vibration_sensor_controller import VibrationSensorController, VibrationLevel, VibrationSensorManager


class VibrationWebSocketServer:
    """WebSocket server for streaming vibration data"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.sensor_manager = VibrationSensorManager()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.running = False
        
    async def register_client(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Register a new WebSocket client"""
        self.clients.add(websocket)
        self.logger.info(f"Client {websocket.remote_address} connected. Total clients: {len(self.clients)}")
        
        # Send welcome message
        await websocket.send(json.dumps({
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to vibration sensor stream"
        }))
        
    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Unregister a WebSocket client"""
        if websocket in self.clients:
            self.clients.remove(websocket)
            self.logger.info(f"Client {websocket.remote_address} disconnected. Total clients: {len(self.clients)}")
            
    async def broadcast_sensor_data(self, sensor_data: Dict) -> None:
        """Broadcast sensor data to all connected clients"""
        if not self.clients:
            return
            
        message = json.dumps({
            "type": "sensor_data",
            "data": sensor_data,
            "timestamp": datetime.now().isoformat()
        })
        
        # Send to all connected clients
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                self.logger.error(f"Error sending to client: {e}")
                disconnected_clients.add(client)
                
        # Remove disconnected clients
        for client in disconnected_clients:
            await self.unregister_client(client)
            
    async def handle_client_message(self, websocket: websockets.WebSocketServerProtocol, message: str) -> None:
        """Handle incoming messages from clients"""
        try:
            data = json.loads(message)
            command_type = data.get("type")
            
            if command_type == "subscribe":
                # Client wants to subscribe to specific sensor
                sensor_id = data.get("sensor_id")
                await websocket.send(json.dumps({
                    "type": "subscription",
                    "sensor_id": sensor_id,
                    "status": "subscribed",
                    "timestamp": datetime.now().isoformat()
                }))
                
            elif command_type == "set_threshold":
                # Client wants to set threshold for a sensor
                sensor_id = data.get("sensor_id")
                threshold = data.get("threshold")
                if sensor_id in self.sensor_manager.sensors:
                    success = await self.sensor_manager.sensors[sensor_id].set_threshold(threshold)
                    await websocket.send(json.dumps({
                        "type": "threshold_update",
                        "sensor_id": sensor_id,
                        "threshold": threshold,
                        "success": success,
                        "timestamp": datetime.now().isoformat()
                    }))
                    
            elif command_type == "calibrate":
                # Client wants to calibrate a sensor
                sensor_id = data.get("sensor_id")
                if sensor_id in self.sensor_manager.sensors:
                    success = await self.sensor_manager.sensors[sensor_id].calibrate_sensor()
                    await websocket.send(json.dumps({
                        "type": "calibration",
                        "sensor_id": sensor_id,
                        "success": success,
                        "timestamp": datetime.now().isoformat()
                    }))
                    
            elif command_type == "get_status":
                # Client wants status of all sensors
                status = {}
                for sensor_id, sensor in self.sensor_manager.sensors.items():
                    status[sensor_id] = {
                        "connected": sensor.is_connected,
                        "threshold": sensor.sensor_threshold
                    }
                await websocket.send(json.dumps({
                    "type": "status",
                    "sensors": status,
                    "timestamp": datetime.now().isoformat()
                }))
                
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Invalid JSON format",
                "timestamp": datetime.now().isoformat()
            }))
        except Exception as e:
            self.logger.error(f"Error handling client message: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }))
            
    async def client_handler(self, websocket: websockets.WebSocketServerProtocol, path: str) -> None:
        """Handle WebSocket client connection"""
        await self.register_client(websocket)
        
        try:
            async for message in websocket:
                await self.handle_client_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)
            
    async def vibration_callback(self, sensor_data: Dict) -> None:
        """Callback for vibration events to broadcast via WebSocket"""
        # Add alert type based on vibration level
        level = sensor_data.get("vibration_level", VibrationLevel.NONE)
        
        if level == VibrationLevel.EXTREME:
            sensor_data["alert"] = "earthquake"
        elif level == VibrationLevel.HIGH:
            sensor_data["alert"] = "machine_fault"
        elif level == VibrationLevel.MEDIUM:
            sensor_data["alert"] = "proximity_warning"
            
        await self.broadcast_sensor_data(sensor_data)
        
    async def add_sensor(self, sensor_id: str, port: str = None, baudrate: int = 115200) -> bool:
        """Add a sensor to the manager with WebSocket callback"""
        sensor = VibrationSensorController(sensor_id, port, baudrate)
        if await sensor.connect():
            self.sensor_manager.sensors[sensor_id] = sensor
            # Add both manager callback and WebSocket broadcast callback
            sensor.add_vibration_callback(self.sensor_manager.handle_vibration_event)
            sensor.add_vibration_callback(self.vibration_callback)
            
            # Notify all clients about new sensor
            await self.broadcast_sensor_data({
                "type": "sensor_added",
                "sensor_id": sensor_id,
                "port": port or "auto-detected",
                "baudrate": baudrate
            })
            
            return True
        return False
        
    async def start_server(self) -> None:
        """Start the WebSocket server"""
        self.logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        self.running = True
        
        # Start WebSocket server
        async with websockets.serve(self.client_handler, self.host, self.port):
            self.logger.info("WebSocket server started")
            
            # Keep server running
            while self.running:
                await asyncio.sleep(1)
                
    async def monitoring_task(self) -> None:
        """Task to monitor all sensors"""
        await self.sensor_manager.start_monitoring_all()
        
    async def run(self, sensors: List[Dict[str, any]] = None) -> None:
        """Run the WebSocket server with sensors"""
        # Add sensors if provided
        if sensors:
            for sensor_config in sensors:
                await self.add_sensor(
                    sensor_config["id"],
                    sensor_config.get("port"),  # Serial port
                    sensor_config.get("baudrate", 115200)
                )
                
        # Start monitoring and server tasks
        tasks = [
            self.start_server(),
            self.monitoring_task()
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
            self.running = False
            await self.sensor_manager.shutdown()


# Example WebSocket client (for testing)
async def test_client():
    """Test WebSocket client"""
    uri = "ws://localhost:8765"
    
    async with websockets.connect(uri) as websocket:
        # Get initial status
        await websocket.send(json.dumps({
            "type": "get_status"
        }))
        
        # Subscribe to sensor
        await websocket.send(json.dumps({
            "type": "subscribe",
            "sensor_id": "sensor1"
        }))
        
        # Listen for messages
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Received: {data}")
            
            # Handle different message types
            if data.get("type") == "sensor_data":
                level = data["data"].get("vibration_level")
                if level in [VibrationLevel.HIGH.name, VibrationLevel.EXTREME.name]:
                    print(f"ALERT! High vibration detected: {level}")


# Main function
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    server = VibrationWebSocketServer()
    
    # Configure sensors
    sensors = [
        {"id": "sensor1"},  # Auto-detect serial port
        # {"id": "sensor1", "port": "COM3"},  # Windows specific port
        # {"id": "sensor1", "port": "/dev/ttyUSB0"},  # Linux specific port
    ]
    
    await server.run(sensors)


if __name__ == "__main__":
    asyncio.run(main())