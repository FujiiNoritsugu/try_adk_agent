#!/usr/bin/env python3
"""MCP server for emotion sync game and rhythm game management"""

import asyncio
import json
import random
import sys
import os
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field
from datetime import datetime
import time

# Add parent and src directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from src.devices import VibrationPatternGenerator


class StartGameArgs(BaseModel):
    """Arguments for start_emotion_sync_game tool"""
    difficulty: str = Field(description="ゲームの難易度 (easy, normal, hard)", default="normal")


class CheckEmotionMatchArgs(BaseModel):
    """Arguments for check_emotion_match tool"""
    joy: int = Field(description="現在の喜びの感情値 (0-5)", ge=0, le=5)
    fun: int = Field(description="現在の楽しさの感情値 (0-5)", ge=0, le=5)
    anger: int = Field(description="現在の怒りの感情値 (0-5)", ge=0, le=5)
    sad: int = Field(description="現在の悲しみの感情値 (0-5)", ge=0, le=5)


class GetGameStatusArgs(BaseModel):
    """Arguments for get_game_status tool"""
    pass


class StartRhythmGameArgs(BaseModel):
    """Arguments for start_rhythm_game tool"""
    difficulty: str = Field(description="ゲームの難易度 (easy, normal, hard)", default="easy")


class CheckRhythmArgs(BaseModel):
    """Arguments for check_rhythm tool"""
    touch_timestamps: List[float] = Field(description="タッチのタイムスタンプリスト（秒単位）")


app = Server("game-server")

# Global game state
game_state = {
    "active": False,
    "target_emotions": {},
    "difficulty": "normal",
    "start_time": None,
    "attempts": 0,
    "best_score": None
}

# Rhythm game state
rhythm_state = {
    "active": False,
    "difficulty": "easy",
    "pattern_timestamps": [],
    "start_time": None,
    "attempts": 0,
    "best_score": None
}


def generate_target_emotions(difficulty: str) -> Dict[str, int]:
    """Generate random target emotions based on difficulty"""
    if difficulty == "easy":
        # Only one emotion, value 3-5
        emotion = random.choice(["joy", "fun", "anger", "sad"])
        return {
            "joy": 3 if emotion == "joy" else 0,
            "fun": 3 if emotion == "fun" else 0,
            "anger": 3 if emotion == "anger" else 0,
            "sad": 3 if emotion == "sad" else 0
        }
    elif difficulty == "normal":
        # One or two emotions, values 2-5
        primary = random.choice(["joy", "fun", "anger", "sad"])
        use_secondary = random.choice([True, False])
        secondary = random.choice([e for e in ["joy", "fun", "anger", "sad"] if e != primary])

        return {
            "joy": random.randint(2, 5) if primary == "joy" else (random.randint(1, 3) if use_secondary and secondary == "joy" else 0),
            "fun": random.randint(2, 5) if primary == "fun" else (random.randint(1, 3) if use_secondary and secondary == "fun" else 0),
            "anger": random.randint(2, 5) if primary == "anger" else (random.randint(1, 3) if use_secondary and secondary == "anger" else 0),
            "sad": random.randint(2, 5) if primary == "sad" else (random.randint(1, 3) if use_secondary and secondary == "sad" else 0)
        }
    else:  # hard
        # Multiple emotions with specific values
        return {
            "joy": random.randint(0, 5),
            "fun": random.randint(0, 5),
            "anger": random.randint(0, 5),
            "sad": random.randint(0, 5)
        }


def calculate_emotion_score(target: Dict[str, int], current: Dict[str, int]) -> Dict[str, Any]:
    """Calculate how close current emotions are to target"""
    total_diff = 0
    max_diff = 0
    emotion_details = {}

    for emotion in ["joy", "fun", "anger", "sad"]:
        diff = abs(target[emotion] - current[emotion])
        total_diff += diff
        max_diff = max(max_diff, diff)
        emotion_details[emotion] = {
            "target": target[emotion],
            "current": current[emotion],
            "diff": diff
        }

    # Calculate score (0-100)
    # Perfect match = 100, max possible diff = 20 (4 emotions × 5 max diff)
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

    return {
        "score": score,
        "total_diff": total_diff,
        "max_diff": max_diff,
        "success_level": success_level,
        "emotion_details": emotion_details
    }


