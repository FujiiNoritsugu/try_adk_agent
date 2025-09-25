#!/usr/bin/env python3
"""Debug script to test Leap Motion connection and data flow."""

import asyncio
import time
import logging
from datetime import datetime

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import Leap Motion library
try:
    import leap
    from leap import datatypes as ldt
    LEAP_AVAILABLE = True
    logger.info("✓ Leap Motion SDK imported successfully")
except ImportError as e:
    logger.error(f"✗ Failed to import Leap Motion SDK: {e}")
    LEAP_AVAILABLE = False
    exit(1)

class DebugLeapListener(leap.Listener):
    """Debug Leap Motion event listener with detailed logging"""
    def __init__(self):
        super().__init__()
        self.latest_frame = None
        self.frame_count = 0
        self.last_log_time = time.time()
        logger.info("DebugLeapListener initialized")

    def on_connection_event(self, event):
        """Log connection events"""
        logger.info(f"Connection event: {event}")

    def on_device_event(self, event):
        """Log device events"""
        logger.info(f"Device event: {event}")

    def on_tracking_event(self, event):
        """Store and log tracking events"""
        self.latest_frame = event
        self.frame_count += 1
        
        # Log every 100 frames or every 2 seconds
        current_time = time.time()
        if self.frame_count % 100 == 0 or (current_time - self.last_log_time) > 2:
            if event.hands:
                logger.info(f"Frame {self.frame_count}: {len(event.hands)} hand(s) detected")
                for i, hand in enumerate(event.hands):
                    pos = hand.palm.position
                    logger.debug(f"  Hand {i}: pos=({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})")
            else:
                logger.debug(f"Frame {self.frame_count}: No hands detected")
            self.last_log_time = current_time

def test_leap_connection():
    """Test basic Leap Motion connection"""
    logger.info("\n=== Testing Leap Motion Connection ===")
    
    try:
        # Create connection
        connection = leap.Connection()
        logger.info("✓ Leap Connection object created")
        
        # Create and add listener
        listener = DebugLeapListener()
        connection.add_listener(listener)
        logger.info("✓ Listener added to connection")
        
        # Open connection
        logger.info("Opening connection...")
        connection.open()
        logger.info("✓ Connection opened")
        
        # Wait for connection to establish
        logger.info("Waiting for connection to establish...")
        time.sleep(2)
        
        # Monitor for 10 seconds
        logger.info("\n=== Monitoring for 10 seconds ===")
        logger.info("Place your hand over the Leap Motion sensor...")
        
        for i in range(10):
            time.sleep(1)
            if listener.latest_frame:
                event = listener.latest_frame
                if event.hands:
                    logger.info(f"✓ Second {i+1}: {len(event.hands)} hand(s) detected!")
                    hand = event.hands[0]
                    pos = hand.palm.position
                    vel = hand.palm.velocity
                    vel_mag = (vel.x**2 + vel.y**2 + vel.z**2) ** 0.5
                    logger.info(f"  Position: ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})")
                    logger.info(f"  Velocity: {vel_mag:.1f} mm/s")
                else:
                    logger.info(f"- Second {i+1}: No hands detected")
            else:
                logger.warning(f"! Second {i+1}: No frames received")
        
        logger.info(f"\nTotal frames received: {listener.frame_count}")
        
        # Close connection
        connection.close()
        logger.info("✓ Connection closed")
        
    except Exception as e:
        logger.error(f"✗ Error during test: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

def test_direct_polling():
    """Test direct polling approach"""
    logger.info("\n=== Testing Direct Polling ===")
    
    try:
        connection = leap.Connection()
        connection.open()
        time.sleep(1)
        
        logger.info("Polling for 5 seconds...")
        for i in range(50):
            # Try to get tracking data directly
            # Note: This approach might vary based on SDK version
            time.sleep(0.1)
            logger.debug(f"Poll {i+1}")
            
    except Exception as e:
        logger.error(f"✗ Polling test failed: {e}")

if __name__ == "__main__":
    logger.info("=== Leap Motion Debug Script ===")
    logger.info(f"Python Leap SDK available: {LEAP_AVAILABLE}")
    
    if LEAP_AVAILABLE:
        # Test connection and event handling
        test_leap_connection()
        
        # Test direct polling if needed
        # test_direct_polling()
    else:
        logger.error("Cannot proceed without Leap Motion SDK")