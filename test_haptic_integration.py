#!/usr/bin/env python3
"""
Test script for haptic feedback integration
"""

import asyncio
import json
import logging
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.devices import ArduinoController, VibrationPatternGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_arduino_connection():
    """Test direct Arduino connection and basic operations"""
    print("=== Arduino Connection Test ===")
    
    # Replace with your Arduino's IP address
    ARDUINO_IP = input("Enter Arduino IP address (e.g., 192.168.1.100): ").strip()
    if not ARDUINO_IP:
        ARDUINO_IP = "192.168.1.100"
    
    try:
        # Create controller
        controller = ArduinoController("test_device", ARDUINO_IP)
        
        # Test connection
        print(f"Connecting to Arduino at {ARDUINO_IP}...")
        connected = await controller.connect()
        
        if not connected:
            print("❌ Failed to connect to Arduino")
            return False
            
        print("✅ Connected successfully!")
        
        # Get status
        print("\nGetting device status...")
        status = await controller.get_status()
        print(f"Status: {json.dumps(status, indent=2)}")
        
        # Test patterns
        patterns = [
            ("pulse", 0.5, 1000, 2),
            ("wave", 0.7, 1500, 1),
            ("burst", 0.8, 500, 3),
            ("fade", 0.6, 2000, 1)
        ]
        
        for pattern_type, intensity, duration, repeat in patterns:
            print(f"\n📳 Testing {pattern_type} pattern...")
            
            pattern = VibrationPatternGenerator.create_custom_pattern(
                pattern_type=pattern_type,
                intensity=intensity,
                duration_ms=duration,
                repeat_count=repeat
            )
            
            success = await controller.send_pattern(pattern)
            if success:
                print(f"✅ {pattern_type} pattern sent successfully")
                await asyncio.sleep(3)  # Wait for pattern to complete
            else:
                print(f"❌ Failed to send {pattern_type} pattern")
        
        # Test stop
        print("\n⏹️ Testing stop function...")
        await controller.stop()
        print("✅ Stop command sent")
        
        # Disconnect
        await controller.disconnect()
        print("✅ Disconnected successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_emotion_patterns():
    """Test emotion-based pattern generation"""
    print("\n=== Emotion Pattern Test ===")
    
    # Test emotion combinations
    emotion_tests = [
        {"joy": 5, "fun": 2, "anger": 0, "sad": 0},
        {"joy": 0, "fun": 0, "anger": 5, "sad": 1},
        {"joy": 1, "fun": 1, "anger": 0, "sad": 4},
        {"joy": 3, "fun": 4, "anger": 1, "sad": 0},
        {"joy": 0, "fun": 0, "anger": 0, "sad": 0},  # No emotion
    ]
    
    for i, emotions in enumerate(emotion_tests):
        print(f"\nTest {i+1}: {emotions}")
        
        pattern = VibrationPatternGenerator.from_emotion_values(
            joy=emotions["joy"],
            fun=emotions["fun"],
            anger=emotions["anger"],
            sad=emotions["sad"]
        )
        
        if pattern.steps:
            print(f"Generated pattern: {len(pattern.steps)} steps, {pattern.repeat_count} repeats")
            for j, step in enumerate(pattern.steps):
                print(f"  Step {j+1}: intensity={step.intensity:.2f}, duration={step.duration}ms")
        else:
            print("No pattern generated (all emotions zero)")


async def test_mcp_server():
    """Test MCP server functionality (requires server to be running)"""
    print("\n=== MCP Server Test ===")
    print("This test requires the MCP server to be running separately.")
    print("To run: python mcp_servers/vibration_server.py")
    
    # This would require implementing MCP client functionality
    # For now, just show the expected usage
    print("\nExpected MCP tool calls:")
    print("1. initialize_arduino({'host': '192.168.1.100', 'port': 80})")
    print("2. generate_vibration_pattern({'joy': 4, 'fun': 2, 'anger': 0, 'sad': 0})")
    print("3. control_vibration({'vibration_settings': {...}})")
    print("4. send_arduino_vibration({'pattern_type': 'pulse', 'intensity': 0.7, 'duration_ms': 1000, 'repeat_count': 2})")


async def main():
    """Main test runner"""
    print("🔧 Haptic Feedback Integration Test Suite")
    print("=" * 50)
    
    while True:
        print("\nSelect a test to run:")
        print("1. Arduino Connection Test")
        print("2. Emotion Pattern Generation Test")
        print("3. MCP Server Usage Info")
        print("4. Run All Tests")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            await test_arduino_connection()
        elif choice == "2":
            await test_emotion_patterns()
        elif choice == "3":
            await test_mcp_server()
        elif choice == "4":
            await test_emotion_patterns()
            if await test_arduino_connection():
                await test_mcp_server()
        elif choice == "5":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()