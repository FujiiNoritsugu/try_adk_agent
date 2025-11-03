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
# WSL2環境ではWindowsホストのIPアドレスを自動検出
def get_vtube_studio_host():
    """VTube Studioのホストアドレスを取得（WSL2対応）"""
    env_host = os.getenv('VTUBE_STUDIO_HOST')
    if env_host:
        return env_host

    # WSL2環境: /etc/resolv.confからWindowsホストIPを取得
    try:
        with open('/etc/resolv.conf', 'r') as f:
            for line in f:
                if line.startswith('nameserver'):
                    return line.split()[1]
    except Exception:
        pass

    return 'localhost'

VTUBE_STUDIO_HOST = get_vtube_studio_host()
VTUBE_STUDIO_PORT = int(os.getenv('VTUBE_STUDIO_PORT', '8001'))
PLUGIN_NAME = "EmotionalChatbot"
PLUGIN_DEVELOPER = "ADK Agent"

logger.info(f"VTube Studio Host: {VTUBE_STUDIO_HOST}:{VTUBE_STUDIO_PORT}")

# 認証トークンファイル
TOKEN_FILE = os.path.expanduser("~/.vtube_studio_token")


class VTubeStudioClient:
    """VTube Studio WebSocket APIクライアント"""

    def __init__(self):
        self.ws_url = f"ws://{VTUBE_STUDIO_HOST}:{VTUBE_STUDIO_PORT}"
        self.token = self._load_token()
        self.ws = None  # 永続的なWebSocket接続
        self.authenticated = False  # 認証状態

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

    async def connect(self):
        """WebSocket接続を確立"""
        if self.ws is None:
            logger.info(f"Connecting to VTube Studio at {self.ws_url}...")
            self.ws = await websockets.connect(self.ws_url, ping_interval=None)
            self.authenticated = False  # 新しい接続では再認証が必要

    async def disconnect(self):
        """WebSocket接続を切断"""
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
        self.ws = None
        self.authenticated = False

    async def _send_request(self, message_type: str, data: dict = None, retry_auth: bool = True) -> dict:
        """VTube Studio APIにリクエストを送信"""
        try:
            # WebSocket接続を確立
            await self.connect()

            # 認証が必要なリクエストで、まだ認証されていない場合は先に認証
            if message_type not in ["AuthenticationTokenRequest", "AuthenticationRequest"] and not self.authenticated:
                logger.info("Not authenticated yet. Authenticating first...")
                auth_result = await self.authenticate()
                if not auth_result.get("data", {}).get("authenticated"):
                    return {"error": "Authentication required but failed"}

            request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": "emotional_chatbot_request",
                "messageType": message_type
            }
            if data:
                request["data"] = data

            # 認証が必要なリクエストにはトークンを追加
            # AuthenticationTokenRequest と AuthenticationRequest 以外のすべてのリクエストに必要
            if self.token and message_type not in ["AuthenticationTokenRequest", "AuthenticationRequest"]:
                if "data" not in request:
                    request["data"] = {}
                request["data"]["authenticationToken"] = self.token

            logger.info(f"Sending request: {message_type}")
            await self.ws.send(json.dumps(request))

            response = await self.ws.recv()
            result = json.loads(response)
            logger.info(f"Received response: {result.get('messageType')}")

            # エラーの詳細をログに記録
            if result.get('messageType') == 'APIError':
                error_id = result.get('data', {}).get('errorID', 'Unknown')
                error_msg = result.get('data', {}).get('message', 'No error message')
                logger.error(f"VTube Studio API Error - ID: {error_id}, Message: {error_msg}")

                # Error ID 8: 認証エラー → 再接続して再認証
                if error_id == 8 and retry_auth:
                    logger.info("Authentication error detected. Reconnecting and re-authenticating...")
                    await self.disconnect()
                    await self.connect()
                    auth_result = await self.authenticate()
                    if auth_result.get("data", {}).get("authenticated"):
                        logger.info("Re-authentication successful. Retrying original request...")
                        return await self._send_request(message_type, data, retry_auth=False)
                    else:
                        logger.error("Re-authentication failed.")

            return result
        except Exception as e:
            logger.error(f"VTube Studio API error: {e}")
            # 接続エラーの場合は再接続を試みる
            await self.disconnect()
            return {"error": str(e)}

    async def authenticate(self) -> dict:
        """VTube Studio APIの認証（現在のWebSocket接続内で実行）"""
        logger.info("Starting VTube Studio authentication...")

        # WebSocket接続を確立
        await self.connect()

        # トークンリクエスト
        request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "auth_token_request",
            "messageType": "AuthenticationTokenRequest",
            "data": {
                "pluginName": PLUGIN_NAME,
                "pluginDeveloper": PLUGIN_DEVELOPER,
                "pluginIcon": ""
            }
        }
        logger.info("Sending request: AuthenticationTokenRequest")
        await self.ws.send(json.dumps(request))
        response = await self.ws.recv()
        token_response = json.loads(response)
        logger.info(f"Received response: {token_response.get('messageType')}")

        if "data" not in token_response or "authenticationToken" not in token_response["data"]:
            logger.error("Token request failed!")
            return token_response

        self.token = token_response["data"]["authenticationToken"]
        self._save_token(self.token)
        logger.info(f"Token received: {self.token[:20]}...")

        # 認証リクエスト（同じWebSocket接続内で）
        auth_request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "auth_request",
            "messageType": "AuthenticationRequest",
            "data": {
                "pluginName": PLUGIN_NAME,
                "pluginDeveloper": PLUGIN_DEVELOPER,
                "authenticationToken": self.token
            }
        }
        logger.info("Sending request: AuthenticationRequest")
        await self.ws.send(json.dumps(auth_request))
        auth_response_raw = await self.ws.recv()
        auth_response = json.loads(auth_response_raw)
        logger.info(f"Received response: {auth_response.get('messageType')}")

        if auth_response.get("data", {}).get("authenticated"):
            logger.info("Authentication successful!")
            self.authenticated = True
        else:
            logger.error("Authentication failed!")
            self.authenticated = False

        return auth_response

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
                "利用可能なアニメーション: 'shake'（振る/揺れる）、'shock'（ショック/驚き）など。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "animation_name": {
                        "type": "string",
                        "description": "再生するアニメーション名",
                        "enum": [
                            "shake",      # 振る/揺れる
                            "shock"       # ショック/驚き
                        ]
                    },
                    "intensity": {
                        "type": "number",
                        "description": "アニメーションの強度（0-10）",
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

            # 既存のVTube Studioホットキーにマッピング
            # 利用可能: ['Heart Eyes', 'Eyes Cry', 'Angry Sign', 'Shock Sign', 'Remove Expressions', 'Anim Shake']
            hotkey_map = {
                "joy": "Heart Eyes",      # 喜び → ハートの目
                "fun": "Heart Eyes",      # 楽しさ → ハートの目
                "anger": "Angry Sign",    # 怒り → 怒りサイン
                "sad": "Eyes Cry"         # 悲しみ → 泣く目
            }

            # 感情値が低い場合は中立表情（Remove Expressions）
            if max_value < 1:
                hotkey_name = "Remove Expressions"
            else:
                hotkey_name = hotkey_map.get(dominant_emotion, "Remove Expressions")

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

            # 既存のVTube Studioホットキーにマッピング
            animation_map = {
                "shake": "Anim Shake",      # 振る/揺れる
                "shock": "Shock Sign"       # ショック/驚き
            }

            hotkey_name = animation_map.get(animation_name, "Anim Shake")
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
