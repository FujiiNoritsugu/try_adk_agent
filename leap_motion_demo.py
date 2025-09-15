#!/usr/bin/env python3
"""
Leap Motion ADK Integration Demo
Shows how to use Leap Motion to control ADK input
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_leap_motion_demo():
    """Run demo showing Leap Motion integration"""
    
    # Connect to Leap Motion MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["server_leapmotion/server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize session
            await session.initialize()
            
            print("Leap Motion ADK Integration Demo")
            print("=" * 50)
            print("Available gestures:")
            print("- Swipe: Quick hand movement (intensity: 0.3)")
            print("- Circle: Circular hand motion (intensity: 0.5)")
            print("- Tap: Single finger tap (intensity: 0.7)")
            print("- Grab: Close fist (intensity: 0.8)")
            print("- Pinch: Two finger pinch (intensity: 0.6)")
            print("\nHand height maps to body areas:")
            print("- Above 250: 頭 (head)")
            print("- 150-250: 胸 (chest)")
            print("- 50-150: 腹 (stomach)")
            print("- Below 50: 足 (feet)")
            print("=" * 50)
            print("\nPlace your hand over the Leap Motion sensor...")
            print("Press Ctrl+C to stop\n")
            
            try:
                while True:
                    # Get Leap Motion data
                    result = await session.call_tool(
                        "get_leap_motion_data",
                        arguments={}
                    )
                    
                    if result and len(result) > 0:
                        data = json.loads(result[0].text)
                        
                        if "error" not in data:
                            print(f"\nLeap Motion Data:")
                            print(f"  Gesture: {data['gesture_type']}")
                            print(f"  Position: x={data['hand_position']['x']:.1f}, "
                                  f"y={data['hand_position']['y']:.1f}, "
                                  f"z={data['hand_position']['z']:.1f}")
                            print(f"  Velocity: {data['hand_velocity']:.1f}")
                            print(f"  Confidence: {data['confidence']:.2f}")
                            
                            # Convert to touch input
                            touch_result = await session.call_tool(
                                "convert_to_touch",
                                arguments={}
                            )
                            
                            if touch_result and len(touch_result) > 0:
                                touch_data = json.loads(touch_result[0].text)
                                print(f"\nConverted to ADK Input:")
                                print(f"  Intensity: {touch_data['data']}")
                                print(f"  Body Area: {touch_data['touched_area']}")
                                print(f"  Format: {json.dumps({'data': touch_data['data'], 'touched_area': touch_data['touched_area']})}")
                    
                    await asyncio.sleep(0.5)
                    
            except KeyboardInterrupt:
                print("\nDemo stopped")

async def test_gesture_mapping():
    """Test custom gesture mapping"""
    
    server_params = StdioServerParameters(
        command="python",
        args=["server_leapmotion/server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("\nTesting custom gesture mapping...")
            
            # Set custom mapping for swipe gesture
            result = await session.call_tool(
                "set_gesture_mapping",
                arguments={
                    "gesture": "swipe",
                    "intensity": 0.9,
                    "area": "頭"
                }
            )
            
            print(f"Custom mapping result: {result[0].text if result else 'No result'}")

if __name__ == "__main__":
    print("Choose demo mode:")
    print("1. Real-time Leap Motion tracking")
    print("2. Test custom gesture mapping")
    
    choice = input("Enter choice (1 or 2): ")
    
    if choice == "1":
        asyncio.run(run_leap_motion_demo())
    elif choice == "2":
        asyncio.run(test_gesture_mapping())
    else:
        print("Invalid choice")