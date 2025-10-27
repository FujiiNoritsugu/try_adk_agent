#!/bin/bash
# 簡易テスト：3回の入力を送ってゲーム検出を確認

echo "=== 胸を3回タップ ===" >&2

echo '{"data": 0.5, "touched_area": "胸", "gesture_type": "tap"}'
sleep 0.5

echo '{"data": 0.5, "touched_area": "胸", "gesture_type": "tap"}'
sleep 0.5

echo '{"data": 0.5, "touched_area": "胸", "gesture_type": "tap"}'

echo "=== 送信完了 ===" >&2
