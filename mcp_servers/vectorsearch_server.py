#!/usr/bin/env python3
"""MCP server for Vector Search operations"""

import asyncio
import json
import sys
import os
from typing import Any, Dict, List
from mcp.server import Server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.vectorsearch.embedder import EmotionEmbedder, TouchInput, Emotion
from src.vectorsearch.vector_search_client import VectorSearchClient


class SearchSimilarArgs(BaseModel):
    """Arguments for search_similar_interactions tool"""
    touched_area: str = Field(description="触られた体の部位")
    data: float = Field(description="触覚の強度（0-1）", ge=0.0, le=1.0)
    gesture_type: str = Field(default="", description="ジェスチャータイプ")
    joy: float = Field(description="喜びの感情値（0-5）", ge=0.0, le=5.0)
    fun: float = Field(description="楽しさの感情値（0-5）", ge=0.0, le=5.0)
    anger: float = Field(description="怒りの感情値（0-5）", ge=0.0, le=5.0)
    sad: float = Field(description="悲しみの感情値（0-5）", ge=0.0, le=5.0)
    top_k: int = Field(default=5, description="取得する類似結果の数", ge=1, le=10)


class SaveInteractionArgs(BaseModel):
    """Arguments for save_interaction tool"""
    touched_area: str = Field(description="触られた体の部位")
    data: float = Field(description="触覚の強度（0-1）", ge=0.0, le=1.0)
    gesture_type: str = Field(default="", description="ジェスチャータイプ")
    hand_velocity: float = Field(default=0.0, description="手の速度")
    joy: float = Field(description="喜びの感情値（0-5）", ge=0.0, le=5.0)
    fun: float = Field(description="楽しさの感情値（0-5）", ge=0.0, le=5.0)
    anger: float = Field(description="怒りの感情値（0-5）", ge=0.0, le=5.0)
    sad: float = Field(description="悲しみの感情値（0-5）", ge=0.0, le=5.0)
    response_text: str = Field(description="生成した応答テキスト")
    session_id: str = Field(default="", description="セッションID")


class CheckPatternMemoryArgs(BaseModel):
    """Arguments for check_pattern_memory tool"""
    touched_area: str = Field(description="触られた体の部位")
    data: float = Field(description="触覚の強度（0-1）", ge=0.0, le=1.0)
    gesture_type: str = Field(default="", description="ジェスチャータイプ")


class GetIntimacyScoreArgs(BaseModel):
    """Arguments for get_intimacy_score tool"""
    pass


app = Server("vectorsearch-server")

# Initialize embedder and client
embedder = EmotionEmbedder()
vector_client = VectorSearchClient()


async def search_similar_interactions(arguments: SearchSimilarArgs) -> List[TextContent]:
    """類似した過去のインタラクションを検索"""

    print(f"[DEBUG] Searching similar interactions for: {arguments.touched_area}", file=sys.stderr)

    # Create TouchInput and Emotion from arguments
    touch_input = TouchInput(
        data=arguments.data,
        touched_area=arguments.touched_area,
        gesture_type=arguments.gesture_type if arguments.gesture_type else None
    )

    emotion = Emotion(
        joy=arguments.joy,
        fun=arguments.fun,
        anger=arguments.anger,
        sad=arguments.sad
    )

    # Generate embedding for search query
    # Use search-specific method that doesn't include response text
    query_text = embedder.create_search_query_text(
        touch_input,
        emotion
    )
    query_embedding = embedder.generate_embedding(query_text)

    # Search vector database
    results = vector_client.search_similar(
        query_embedding,
        top_k=arguments.top_k,
        threshold=0.7
    )

    # Format results for agent
    if not results:
        response = {
            "found": False,
            "message": "類似した過去の応答は見つかりませんでした",
            "similar_interactions": []
        }
    else:
        similar_interactions = []
        for result in results:
            metadata = result.get("metadata", {})
            similar_interactions.append({
                "similarity": result.get("distance", 0.0),
                "timestamp": metadata.get("timestamp", "不明"),
                "input": metadata.get("input", {}),
                "emotion": metadata.get("emotion", {}),
                "response": metadata.get("response_text", "")
            })

        response = {
            "found": True,
            "count": len(results),
            "similar_interactions": similar_interactions
        }

    print(f"[DEBUG] Found {len(results)} similar interactions", file=sys.stderr)

    return [TextContent(type="text", text=json.dumps(response, ensure_ascii=False, indent=2))]


