#!/bin/bash
# LeapMotion Bridge とADKエージェントの統合テスト
# モックデータを送信してADKが反応するかテスト

# モックデータを5秒間隔で3回送信
for i in {1..3}; do
    echo "Sending test input $i..."
    echo '{"data": 0.7, "touched_area": "頭", "gesture_type": "tap"}'
    sleep 2
done
