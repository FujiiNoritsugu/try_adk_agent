#!/usr/bin/env python3
"""Test direct vibration to Arduino"""

import asyncio
import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from src.devices import ArduinoController, VibrationPatternGenerator


async def test_vibration():
    """Test Arduino vibration directly"""

    print("=== Testing Arduino Vibration ===")

    # Create controller
    arduino = ArduinoController(
        device_id="test",
        host="192.168.43.166",
        port=80
    )

    print("Connecting to Arduino...")
    connected = await arduino.connect()

    if not connected:
        print("Failed to connect to Arduino!")
        return

    print("Connected! Getting status...")
    status = await arduino.get_status()
    print(f"Status: {status}")

    print("\nGenerating vibration pattern...")
    pattern = VibrationPatternGenerator.create_custom_pattern(
        pattern_type="pulse",
        intensity=0.7,
        duration_ms=1000,
        repeat_count=3
    )
    print(f"Pattern: {pattern.to_dict()}")

    print("\nSending pattern to Arduino...")
    success = await arduino.send_pattern(pattern)
    print(f"Send result: {success}")

    if success:
        print("✓ Vibration should be running now!")
        await asyncio.sleep(2)
    else:
        print("✗ Failed to send vibration")

    print("\nStopping vibration...")
    await arduino.stop()

    print("\nDisconnecting...")
    await arduino.disconnect()

    print("Done!")


if __name__ == "__main__":
    asyncio.run(test_vibration())