async def start_emotion_sync_game(arguments: StartGameArgs) -> List[TextContent]:
    """感情シンクロゲームを開始します"""
    global game_state

    # Generate target emotions
    target = generate_target_emotions(arguments.difficulty)

    # Update game state
    game_state = {
        "active": True,
        "target_emotions": target,
        "difficulty": arguments.difficulty,
        "start_time": datetime.now().isoformat(),
        "attempts": 0,
        "best_score": None
    }

    # Generate celebration pattern for game start
    start_pattern = VibrationPatternGenerator.celebration_pattern("close")

    result = {
        "success": True,
        "message": "感情シンクロゲームを開始しました！",
        "game_state": {
            "active": True,
            "difficulty": arguments.difficulty,
            "target_emotions": target
        },
        "instructions": "触り方を調整して、目標の感情値に近づけてください！",
        "start_vibration": start_pattern.to_dict()
    }

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def check_emotion_match(arguments: CheckEmotionMatchArgs) -> List[TextContent]:
    """現在の感情値が目標とどれだけ一致しているかチェックします"""
    global game_state

    if not game_state["active"]:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "ゲームが開始されていません。start_emotion_sync_gameを実行してください"
            }, ensure_ascii=False)
        )]

    # Increment attempts
    game_state["attempts"] += 1

    current_emotions = {
        "joy": arguments.joy,
        "fun": arguments.fun,
        "anger": arguments.anger,
        "sad": arguments.sad
    }

    # Calculate score
    score_result = calculate_emotion_score(game_state["target_emotions"], current_emotions)

    # Update best score
    if game_state["best_score"] is None or score_result["score"] > game_state["best_score"]:
        game_state["best_score"] = score_result["score"]

    # Generate celebration pattern based on success level
    celebration = None
    if score_result["success_level"] in ["perfect", "good", "close"]:
        celebration_pattern = VibrationPatternGenerator.celebration_pattern(score_result["success_level"])
        celebration = celebration_pattern.to_dict()

    # Check if game is won
    game_won = score_result["success_level"] in ["perfect", "good"]
    if game_won:
        game_state["active"] = False

    result = {
        "success": True,
        "game_won": game_won,
        "score": score_result["score"],
        "success_level": score_result["success_level"],
        "attempts": game_state["attempts"],
        "best_score": game_state["best_score"],
        "emotion_details": score_result["emotion_details"],
        "total_diff": score_result["total_diff"],
        "celebration_vibration": celebration,
        "feedback": _generate_feedback(score_result, game_state["attempts"])
    }

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def get_game_status(arguments: GetGameStatusArgs) -> List[TextContent]:
    """現在のゲーム状態を取得します"""
    global game_state

    result = {
        "active": game_state["active"],
        "difficulty": game_state["difficulty"] if game_state["active"] else None,
        "target_emotions": game_state["target_emotions"] if game_state["active"] else None,
        "attempts": game_state["attempts"],
        "best_score": game_state["best_score"]
    }

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def start_rhythm_game(arguments: StartRhythmGameArgs) -> List[TextContent]:
    """リズムゲームを開始します"""
    global rhythm_state

    # Generate rhythm pattern
    rhythm_pattern = VibrationPatternGenerator.rhythm_pattern(arguments.difficulty)

    # Extract beat timestamps from pattern
    timestamps = []
    current_time = 0.0
    for step in rhythm_pattern.steps:
        if step.intensity > 0:  # Only count beats (non-zero intensity)
            timestamps.append(current_time / 1000.0)  # Convert to seconds
        current_time += step.duration

    # Update rhythm state
    rhythm_state = {
        "active": True,
        "difficulty": arguments.difficulty,
        "pattern_timestamps": timestamps,
        "start_time": time.time(),
        "attempts": 0,
        "best_score": None
    }

    result = {
        "success": True,
        "message": "リズムゲームを開始しました！",
        "game_state": {
            "active": True,
            "difficulty": arguments.difficulty,
            "beat_count": len(timestamps)
        },
        "instructions": "振動パターンを覚えて、同じリズムでタッチしてください！",
        "rhythm_pattern": rhythm_pattern.to_dict(),
        "expected_beats": len(timestamps)
    }

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def check_rhythm(arguments: CheckRhythmArgs) -> List[TextContent]:
    """ユーザーのタッチタイミングがリズムと一致しているかチェックします"""
    global rhythm_state

    if not rhythm_state["active"]:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "リズムゲームが開始されていません。start_rhythm_gameを実行してください"
            }, ensure_ascii=False)
        )]

    rhythm_state["attempts"] += 1

    expected = rhythm_state["pattern_timestamps"]
    actual = arguments.touch_timestamps

    # Normalize timestamps (relative to first beat)
    if len(actual) > 0 and len(expected) > 0:
        actual_normalized = [t - actual[0] for t in actual]
        expected_normalized = [t - expected[0] for t in expected]
    else:
        actual_normalized = actual
        expected_normalized = expected

    # Calculate timing accuracy
    score_data = _calculate_rhythm_score(expected_normalized, actual_normalized)

    # Update best score
    if rhythm_state["best_score"] is None or score_data["score"] > rhythm_state["best_score"]:
        rhythm_state["best_score"] = score_data["score"]

    # Generate celebration
    celebration = None
    if score_data["success_level"] in ["perfect", "good", "close"]:
        celebration_pattern = VibrationPatternGenerator.celebration_pattern(score_data["success_level"])
        celebration = celebration_pattern.to_dict()

    # Check if game is won
    game_won = score_data["success_level"] in ["perfect", "good"]
    if game_won:
        rhythm_state["active"] = False

    result = {
        "success": True,
        "game_won": game_won,
        "score": score_data["score"],
        "success_level": score_data["success_level"],
        "attempts": rhythm_state["attempts"],
        "best_score": rhythm_state["best_score"],
        "timing_errors": score_data["timing_errors"],
        "avg_error": score_data["avg_error"],
        "celebration_vibration": celebration,
        "feedback": _generate_rhythm_feedback(score_data, rhythm_state["attempts"])
    }

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


