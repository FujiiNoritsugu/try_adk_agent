#!/usr/bin/env python3
"""Network connectivity diagnostic tool for Leap Motion server."""

import subprocess
import socket
import asyncio
import aiohttp

SERVER_IP = "192.168.43.162"
SERVER_PORT = 5000


def ping_test():
    """Test basic network connectivity with ping."""
    print(f"1. Testing ping to {SERVER_IP}...")
    try:
        result = subprocess.run(
            ["ping", "-c", "3", SERVER_IP],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✓ Ping successful!")
            print(result.stdout.split('\n')[-3:-1])  # Show statistics
        else:
            print("✗ Ping failed")
            print(result.stderr)
    except subprocess.TimeoutExpired:
        print("✗ Ping timed out")
    except Exception as e:
        print(f"✗ Ping error: {e}")


def port_scan():
    """Test if the port is open."""
    print(f"\n2. Testing port {SERVER_PORT} connectivity...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    
    try:
        result = sock.connect_ex((SERVER_IP, SERVER_PORT))
        if result == 0:
            print(f"✓ Port {SERVER_PORT} is open")
        else:
            print(f"✗ Port {SERVER_PORT} is closed or unreachable (error code: {result})")
    except socket.gaierror:
        print("✗ Hostname could not be resolved")
    except socket.error as e:
        print(f"✗ Socket error: {e}")
    finally:
        sock.close()


async def http_test():
    """Test HTTP connectivity with detailed error information."""
    print(f"\n3. Testing HTTP connection to http://{SERVER_IP}:{SERVER_PORT}...")
    
    timeout = aiohttp.ClientTimeout(total=5)
    connector = aiohttp.TCPConnector(force_close=True)
    
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        try:
            async with session.get(f"http://{SERVER_IP}:{SERVER_PORT}/") as response:
                print(f"✓ HTTP connection successful! Status: {response.status}")
                print(f"Headers: {dict(response.headers)}")
        except aiohttp.ClientConnectorError as e:
            print(f"✗ Connection error: {e}")
            print("  Possible causes:")
            print("  - Server is not running")
            print("  - Firewall is blocking the connection")
            print("  - Wrong IP address or port")
        except asyncio.TimeoutError:
            print("✗ Connection timed out")
            print("  The server might be running but very slow to respond")
        except Exception as e:
            print(f"✗ Unexpected error: {type(e).__name__}: {e}")


def network_info():
    """Display local network information."""
    print("\n4. Local network information:")
    try:
        # Get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"   Your IP: {local_ip}")
        
        # Check if on same subnet (simple check for common subnets)
        local_parts = local_ip.split('.')
        server_parts = SERVER_IP.split('.')
        if local_parts[:3] == server_parts[:3]:
            print(f"   ✓ Appears to be on same subnet")
        else:
            print(f"   ⚠ May be on different subnet")
            
    except Exception as e:
        print(f"   Could not get network info: {e}")


def main():
    """Run all diagnostic tests."""
    print("=== Leap Motion Server Connectivity Diagnostics ===")
    print(f"Target: {SERVER_IP}:{SERVER_PORT}")
    print("=" * 50)
    
    # Run synchronous tests
    ping_test()
    port_scan()
    network_info()
    
    # Run async test
    asyncio.run(http_test())
    
    print("\n=== Troubleshooting Guide ===")
    print("If all tests fail:")
    print("1. Verify the server is running: python ~/server_leapmotion/server.py")
    print("2. Check server logs for binding errors")
    print("3. Ensure firewall allows incoming connections on port 5000")
    print("4. Verify both machines are on the same network")
    print("5. Try temporarily disabling firewall on the server machine")
    print(f"\nOn the server machine, run:")
    print(f"  netstat -tlnp | grep {SERVER_PORT}")
    print(f"  sudo ufw status (check firewall)")


if __name__ == "__main__":
    main()