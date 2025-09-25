#!/usr/bin/env python3
"""Test simplified Leap Motion data retrieval approach."""

import requests
import json
import time

SERVER_URL = "http://192.168.43.162:8001"

print("Testing Leap Motion server endpoints...\n")

# Test available endpoints
endpoints = [
    "/",
    "/health", 
    "/leap-data",
    "/touch-input",
    "/gesture-mappings",
    "/leap",  # This might not exist
    "/debug"  # This might not exist
]

print("1. Checking available endpoints:")
for endpoint in endpoints:
    try:
        response = requests.get(f"{SERVER_URL}{endpoint}", timeout=2)
        status = "✓" if response.status_code == 200 else f"✗ ({response.status_code})"
        print(f"  {endpoint}: {status}")
    except Exception as e:
        print(f"  {endpoint}: ✗ (Error)")

# Focus on the working endpoint
print("\n2. Testing /touch-input endpoint repeatedly:")
for i in range(5):
    try:
        response = requests.get(f"{SERVER_URL}/touch-input", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"\nAttempt {i+1}:")
            print(f"  Raw data: {json.dumps(data, indent=2)}")
            
            # Check if raw_leap_data exists
            if 'raw_leap_data' in data and data['raw_leap_data']:
                print("  ✓ Leap data detected!")
                leap = data['raw_leap_data']
                print(f"    Position: {leap.get('hand_position', {})}")
                print(f"    Velocity: {leap.get('hand_velocity', 0)}")
            else:
                print("  - No Leap data in response")
    except Exception as e:
        print(f"\nAttempt {i+1}: Error - {e}")
    
    time.sleep(2)

print("\n3. Recommendation:")
print("The server seems to be working but not detecting hands.")
print("Possible issues to check on the server:")
print("- Ensure the Leap Motion SDK is properly installed")
print("- Check if the connection.open() call is successful")
print("- Verify the event listener is receiving tracking events")
print("- The listener might need to wait after connection.open()")
print("\nYou may need to add debug logging to server_http.py to see:")
print("- If on_tracking_event is being called")
print("- What data is in the event object")
print("- If event.hands exists and contains data")