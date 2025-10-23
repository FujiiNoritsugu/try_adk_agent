#!/usr/bin/env python3
"""Live test script for ticklish feedback mechanism"""

import json
import time
import sys

def generate_test_inputs():
    """Generate test inputs for ticklish feedback"""

    print("=== くすぐったさフィードバック機能 ライブテスト ===\n")
    print("このスクリプトは、エージェントに連続した触覚入力を送信します。")
    print("エージェントが起動している状態で実行してください。\n")
    print("使用方法:")
    print("  python tests/test_ticklish_live.py | adk run .\n")
    print("テストシナリオ:")
    print("1. 1回目のタッチ（初回）")
    print("2. 2回目のタッチ（2秒後、軽いくすぐったさ）")
    print("3. 3回目のタッチ（2秒後、中程度のくすぐったさ）")
    print("4. 4回目のタッチ（2秒後、中程度のくすぐったさ）")
    print("5. 5回目のタッチ（2秒後、強いくすぐったさ）")
    print("6. 6回目のタッチ（2秒後、強いくすぐったさ）\n")
    print("="*60)
    print()

    # Wait for user to be ready
    time.sleep(3)

    test_cases = [
        {
            "count": 1,
            "description": "1回目: 初めてのタッチ",
            "input": {"data": 0.5, "touched_area": "頭"},
            "wait_before": 0
        },
        {
            "count": 2,
            "description": "2回目: 同じ部位をもう一度（軽いくすぐったさ）",
            "input": {"data": 0.5, "touched_area": "頭"},
            "wait_before": 2
        },
        {
            "count": 3,
            "description": "3回目: さらに続けて（中程度のくすぐったさ）",
            "input": {"data": 0.5, "touched_area": "頭"},
            "wait_before": 2
        },
        {
            "count": 4,
            "description": "4回目: まだ続けて（中程度のくすぐったさ）",
            "input": {"data": 0.5, "touched_area": "頭"},
            "wait_before": 2
        },
        {
            "count": 5,
            "description": "5回目: どんどんくすぐったく（強いくすぐったさ）",
            "input": {"data": 0.5, "touched_area": "頭"},
            "wait_before": 2
        },
        {
            "count": 6,
            "description": "6回目: 最大くすぐったさ！",
            "input": {"data": 0.5, "touched_area": "頭"},
            "wait_before": 2
        }
    ]

    for test in test_cases:
        # Wait before sending input
        if test["wait_before"] > 0:
            print(f"\n[待機中: {test['wait_before']}秒...]", file=sys.stderr)
            time.sleep(test["wait_before"])

        # Log the test
        print(f"\n[テスト {test['count']}/6] {test['description']}", file=sys.stderr)
        print(f"[入力データ] {json.dumps(test['input'], ensure_ascii=False)}", file=sys.stderr)

        # Send input to agent (via stdout)
        print(json.dumps(test["input"]))
        sys.stdout.flush()

        # Wait for agent to process
        time.sleep(1)

    print("\n" + "="*60, file=sys.stderr)
    print("\n✅ すべてのテスト入力を送信しました！", file=sys.stderr)
    print("\nエージェントの応答を確認してください:", file=sys.stderr)
    print("- 1-2回目: 通常の反応", file=sys.stderr)
    print("- 3-4回目: 「くすぐったい」という反応、中程度の振動", file=sys.stderr)
    print("- 5-6回目: 「やめて〜！」という反応、強い振動", file=sys.stderr)
    print(file=sys.stderr)


if __name__ == "__main__":
    try:
        generate_test_inputs()
    except KeyboardInterrupt:
        print("\n\nテストを中断しました", file=sys.stderr)
        sys.exit(0)
