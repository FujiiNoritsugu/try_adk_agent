#!/usr/bin/env python3
import asyncio
import json
import logging
from typing import Any
import aiohttp
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
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("voicevox-mcp-server")
logging.getLogger("mcp.server.lowlevel.server").setLevel(logging.WARNING)


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
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.voicevox_url}/speakers") as response:
                    if response.status == 200:
                        logger.info("Successfully connected to VOICEVOX")
                    else:
                        logger.warning(f"VOICEVOX connection failed: {response.status}")
        except Exception as e:
            logger.warning(f"VOICEVOX not available: {e}")

    async def text_to_speech(self, text: str, speaker_id: int = None, keep_file: bool = False) -> dict:
        """テキストを音声に変換して再生

        Args:
            text: 音声に変換するテキスト
            speaker_id: スピーカーID
            keep_file: Trueの場合、音声ファイルを削除せずに保持（リップシンク用）
        """
        try:
            if speaker_id is None:
                speaker_id = self.speaker_id

            # 音声合成用のクエリを作成
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.voicevox_url}/audio_query",
                    params={"text": text, "speaker": speaker_id},
                ) as query_response:

                    if query_response.status != 200:
                        return {
                            "success": False,
                            "error": f"Failed to create audio query: {query_response.status}",
                        }

                    query_data = await query_response.json()

                # 音声合成
                async with session.post(
                    f"{self.voicevox_url}/synthesis",
                    params={"speaker": speaker_id},
                    json=query_data,
                ) as synthesis_response:

                    if synthesis_response.status != 200:
                        return {
                            "success": False,
                            "error": f"Failed to synthesize audio: {synthesis_response.status}",
                        }

                    audio_content = await synthesis_response.read()

            # 一時ファイルに保存
            # keep_fileがTrueの場合は、削除されないディレクトリに保存
            if keep_file:
                # /tmp/voicevox/ ディレクトリに保存（リップシンク用に保持）
                voicevox_dir = "/tmp/voicevox"
                os.makedirs(voicevox_dir, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False, dir=voicevox_dir
                ) as tmp_file:
                    tmp_file.write(audio_content)
                    tmp_file_path = tmp_file.name

                logger.info(f"Audio file saved for lipsync: {tmp_file_path}")
            else:
                # 通常の一時ファイル（再生スクリプトが削除）
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_file.write(audio_content)
                    tmp_file_path = tmp_file.name

            # シェルスクリプトを使って音声を非同期で再生
            script_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "etc", "play_audio.sh"
            )
            logger.info(f"Script path: {script_path}")
            logger.info(f"Audio file path: {tmp_file_path}")
            logger.info(f"Audio file size: {os.path.getsize(tmp_file_path)} bytes")

            # スクリプトの存在確認
            if not os.path.exists(script_path):
                logger.error(f"Script not found: {script_path}")
                return {"success": False, "error": f"Script not found: {script_path}"}

            # keep_fileがTrueの場合は、ファイルをコピーして渡す（元ファイルを保持）
            if keep_file:
                # 再生用に一時コピーを作成
                playback_path = tmp_file_path + ".playback.wav"
                import shutil
                shutil.copy(tmp_file_path, playback_path)

                # シェルスクリプトを非同期で実行（コピーを再生・削除）
                process = subprocess.Popen(
                    [script_path, playback_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            else:
                # シェルスクリプトを非同期で実行（元ファイルを再生・削除）
                process = subprocess.Popen(
                    [script_path, tmp_file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

            logger.info(f"Started process with PID: {process.pid}")

            return {
                "success": True,
                "text": text,
                "speaker_id": speaker_id,
                "audio_file": tmp_file_path,  # WAVファイルパスを返す
            }

        except Exception as e:
            logger.error(f"Error in text_to_speech: {e}")
            return {"success": False, "error": str(e)}

    async def set_speaker(self, speaker_id: int) -> dict:
        """スピーカーIDを設定"""
        try:
            # スピーカーが存在するか確認
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.voicevox_url}/speakers") as response:
                    if response.status == 200:
                        speakers = await response.json()
                        valid_ids = []
                        for speaker in speakers:
                            for style in speaker["styles"]:
                                valid_ids.append(style["id"])

                        if speaker_id in valid_ids:
                            self.speaker_id = speaker_id
                            return {"success": True, "speaker_id": speaker_id}
                        else:
                            return {
                                "success": False,
                                "error": f"Invalid speaker_id. Valid IDs: {valid_ids}",
                            }
                    else:
                        return {"success": False, "error": "Failed to get speaker list"}
        except Exception as e:
            logger.error(f"Error in set_speaker: {e}")
            return {"success": False, "error": str(e)}

    async def get_speakers(self) -> dict:
        """利用可能なスピーカーリストを取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.voicevox_url}/speakers") as response:
                    if response.status == 200:
                        speakers = await response.json()
                        return {"success": True, "speakers": speakers}
                    else:
                        return {
                            "success": False,
                            "error": f"Failed to get speakers: {response.status}",
                        }
        except Exception as e:
            logger.error(f"Error in get_speakers: {e}")
            return {"success": False, "error": str(e)}


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
                description="VOICEVOXを使用してテキストを音声に変換し再生する。keep_file=trueを指定すると、リップシンク用に音声ファイルを保持する。",
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
                        "keep_file": {
                            "type": "boolean",
                            "description": "音声ファイルを削除せずに保持するか（リップシンク用、デフォルトはfalse）",
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
                keep_file = arguments.get("keep_file", False)
                result = await voicevox_server.text_to_speech(text, speaker_id, keep_file)
                return [
                    TextContent(
                        type="text", text=json.dumps(result, ensure_ascii=False)
                    )
                ]

            elif name == "set_speaker":
                speaker_id = arguments.get("speaker_id", 1)
                result = await voicevox_server.set_speaker(speaker_id)
                return [TextContent(type="text", text=json.dumps(result))]

            elif name == "get_speakers":
                result = await voicevox_server.get_speakers()
                return [
                    TextContent(
                        type="text", text=json.dumps(result, ensure_ascii=False)
                    )
                ]

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
