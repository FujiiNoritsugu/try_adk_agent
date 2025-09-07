#!/usr/bin/env python3
"""MCP server for emoji generation based on emotions"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field


class AddEmojiArgs(BaseModel):
    """Arguments for add_emoji tool"""
    joy: int = Field(description="喜びの感情値 (0-5)", ge=0, le=5)
    fun: int = Field(description="楽しさの感情値 (0-5)", ge=0, le=5)
    anger: int = Field(description="怒りの感情値 (0-5)", ge=0, le=5)
    sad: int = Field(description="悲しみの感情値 (0-5)", ge=0, le=5)


app = Server("emoji-server")


async def add_emoji(arguments: AddEmojiArgs) -> List[TextContent]:
    """感情パラメータに基づいて適切な絵文字を返却します"""
    
    # 感情値を辞書化
    emotions = {
        "joy": arguments.joy, 
        "fun": arguments.fun, 
        "anger": arguments.anger, 
        "sad": arguments.sad
    }
    
    # 感情と絵文字のマッピング
    emoji_map = {
        "joy": ["😊", "😄", "😃", "😁", "🥰", "😍"],
        "fun": ["🎉", "🎊", "✨", "🌟", "🎈", "🎯"],
        "anger": ["😠", "😡", "💢", "😤", "🔥", "⚡"],
        "sad": ["😢", "😭", "💔", "😞", "😔", "🥺"],
    }
    
    # 最も強い感情を見つける
    max_emotion = max(emotions.items(), key=lambda x: x[1])
    emotion_name, emotion_value = max_emotion
    
    # 感情値が0の場合は絵文字を追加しない
    if emotion_value == 0:
        return [TextContent(type="text", text="")]
    
    # 感情の強さに応じて絵文字を選択
    emoji_index = min(emotion_value - 1, 5)
    emoji = emoji_map[emotion_name][emoji_index]
    
    # 複数の高い感情がある場合は追加の絵文字を付ける
    additional_emojis = []
    for emo_name, emo_value in emotions.items():
        if emo_name != emotion_name and emo_value >= 3:
            additional_emojis.append(emoji_map[emo_name][min(emo_value - 1, 5)])
    
    # 絵文字を結合
    emoji_str = emoji + "".join(additional_emojis[:2])  # 最大3つまで
    
    return [TextContent(type="text", text=emoji_str)]


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="add_emoji",
            description="感情パラメータに基づいて適切な絵文字を返却します",
            inputSchema=AddEmojiArgs.model_json_schema(),
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Call a tool by name"""
    if name == "add_emoji":
        args = AddEmojiArgs(**arguments)
        return await add_emoji(args)
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