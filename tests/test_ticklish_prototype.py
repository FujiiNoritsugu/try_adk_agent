#!/usr/bin/env python3
"""Test ticklish feedback mechanism prototype"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.devices.vibration_patterns import VibrationPatternGenerator


def test_ticklish_patterns():
    """Test different ticklish levels"""
    print("=== Ticklish Feedback Mechanism Test ===\n")

    test_cases = [
        (0, "触り始め"),
        (2, "軽いくすぐったさ"),
        (5, "中程度のくすぐったさ"),
        (8, "強いくすぐったさ（逃げたい！）"),
        (10, "最大くすぐったさ"),
    ]

    for level, description in test_cases:
        print(f"レベル {level}: {description}")
        pattern = VibrationPatternGenerator.ticklish_pattern(level)

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


def test_pattern_dict():
    """Test pattern dictionary conversion"""
    print("=== Pattern Dictionary Conversion Test ===\n")

    pattern = VibrationPatternGenerator.ticklish_pattern(5)
    pattern_dict = pattern.to_dict()

    print("Pattern dictionary format:")
    print(f"  steps: {len(pattern_dict['steps'])} steps")
    print(f"  interval: {pattern_dict['interval']}ms")
    print(f"  repeat_count: {pattern_dict['repeat_count']}")
    print("\nFirst step example:")
    print(f"  {pattern_dict['steps'][0]}")


if __name__ == "__main__":
    test_ticklish_patterns()
    print("\n" + "="*50 + "\n")
    test_pattern_dict()
    print("\n✅ Ticklish prototype test completed!")
