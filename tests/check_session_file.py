#!/usr/bin/env python3
"""セッションファイルの内容を確認"""

import pickle
from pathlib import Path
from datetime import datetime

SESSION_FILE = Path("/tmp/adk_agent_session_touches.pkl")

if not SESSION_FILE.exists():
    print("❌ セッションファイルが存在しません")
    print(f"   パス: {SESSION_FILE}")
    exit(1)

try:
    with open(SESSION_FILE, "rb") as f:
        data = pickle.load(f)

    print(f"✅ セッションファイル読み込み成功")
    print(f"   パス: {SESSION_FILE}")
    print(f"   記録数: {len(data)}")
    print()

    if not data:
        print("⚠️  記録が空です")
        exit(0)

    print("📋 記録内容:")
    for i, touch in enumerate(data, 1):
        timestamp = touch.get("timestamp")
        area = touch.get("touched_area")
        intensity = touch.get("data")
        gesture = touch.get("gesture_type", "N/A")

        # 時間経過を計算
        if timestamp:
            elapsed = (datetime.now() - timestamp).total_seconds()
            time_str = f"{elapsed:.1f}秒前"
        else:
            time_str = "不明"

        print(f"  {i}. {area} (強度={intensity:.2f}, ジェスチャー={gesture}) - {time_str}")

    # 最近10秒以内の胸タッチをカウント
    now = datetime.now()
    recent_chest_touches = [
        t for t in data
        if (now - t.get("timestamp")).total_seconds() <= 10
        and t.get("touched_area") == "胸"
    ]

    print()
    print(f"🔍 直近10秒以内の「胸」タッチ: {len(recent_chest_touches)}回")

    if len(recent_chest_touches) >= 3:
        print("   ✅ ゲーム開始条件を満たしています！")
    else:
        print(f"   ❌ あと{3 - len(recent_chest_touches)}回必要です")

except Exception as e:
    print(f"❌ エラー: {e}")
    exit(1)
