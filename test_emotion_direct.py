#!/usr/bin/env python3
"""
Direct test script for emotion pattern generation
"""

import asyncio
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from test_haptic_integration import test_emotion_patterns

async def main():
    """Run emotion pattern test directly"""
    print("Running Emotion Pattern Generation Test...")
    success = await test_emotion_patterns()
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")

if __name__ == "__main__":
    asyncio.run(main())