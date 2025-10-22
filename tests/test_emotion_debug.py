#!/usr/bin/env python3
"""
Debug version of emotion pattern test
"""

import asyncio
import sys
import os
import logging

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.devices import ArduinoController, VibrationPatternGenerator

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def test_emotion_patterns_debug():
    """Test emotion-based pattern generation with debug info"""
    print("\n=== Emotion Pattern Test (Debug) ===")

    # Replace with your Arduino's IP address
    ARDUINO_IP = "192.168.43.166"
    
    try:
        # Create controller
        print(f"\n1. Creating ArduinoController...")
        controller = ArduinoController("test_device", ARDUINO_IP)
        print(f"   Controller created: {controller}")
        print(f"   Base URL: {controller.base_url}")
        
        # Connect to Arduino
        print(f"\n2. Connecting to Arduino at {ARDUINO_IP}...")
        connected = await controller.connect()
        
        if not connected:
            print("❌ Failed to connect to Arduino")
            
            # Try manual status check
            print("\n3. Attempting manual status check...")
            await controller._create_session()
            status = await controller.get_status()
            print(f"   Manual status result: {status}")
            
            return False
            
        print("✅ Connected successfully!")

        # Test one emotion combination
        emotions = {"joy": 5, "fun": 2, "anger": 0, "sad": 0}
        print(f"\n4. Testing emotion pattern: {emotions}")

        pattern = VibrationPatternGenerator.from_emotion_values(
            joy=emotions["joy"],
            fun=emotions["fun"],
            anger=emotions["anger"],
            sad=emotions["sad"],
        )

        if pattern.steps:
            print(f"   Generated pattern: {len(pattern.steps)} steps, {pattern.repeat_count} repeats")
            for j, step in enumerate(pattern.steps):
                print(f"     Step {j+1}: intensity={step.intensity:.2f}, duration={step.duration}ms")
            
            # Send pattern to Arduino
            print("\n5. Sending pattern to Arduino...")
            success = await controller.send_pattern(pattern)
            if success:
                print("✅ Pattern sent successfully")
                await asyncio.sleep(3)  # Wait for pattern to complete
            else:
                print("❌ Failed to send pattern")
        else:
            print("   No pattern generated")
        
        # Disconnect
        await controller.disconnect()
        print("\n✅ Disconnected successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run debug test"""
    success = await test_emotion_patterns_debug()
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")

if __name__ == "__main__":
    asyncio.run(main())