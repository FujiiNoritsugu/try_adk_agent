#!/usr/bin/env python3
import asyncio
import json
import logging
from typing import Any
import requests
from io import BytesIO
import tempfile
import os
from pathlib import Path
import subprocess

from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pydantic import AnyUrl

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("voicevox-mcp-server")


class VoiceVoxServer:
    """VOICEVOX用MCPサーバー"""

    def __init__(self):
        self.voicevox_url = "http://localhost:50021"
        self.speaker_id = 1  # デフォルトスピーカーID
        logger.info("VoiceVoxServer initialized")

    async def initialize(self) -> None:
        """サーバー初期化"""
        try:
            # VOICEVOXの接続確認
            response = requests.get(f"{self.voicevox_url}/speakers")
            if response.status_code == 200:
                logger.info("Successfully connected to VOICEVOX")
            else:
                logger.warning(f"VOICEVOX connection failed: {response.status_code}")
        except Exception as e:
            logger.warning(f"VOICEVOX not available: {e}")

    def text_to_speech(self, text: str, speaker_id: int = None) -> dict:
        """テキストを音声に変換して再生"""
        try:
            if speaker_id is None:
                speaker_id = self.speaker_id

            # 音声合成用のクエリを作成
            query_response = requests.post(
                f"{self.voicevox_url}/audio_query",
                params={"text": text, "speaker": speaker_id}
            )
            
            if query_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to create audio query: {query_response.status_code}"
                }

            query_data = query_response.json()

            # 音声合成
            synthesis_response = requests.post(
                f"{self.voicevox_url}/synthesis",
                params={"speaker": speaker_id},
                json=query_data
            )

            if synthesis_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to synthesize audio: {synthesis_response.status_code}"
                }

            # 一時ファイルに保存して再生
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(synthesis_response.content)
                tmp_file_path = tmp_file.name

            # paplayで再生
            subprocess.run(["paplay", tmp_file_path])

            # 一時ファイルを削除
            os.remove(tmp_file_path)

            return {
                "success": True,
                "text": text,
                "speaker_id": speaker_id
            }

        except Exception as e:
            logger.error(f"Error in text_to_speech: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def set_speaker(self, speaker_id: int) -> dict:
        """スピーカーIDを設定"""
        try:
            # スピーカーが存在するか確認
            response = requests.get(f"{self.voicevox_url}/speakers")
            if response.status_code == 200:
                speakers = response.json()
                valid_ids = []
                for speaker in speakers:
                    for style in speaker["styles"]:
                        valid_ids.append(style["id"])
                
                if speaker_id in valid_ids:
                    self.speaker_id = speaker_id
                    return {
                        "success": True,
                        "speaker_id": speaker_id
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Invalid speaker_id. Valid IDs: {valid_ids}"
                    }
            else:
                return {
                    "success": False,
                    "error": "Failed to get speaker list"
                }
        except Exception as e:
            logger.error(f"Error in set_speaker: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_speakers(self) -> dict:
        """利用可能なスピーカーリストを取得"""
        try:
            response = requests.get(f"{self.voicevox_url}/speakers")
            if response.status_code == 200:
                return {
                    "success": True,
                    "speakers": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to get speakers: {response.status_code}"
                }
        except Exception as e:
            logger.error(f"Error in get_speakers: {e}")
            return {
                "success": False,
                "error": str(e)
            }


async def run():
    """MCPサーバーを起動"""
    logger.info("Starting VOICEVOX MCP server...")
    
    voicevox_server = VoiceVoxServer()
    await voicevox_server.initialize()

    async with stdio_server() as (read_stream, write_stream):
        # ツール定義
        tools = [
            Tool(
                name="text_to_speech",
                description="VOICEVOXを使用してテキストを音声に変換し再生する",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "音声に変換するテキスト",
                        },
                        "speaker_id": {
                            "type": "integer",
                            "description": "スピーカーID（省略時はデフォルト値を使用）",
                        },
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="set_speaker",
                description="デフォルトのスピーカーIDを設定する",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "speaker_id": {
                            "type": "integer",
                            "description": "設定するスピーカーID",
                        },
                    },
                    "required": ["speaker_id"],
                },
            ),
            Tool(
                name="get_speakers",
                description="利用可能なスピーカーのリストを取得する",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

        # ツールハンドラー
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
            logger.info(f"Tool called: {name}, arguments: {arguments}")
            
            if name == "text_to_speech":
                text = arguments.get("text", "")
                speaker_id = arguments.get("speaker_id")
                result = voicevox_server.text_to_speech(text, speaker_id)
                return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
            
            elif name == "set_speaker":
                speaker_id = arguments.get("speaker_id", 1)
                result = voicevox_server.set_speaker(speaker_id)
                return [TextContent(type="text", text=json.dumps(result))]
            
            elif name == "get_speakers":
                result = voicevox_server.get_speakers()
                return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
            
            else:
                error_msg = f"Unknown tool: {name}"
                logger.error(error_msg)
                return [TextContent(type="text", text=json.dumps({"error": error_msg}))]

        # サーバー初期化オプション
        initialization_options = InitializationOptions(
            server_name="voicevox-mcp-server",
            server_version="0.1.0",
            capabilities={
                "tools": {},
            },
        )

        # MCPサーバー起動
        from mcp.server import Server
        server = Server(initialization_options)
        
        # ハンドラー登録
        @server.list_tools()
        async def list_tools():
            return tools

        @server.call_tool()
        async def call_tool(name: str, arguments: Any):
            return await handle_call_tool(name, arguments)

        # サーバー実行
        await server.run(read_stream, write_stream, initialization_options)


if __name__ == "__main__":
    asyncio.run(run())