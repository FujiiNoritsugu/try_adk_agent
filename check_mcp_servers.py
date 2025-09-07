#!/usr/bin/env python3
"""
Check if MCP servers are running
"""

import subprocess
import psutil
import os

def check_process_running(process_name):
    """Check if a process with the given name is running"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and process_name in ' '.join(proc.info['cmdline']):
                return True, proc.info
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False, None

def check_mcp_servers():
    """Check the status of MCP servers"""
    print("=== MCP Server Status Check ===\n")
    
    # Check emoji server
    print("1. Checking emoji_server.py...")
    running, info = check_process_running("emoji_server.py")
    if running:
        print(f"   ✅ Running (PID: {info['pid']})")
    else:
        print("   ❌ Not running")
    
    # Check vibration server
    print("\n2. Checking vibration_server.py...")
    running, info = check_process_running("vibration_server.py")
    if running:
        print(f"   ✅ Running (PID: {info['pid']})")
    else:
        print("   ❌ Not running")
    
    # Check if the server files exist
    print("\n3. Checking server files...")
    servers = ["mcp_servers/emoji_server.py", "mcp_servers/vibration_server.py"]
    for server in servers:
        if os.path.exists(server):
            print(f"   ✅ {server} exists")
        else:
            print(f"   ❌ {server} not found")
    
    # Try to start servers manually
    print("\n4. Testing manual server startup...")
    
    # Test emoji server
    print("   Testing emoji_server.py...")
    try:
        result = subprocess.run(
            ["python", "mcp_servers/emoji_server.py", "--help"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            print("   ✅ emoji_server.py can be executed")
        else:
            print(f"   ❌ emoji_server.py error: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Failed to test emoji_server.py: {e}")
    
    # Test vibration server
    print("   Testing vibration_server.py...")
    try:
        result = subprocess.run(
            ["python", "mcp_servers/vibration_server.py", "--help"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            print("   ✅ vibration_server.py can be executed")
        else:
            print(f"   ❌ vibration_server.py error: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Failed to test vibration_server.py: {e}")

if __name__ == "__main__":
    check_mcp_servers()