def _calculate_rhythm_score(expected: List[float], actual: List[float]) -> Dict[str, Any]:
    """Calculate rhythm matching score"""
    # Check beat count match
    beat_count_diff = abs(len(expected) - len(actual))

    if len(actual) == 0 or len(expected) == 0:
        return {
            "score": 0,
            "success_level": "try_again",
            "timing_errors": [],
            "avg_error": 999.0
        }

    # Calculate timing errors for each beat
    timing_errors = []
    matched_count = min(len(expected), len(actual))

    for i in range(matched_count):
        error = abs(expected[i] - actual[i])
        timing_errors.append(error)

    # Average timing error
    avg_error = sum(timing_errors) / len(timing_errors) if timing_errors else 999.0

    # Calculate score (0-100)
    # Perfect timing: <0.1s error = 100 points
    # Good timing: <0.2s error = 85+ points
    # Close timing: <0.3s error = 70+ points
    if avg_error < 0.1 and beat_count_diff == 0:
        score = 100
        success_level = "perfect"
    elif avg_error < 0.2 and beat_count_diff <= 1:
        score = max(85, 100 - int(avg_error * 100))
        success_level = "good"
    elif avg_error < 0.3 and beat_count_diff <= 2:
        score = max(70, 100 - int(avg_error * 150))
        success_level = "close"
    else:
        score = max(0, 100 - int(avg_error * 200) - beat_count_diff * 10)
        success_level = "try_again"

    return {
        "score": score,
        "success_level": success_level,
        "timing_errors": timing_errors,
        "avg_error": avg_error,
        "beat_count_diff": beat_count_diff
    }


def _generate_rhythm_feedback(score_data: Dict, attempts: int) -> str:
    """Generate feedback for rhythm game"""
    level = score_data["success_level"]
    score = score_data["score"]
    avg_error = score_data["avg_error"]

    if level == "perfect":
        return f"パーフェクト！🎵 {attempts}回目で完璧なリズムです！"
    elif level == "good":
        return f"素晴らしい！🎶 スコア{score}点！タイミングばっちり！"
    elif level == "close":
        return f"惜しい！もう少し正確に。平均誤差{avg_error:.2f}秒"
    else:
        if avg_error > 0.5:
            return f"リズムをよく聞いて、もう一度トライ！"
        else:
            return f"もう少し正確に。平均誤差{avg_error:.2f}秒"


def _generate_feedback(score_result: Dict, attempts: int) -> str:
    """Generate encouraging feedback based on score"""
    level = score_result["success_level"]
    score = score_result["score"]

    if level == "perfect":
        return f"パーフェクト！🎉 {attempts}回目で完璧に一致させました！"
    elif level == "good":
        return f"素晴らしい！✨ スコア{score}点で成功です！"
    elif level == "close":
        return f"惜しい！もう少しです。スコア{score}点"
    else:
        # Find which emotions need adjustment
        far_emotions = [k for k, v in score_result["emotion_details"].items() if v["diff"] >= 2]
        if far_emotions:
            emotion_names = {"joy": "喜び", "fun": "楽しさ", "anger": "怒り", "sad": "悲しみ"}
            hints = [emotion_names[e] for e in far_emotions[:2]]
            return f"{'と'.join(hints)}を調整してみてください"
        else:
            return f"少しずつ近づいています。スコア{score}点"


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="start_emotion_sync_game",
            description="感情シンクロゲームを開始します。目標となる感情値が設定されます",
            inputSchema=StartGameArgs.model_json_schema(),
        ),
        Tool(
            name="check_emotion_match",
            description="現在の感情値が目標とどれだけ一致しているかチェックします",
            inputSchema=CheckEmotionMatchArgs.model_json_schema(),
        ),
        Tool(
            name="get_game_status",
            description="現在のゲーム状態（アクティブかどうか、目標感情など）を取得します",
            inputSchema=GetGameStatusArgs.model_json_schema(),
        ),
        Tool(
            name="start_rhythm_game",
            description="リズムゲームを開始します。振動パターンが生成されます",
            inputSchema=StartRhythmGameArgs.model_json_schema(),
        ),
        Tool(
            name="check_rhythm",
            description="ユーザーのタッチタイミングがリズムパターンと一致しているかチェックします",
            inputSchema=CheckRhythmArgs.model_json_schema(),
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Call a tool by name"""
    if name == "start_emotion_sync_game":
        args = StartGameArgs(**arguments)
        return await start_emotion_sync_game(args)
    elif name == "check_emotion_match":
        args = CheckEmotionMatchArgs(**arguments)
        return await check_emotion_match(args)
    elif name == "get_game_status":
        args = GetGameStatusArgs(**arguments)
        return await get_game_status(args)
    elif name == "start_rhythm_game":
        args = StartRhythmGameArgs(**arguments)
        return await start_rhythm_game(args)
    elif name == "check_rhythm":
        args = CheckRhythmArgs(**arguments)
        return await check_rhythm(args)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
