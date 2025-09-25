#!/usr/bin/env python3
"""Real-time monitoring of Leap Motion data."""

import requests
import json
import time
from datetime import datetime

SERVER_URL = "http://192.168.43.162:8001"

def monitor():
    print("Leap Motionデータのリアルタイム監視を開始します...")
    print("手をLeap Motionコントローラーの上にかざしてください")
    print("=" * 70)
    
    no_hand_count = 0
    
    try:
        while True:
            try:
                # Get leap data
                response = requests.get(f"{SERVER_URL}/leap-data", timeout=1)
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                if response.status_code == 200:
                    data = response.json()
                    pos = data['hand_position']
                    vel = data['hand_velocity']
                    gesture = data['gesture_type']
                    fingers = data['fingers_extended']
                    conf = data['confidence']
                    
                    print(f"[{timestamp}] ✋ 手を検出!")
                    print(f"  位置: X={pos['x']:7.1f}, Y={pos['y']:7.1f}, Z={pos['z']:7.1f}")
                    print(f"  速度: {vel:7.1f} mm/s")
                    print(f"  ジェスチャー: {gesture}")
                    print(f"  伸ばした指: {fingers}本")
                    print(f"  信頼度: {conf:.2f}")
                    
                    # Also get touch input format
                    touch_response = requests.get(f"{SERVER_URL}/touch-input", timeout=1)
                    if touch_response.status_code == 200:
                        touch_data = touch_response.json()
                        print(f"  タッチ強度: {touch_data['data']}")
                        print(f"  タッチエリア: {touch_data['touched_area']}")
                    
                    print("-" * 70)
                    no_hand_count = 0
                    
                elif response.status_code == 404:
                    no_hand_count += 1
                    if no_hand_count % 5 == 1:  # Print every 5th time
                        print(f"[{timestamp}] 手が検出されていません...")
                
            except requests.exceptions.RequestException:
                print(f"[{timestamp}] 接続エラー")
                
            time.sleep(0.5)  # 2Hz update rate
            
    except KeyboardInterrupt:
        print("\n\n監視を終了しました")

if __name__ == "__main__":
    monitor()