#!/usr/bin/env python3
"""
Test script for Leap Motion HTTP server with improved diagnostics
"""
import httpx
import asyncio
import json
import time
from datetime import datetime

async def test_leap_server(server_url):
    """Test all endpoints of the Leap Motion HTTP server"""
    
    async with httpx.AsyncClient() as client:
        print(f"\n=== Testing Leap Motion HTTP Server at {server_url} ===")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Test 1: Root endpoint
        try:
            response = await client.get(f"{server_url}/")
            print("1. Root endpoint:")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 2: Health check
        print("\n2. Health check:")
        try:
            response = await client.get(f"{server_url}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Leap available: {data.get('leap_available')}")
                print(f"   Leap connected: {data.get('leap_connected')}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 3: Debug information (more detailed)
        print("\n3. Debug information:")
        try:
            response = await client.get(f"{server_url}/debug")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                debug_data = response.json()
                print(f"   Response: {json.dumps(debug_data, indent=2)}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 4: Simple leap endpoint
        print("\n4. Simple leap data:")
        try:
            response = await client.get(f"{server_url}/leap")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 5: Continuous monitoring
        print("\n5. Continuous hand detection (10 seconds):")
        print("   Move your hand over the Leap Motion sensor...")
        
        start_time = time.time()
        detection_count = 0
        no_detection_count = 0
        
        while time.time() - start_time < 10:
            try:
                response = await client.get(f"{server_url}/leap")
                if response.status_code == 200:
                    data = response.json()
                    hands = data.get('hands', [])
                    
                    if hands:
                        detection_count += 1
                        print(f"\r   ✓ Hands detected: {len(hands)} hand(s) | "
                              f"Position: ({hands[0]['position']['x']:.1f}, "
                              f"{hands[0]['position']['y']:.1f}, "
                              f"{hands[0]['position']['z']:.1f}) | "
                              f"Velocity: {hands[0]['velocity']:.1f}", end="")
                    else:
                        no_detection_count += 1
                        print(f"\r   ✗ No hands detected ({no_detection_count} times)", end="")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"\n   Error during monitoring: {e}")
                break
        
        print(f"\n   Summary: Detected hands {detection_count} times out of "
              f"{detection_count + no_detection_count} checks")
        
        # Test 6: Touch input conversion
        print("\n6. Touch input conversion:")
        try:
            response = await client.get(f"{server_url}/touch-input")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 7: Leap data endpoint
        print("\n7. Full leap data:")
        try:
            response = await client.get(f"{server_url}/leap-data")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {json.dumps(response.json(), indent=2)}")
            elif response.status_code == 404:
                print(f"   No hand detected (404)")
            elif response.status_code == 503:
                print(f"   Leap Motion SDK not available (503)")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    import sys
    
    # デフォルトのサーバーURL
    server_url = "http://localhost:8001"
    
    # コマンドライン引数でサーバーURLを指定可能
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    
    print("Leap Motion HTTP Server Test")
    print(f"Testing server at: {server_url}")
    print("\nMake sure:")
    print("1. The Leap Motion device is connected")
    print("2. The server_http.py is running on the other PC")
    print("3. You can access the server from this PC")
    
    asyncio.run(test_leap_server(server_url))