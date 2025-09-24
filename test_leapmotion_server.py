#!/usr/bin/env python3
"""Test script to verify Leap Motion server functionality"""

import sys
import os

# Add leap module path
sys.path.insert(0, os.path.expanduser('~/leapc-python-bindings-main/leapc-python-api/src'))

try:
    import leap
    from leap import datatypes as ldt
    print("✓ Leap Motion module imported successfully")
    print(f"  Module location: {leap.__file__}")

    # Test creating a connection
    connection = leap.Connection()
    print("✓ Leap.Connection created successfully")

    # Test creating a listener
    class TestListener(leap.Listener):
        def __init__(self):
            super().__init__()
            self.frame_count = 0

        def on_tracking_event(self, event):
            self.frame_count += 1
            if self.frame_count == 1:
                print(f"✓ Received first tracking event")
                print(f"  Tracking frame ID: {event.tracking_frame_id}")
                print(f"  Number of hands: {len(event.hands)}")

                if event.hands:
                    hand = event.hands[0]
                    print(f"  Hand detected:")
                    print(f"    Position: ({hand.palm.position.x:.1f}, {hand.palm.position.y:.1f}, {hand.palm.position.z:.1f})")
                    print(f"    Type: {hand.type}")

    listener = TestListener()
    print("✓ TestListener created successfully")

    # Test adding listener to connection
    connection.add_listener(listener)
    print("✓ Listener added to connection")

    # Try to open connection
    print("\nAttempting to open Leap Motion connection...")
    print("Please ensure Leap Motion device is connected and service is running.")

    try:
        with connection.open():
            print("✓ Connection opened successfully")
            print("\nWaiting for frames (place your hand over the sensor)...")
            print("Press Ctrl+C to stop\n")

            import time
            start_time = time.time()
            last_report = 0

            while True:
                current_time = time.time() - start_time
                if current_time - last_report > 5:
                    print(f"  [{current_time:.0f}s] Frames received: {listener.frame_count}")
                    last_report = current_time
                time.sleep(0.1)

    except KeyboardInterrupt:
        print(f"\n\nTest stopped. Total frames received: {listener.frame_count}")
        if listener.frame_count > 0:
            print("✓ Leap Motion is working correctly!")
        else:
            print("⚠ No frames received. Check if:")
            print("  - Leap Motion device is connected")
            print("  - Leap Motion service/daemon is running")
            print("  - Your hand was placed over the sensor")
    except Exception as e:
        print(f"✗ Failed to open connection: {e}")
        print("\nTroubleshooting:")
        print("  1. Check if Leap Motion device is connected (USB)")
        print("  2. Check if Leap Motion service is running:")
        print("     - Linux: sudo systemctl status leapd")
        print("     - Or: sudo leapd")
        print("  3. Check permissions (may need to run as sudo)")

except ImportError as e:
    print(f"✗ Failed to import leap module: {e}")
    print("\nPlease ensure:")
    print("  1. leapc-python-bindings is installed")
    print("  2. The path to the module is correct")
    print(f"  3. Current sys.path: {sys.path[:3]}")
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()