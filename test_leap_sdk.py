#!/usr/bin/env python3
"""Test basic Leap Motion SDK functionality."""

import time
import sys

try:
    import leap
    print("✓ Leap Motion SDK imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Leap Motion SDK: {e}")
    sys.exit(1)

class TestListener(leap.Listener):
    def __init__(self):
        super().__init__()
        self.events_received = {
            "connection": 0,
            "device": 0,
            "tracking": 0
        }
        print("TestListener initialized")
    
    def on_connection_event(self, event):
        self.events_received["connection"] += 1
        print(f"Connection event: {event}")
    
    def on_device_event(self, event):
        self.events_received["device"] += 1
        print(f"Device event: {event}")
        if hasattr(event, 'device'):
            print(f"  Device info: {event.device}")
    
    def on_tracking_event(self, event):
        self.events_received["tracking"] += 1
        if self.events_received["tracking"] % 30 == 1:  # Log every 30 frames
            hands = len(event.hands) if hasattr(event, 'hands') and event.hands else 0
            print(f"Tracking event #{self.events_received['tracking']}: {hands} hands")

def test_basic_connection():
    """Test basic Leap Motion connection."""
    print("\n1. Creating Leap Connection...")
    connection = leap.Connection()
    print("✓ Connection object created")
    
    print("\n2. Creating and adding listener...")
    listener = TestListener()
    connection.add_listener(listener)
    print("✓ Listener added")
    
    print("\n3. Opening connection...")
    connection.open()
    print("✓ Connection opened")
    
    print("\n4. Waiting for events (10 seconds)...")
    print("Place your hand over the Leap Motion sensor")
    
    for i in range(10):
        time.sleep(1)
        print(f"\rSecond {i+1}: Events - Connection:{listener.events_received['connection']}, "
              f"Device:{listener.events_received['device']}, "
              f"Tracking:{listener.events_received['tracking']}", end="")
    
    print("\n\n5. Event summary:")
    for event_type, count in listener.events_received.items():
        print(f"  {event_type}: {count} events")
    
    print("\n6. Closing connection...")
    connection.close()
    print("✓ Connection closed")

def test_polling_approach():
    """Test different approach with polling."""
    print("\n\nTesting polling approach...")
    
    # Create connection without listener
    connection = leap.Connection()
    connection.open()
    time.sleep(1)
    
    print("Checking connection state...")
    # The exact API might vary, but we can try different approaches
    
    connection.close()

if __name__ == "__main__":
    print("=== Leap Motion SDK Basic Test ===")
    
    # Test basic connection with events
    test_basic_connection()
    
    # Test polling if needed
    # test_polling_approach()
    
    print("\nTest complete!")