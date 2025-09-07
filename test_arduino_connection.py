#!/usr/bin/env python3
"""
Debug script for Arduino connection
"""

import asyncio
import aiohttp
import json

async def test_connection():
    """Test basic HTTP connection to Arduino"""
    ARDUINO_IP = "192.168.43.166"
    ARDUINO_PORT = 80
    
    print(f"Testing connection to Arduino at {ARDUINO_IP}:{ARDUINO_PORT}...")
    
    # Test with curl first
    print("\n1. Testing with basic HTTP request...")
    
    timeout = aiohttp.ClientTimeout(total=5.0)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Try status endpoint
            url = f"http://{ARDUINO_IP}:{ARDUINO_PORT}/status"
            print(f"   Requesting: {url}")
            
            try:
                async with session.get(url) as response:
                    print(f"   Response status: {response.status}")
                    if response.status == 200:
                        data = await response.text()
                        print(f"   Response data: {data}")
                        try:
                            json_data = json.loads(data)
                            print(f"   Parsed JSON: {json.dumps(json_data, indent=2)}")
                        except json.JSONDecodeError:
                            print("   Response is not valid JSON")
                    else:
                        print(f"   Unexpected status code: {response.status}")
            except asyncio.TimeoutError:
                print("   ❌ Connection timeout - Arduino may not be reachable")
            except aiohttp.ClientConnectorError as e:
                print(f"   ❌ Connection error: {e}")
            except Exception as e:
                print(f"   ❌ Unexpected error: {type(e).__name__}: {e}")
                
            # Try root endpoint
            print("\n2. Testing root endpoint...")
            url = f"http://{ARDUINO_IP}:{ARDUINO_PORT}/"
            print(f"   Requesting: {url}")
            
            try:
                async with session.get(url) as response:
                    print(f"   Response status: {response.status}")
                    if response.status == 200:
                        data = await response.text()
                        print(f"   Response preview: {data[:200]}...")
            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {e}")
                
    except Exception as e:
        print(f"❌ Session creation failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())