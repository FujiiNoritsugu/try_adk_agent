#!/usr/bin/env python3
"""
Leap Motion to ADK Bridge
LeapMotionのHTTPサーバーからデータを取得し、ADKの標準入力形式で出力する
使用方法: python leap_to_adk_bridge.py | adk run agent_leap
"""

import asyncio
import httpx
import json
import sys
import logging
from datetime import datetime
from typing import Optional, Dict
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging (標準エラー出力に出力してADKの標準入力を妨げない)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class TouchInput:
    """ADKに送信するTouchInputデータ"""
    def __init__(self, data: float, touched_area: str,
                 gesture_type: Optional[str] = None,
                 hand_position: Optional[Dict[str, float]] = None,
                 hand_velocity: Optional[float] = None,
                 leap_confidence: Optional[float] = None):
        self.data = data
        self.touched_area = touched_area
        self.gesture_type = gesture_type
        self.hand_position = hand_position
        self.hand_velocity = hand_velocity
        self.leap_confidence = leap_confidence

    def to_dict(self):
        result = {
            "data": self.data,
            "touched_area": self.touched_area
        }
        if self.gesture_type:
            result["gesture_type"] = self.gesture_type
        if self.hand_position:
            result["hand_position"] = self.hand_position
        if self.hand_velocity is not None:
            result["hand_velocity"] = self.hand_velocity
        if self.leap_confidence is not None:
            result["leap_confidence"] = self.leap_confidence
        return result


async def poll_leap_motion(leap_server_url: str, poll_interval: float = 0.1,
                           min_process_interval: float = 0.5):
    """Leap Motionサーバーをポーリングし、データをADKに送信"""

    last_processed_time = None

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        logger.info(f"Starting Leap Motion polling from {leap_server_url}")

        while True:
            try:
                # Touch input形式でデータを取得
                response = await client.get(f"{leap_server_url}/touch-input")

                if response.status_code == 200:
                    data = response.json()

                    # モックデータでない、実際の手の検出があった場合のみ処理
                    if (not data.get("mock", False) and
                        data.get("gesture_type") != "none"):

                        # 最小間隔チェック
                        current_time = datetime.now()
                        if (last_processed_time is None or
                            (current_time - last_processed_time).total_seconds() >= min_process_interval):

                            # TouchInput形式に変換
                            touch_input = TouchInput(
                                data=data.get("data", 0.5),
                                touched_area=data.get("touched_area", "空中"),
                                gesture_type=data.get("gesture_type"),
                                hand_position=(
                                    data.get("raw_leap_data", {}).get("hand_position")
                                    if data.get("raw_leap_data") else None
                                ),
                                hand_velocity=(
                                    data.get("raw_leap_data", {}).get("hand_velocity")
                                    if data.get("raw_leap_data") else None
                                ),
                                leap_confidence=(
                                    data.get("raw_leap_data", {}).get("confidence", 1.0)
                                    if data.get("raw_leap_data") else None
                                )
                            )

                            # ADKの標準入力形式でJSON出力
                            output = json.dumps(touch_input.to_dict(), ensure_ascii=False)
                            print(output, flush=True)  # 標準出力に送信

                            logger.info(f"Sent to ADK: {touch_input.gesture_type} at {touch_input.touched_area}")
                            last_processed_time = current_time

                # 短い間隔でポーリング
                await asyncio.sleep(poll_interval)

            except httpx.RequestError as e:
                logger.error(f"Error polling Leap Motion server: {e}")
                logger.error(f"Server URL: {leap_server_url}")
                logger.error(f"Error type: {type(e).__name__}")
                await asyncio.sleep(1)  # エラー時は少し長めに待機
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                await asyncio.sleep(1)


def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Leap Motion to ADK Bridge")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (generates test data)")
    parser.add_argument("--url", default=os.getenv("LEAP_MOTION_SERVER_URL", "http://192.168.43.162:8001"),
                       help="Leap Motion server URL")
    args = parser.parse_args()

    leap_server_url = args.url
    poll_interval = float(os.getenv("LEAP_POLL_INTERVAL", "0.1"))
    min_process_interval = float(os.getenv("LEAP_MIN_PROCESS_INTERVAL", "0.5"))

    logger.info("=" * 60)
    logger.info("Leap Motion to ADK Bridge")
    if args.mock:
        logger.info("Mode: MOCK (generating test data)")
        logger.info("Will generate test gestures every 3 seconds")
    else:
        logger.info(f"Mode: LIVE")
        logger.info(f"Leap Motion Server: {leap_server_url}")
        logger.info(f"Poll Interval: {poll_interval}s")
        logger.info(f"Min Process Interval: {min_process_interval}s")
    logger.info("=" * 60)

    try:
        if args.mock:
            asyncio.run(mock_mode())
        else:
            asyncio.run(poll_leap_motion(leap_server_url, poll_interval, min_process_interval))
    except KeyboardInterrupt:
        logger.info("Bridge stopped by user")


async def mock_mode():
    """モックモード: テストデータを生成してADKに送信"""
    import random
    import json

    gestures = ["tap", "swipe", "circle", "grab"]
    areas = ["頭", "肩", "背中", "腕"]

    logger.info("Starting mock mode...")

    while True:
        try:
            # ランダムなテストデータを生成
            touch_input = TouchInput(
                data=random.uniform(0.3, 0.8),
                touched_area=random.choice(areas),
                gesture_type=random.choice(gestures),
                hand_velocity=random.uniform(50, 200),
                leap_confidence=random.uniform(0.8, 1.0)
            )

            # ADKの標準入力形式でJSON出力
            output = json.dumps(touch_input.to_dict(), ensure_ascii=False)
            print(output, flush=True)  # 標準出力に送信

            logger.info(f"[MOCK] Sent: {touch_input.gesture_type} at {touch_input.touched_area} (intensity: {touch_input.data:.2f})")

            # 3秒待機
            await asyncio.sleep(3)

        except KeyboardInterrupt:
            logger.info("Mock mode stopped")
            break
        except Exception as e:
            logger.error(f"Error in mock mode: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    main()
