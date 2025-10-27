#!/bin/bash
# クイックテスト：3回の胸タップを0.3秒間隔で送信

echo '{"data": 0.5, "touched_area": "胸", "gesture_type": "tap"}'
sleep 0.3
echo '{"data": 0.5, "touched_area": "胸", "gesture_type": "tap"}'
sleep 0.3
echo '{"data": 0.5, "touched_area": "胸", "gesture_type": "tap"}'