async def save_interaction(arguments: SaveInteractionArgs) -> List[TextContent]:
    """新しいインタラクションをVector Searchに保存"""

    print(f"[DEBUG] Saving interaction: {arguments.response_text[:50]}...", file=sys.stderr)

    # Create TouchInput and Emotion
    touch_input = TouchInput(
        data=arguments.data,
        touched_area=arguments.touched_area,
        gesture_type=arguments.gesture_type if arguments.gesture_type else None,
        hand_velocity=arguments.hand_velocity if arguments.hand_velocity > 0 else None
    )

    emotion = Emotion(
        joy=arguments.joy,
        fun=arguments.fun,
        anger=arguments.anger,
        sad=arguments.sad
    )

    # Create interaction record with embedding
    record = embedder.create_interaction_record(
        input_data=touch_input,
        emotion=emotion,
        response_text=arguments.response_text,
        session_id=arguments.session_id if arguments.session_id else None
    )

    # Save to vector database
    success = vector_client.upsert_interaction(record)

    if success:
        response = {
            "success": True,
            "message": "インタラクションを保存しました",
            "record_id": record.id
        }
    else:
        response = {
            "success": False,
            "message": "保存に失敗しました"
        }

    print(f"[DEBUG] Save result: {success}", file=sys.stderr)

    return [TextContent(type="text", text=json.dumps(response, ensure_ascii=False))]


async def get_stats() -> List[TextContent]:
    """Vector Searchの統計情報を取得"""

    stats = vector_client.get_stats()

    print(f"[DEBUG] Stats: {stats}", file=sys.stderr)

    return [TextContent(type="text", text=json.dumps(stats, ensure_ascii=False, indent=2))]


async def check_pattern_memory(arguments: CheckPatternMemoryArgs) -> List[TextContent]:
    """同じ触れ方パターンが過去にあったかチェック"""

    print(f"[DEBUG] Checking pattern memory for: {arguments.touched_area}", file=sys.stderr)

    # Create TouchInput from arguments
    touch_input = TouchInput(
        data=arguments.data,
        touched_area=arguments.touched_area,
        gesture_type=arguments.gesture_type if arguments.gesture_type else None
    )

    # Create search query text (without emotion)
    query_text = f"触覚入力: 部位={touch_input.touched_area}, 強度={touch_input.data:.2f}"
    if touch_input.gesture_type:
        query_text += f", ジェスチャー={touch_input.gesture_type}"

    query_embedding = embedder.generate_embedding(query_text)

    # Search for very similar patterns (high threshold)
    results = vector_client.search_similar(
        query_embedding,
        top_k=10,
        threshold=0.85  # High similarity threshold for pattern recognition
    )

    if not results:
        response = {
            "remembered": False,
            "message": "この触れ方は初めてですね",
            "similar_count": 0
        }
    else:
        # Count matching patterns
        exact_matches = [r for r in results if r.get("distance", 0) > 0.95]
        similar_matches = [r for r in results if 0.85 <= r.get("distance", 0) < 0.95]

        # Calculate how many times this pattern occurred
        total_count = len(results)

        # Extract common response patterns
        responses = [r.get("response_text", "") for r in results[:3]]

        response = {
            "remembered": True,
            "message": f"この触れ方、覚えています！{total_count}回目ですね",
            "similar_count": total_count,
            "exact_matches": len(exact_matches),
            "similar_matches": len(similar_matches),
            "past_responses": responses,
            "touched_area": arguments.touched_area,
            "pattern_familiarity": min(1.0, total_count / 10.0)  # 0-1 scale
        }

    print(f"[DEBUG] Pattern memory result: remembered={response.get('remembered')}", file=sys.stderr)

    return [TextContent(type="text", text=json.dumps(response, ensure_ascii=False))]


