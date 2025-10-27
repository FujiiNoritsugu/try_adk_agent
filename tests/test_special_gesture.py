#!/usr/bin/env python3
"""
特殊ジェスチャー検出のテスト
胸を3回タップする入力をシミュレートして、ゲーム開始が正しく検出されるか確認
"""

import json
import time
import sys

def create_touch_input(touched_area: str, intensity: float = 0.5):
    """Touch入力JSONを生成"""
    return {
        "data": intensity,
        "touched_area": touched_area,
        "gesture_type": "tap"
    }

def main():
    print("=== 特殊ジェスチャー検出テスト ===", file=sys.stderr)
    print("胸を3回タップして、ゲーム開始が検出されるかテスト", file=sys.stderr)
    print("", file=sys.stderr)

    # 胸を3回タップ
    for i in range(3):
        touch = create_touch_input("胸", 0.5)
        output = json.dumps(touch, ensure_ascii=False)
        print(output, flush=True)

        print(f"[テスト] {i+1}回目のタップを送信: {touch['touched_area']}", file=sys.stderr)

        # 各タップの間隔（2秒）
        if i < 2:
            time.sleep(2)

    print("", file=sys.stderr)
    print("=== テスト完了 ===", file=sys.stderr)
    print("エージェントが「ゲームモードに入るね！」と反応すれば成功", file=sys.stderr)

if __name__ == "__main__":
    main()
