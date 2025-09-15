#!/usr/bin/env python3
"""
Setup script for Leap Motion Python bindings
Provides alternative installation methods for Leap Motion SDK
"""

import os
import sys
import platform
import subprocess

def install_leap_python():
    """Install Leap Motion Python bindings"""
    system = platform.system()
    
    print(f"Detected system: {system}")
    
    # Try to install leap-python3 first (community maintained)
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "leap-python3"])
        print("Successfully installed leap-python3")
        return True
    except subprocess.CalledProcessError:
        print("Failed to install leap-python3")
    
    # Provide manual installation instructions
    print("\n" + "="*60)
    print("ULTRALEAP (LEAP MOTION) SDK INSTALLATION GUIDE")
    print("="*60)
    print("\nNOTE: Leap Motion is now Ultraleap. Latest version is Gemini V5.")
    print("GitHub: https://github.com/ultraleap")
    
    if system == "Linux":
        print("""
For Linux (Ubuntu/Debian):
1. Download Ultraleap Gemini V5 from: https://developer.leapmotion.com/
   (Free account required)
2. Install the .deb package:
   sudo dpkg -i Ultraleap-*-Linux.deb
3. Install Python bindings:
   cd /usr/share/Ultraleap/LeapSDK/lib
   sudo cp LeapPython.so /usr/local/lib/python3.*/dist-packages/
   sudo cp Leap.py /usr/local/lib/python3.*/dist-packages/
""")
    elif system == "Windows":
        print("""
For Windows:
1. Download Ultraleap Gemini V5 from: https://developer.leapmotion.com/
   (Free account required, v5.13.2 or later recommended)
2. Run the installer and SELECT the SDK component
3. Add Ultraleap SDK to Python path:
   - Find LeapSDK folder (C:\\Program Files\\Ultraleap\\LeapSDK)
   - Copy LeapPython.pyd and Leap.py to your Python site-packages
""")
    elif system == "Darwin":  # macOS
        print("""
For macOS:
1. Download Ultraleap Gemini V5 from: https://developer.leapmotion.com/
   (Free account required, v5.14.0 or later recommended)
2. Install the .dmg package and SELECT the SDK component
3. Install Python bindings:
   cd /Applications/Ultraleap.app/Contents/LeapSDK/lib
   sudo cp LeapPython.so /usr/local/lib/python3.*/site-packages/
   sudo cp Leap.py /usr/local/lib/python3.*/site-packages/
""")
    
    print("\nAlternatively, you can use the pyleap package:")
    print("pip install pyleap")
    
    return False

if __name__ == "__main__":
    success = install_leap_python()
    if success:
        print("\nLeap Motion Python bindings installed successfully!")
    else:
        print("\nPlease follow the manual installation instructions above.")