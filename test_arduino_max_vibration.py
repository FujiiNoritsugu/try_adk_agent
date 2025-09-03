#!/usr/bin/env python3
"""
Test script to send maximum vibration to Arduino
"""

import asyncio
import aiohttp
import json

async def test_max_vibration():
    """Test Arduino with maximum vibration intensity"""
    
    # Arduino接続設定
    host = "192.168.43.166"
    port = 80
    base_url = f"http://{host}:{port}"
    
    async with aiohttp.ClientSession() as session:
        print("[TEST] Testing maximum vibration intensity")
        
        # 最大強度のシンプルなパターン
        max_pattern = {
            "steps": [
                {"intensity": 100, "duration": 1000},  # 100%強度で1秒
                {"intensity": 0, "duration": 500},     # 停止0.5秒
                {"intensity": 100, "duration": 1000},  # 100%強度で1秒
            ],
            "interval": 0,  # インターバルなし
            "repeat_count": 3  # 3回繰り返し
        }
        
        print(f"[TEST] Sending MAX intensity pattern: {json.dumps(max_pattern, indent=2)}")
        
        try:
            async with session.post(f"{base_url}/pattern", json=max_pattern) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"[TEST] Pattern response: {json.dumps(result, indent=2)}")
                else:
                    print(f"[TEST] Pattern request failed: HTTP {response.status}")
                    text = await response.text()
                    print(f"[TEST] Response text: {text}")
        except Exception as e:
            print(f"[TEST] Pattern request error: {e}")
        
        # 10秒待機
        print("\n[TEST] Waiting 10 seconds for pattern to complete...")
        await asyncio.sleep(10)
        
        # PWMテスト - 直接PWM値を送信する別のパターン
        print("\n[TEST] Testing with different PWM values")
        test_patterns = [
            {"name": "Low", "intensity": 30},
            {"name": "Medium", "intensity": 60},
            {"name": "High", "intensity": 85},
            {"name": "Maximum", "intensity": 100},
        ]
        
        for test in test_patterns:
            pattern = {
                "steps": [{"intensity": test["intensity"], "duration": 2000}],
                "interval": 0,
                "repeat_count": 1
            }
            
            print(f"\n[TEST] Testing {test['name']} intensity ({test['intensity']}%)")
            
            try:
                async with session.post(f"{base_url}/pattern", json=pattern) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"[TEST] Response: {result}")
                    else:
                        print(f"[TEST] Failed: HTTP {response.status}")
            except Exception as e:
                print(f"[TEST] Error: {e}")
            
            await asyncio.sleep(3)
        
        # 停止
        print("\n[TEST] Sending stop command")
        try:
            async with session.post(f"{base_url}/stop") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"[TEST] Stop response: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"[TEST] Stop error: {e}")

if __name__ == "__main__":
    print("=== Arduino Maximum Vibration Test ===")
    print("Make sure:")
    print("1. Arduino is powered properly")
    print("2. Vibration motor is connected to pin 9")
    print("3. Motor driver/transistor is working")
    print("4. Power supply is sufficient for the motor")
    print("=====================================\n")
    
    asyncio.run(test_max_vibration())