async def get_intimacy_score(arguments: GetIntimacyScoreArgs) -> List[TextContent]:
    """親密度スコアを計算"""

    print(f"[DEBUG] Calculating intimacy score", file=sys.stderr)

    # Get all interactions
    stats = vector_client.get_stats()
    total_interactions = stats.get("total_records", 0)

    if total_interactions == 0:
        response = {
            "intimacy_score": 0,
            "intimacy_level": "stranger",
            "total_interactions": 0,
            "gentle_ratio": 0.0,
            "message": "まだ触れ合っていないので、親密度は0です"
        }
    else:
        # Search for recent gentle touches (data < 0.6)
        # Use a generic query to get recent interactions
        query_text = "優しい触覚"
        query_embedding = embedder.generate_embedding(query_text)

        recent_results = vector_client.search_similar(
            query_embedding,
            top_k=min(50, total_interactions),
            threshold=0.0  # Get all recent interactions
        )

        # Count gentle touches (intensity < 0.6)
        gentle_count = sum(1 for r in recent_results
                          if r.get("metadata", {}).get("data", 1.0) < 0.6)

        gentle_ratio = gentle_count / len(recent_results) if recent_results else 0.0

        # Calculate intimacy score (0-100)
        # Based on: total interactions + gentle ratio
        base_score = min(50, total_interactions * 2)  # Up to 50 points from interaction count
        gentleness_bonus = gentle_ratio * 50  # Up to 50 points from gentle touches
        intimacy_score = int(base_score + gentleness_bonus)

        # Determine intimacy level
        if intimacy_score < 20:
            intimacy_level = "stranger"
            level_description = "まだあまり知らない関係"
        elif intimacy_score < 40:
            intimacy_level = "acquaintance"
            level_description = "少し打ち解けてきた関係"
        elif intimacy_score < 60:
            intimacy_level = "friend"
            level_description = "友達のような関係"
        elif intimacy_score < 80:
            intimacy_level = "close_friend"
            level_description = "親しい友達の関係"
        else:
            intimacy_level = "intimate"
            level_description = "とても親密な関係"

        response = {
            "intimacy_score": intimacy_score,
            "intimacy_level": intimacy_level,
            "level_description": level_description,
            "total_interactions": total_interactions,
            "gentle_ratio": round(gentle_ratio, 2),
            "gentle_count": gentle_count,
            "message": f"親密度: {intimacy_score}点 ({level_description})"
        }

    print(f"[DEBUG] Intimacy score: {response.get('intimacy_score')}", file=sys.stderr)

    return [TextContent(type="text", text=json.dumps(response, ensure_ascii=False))]


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="search_similar_interactions",
            description="類似した過去のインタラクション履歴を検索します。現在の触覚入力と感情値に基づいて、過去の似た状況での応答を取得します。",
            inputSchema=SearchSimilarArgs.model_json_schema(),
        ),
        Tool(
            name="save_interaction",
            description="新しいインタラクション（触覚入力、感情値、応答）をVector Searchに保存します。",
            inputSchema=SaveInteractionArgs.model_json_schema(),
        ),
        Tool(
            name="get_interaction_stats",
            description="Vector Searchの統計情報（保存されたインタラクション数など）を取得します。",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="check_pattern_memory",
            description="同じ触れ方パターンが過去にあったかチェックします。覚えている触れ方なら「覚えています！」と反応できます。",
            inputSchema=CheckPatternMemoryArgs.model_json_schema(),
        ),
        Tool(
            name="get_intimacy_score",
            description="現在の親密度スコアを取得します。優しい触れ方の履歴が多いほど親密度が上がります。",
            inputSchema=GetIntimacyScoreArgs.model_json_schema(),
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Call a tool by name"""
    if name == "search_similar_interactions":
        args = SearchSimilarArgs(**arguments)
        return await search_similar_interactions(args)
    elif name == "save_interaction":
        args = SaveInteractionArgs(**arguments)
        return await save_interaction(args)
    elif name == "get_interaction_stats":
        return await get_stats()
    elif name == "check_pattern_memory":
        args = CheckPatternMemoryArgs(**arguments)
        return await check_pattern_memory(args)
    elif name == "get_intimacy_score":
        args = GetIntimacyScoreArgs(**arguments)
        return await get_intimacy_score(args)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server

    print("[INFO] Starting Vector Search MCP server...", file=sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
