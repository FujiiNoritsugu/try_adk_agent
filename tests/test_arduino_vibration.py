#!/usr/bin/env python3
"""
Test script to verify Arduino vibration control
"""

import asyncio
import aiohttp
import json

async def test_arduino():
    """Test Arduino vibration control directly"""
    
    # Arduino接続設定
    host = "192.168.43.166"
    port = 80
    base_url = f"http://{host}:{port}"
    
    async with aiohttp.ClientSession() as session:
        # 1. ステータス確認
        print(f"[TEST] Checking Arduino status at {base_url}/status")
        try:
            async with session.get(f"{base_url}/status") as response:
                if response.status == 200:
                    status = await response.json()
                    print(f"[TEST] Status response: {json.dumps(status, indent=2)}")
                else:
                    print(f"[TEST] Status request failed: HTTP {response.status}")
        except Exception as e:
            print(f"[TEST] Status request error: {e}")
        
        # 2. シンプルな振動パターンを送信
        print("\n[TEST] Sending simple vibration pattern")
        
        # 最もシンプルなパターン
        simple_pattern = {
            "steps": [
                {"intensity": 80, "duration": 500},  # 80%強度で500ms
                {"intensity": 0, "duration": 200},   # 停止200ms
                {"intensity": 60, "duration": 300}   # 60%強度で300ms
            ],
            "interval": 50,
            "repeat_count": 1
        }
        
        print(f"[TEST] Pattern to send: {json.dumps(simple_pattern, indent=2)}")
        
        try:
            async with session.post(f"{base_url}/pattern", json=simple_pattern) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"[TEST] Pattern response: {json.dumps(result, indent=2)}")
                else:
                    print(f"[TEST] Pattern request failed: HTTP {response.status}")
                    text = await response.text()
                    print(f"[TEST] Response text: {text}")
        except Exception as e:
            print(f"[TEST] Pattern request error: {e}")
        
        # 3. 停止コマンドを送信
        print("\n[TEST] Sending stop command after 3 seconds")
        await asyncio.sleep(3)
        
        try:
            async with session.post(f"{base_url}/stop") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"[TEST] Stop response: {json.dumps(result, indent=2)}")
                else:
                    print(f"[TEST] Stop request failed: HTTP {response.status}")
        except Exception as e:
            print(f"[TEST] Stop request error: {e}")

if __name__ == "__main__":
    asyncio.run(test_arduino())