#!/usr/bin/env python3
"""Test connection to Leap Motion server on remote machine."""

import json
import asyncio
import aiohttp
from mcp import ClientSession
from mcp.client.session import ClientSession as MCPSession


SERVER_IP = "192.168.43.162"
SERVER_PORT = 5000


async def test_mcp_over_http():
    """Test MCP connection over HTTP."""
    
    print(f"\n--- Testing MCP over HTTP to {SERVER_IP}:{SERVER_PORT} ---")
    
    base_url = f"http://{SERVER_IP}:{SERVER_PORT}/mcp/v1"
    
    try:
        async with aiohttp.ClientSession() as http_session:
            # Test listing tools
            async with http_session.get(f"{base_url}/tools") as response:
                if response.status == 200:
                    tools_data = await response.json()
                    print("✓ Successfully retrieved tools list:")
                    for tool in tools_data.get("tools", []):
                        print(f"  - {tool['name']}: {tool['description']}")
                else:
                    print(f"✗ Failed to get tools: HTTP {response.status}")
                    return
            
            # Test get_hand_data
            print("\n--- Testing get_hand_data ---")
            tool_call = {
                "name": "get_hand_data",
                "arguments": {}
            }
            
            async with http_session.post(f"{base_url}/tools/call", json=tool_call) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"Hand data: {json.dumps(result, indent=2)}")
                else:
                    print(f"✗ Failed to call get_hand_data: HTTP {response.status}")
                    error = await response.text()
                    print(f"Error: {error}")
            
            # Test detect_gesture
            print("\n--- Testing detect_gesture ---")
            tool_call = {
                "name": "detect_gesture",
                "arguments": {}
            }
            
            async with http_session.post(f"{base_url}/tools/call", json=tool_call) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"Gesture data: {json.dumps(result, indent=2)}")
                else:
                    print(f"✗ Failed to call detect_gesture: HTTP {response.status}")
            
            # Monitor real-time data
            print("\n--- Real-time monitoring (5 samples, 1 second apart) ---")
            for i in range(5):
                await asyncio.sleep(1)
                
                tool_call = {
                    "name": "get_hand_data",
                    "arguments": {}
                }
                
                async with http_session.post(f"{base_url}/tools/call", json=tool_call) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = json.loads(result.get("content", [{}])[0].get("text", "{}"))
                        
                        if content.get("hands_detected", 0) > 0:
                            pos = content.get("position", {})
                            vel = content.get("velocity", 0)
                            print(f"Sample {i+1}: Hand detected at ({pos.get('x', 0):.1f}, {pos.get('y', 0):.1f}, {pos.get('z', 0):.1f}), velocity: {vel:.1f}")
                        else:
                            print(f"Sample {i+1}: No hands detected")
                    else:
                        print(f"Sample {i+1}: Request failed")
                        
    except aiohttp.ClientConnectorError as e:
        print(f"✗ Cannot connect to server: {e}")
        print("\nPlease check:")
        print("1. Server is running on the remote machine")
        print("2. Firewall allows connections on port 5000")
        print("3. Both machines are on the same network")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


async def test_direct_http():
    """Test direct HTTP connection to the server."""
    
    print(f"--- Testing direct HTTP connection to {SERVER_IP}:{SERVER_PORT} ---")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test basic connectivity
            try:
                async with session.get(f"http://{SERVER_IP}:{SERVER_PORT}/", timeout=5) as response:
                    print(f"✓ Server responded with status {response.status}")
            except asyncio.TimeoutError:
                print("✗ Connection timed out after 5 seconds")
                return False
            except Exception as e:
                print(f"✗ Connection failed: {e}")
                return False
            
            # Test health endpoint if available
            try:
                async with session.get(f"http://{SERVER_IP}:{SERVER_PORT}/health", timeout=5) as response:
                    if response.status == 200:
                        print("✓ Health check passed")
                    else:
                        print(f"Health check returned status {response.status}")
            except:
                print("Health endpoint not available")
            
            return True
                    
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


async def main():
    """Run all tests."""
    # First test direct HTTP connection
    connected = await test_direct_http()
    
    if connected:
        # Then test MCP functionality
        await test_mcp_over_http()
    else:
        print("\nCannot proceed with MCP tests - server is not reachable")


if __name__ == "__main__":
    asyncio.run(main())