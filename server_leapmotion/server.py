import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
from pydantic import BaseModel, Field
import logging
from typing import Optional, Dict, Any
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Leap Motion library
try:
    import leap
    LEAP_AVAILABLE = True
except ImportError:
    logger.warning("Leap Motion SDK not found. Install with: pip install leapmotion")
    LEAP_AVAILABLE = False

class LeapMotionData(BaseModel):
    """Structure for Leap Motion sensor data"""
    hand_position: Dict[str, float] = Field(description="3D position of hand (x, y, z)")
    hand_velocity: float = Field(description="Speed of hand movement")
    gesture_type: str = Field(description="Type of gesture detected")
    confidence: float = Field(description="Confidence level of detection (0-1)")
    palm_normal: Dict[str, float] = Field(description="Palm normal vector")
    fingers_extended: int = Field(description="Number of extended fingers")

class LeapMotionServer:
    def __init__(self):
        self.server = Server("leapmotion-server")
        self.controller = None
        self.latest_frame = None
        self.gesture_mappings = {
            "swipe": {"intensity": 0.3, "area": "air"},
            "circle": {"intensity": 0.5, "area": "air"},
            "tap": {"intensity": 0.7, "area": "air"},
            "grab": {"intensity": 0.8, "area": "air"},
            "pinch": {"intensity": 0.6, "area": "air"}
        }
        
        # Setup server handlers
        self.setup_handlers()
        
        # Initialize Leap Motion if available
        if LEAP_AVAILABLE:
            self.init_leap_motion()
    
    def init_leap_motion(self):
        """Initialize Leap Motion controller"""
        try:
            self.controller = leap.Controller()
            self.controller.set_policy(leap.Controller.POLICY_BACKGROUND_FRAMES)
            logger.info("Leap Motion controller initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Leap Motion: {e}")
            self.controller = None
    
    def get_current_frame(self) -> Optional[Dict[str, Any]]:
        """Get current frame data from Leap Motion"""
        if not self.controller or not self.controller.is_connected:
            return None
        
        frame = self.controller.frame()
        if not frame.is_valid or len(frame.hands) == 0:
            return None
        
        hand = frame.hands[0]
        
        # Extract hand data
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
    
    def setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="get_leap_motion_data",
                    description="Get current Leap Motion sensor data",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="convert_to_touch",
                    description="Convert Leap Motion data to ADK touch input format",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="set_gesture_mapping",
                    description="Set custom gesture to touch intensity mapping",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "gesture": {
                                "type": "string",
                                "description": "Gesture type (swipe, circle, tap, grab, pinch)"
                            },
                            "intensity": {
                                "type": "number",
                                "description": "Touch intensity (0-1)"
                            },
                            "area": {
                                "type": "string",
                                "description": "Body area"
                            }
                        },
                        "required": ["gesture", "intensity", "area"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]):
            if name == "get_leap_motion_data":
                if not LEAP_AVAILABLE:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "error": "Leap Motion SDK not available",
                            "message": "Please install the Leap Motion SDK"
                        })
                    )]
                
                frame_data = self.get_current_frame()
                if not frame_data:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "error": "No hand detected",
                            "message": "Please place your hand over the Leap Motion sensor"
                        })
                    )]
                
                gesture = self.detect_gesture(frame_data)
                leap_data = LeapMotionData(
                    hand_position=frame_data["hand_position"],
                    hand_velocity=frame_data["hand_velocity"],
                    gesture_type=gesture,
                    confidence=frame_data["confidence"],
                    palm_normal=frame_data["palm_normal"],
                    fingers_extended=frame_data["fingers_extended"]
                )
                
                return [TextContent(
                    type="text",
                    text=json.dumps(leap_data.model_dump(), indent=2)
                )]
            
            elif name == "convert_to_touch":
                frame_data = self.get_current_frame()
                touch_input = self.map_to_touch_input(frame_data)
                
                return [TextContent(
                    type="text",
                    text=json.dumps(touch_input, indent=2)
                )]
            
            elif name == "set_gesture_mapping":
                gesture = arguments.get("gesture")
                intensity = arguments.get("intensity", 0.5)
                area = arguments.get("area", "air")
                
                if gesture not in self.gesture_mappings:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "error": "Invalid gesture",
                            "valid_gestures": list(self.gesture_mappings.keys())
                        })
                    )]
                
                self.gesture_mappings[gesture] = {
                    "intensity": intensity,
                    "area": area
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "gesture": gesture,
                        "mapping": self.gesture_mappings[gesture]
                    })
                )]
            
            else:
                return [TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )]
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

async def main():
    server = LeapMotionServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())