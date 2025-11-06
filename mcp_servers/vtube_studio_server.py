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

    async def sync_lipsync_with_audio(self, audio_file_path: str) -> dict:
        """
        音声ファイルに合わせてリップシンクを実行

        WAVファイルの音量を解析して、MouthOpenパラメータをリアルタイムで制御
        """
        try:
            import wave
            import numpy as np
            import time

            # WAVファイルを開く
            with wave.open(audio_file_path, 'rb') as wav_file:
                # WAVファイルのパラメータを取得
                framerate = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                audio_data = wav_file.readframes(n_frames)

                # バイトデータをnumpy配列に変換
                if wav_file.getsampwidth() == 2:  # 16-bit audio
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                else:
                    logger.warning(f"Unsupported sample width: {wav_file.getsampwidth()}")
                    return {"success": False, "error": "Unsupported audio format"}

                # ステレオの場合はモノラルに変換
                if wav_file.getnchannels() == 2:
                    audio_array = audio_array[::2]  # 左チャンネルのみ使用

                # 音量を正規化（0-1）
                max_amplitude = np.max(np.abs(audio_array))
                if max_amplitude > 0:
                    normalized_audio = np.abs(audio_array) / max_amplitude
                else:
                    normalized_audio = np.zeros_like(audio_array)

                # フレームレートに基づいてサンプリング間隔を決定（30fps想定）
                fps = 30
                samples_per_frame = framerate // fps

                logger.info(f"Starting lipsync: {n_frames} frames at {framerate}Hz, {fps}fps")

                # リップシンクを実行
                start_time = time.time()
                for i in range(0, len(normalized_audio), samples_per_frame):
                    # 現在のフレームの音量を計算（RMS）
                    frame_samples = normalized_audio[i:i+samples_per_frame]
                    if len(frame_samples) > 0:
                        rms = np.sqrt(np.mean(frame_samples ** 2))
                        mouth_open_value = min(1.0, rms * 2.0)  # 音量を口の開き具合に変換
                    else:
                        mouth_open_value = 0.0

                    # MouthOpenパラメータを送信
                    await self._send_request(
                        "InjectParameterDataRequest",
                        {
                            "parameterValues": [
                                {
                                    "id": "MouthOpen",
                                    "value": mouth_open_value
                                }
                            ]
                        }
                    )

                    # フレームレートに合わせて待機
                    elapsed = time.time() - start_time
                    expected_time = i / framerate
                    sleep_time = expected_time - elapsed
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)

                # 最後に口を閉じる
                await self._send_request(
                    "InjectParameterDataRequest",
                    {
                        "parameterValues": [
                            {
                                "id": "MouthOpen",
                                "value": 0.0
                            }
                        ]
                    }
                )

                logger.info("Lipsync completed")

                # リップシンク完了後に音声ファイルを削除（クリーンアップ）
                try:
                    if os.path.exists(audio_file_path):
                        os.remove(audio_file_path)
                        logger.info(f"Audio file deleted: {audio_file_path}")
                except Exception as delete_error:
                    logger.warning(f"Failed to delete audio file: {delete_error}")

                return {
                    "success": True,
                    "duration": time.time() - start_time,
                    "frames": len(normalized_audio) // samples_per_frame
                }

        except Exception as e:
            logger.error(f"Lipsync error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


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
                "オプションでreset_after_secondsを指定すると、指定秒数後に自動的に中立表情に戻ります。"
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
                    },
                    "reset_after_seconds": {
                        "type": "number",
                        "description": "指定秒数後に表情を中立に戻す（オプション、0より大きい値を指定）"
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
        ),
        Tool(
            name="sync_lipsync_with_audio",
            description=(
                "音声ファイルに合わせてアバターのリップシンクを実行します。"
                "WAVファイルの音量を解析して、MouthOpenパラメータをリアルタイムで制御します。"
                "VOICEVOXのtext_to_speechツールが返すaudio_fileパスを渡してください。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "audio_file_path": {
                        "type": "string",
                        "description": "リップシンクする音声ファイルのパス（WAV形式）"
                    }
                },
                "required": ["audio_file_path"]
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
            reset_after_seconds = arguments.get("reset_after_seconds")

            # 感情値を辞書にまとめる
            emotions = {
                "joy": joy,
                "fun": fun,
                "anger": anger,
                "sad": sad
            }

            # 既存のVTube Studioホットキーにマッピング
            hotkey_map = {
                "joy": "Joy",             # 喜び
                "fun": "Pleasure",        # 楽しさ → 快感
                "anger": "Anger",         # 怒り
                "sad": "Sadness"          # 悲しみ
            }

            # 閾値以上の感情をすべて適用（優先順位: anger > sad > joy > fun）
            triggered_emotions = []
            applied_hotkeys = []

            # 感情の優先順位（強い感情を優先）
            priority_order = ["anger", "sad", "joy", "fun"]

            for emotion_name in priority_order:
                emotion_value = emotions[emotion_name]
                if emotion_value >= 0.5:  # 閾値: 0.5以上
                    hotkey_name = hotkey_map[emotion_name]
                    logger.info(f"Attempting to trigger hotkey '{hotkey_name}' for {emotion_name}={emotion_value:.1f}")
                    result = await client.trigger_hotkey(hotkey_name)

                    if "error" not in result:
                        triggered_emotions.append(f"{emotion_name}={emotion_value:.1f}")
                        applied_hotkeys.append(hotkey_name)
                        logger.info(f"Successfully triggered hotkey '{hotkey_name}' for {emotion_name}={emotion_value:.1f}")
                    else:
                        logger.error(f"Failed to trigger hotkey '{hotkey_name}': {result.get('error')}")

            # どの感情も閾値を超えていない場合は中立表情
            if not triggered_emotions:
                result = await client.trigger_hotkey("Remove Expressions")
                if "error" in result:
                    return [TextContent(
                        type="text",
                        text=f"Expression update failed: {result['error']}"
                    )]
                response_text = "Avatar expression set to neutral (all emotions below threshold)"
            else:
                response_text = f"Avatar expressions applied: {', '.join(applied_hotkeys)} ({', '.join(triggered_emotions)})"

            # 自動リセットが指定されている場合、遅延タスクを作成
            if reset_after_seconds and reset_after_seconds > 0:
                async def reset_expression():
                    await asyncio.sleep(reset_after_seconds)
                    logger.info(f"Resetting expression after {reset_after_seconds}s...")
                    await client.trigger_hotkey("Remove Expressions")

                # バックグラウンドタスクとして実行
                asyncio.create_task(reset_expression())
                response_text += f" Will reset to neutral after {reset_after_seconds}s."

            return [TextContent(
                type="text",
                text=response_text
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

        elif name == "sync_lipsync_with_audio":
            audio_file_path = arguments["audio_file_path"]

            result = await client.sync_lipsync_with_audio(audio_file_path)

            if "error" in result or not result.get("success"):
                return [TextContent(
                    type="text",
                    text=f"Lipsync failed: {result.get('error', 'Unknown error')}"
                )]

            return [TextContent(
                type="text",
                text=f"Lipsync completed successfully. Duration: {result['duration']:.2f}s, Frames: {result['frames']}"
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
