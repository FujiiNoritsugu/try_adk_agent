#!/usr/bin/env python3
"""MCP server for emotion sync game management"""

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
