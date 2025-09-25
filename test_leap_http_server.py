#!/usr/bin/env python3
"""Test Leap Motion HTTP server connection and data retrieval."""

import requests
import json
import time
import sys
from datetime import datetime

# Server configuration - update port if needed
SERVER_IP = "192.168.43.162"
SERVER_PORT = 8001  # Change to 8001 if using default port

BASE_URL = f"http://{SERVER_IP}:{SERVER_PORT}"

def test_connection():
    """Test basic connection to the server."""
    print(f"\n1. Testing connection to {BASE_URL}")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print(f"✓ Server is reachable! Status: {response.status_code}")
            data = response.json()
            print(f"  Service: {data.get('service', 'Unknown')}")
            print(f"  Version: {data.get('version', 'Unknown')}")
            print(f"  Leap Available: {data.get('leap_available', False)}")
            return True
        else:
            print(f"✗ Server returned status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Connection failed: {e}")
        return False

def test_health():
    """Test health endpoint."""
    print(f"\n2. Testing health endpoint")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health check passed")
            print(f"  Status: {data.get('status', 'unknown')}")
            print(f"  Leap Connected: {data.get('leap_connected', False)}")
            return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
    return False

def test_leap_data():
    """Test Leap Motion data endpoint."""
    print(f"\n3. Testing Leap Motion data endpoint")
    try:
        response = requests.get(f"{BASE_URL}/leap-data", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Leap data received successfully!")
            print(f"  Hand Position: x={data['hand_position']['x']:.1f}, y={data['hand_position']['y']:.1f}, z={data['hand_position']['z']:.1f}")
            print(f"  Hand Velocity: {data['hand_velocity']:.1f}")
            print(f"  Gesture Type: {data['gesture_type']}")
            print(f"  Fingers Extended: {data['fingers_extended']}")
            print(f"  Confidence: {data['confidence']:.2f}")
            return True
        elif response.status_code == 404:
            data = response.json()
            print(f"! No hand detected: {data.get('message', 'Unknown error')}")
            return True  # Server is working, just no hand
        elif response.status_code == 503:
            print(f"✗ Leap Motion SDK not available on server")
            return False
    except Exception as e:
        print(f"✗ Failed to get Leap data: {e}")
    return False

def test_touch_input():
    """Test touch input conversion endpoint."""
    print(f"\n4. Testing touch input conversion")
    try:
        response = requests.get(f"{BASE_URL}/touch-input", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Touch input data received!")
            print(f"  Intensity: {data['data']}")
            print(f"  Touched Area: {data['touched_area']}")
            print(f"  Gesture Type: {data['gesture_type']}")
            if data.get('mock', False):
                print(f"  (Using mock data - Leap Motion not available)")
            return True
    except Exception as e:
        print(f"✗ Failed to get touch input: {e}")
    return False

def monitor_realtime(duration=10):
    """Monitor Leap Motion data in real-time."""
    print(f"\n5. Real-time monitoring for {duration} seconds")
    print("Move your hand over the Leap Motion controller")
    print("-" * 60)
    
    start_time = time.time()
    samples = 0
    hands_detected = 0
    
    while time.time() - start_time < duration:
        try:
            response = requests.get(f"{BASE_URL}/leap-data", timeout=1)
            samples += 1
            
            if response.status_code == 200:
                data = response.json()
                hands_detected += 1
                pos = data['hand_position']
                vel = data['hand_velocity']
                gesture = data['gesture_type']
                fingers = data['fingers_extended']
                
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"[{timestamp}] Hand: x={pos['x']:6.1f} y={pos['y']:6.1f} z={pos['z']:6.1f} | vel={vel:6.1f} | {gesture:8s} | fingers={fingers}")
            elif response.status_code == 404:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"[{timestamp}] No hand detected")
                
            time.sleep(0.2)  # 5 Hz update rate
            
        except Exception as e:
            print(f"Error: {type(e).__name__}")
            time.sleep(0.5)
    
    print("-" * 60)
    print(f"Monitoring complete:")
    print(f"  Total samples: {samples}")
    print(f"  Hands detected: {hands_detected} ({hands_detected/samples*100:.1f}%)")

def test_gesture_mappings():
    """Test gesture mapping endpoints."""
    print(f"\n6. Testing gesture mappings")
    try:
        # Get current mappings
        response = requests.get(f"{BASE_URL}/gesture-mappings", timeout=5)
        if response.status_code == 200:
            mappings = response.json()
            print(f"✓ Current gesture mappings:")
            for gesture, mapping in mappings.items():
                print(f"  {gesture}: intensity={mapping['intensity']}, area={mapping['area']}")
            return True
    except Exception as e:
        print(f"✗ Failed to get gesture mappings: {e}")
    return False

def main():
    print("=" * 60)
    print(f"Leap Motion HTTP Server Test")
    print(f"Target: {BASE_URL}")
    print("=" * 60)
    
    # Run tests
    if not test_connection():
        print("\n❌ Cannot connect to server!")
        print("\nTroubleshooting:")
        print(f"1. Check if server is running on {SERVER_IP}:{SERVER_PORT}")
        print("2. Verify network connectivity between machines")
        print("3. Check firewall settings (allow port 8080 or 8001)")
        print("4. If using different port, update SERVER_PORT in this script")
        sys.exit(1)
    
    test_health()
    test_leap_data()
    test_touch_input()
    test_gesture_mappings()
    
    # Ask for real-time monitoring
    print("\n" + "=" * 60)
    try:
        response = input("Run real-time monitoring? (y/N): ").strip().lower()
        if response == 'y':
            monitor_realtime(10)
    except KeyboardInterrupt:
        print("\nSkipping real-time monitoring")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()