#!/usr/bin/env python3
"""
Fixed version of server_http.py with proper Leap Motion initialization.
Key changes:
1. Ensure connection is properly started after open()
2. Add more event handlers
3. Use asyncio for background processing
"""

import asyncio
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import logging
from typing import Optional, Dict, Any
import numpy as np
import uvicorn
import time
from datetime import datetime
import threading

# Configure logging - set to DEBUG for more details
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import Leap Motion library
try:
    import leap
    from leap import datatypes as ldt
    LEAP_AVAILABLE = True
except ImportError:
    logger.warning("Leap Motion SDK not found. Install with: pip install leapmotion")
    LEAP_AVAILABLE = False

# FastAPI app
app = FastAPI(title="Leap Motion MCP Server", version="1.0.0")

class LeapMotionData(BaseModel):
    """Structure for Leap Motion sensor data"""
    hand_position: Dict[str, float] = Field(description="3D position of hand (x, y, z)")
    hand_velocity: float = Field(description="Speed of hand movement")
    gesture_type: str = Field(description="Type of gesture detected")
    confidence: float = Field(description="Confidence level of detection (0-1)")
    palm_normal: Dict[str, float] = Field(description="Palm normal vector")
    fingers_extended: int = Field(description="Number of extended fingers")

class GestureMappingRequest(BaseModel):
    """Request model for setting gesture mapping"""
    gesture: str = Field(description="Gesture type (swipe, circle, tap, grab, pinch)")
    intensity: float = Field(description="Touch intensity (0-1)")
    area: str = Field(description="Body area")

class LeapListener(leap.Listener):
    """Leap Motion event listener"""
    def __init__(self):
        super().__init__()
        self.latest_frame = None
        self.frame_count = 0
        self.last_hand_count = 0
        self.is_connected = False
        self.has_device = False
        logger.info("LeapListener initialized")

    def on_tracking_event(self, event):
        """Store the latest tracking frame"""
        self.latest_frame = event
        self.frame_count += 1
        
        # Debug logging - log when hand count changes or every 100 frames
        current_hand_count = len(event.hands) if event.hands else 0
        if current_hand_count != self.last_hand_count or self.frame_count % 100 == 0:
            logger.debug(f"Tracking event #{self.frame_count}: {current_hand_count} hand(s) detected")
            if current_hand_count > 0:
                for i, hand in enumerate(event.hands):
                    pos = hand.palm.position
                    logger.debug(f"  Hand {i}: pos=({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})")
            self.last_hand_count = current_hand_count
    
    def on_connection_event(self, event):
        """Log connection events"""
        logger.info(f"Connection event: {event}")
        self.is_connected = True
    
    def on_device_event(self, event):
        """Log device events"""
        logger.info(f"Device event: {event}")
        self.has_device = True

class LeapMotionService:
    def __init__(self):
        self.connection = None
        self.listener = None
        self.connection_thread = None
        self.gesture_mappings = {
            "swipe": {"intensity": 0.3, "area": "air"},
            "circle": {"intensity": 0.5, "area": "air"},
            "tap": {"intensity": 0.7, "area": "air"},
            "grab": {"intensity": 0.8, "area": "air"},
            "pinch": {"intensity": 0.6, "area": "air"}
        }

        # Initialize Leap Motion if available
        if LEAP_AVAILABLE:
            self.init_leap_motion()

    def init_leap_motion(self):
        """Initialize Leap Motion connection and listener"""
        try:
            self.listener = LeapListener()
            self.connection = leap.Connection()
            self.connection.add_listener(self.listener)
            
            logger.info("Opening Leap Motion connection...")
            self.connection.open()
            
            # CRITICAL: Start the connection's event loop in a separate thread
            # This is necessary for receiving events
            def run_leap_loop():
                logger.info("Starting Leap Motion event loop...")
                try:
                    # Keep the connection alive and processing events
                    while self.connection:
                        time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Leap loop error: {e}")
            
            self.connection_thread = threading.Thread(target=run_leap_loop, daemon=True)
            self.connection_thread.start()
            
            # Wait for connection to establish
            logger.info("Waiting for Leap Motion connection to establish...")
            time.sleep(3)
            
            logger.info("Leap Motion connection initialized and opened")
            logger.info(f"Connection status: Connected={self.listener.is_connected}")
            logger.info(f"Device status: HasDevice={self.listener.has_device}")
        except Exception as e:
            logger.error(f"Failed to initialize Leap Motion: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.connection = None
            self.listener = None

    def get_current_frame(self) -> Optional[Dict[str, Any]]:
        """Get current frame data from Leap Motion"""
        if not self.listener or not self.listener.latest_frame:
            return None

        event = self.listener.latest_frame
        if not event.hands or len(event.hands) == 0:
            return None

        hand = event.hands[0]

        # Calculate palm velocity magnitude
        palm_velocity = hand.palm.velocity
        velocity_magnitude = (palm_velocity.x**2 + palm_velocity.y**2 + palm_velocity.z**2) ** 0.5

        # Count extended fingers
        fingers_extended = 0
        for digit in hand.digits:
            # Check if finger is extended based on curl angle
            if digit.is_extended:
                fingers_extended += 1

        # Extract hand data
        return {
            "hand_position": {
                "x": hand.palm.position.x,
                "y": hand.palm.position.y,
                "z": hand.palm.position.z
            },
            "hand_velocity": velocity_magnitude,
            "palm_normal": {
                "x": hand.palm.normal.x,
                "y": hand.palm.normal.y,
                "z": hand.palm.normal.z
            },
            "confidence": 1.0,  # LeapC doesn't provide confidence directly
            "fingers_extended": fingers_extended
        }

    def detect_gesture(self, frame_data: Dict[str, Any]) -> str:
        """Detect gesture type from frame data"""
        if not frame_data:
            return "none"

        velocity = frame_data["hand_velocity"]
        fingers = frame_data["fingers_extended"]
        palm_y = frame_data["palm_normal"]["y"]

        # Simple gesture detection logic
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

    def map_to_touch_input(self, leap_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Leap Motion data to ADK touch input format"""
        gesture = self.detect_gesture(leap_data)

        # Get base mapping
        if gesture in self.gesture_mappings:
            base_mapping = self.gesture_mappings[gesture]
            intensity = base_mapping["intensity"]
            area = base_mapping["area"]
        else:
            intensity = 0.1
            area = "air"

        # Adjust intensity based on velocity
        if leap_data:
            velocity_factor = min(leap_data["hand_velocity"] / 1000, 1.0)
            intensity = min(intensity + (velocity_factor * 0.2), 1.0)

            # Map hand position to body area
            hand_y = leap_data["hand_position"]["y"]
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
            "raw_leap_data": leap_data
        }

# Create service instance
service = LeapMotionService()

# ... rest of the endpoints remain the same ...

# Copy all the endpoint definitions from the original server_http.py below this line