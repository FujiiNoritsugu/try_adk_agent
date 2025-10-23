#!/usr/bin/env python3
"""Test emotion sync game functionality"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.devices.vibration_patterns import VibrationPatternGenerator


def test_celebration_patterns():
    """Test celebration vibration patterns"""
    print("=== Celebration Pattern Test ===\n")

    levels = ["perfect", "good", "close"]

    for level in levels:
        print(f"Success Level: {level}")
        pattern = VibrationPatternGenerator.celebration_pattern(level)

        print(f"  ステップ数: {len(pattern.steps)}")
        print(f"  繰り返し: {pattern.repeat_count}回")
        print(f"  インターバル: {pattern.interval}ms")

        # 各ステップの詳細
        for i, step in enumerate(pattern.steps):
            print(f"    ステップ{i+1}: 強度={step.intensity:.1f}, 時間={step.duration}ms")

        # 合計時間を計算
        total_time = sum(step.duration for step in pattern.steps) * pattern.repeat_count
        total_time += pattern.interval * (len(pattern.steps) - 1) * pattern.repeat_count
        print(f"  合計時間: 約{total_time}ms\n")


def test_game_simulation():
    """Simulate a game scenario"""
    print("=== Emotion Sync Game Simulation ===\n")

    # Simulate target emotions
    target = {"joy": 4, "fun": 2, "anger": 0, "sad": 0}
    print(f"目標感情: {target}\n")

    # Test cases with different attempts
    attempts = [
        {"joy": 2, "fun": 1, "anger": 0, "sad": 0, "description": "1回目の試行（遠い）"},
        {"joy": 3, "fun": 2, "anger": 1, "sad": 0, "description": "2回目の試行（近い）"},
        {"joy": 4, "fun": 3, "anger": 0, "sad": 0, "description": "3回目の試行（かなり近い）"},
        {"joy": 4, "fun": 2, "anger": 0, "sad": 0, "description": "4回目の試行（完璧！）"},
    ]

    for attempt in attempts:
        current = {k: v for k, v in attempt.items() if k != "description"}
        description = attempt["description"]

        # Calculate difference
        total_diff = sum(abs(target[k] - current[k]) for k in ["joy", "fun", "anger", "sad"])
        score = max(0, 100 - (total_diff * 5))

        # Determine success level
        if score == 100:
            success_level = "perfect"
        elif score >= 85:
            success_level = "good"
        elif score >= 70:
            success_level = "close"
        else:
            success_level = "try_again"

        print(f"{description}")
        print(f"  現在の感情: joy={current['joy']}, fun={current['fun']}, anger={current['anger']}, sad={current['sad']}")
        print(f"  差分合計: {total_diff}")
        print(f"  スコア: {score}点")
        print(f"  成功レベル: {success_level}")

        if success_level in ["perfect", "good", "close"]:
            pattern = VibrationPatternGenerator.celebration_pattern(success_level)
            total_time = sum(step.duration for step in pattern.steps) * pattern.repeat_count
            print(f"  祝福振動: {len(pattern.steps)}ステップ, 約{total_time}ms")

        print()


def test_pattern_dict_conversion():
    """Test pattern dictionary conversion for all celebration levels"""
    print("=== Pattern Dictionary Conversion Test ===\n")

    for level in ["perfect", "good", "close"]:
        print(f"Level: {level}")
        pattern = VibrationPatternGenerator.celebration_pattern(level)
        pattern_dict = pattern.to_dict()

        print(f"  Dictionary format:")
        print(f"    steps: {len(pattern_dict['steps'])} steps")
        print(f"    interval: {pattern_dict['interval']}ms")
        print(f"    repeat_count: {pattern_dict['repeat_count']}")
        print(f"    First step: {pattern_dict['steps'][0]}")
        print()


if __name__ == "__main__":
    test_celebration_patterns()
    print("\n" + "="*50 + "\n")
    test_game_simulation()
    print("\n" + "="*50 + "\n")
    test_pattern_dict_conversion()
    print("\n✅ Emotion sync game test completed!")
