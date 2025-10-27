#!/bin/bash
# 感情シンクロゲームのテスト

echo "=== 感情シンクロゲームテスト ===" >&2

# 1回目のタッチ（軽め）
echo '{"data": 0.3, "touched_area": "頭", "gesture_type": "pat"}'
sleep 2

# 2回目のタッチ（中程度）
echo '{"data": 0.5, "touched_area": "肩", "gesture_type": "tap"}'
sleep 2

# 3回目のタッチ（強め）
echo '{"data": 0.7, "touched_area": "背中", "gesture_type": "press"}'

echo "" >&2
echo "=== テスト完了 ===" >&2
