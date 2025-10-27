#!/bin/bash
# リズムゲームのテスト

echo "=== リズムゲームテスト ===" >&2

# リズムゲーム開始
echo '{"data": 0.5, "touched_area": "頭", "gesture_type": "tap"}'
sleep 3

# リズムパターンを覚えた後、タッチ（想定: 0.5秒間隔で3回）
echo '{"data": 0.5, "touched_area": "頭", "gesture_type": "tap"}'
sleep 0.5

echo '{"data": 0.5, "touched_area": "頭", "gesture_type": "tap"}'
sleep 0.5

echo '{"data": 0.5, "touched_area": "頭", "gesture_type": "tap"}'

echo "" >&2
echo "=== テスト完了 ===" >&2
