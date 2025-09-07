#!/usr/bin/env python3
"""
Debug script to manually start MCP servers and test ADK agent
"""

import subprocess
import time
import signal
import sys
import os

def start_mcp_server(name, path):
    """Start an MCP server"""
    print(f"Starting {name}...")
    process = subprocess.Popen(
        ["python", path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    time.sleep(2)  # Wait for server to start
    
    if process.poll() is None:
        print(f"✅ {name} started (PID: {process.pid})")
        return process
    else:
        stdout, stderr = process.communicate()
        print(f"❌ {name} failed to start")
        print(f"   Stdout: {stdout}")
        print(f"   Stderr: {stderr}")
        return None

def stop_processes(processes):
    """Stop all processes"""
    for name, process in processes.items():
        if process:
            print(f"Stopping {name}...")
            process.terminate()
            process.wait()

def main():
    """Main function"""
    processes = {}
    
    def signal_handler(sig, frame):
        print("\n\nShutting down...")
        stop_processes(processes)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=== Manual MCP Server Startup ===\n")
    
    # Start servers
    processes["emoji_server"] = start_mcp_server(
        "emoji_server", 
        "mcp_servers/emoji_server.py"
    )
    
    processes["vibration_server"] = start_mcp_server(
        "vibration_server", 
        "mcp_servers/vibration_server.py"
    )
    
    # Check if all servers started
    if all(p is not None for p in processes.values()):
        print("\n✅ All MCP servers started successfully!")
        print("\nYou can now run ADK web in another terminal.")
        print("The MCP servers will continue running here.")
        print("Press Ctrl+C to stop the servers.\n")
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        print("\n❌ Some servers failed to start")
        stop_processes(processes)

if __name__ == "__main__":
    main()