#!/usr/bin/env python3
"""Test vibration flow to diagnose issue"""

import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Simulate a simple touch input
touch_input = {
    "data": 0.7,
    "touched_area": "頭",
    "gesture_type": "tap"
}

print("Sending touch input to agent:")
print(json.dumps(touch_input, ensure_ascii=False))
print(json.dumps(touch_input, ensure_ascii=False), flush=True)
