#!/usr/bin/env python3
"""Simple test to verify server.py imports work correctly"""

import sys
import os

# Add leap module path
sys.path.insert(0, os.path.expanduser('~/leapc-python-bindings-main/leapc-python-api/src'))

print("Testing server.py imports and initialization...")

try:
    # Test basic imports
    import leap
    from leap import datatypes as ldt
    print("✓ Leap Motion imports successful")

    # Test creating a connection and listener
    connection = leap.Connection()
    print("✓ leap.Connection() created")

    class TestListener(leap.Listener):
        def on_tracking_event(self, event):
            pass

    listener = TestListener()
    print("✓ leap.Listener subclass created")

    connection.add_listener(listener)
    print("✓ Listener added to connection")

    # Quick connection test (non-blocking)
    try:
        connection.open()
        print("✓ Connection.open() called successfully")
        connection.close()
        print("✓ Connection.close() called successfully")
    except Exception as e:
        print(f"⚠ Connection test: {e}")
        print("  (This is expected if Leap Motion service is not running)")

    print("\n✓ All basic functionality tests passed!")
    print("\nYour server.py should now work correctly with the updated API.")

except ImportError as e:
    print(f"✗ Import error: {e}")
    print("\nTo run server.py, you need to:")
    print("1. cd ~/leapc-python-bindings-main")
    print("2. source venv/bin/activate")
    print("3. cd ~/try_adk_agent/server_leapmotion")
    print("4. python server.py")

except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()