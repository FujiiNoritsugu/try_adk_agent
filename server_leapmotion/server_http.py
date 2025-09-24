import asyncio
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import logging
from typing import Optional, Dict, Any
import numpy as np
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
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

    def on_tracking_event(self, event):
        """Store the latest tracking frame"""
        self.latest_frame = event

class LeapMotionService:
    def __init__(self):
        self.connection = None
        self.listener = None
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
            self.connection.open()
            logger.info("Leap Motion connection initialized and opened")
        except Exception as e:
            logger.error(f"Failed to initialize Leap Motion: {e}")
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

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint - service information"""
    return {
        "service": "Leap Motion MCP Server",
        "version": "1.0.0",
        "leap_available": LEAP_AVAILABLE,
        "endpoints": {
            "GET /": "Service information",
            "GET /health": "Health check",
            "GET /leap-data": "Get current Leap Motion data",
            "GET /touch-input": "Get touch input format",
            "POST /gesture-mapping": "Set gesture mapping",
            "GET /gesture-mappings": "Get all gesture mappings"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "leap_available": LEAP_AVAILABLE,
        "leap_connected": service.connection is not None
    }

@app.get("/leap-data")
async def get_leap_motion_data():
    """Get current Leap Motion sensor data"""
    if not LEAP_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Leap Motion SDK not available. Please install the Leap Motion SDK"
        )

    frame_data = service.get_current_frame()
    if not frame_data:
        return JSONResponse(
            status_code=404,
            content={
                "error": "No hand detected",
                "message": "Please place your hand over the Leap Motion sensor"
            }
        )

    gesture = service.detect_gesture(frame_data)
    leap_data = LeapMotionData(
        hand_position=frame_data["hand_position"],
        hand_velocity=frame_data["hand_velocity"],
        gesture_type=gesture,
        confidence=frame_data["confidence"],
        palm_normal=frame_data["palm_normal"],
        fingers_extended=frame_data["fingers_extended"]
    )

    return leap_data.model_dump()

@app.get("/touch-input")
async def convert_to_touch():
    """Convert Leap Motion data to ADK touch input format"""
    if not LEAP_AVAILABLE:
        # Return mock data if Leap Motion is not available
        return {
            "data": 0.5,
            "touched_area": "air",
            "gesture_type": "none",
            "raw_leap_data": None,
            "mock": True
        }

    frame_data = service.get_current_frame()
    touch_input = service.map_to_touch_input(frame_data)
    return touch_input

@app.post("/gesture-mapping")
async def set_gesture_mapping(request: GestureMappingRequest):
    """Set custom gesture to touch intensity mapping"""
    if request.gesture not in service.gesture_mappings:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid gesture",
                "valid_gestures": list(service.gesture_mappings.keys())
            }
        )

    service.gesture_mappings[request.gesture] = {
        "intensity": request.intensity,
        "area": request.area
    }

    return {
        "success": True,
        "gesture": request.gesture,
        "mapping": service.gesture_mappings[request.gesture]
    }

@app.get("/gesture-mappings")
async def get_gesture_mappings():
    """Get all current gesture mappings"""
    return service.gesture_mappings

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up Leap Motion connection on shutdown"""
    if service.connection:
        service.connection.close()
        logger.info("Leap Motion connection closed")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Leap Motion HTTP MCP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8001, help="Port to listen on (default: 8001)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    logger.info(f"Starting Leap Motion HTTP server on {args.host}:{args.port}")
    uvicorn.run(
        "server_http:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )