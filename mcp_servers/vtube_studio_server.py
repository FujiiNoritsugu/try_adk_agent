#!/usr/bin/env python3
"""
VTube Studio統合MCPサーバー

VTube Studio APIを使用してLive2Dアバターの表情とアニメーションを制御します。

必要な設定:
1. VTube Studioを起動
2. 設定 → プラグイン → APIを有効化
3. ポート: 8001（デフォルト）

提供するツール:
- update_expression: 感情値に基づいて表情を更新
- play_animation: 特定のアニメーションを再生（くすぐり、ゲーム成功など）
- authenticate: VTube Studio APIの認証（初回のみ）
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any

import websockets
from mcp.server import Server
from mcp.types import Tool, TextContent

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/agents_log/vtube_studio_server.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# VTube Studio API設定
VTUBE_STUDIO_HOST = os.getenv('VTUBE_STUDIO_HOST', 'localhost')
VTUBE_STUDIO_PORT = int(os.getenv('VTUBE_STUDIO_PORT', '8001'))
PLUGIN_NAME = "EmotionalChatbot"
PLUGIN_DEVELOPER = "ADK Agent"

# 認証トークンファイル
TOKEN_FILE = os.path.expanduser("~/.vtube_studio_token")


class VTubeStudioClient:
    """VTube Studio WebSocket APIクライアント"""

    def __init__(self):
        self.ws_url = f"ws://{VTUBE_STUDIO_HOST}:{VTUBE_STUDIO_PORT}"
        self.token = self._load_token()

    def _load_token(self) -> str | None:
        """保存された認証トークンを読み込み"""
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                return f.read().strip()
        return None

    def _save_token(self, token: str):
        """認証トークンを保存"""
        with open(TOKEN_FILE, 'w') as f:
            f.write(token)
        logger.info(f"Token saved to {TOKEN_FILE}")

    async def _send_request(self, message_type: str, data: dict = None) -> dict:
        """VTube Studio APIにリクエストを送信"""
        try:
            async with websockets.connect(self.ws_url, ping_interval=None) as ws:
                request = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "emotional_chatbot_request",
                    "messageType": message_type
                }
                if data:
                    request["data"] = data

                # 認証が必要なリクエストにはトークンを追加
                if self.token and message_type != "AuthenticationTokenRequest":
                    if "data" not in request:
                        request["data"] = {}
                    request["data"]["pluginName"] = PLUGIN_NAME
                    request["data"]["pluginDeveloper"] = PLUGIN_DEVELOPER
                    request["data"]["authenticationToken"] = self.token

                logger.info(f"Sending request: {message_type}")
                await ws.send(json.dumps(request))

                response = await ws.recv()
                result = json.loads(response)
                logger.info(f"Received response: {result.get('messageType')}")
                return result
        except Exception as e:
            logger.error(f"VTube Studio API error: {e}")
            return {"error": str(e)}

    async def authenticate(self) -> dict:
        """VTube Studio APIの認証"""
        # トークンリクエスト
        response = await self._send_request(
            "AuthenticationTokenRequest",
            {
                "pluginName": PLUGIN_NAME,
                "pluginDeveloper": PLUGIN_DEVELOPER,
                "pluginIcon": ""
            }
        )

        if "data" in response and "authenticationToken" in response["data"]:
            self.token = response["data"]["authenticationToken"]
            self._save_token(self.token)

            # 認証
            auth_response = await self._send_request(
                "AuthenticationRequest",
                {
                    "pluginName": PLUGIN_NAME,
                    "pluginDeveloper": PLUGIN_DEVELOPER,
                    "authenticationToken": self.token
                }
            )
            return auth_response
        else:
            return response

    async def trigger_hotkey(self, hotkey_name: str) -> dict:
        """ホットキーをトリガーして表情やアニメーションを変更"""
        # ホットキーID一覧を取得
        hotkeys_response = await self._send_request("HotkeysInCurrentModelRequest")

        if "data" not in hotkeys_response or "availableHotkeys" not in hotkeys_response["data"]:
            return {"error": "Failed to get hotkeys list"}

        # ホットキー名からIDを検索
        hotkey_id = None
        for hotkey in hotkeys_response["data"]["availableHotkeys"]:
            if hotkey["name"] == hotkey_name:
                hotkey_id = hotkey["hotkeyID"]
                break

        if not hotkey_id:
            logger.warning(f"Hotkey '{hotkey_name}' not found. Available hotkeys: "
                          f"{[h['name'] for h in hotkeys_response['data']['availableHotkeys']]}")
            return {"error": f"Hotkey '{hotkey_name}' not found"}

        # ホットキーをトリガー
        response = await self._send_request(
            "HotkeyTriggerRequest",
            {"hotkeyID": hotkey_id}
        )
        return response

    async def set_expression_parameters(self, joy: float, fun: float, anger: float, sad: float) -> dict:
        """
        カスタムパラメータを使用して表情を設定

        注意: この機能を使うにはVTube Studioでカスタムパラメータを設定する必要があります
        """
        response = await self._send_request(
            "ParameterValueRequest",
            {
                "parameterValues": [
                    {"id": "Joy", "value": joy / 5.0},  # 0-5を0-1に正規化
                    {"id": "Fun", "value": fun / 5.0},
                    {"id": "Anger", "value": anger / 5.0},
                    {"id": "Sad", "value": sad / 5.0}
                ]
            }
        )
        return response


# MCPサーバー初期化
app = Server("vtube-studio-server")
client = VTubeStudioClient()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """利用可能なツールのリスト"""
    return [
        Tool(
            name="authenticate_vtube_studio",
            description="VTube Studio APIの認証を行います（初回のみ必要）。VTube Studioで承認ダイアログが表示されます。",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="update_avatar_expression",
            description=(
                "感情値に基づいてアバターの表情を更新します。"
                "joy（喜び）が高い場合は笑顔、anger（怒り）が高い場合は怒り顔など、"
                "感情値の組み合わせに応じて適切な表情ホットキーをトリガーします。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "joy": {
                        "type": "number",
                        "description": "喜びの感情値（0-5）"
                    },
                    "fun": {
                        "type": "number",
                        "description": "楽しさの感情値（0-5）"
                    },
                    "anger": {
                        "type": "number",
                        "description": "怒りの感情値（0-5）"
                    },
                    "sad": {
                        "type": "number",
                        "description": "悲しみの感情値（0-5）"
                    }
                },
                "required": ["joy", "fun", "anger", "sad"]
            }
        ),
        Tool(
            name="play_avatar_animation",
            description=(
                "特定のアニメーションを再生します。"
                "例: 'ticklish'（くすぐったい）、'celebration'（ゲーム成功の喜び）、"
                "'rhythm'（リズムに合わせた動き）など。"
                "これらのアニメーションはVTube Studioのホットキーとして設定されている必要があります。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "animation_name": {
                        "type": "string",
                        "description": "再生するアニメーション名（ホットキー名）",
                        "enum": [
                            "ticklish",        # くすぐったい反応
                            "celebration",     # 祝福・喜び
                            "rhythm_move",     # リズムゲーム用
                            "shy",             # 恥ずかしい
                            "surprise",        # 驚き
                            "neutral"          # ニュートラル表情
                        ]
                    },
                    "intensity": {
                        "type": "number",
                        "description": "アニメーションの強度（0-10）。くすぐったさレベルなどに使用。",
                        "minimum": 0,
                        "maximum": 10
                    }
                },
                "required": ["animation_name"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """ツールの実行"""
    try:
        if name == "authenticate_vtube_studio":
            result = await client.authenticate()
            if "error" in result:
                return [TextContent(
                    type="text",
                    text=f"Authentication failed: {result['error']}"
                )]
            return [TextContent(
                type="text",
                text="Authentication successful! VTube Studio is now connected."
            )]

        elif name == "update_avatar_expression":
            joy = arguments["joy"]
            fun = arguments["fun"]
            anger = arguments["anger"]
            sad = arguments["sad"]

            # 最も高い感情値に基づいてホットキーを選択
            emotions = {
                "joy": joy,
                "fun": fun,
                "anger": anger,
                "sad": sad
            }
            dominant_emotion = max(emotions, key=emotions.get)
            max_value = emotions[dominant_emotion]

            # 表情ホットキーのマッピング
            hotkey_map = {
                "joy": "happy" if max_value >= 3 else "smile",
                "fun": "excited" if max_value >= 3 else "smile",
                "anger": "angry" if max_value >= 3 else "annoyed",
                "sad": "sad" if max_value >= 3 else "neutral"
            }

            hotkey_name = hotkey_map.get(dominant_emotion, "neutral")
            result = await client.trigger_hotkey(hotkey_name)

            if "error" in result:
                return [TextContent(
                    type="text",
                    text=f"Expression update failed: {result['error']}. "
                         f"Make sure hotkey '{hotkey_name}' exists in VTube Studio."
                )]

            return [TextContent(
                type="text",
                text=f"Avatar expression updated to '{hotkey_name}' "
                     f"(dominant emotion: {dominant_emotion}={max_value:.1f})"
            )]

        elif name == "play_avatar_animation":
            animation_name = arguments["animation_name"]
            intensity = arguments.get("intensity", 5)

            # 強度に応じてホットキー名を調整
            if animation_name == "ticklish" and intensity > 5:
                hotkey_name = "ticklish_strong"
            else:
                hotkey_name = animation_name

            result = await client.trigger_hotkey(hotkey_name)

            if "error" in result:
                return [TextContent(
                    type="text",
                    text=f"Animation failed: {result['error']}. "
                         f"Make sure hotkey '{hotkey_name}' exists in VTube Studio."
                )]

            return [TextContent(
                type="text",
                text=f"Animation '{animation_name}' played (intensity: {intensity})"
            )]

        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    except Exception as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """MCPサーバーの起動"""
    from mcp.server.stdio import stdio_server

    logger.info("Starting VTube Studio MCP server...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
