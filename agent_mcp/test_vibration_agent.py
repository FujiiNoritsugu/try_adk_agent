#!/usr/bin/env python3
"""
Test script for vibration agent with Arduino integration
"""

import asyncio
import json
from agent import vibration_agent, TouchInput


async def test_vibration_agent():
    """Test the vibration agent with various emotion inputs"""
    
    print("=== Vibration Agent Arduino Integration Test ===\n")
    
    # Test scenarios with different touch inputs
    test_scenarios = [
        {
            "name": "Happy Touch",
            "input": TouchInput(data=0.3, touched_area="hand"),
            "expected_emotion": "joy",
            "description": "軽い喜びの感情"
        },
        {
            "name": "Painful Touch", 
            "input": TouchInput(data=0.9, touched_area="arm"),
            "expected_emotion": "anger",
            "description": "痛みによる怒りの感情"
        },
        {
            "name": "Pleasant Touch",
            "input": TouchInput(data=0.5, touched_area="shoulder"), 
            "expected_emotion": "fun",
            "description": "心地よい楽しい感情"
        },
        {
            "name": "Gentle Touch",
            "input": TouchInput(data=0.1, touched_area="cheek"),
            "expected_emotion": "sad",
            "description": "優しい触れ合いによる穏やかな感情"
        }
    ]
    
    try:
        # Initialize vibration agent
        print("Initializing vibration agent...")
        await vibration_agent.initialize()
        print("✓ Vibration agent initialized\n")
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"{i}. Testing: {scenario['name']}")
            print(f"   Input: {scenario['input'].data} intensity on {scenario['input'].touched_area}")
            print(f"   Expected emotion: {scenario['expected_emotion']}")
            print(f"   Description: {scenario['description']}")
            
            try:
                # Run the vibration agent with touch input
                response = await vibration_agent.run(
                    input_data=scenario['input'],
                    context=f"Process this touch input and generate appropriate vibration response for Arduino: {scenario['description']}"
                )
                
                print(f"   Agent Response: {response}")
                
                # Parse and display the response
                if hasattr(response, 'content'):
                    content = response.content
                    print(f"   Response Content: {content[:200]}...")
                
                print("   ✓ Test completed successfully")
                
            except Exception as e:
                print(f"   ✗ Test failed: {str(e)}")
            
            print("-" * 50)
            await asyncio.sleep(2)  # Wait between tests
            
    except Exception as e:
        print(f"Failed to initialize vibration agent: {str(e)}")
    
    finally:
        # Cleanup
        try:
            await vibration_agent.cleanup()
            print("\n✓ Cleanup completed")
        except:
            pass


async def test_direct_mcp_tools():
    """Test MCP tools directly"""
    print("\n=== Direct MCP Tool Testing ===\n")
    
    # Test emotion to vibration pattern generation
    test_emotions = [
        {"joy": 4, "fun": 2, "anger": 0, "sad": 0},
        {"joy": 0, "fun": 0, "anger": 5, "sad": 0}, 
        {"joy": 1, "fun": 3, "anger": 0, "sad": 2},
        {"joy": 0, "fun": 0, "anger": 0, "sad": 4}
    ]
    
    print("Testing emotion-to-pattern conversion...")
    
    for i, emotions in enumerate(test_emotions, 1):
        print(f"\n{i}. Testing emotions: {emotions}")
        
        try:
            # This would be the direct tool call - in actual implementation,
            # you would use the MCP protocol to call tools
            # For demonstration, we'll show what the call would look like
            
            tool_call = {
                "tool": "generate_vibration_pattern",
                "arguments": emotions
            }
            
            print(f"   Tool Call: {json.dumps(tool_call, indent=2)}")
            print("   (This would generate vibration pattern via MCP)")
            
        except Exception as e:
            print(f"   Error: {str(e)}")


async def test_arduino_connection():
    """Test Arduino connection without MCP (direct test)"""
    print("\n=== Direct Arduino Connection Test ===\n")
    
    try:
        # Import our vibration controller
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from vibration_sensor_controller import VibrationSensorController
        
        print("Testing direct Arduino connection...")
        
        # Create controller
        controller = VibrationSensorController("test_sensor")
        
        # Try to connect
        connected = await controller.connect()
        
        if connected:
            print("✓ Connected to Arduino successfully")
            print(f"   Port: {controller.port}")
            
            # Test sensor reading
            data = await controller.read_sensor_data()
            if data:
                print(f"   Sensor data: {data['vibration_value']} (level: {data['vibration_level'].name})")
            
            # Test vibration command
            test_pattern = {
                "steps": [
                    {"intensity": 0.5, "duration_ms": 200},
                    {"intensity": 0.0, "duration_ms": 100}
                ],
                "interval_ms": 50,
                "repeat_count": 3
            }
            
            result = await controller.send_command({
                "action": "vibrate", 
                "pattern": test_pattern
            })
            
            if result and result.get("success"):
                print("✓ Test vibration sent successfully")
            else:
                print(f"✗ Failed to send vibration: {result}")
                
            await controller.disconnect()
            print("✓ Disconnected from Arduino")
            
        else:
            print("✗ Failed to connect to Arduino")
            print("   Make sure Arduino is connected and running the vibration sensor sketch")
            
    except ImportError as e:
        print(f"✗ Import error: {str(e)}")
        print("   Make sure vibration_sensor_controller.py is in the parent directory")
    except Exception as e:
        print(f"✗ Connection test failed: {str(e)}")


async def main():
    """Run all tests"""
    print("Starting Vibration Agent Arduino Integration Tests\n")
    
    # Run tests in sequence
    await test_arduino_connection()
    await test_direct_mcp_tools()
    # await test_vibration_agent()  # Uncomment when agent is fully set up
    
    print("\n=== All Tests Completed ===")


if __name__ == "__main__":
    asyncio.run(main())