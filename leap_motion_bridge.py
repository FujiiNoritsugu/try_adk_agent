#!/usr/bin/env python3
"""
Leap Motion to ADK Web Bridge
This script captures Leap Motion data and sends it to the ADK web interface
"""

import asyncio
import json
import aiohttp
from typing import Optional, Dict, Any
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LeapMotionBridge:
    def __init__(self, adk_url: str = "http://localhost:8080", polling_rate: float = 0.1):
        self.adk_url = adk_url
        self.polling_rate = polling_rate
        self.session = None
        self.running = False
        
        # Try to import Leap Motion
        try:
            import leap
            self.leap = leap
            self.controller = None
            self.leap_available = True
        except ImportError:
            logger.warning("Leap Motion SDK not available. Using mock data.")
            self.leap_available = False
    
    async def initialize(self):
        """Initialize the bridge components"""
        self.session = aiohttp.ClientSession()
        
        if self.leap_available:
            try:
                self.controller = self.leap.Controller()
                self.controller.set_policy(self.leap.Controller.POLICY_BACKGROUND_FRAMES)
                logger.info("Leap Motion controller initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Leap Motion: {e}")
                self.leap_available = False
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
    
    def get_leap_frame(self) -> Optional[Dict[str, Any]]:
        """Get current frame from Leap Motion"""
        if not self.leap_available or not self.controller:
            # Return mock data for testing
            return self.get_mock_frame()
        
        if not self.controller.is_connected:
            logger.warning("Leap Motion controller not connected")
            return None
        
        frame = self.controller.frame()
        if not frame.is_valid or len(frame.hands) == 0:
            return None
        
        hand = frame.hands[0]
        
        return {
            "hand_position": {
                "x": hand.palm_position.x,
                "y": hand.palm_position.y,
                "z": hand.palm_position.z
            },
            "hand_velocity": hand.palm_velocity.magnitude,
            "palm_normal": {
                "x": hand.palm_normal.x,
                "y": hand.palm_normal.y,
                "z": hand.palm_normal.z
            },
            "confidence": hand.confidence,
            "fingers_extended": sum(1 for finger in hand.fingers if finger.is_extended)
        }
    
    def get_mock_frame(self) -> Dict[str, Any]:
        """Get mock frame data for testing"""
        import time
        import math
        
        t = time.time()
        # Simulate hand movement in a circle
        return {
            "hand_position": {
                "x": 100 * math.cos(t),
                "y": 150 + 50 * math.sin(t * 2),
                "z": 50 * math.sin(t)
            },
            "hand_velocity": abs(100 * math.sin(t * 3)),
            "palm_normal": {
                "x": 0,
                "y": -1,
                "z": 0
            },
            "confidence": 0.9,
            "fingers_extended": int(2.5 + 2.5 * math.sin(t * 0.5))
        }
    
    def detect_gesture(self, frame_data: Dict[str, Any]) -> str:
        """Detect gesture from frame data"""
        if not frame_data:
            return "none"
        
        velocity = frame_data["hand_velocity"]
        fingers = frame_data["fingers_extended"]
        palm_y = frame_data["palm_normal"]["y"]
        
        # Gesture detection logic
        if velocity > 500:
            return "swipe"
        elif fingers == 0:
            return "grab"
        elif fingers == 1:
            return "tap"
        elif fingers == 2 and velocity < 100:
            return "pinch"
        elif abs(palm_y) < 0.3 and velocity > 100:
            return "circle"
        else:
            return "none"
    
    def map_to_adk_input(self, frame_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Leap Motion data to ADK input format"""
        if not frame_data:
            return None
        
        gesture = self.detect_gesture(frame_data)
        
        # Gesture to intensity mapping
        gesture_mappings = {
            "swipe": 0.3,
            "circle": 0.5,
            "tap": 0.7,
            "grab": 0.8,
            "pinch": 0.6,
            "none": 0.1
        }
        
        intensity = gesture_mappings.get(gesture, 0.1)
        
        # Adjust intensity based on velocity
        velocity_factor = min(frame_data["hand_velocity"] / 1000, 1.0)
        intensity = min(intensity + (velocity_factor * 0.2), 1.0)
        
        # Map hand Y position to body area
        hand_y = frame_data["hand_position"]["y"]
        if hand_y > 250:
            area = "頭"
        elif hand_y > 150:
            area = "胸"
        elif hand_y > 50:
            area = "腹"
        else:
            area = "足"
        
        return {
            "data": round(intensity, 2),
            "touched_area": area,
            "gesture_type": gesture,
            "hand_position": frame_data["hand_position"],
            "hand_velocity": frame_data["hand_velocity"],
            "leap_confidence": frame_data["confidence"]
        }
    
    async def send_to_adk(self, data: Dict[str, Any]):
        """Send data to ADK web interface"""
        try:
            async with self.session.post(
                f"{self.adk_url}/api/touch",
                json=data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Sent to ADK: {data} -> Response: {result}")
                else:
                    logger.error(f"Failed to send to ADK: {response.status}")
        except Exception as e:
            logger.error(f"Error sending to ADK: {e}")
    
    async def run(self):
        """Main loop to capture and send Leap Motion data"""
        await self.initialize()
        self.running = True
        
        logger.info(f"Starting Leap Motion bridge (polling rate: {self.polling_rate}s)")
        logger.info(f"ADK URL: {self.adk_url}")
        logger.info("Place your hand over the Leap Motion sensor...")
        
        last_gesture = "none"
        
        try:
            while self.running:
                # Get Leap Motion frame
                frame_data = self.get_leap_frame()
                
                if frame_data:
                    # Convert to ADK format
                    adk_data = self.map_to_adk_input(frame_data)
                    
                    if adk_data:
                        # Only send if gesture changed or is active
                        current_gesture = adk_data["gesture_type"]
                        if current_gesture != "none" or current_gesture != last_gesture:
                            await self.send_to_adk(adk_data)
                            last_gesture = current_gesture
                
                await asyncio.sleep(self.polling_rate)
                
        except KeyboardInterrupt:
            logger.info("Stopping Leap Motion bridge...")
        finally:
            self.running = False
            await self.cleanup()

async def main():
    parser = argparse.ArgumentParser(description="Leap Motion to ADK Web Bridge")
    parser.add_argument(
        "--adk-url",
        default="http://localhost:8080",
        help="ADK web interface URL"
    )
    parser.add_argument(
        "--polling-rate",
        type=float,
        default=0.1,
        help="Polling rate in seconds (default: 0.1)"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data instead of real Leap Motion"
    )
    
    args = parser.parse_args()
    
    bridge = LeapMotionBridge(
        adk_url=args.adk_url,
        polling_rate=args.polling_rate
    )
    
    if args.mock:
        bridge.leap_available = False
    
    await bridge.run()

if __name__ == "__main__":
    asyncio.run(main())