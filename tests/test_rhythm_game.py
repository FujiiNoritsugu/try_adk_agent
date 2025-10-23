#!/usr/bin/env python3
"""Test rhythm game functionality"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.devices.vibration_patterns import VibrationPatternGenerator


def test_rhythm_patterns():
    """Test rhythm vibration patterns"""
    print("=== Rhythm Pattern Test ===\n")

    difficulties = ["easy", "normal", "hard"]

    for difficulty in difficulties:
        print(f"Difficulty: {difficulty}")
        pattern = VibrationPatternGenerator.rhythm_pattern(difficulty)

        print(f"  ステップ数: {len(pattern.steps)}")
        print(f"  繰り返し: {pattern.repeat_count}回")
        print(f"  インターバル: {pattern.interval}ms")

        # ビート（強度>0のステップ）を抽出
        beats = []
        current_time = 0.0
        for i, step in enumerate(pattern.steps):
            if step.intensity > 0:
                beats.append({
                    "index": len(beats) + 1,
                    "time": current_time / 1000.0,
                    "intensity": step.intensity,
                    "duration": step.duration
                })
            current_time += step.duration

        print(f"  ビート数: {len(beats)}")
        print(f"  ビートタイミング:")
        for beat in beats:
            print(f"    ビート{beat['index']}: {beat['time']:.2f}秒 (強度={beat['intensity']:.1f}, 時間={beat['duration']}ms)")

        # 合計時間を計算
        total_time = sum(step.duration for step in pattern.steps)
        print(f"  合計時間: {total_time}ms ({total_time/1000.0:.2f}秒)\n")


def test_rhythm_scoring():
    """Test rhythm scoring algorithm"""
    print("=== Rhythm Scoring Test ===\n")

    # Expected pattern: 3 beats at 0.0s, 0.4s, 0.8s
    expected = [0.0, 0.4, 0.8]

    test_cases = [
        {
            "description": "Perfect timing",
            "actual": [0.0, 0.4, 0.8],
            "expected_level": "perfect"
        },
        {
            "description": "Good timing (slight delay)",
            "actual": [0.05, 0.45, 0.85],
            "expected_level": "good"
        },
        {
            "description": "Close timing",
            "actual": [0.1, 0.5, 0.9],
            "expected_level": "close"
        },
        {
            "description": "Poor timing",
            "actual": [0.0, 0.6, 1.0],
            "expected_level": "try_again"
        },
        {
            "description": "Wrong beat count",
            "actual": [0.0, 0.4],
            "expected_level": "try_again"
        }
    ]

    for test in test_cases:
        print(f"{test['description']}")
        actual = test["actual"]

        # Calculate timing errors
        timing_errors = []
        matched_count = min(len(expected), len(actual))

        for i in range(matched_count):
            error = abs(expected[i] - actual[i])
            timing_errors.append(error)

        avg_error = sum(timing_errors) / len(timing_errors) if timing_errors else 999.0
        beat_count_diff = abs(len(expected) - len(actual))

        # Determine success level
        if avg_error < 0.1 and beat_count_diff == 0:
            success_level = "perfect"
            score = 100
        elif avg_error < 0.2 and beat_count_diff <= 1:
            success_level = "good"
            score = max(85, 100 - int(avg_error * 100))
        elif avg_error < 0.3 and beat_count_diff <= 2:
            success_level = "close"
            score = max(70, 100 - int(avg_error * 150))
        else:
            success_level = "try_again"
            score = max(0, 100 - int(avg_error * 200) - beat_count_diff * 10)

        print(f"  入力タイミング: {actual}")
        print(f"  平均誤差: {avg_error:.3f}秒")
        print(f"  ビート数差分: {beat_count_diff}")
        print(f"  スコア: {score}点")
        print(f"  成功レベル: {success_level}")
        print(f"  期待レベル: {test['expected_level']}")
        print(f"  判定: {'✓' if success_level == test['expected_level'] else '✗'}\n")


def test_pattern_extraction():
    """Test extracting beat timestamps from pattern"""
    print("=== Pattern Beat Extraction Test ===\n")

    for difficulty in ["easy", "normal", "hard"]:
        print(f"Difficulty: {difficulty}")
        pattern = VibrationPatternGenerator.rhythm_pattern(difficulty)

        # Extract beats
        timestamps = []
        current_time = 0.0
        for step in pattern.steps:
            if step.intensity > 0:
                timestamps.append(current_time / 1000.0)
            current_time += step.duration

        print(f"  ビートタイムスタンプ: {[f'{t:.2f}s' for t in timestamps]}")
        print(f"  ビート間隔: {[f'{timestamps[i+1]-timestamps[i]:.2f}s' for i in range(len(timestamps)-1)]}\n")


if __name__ == "__main__":
    test_rhythm_patterns()
    print("\n" + "="*50 + "\n")
    test_rhythm_scoring()
    print("\n" + "="*50 + "\n")
    test_pattern_extraction()
    print("\n✅ Rhythm game test completed!")
