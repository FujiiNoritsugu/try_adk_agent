#!/usr/bin/env python3
"""
VTube Studio統合のテストスクリプト

このスクリプトはVTube Studio MCPサーバーの機能をテストします。

実行前の準備:
1. VTube Studioを起動
2. 設定 → プラグイン → APIを有効化（デフォルトポート: 8001）
3. Live2Dモデルをロード
4. 必要なホットキーを設定:
   - happy: 嬉しい表情
   - smile: 笑顔
   - angry: 怒り顔
   - sad: 悲しい表情
   - neutral: ニュートラル表情
   - ticklish: くすぐったい反応アニメーション
   - celebration: 祝福・喜びアニメーション

実行方法:
    python tests/test_vtube_studio.py
"""

import asyncio
import json
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import websockets


class VTubeStudioTester:
    """VTube Studio APIのテストクライアント"""

    def __init__(self, host="localhost", port=8001):
        self.ws_url = f"ws://{host}:{port}"
        self.plugin_name = "TestClient"
        self.plugin_developer = "VTube Studio Test"
        self.token = None

    async def send_request(self, message_type: str, data: dict = None) -> dict:
        """VTube Studio APIにリクエストを送信"""
        async with websockets.connect(self.ws_url, ping_interval=None) as ws:
            request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": "test_request",
                "messageType": message_type
            }
            if data:
                request["data"] = data

            # 認証が必要なリクエストにはトークンを追加
            if self.token and message_type != "AuthenticationTokenRequest":
                if "data" not in request:
                    request["data"] = {}
                request["data"]["pluginName"] = self.plugin_name
                request["data"]["pluginDeveloper"] = self.plugin_developer
                request["data"]["authenticationToken"] = self.token

            print(f"\n📤 Sending: {message_type}")
            await ws.send(json.dumps(request))

            response = await ws.recv()
            result = json.loads(response)
            print(f"📥 Response: {result.get('messageType')}")
            return result

    async def authenticate(self) -> bool:
        """VTube Studio APIの認証"""
        print("\n🔐 Authenticating with VTube Studio...")

        # トークンリクエスト
        token_response = await self.send_request(
            "AuthenticationTokenRequest",
            {
                "pluginName": self.plugin_name,
                "pluginDeveloper": self.plugin_developer,
                "pluginIcon": ""
            }
        )

        if "data" in token_response and "authenticationToken" in token_response["data"]:
            self.token = token_response["data"]["authenticationToken"]
            print(f"✅ Token received: {self.token[:20]}...")

            # 認証
            auth_response = await self.send_request(
                "AuthenticationRequest",
                {
                    "pluginName": self.plugin_name,
                    "pluginDeveloper": self.plugin_developer,
                    "authenticationToken": self.token
                }
            )

            if auth_response.get("data", {}).get("authenticated"):
                print("✅ Authentication successful!")
                return True
            else:
                print("❌ Authentication failed!")
                return False
        else:
            print("❌ Token request failed!")
            return False

    async def get_hotkeys(self) -> list:
        """利用可能なホットキー一覧を取得"""
        print("\n🔑 Getting available hotkeys...")
        response = await self.send_request("HotkeysInCurrentModelRequest")

        if "data" in response and "availableHotkeys" in response["data"]:
            hotkeys = response["data"]["availableHotkeys"]
            print(f"✅ Found {len(hotkeys)} hotkeys:")
            for hotkey in hotkeys:
                print(f"   - {hotkey['name']} (ID: {hotkey['hotkeyID']})")
            return hotkeys
        else:
            print("❌ Failed to get hotkeys")
            return []

    async def trigger_hotkey_by_name(self, hotkey_name: str) -> bool:
        """ホットキー名でホットキーをトリガー"""
        # ホットキー一覧を取得
        hotkeys_response = await self.send_request("HotkeysInCurrentModelRequest")

        if "data" not in hotkeys_response or "availableHotkeys" not in hotkeys_response["data"]:
            print(f"❌ Failed to get hotkeys list")
            return False

        # ホットキー名からIDを検索
        hotkey_id = None
        for hotkey in hotkeys_response["data"]["availableHotkeys"]:
            if hotkey["name"] == hotkey_name:
                hotkey_id = hotkey["hotkeyID"]
                break

        if not hotkey_id:
            print(f"❌ Hotkey '{hotkey_name}' not found")
            return False

        # ホットキーをトリガー
        print(f"\n🎯 Triggering hotkey: {hotkey_name}")
        response = await self.send_request(
            "HotkeyTriggerRequest",
            {"hotkeyID": hotkey_id}
        )

        if response.get("messageType") == "HotkeyTriggerResponse":
            print(f"✅ Hotkey '{hotkey_name}' triggered successfully!")
            return True
        else:
            print(f"❌ Failed to trigger hotkey '{hotkey_name}'")
            return False

    async def test_emotion_expressions(self):
        """感情に基づく表情テスト"""
        print("\n\n🎭 Testing Emotion-based Expressions")
        print("=" * 50)

        emotions_to_test = [
            ("happy", "Joy-based expression (joy=4, others=0)"),
            ("smile", "Fun-based expression (fun=2, others=0)"),
            ("angry", "Anger-based expression (anger=4, others=0)"),
            ("sad", "Sad-based expression (sad=3, others=0)"),
            ("neutral", "Neutral expression (all=0)")
        ]

        for hotkey_name, description in emotions_to_test:
            print(f"\n▶️ Testing: {description}")
            success = await self.trigger_hotkey_by_name(hotkey_name)
            if success:
                print(f"   ⏳ Waiting 2 seconds...")
                await asyncio.sleep(2)
            else:
                print(f"   ⚠️ Skipping '{hotkey_name}' (not configured)")

    async def test_animations(self):
        """アニメーションテスト"""
        print("\n\n🎬 Testing Animations")
        print("=" * 50)

        animations_to_test = [
            ("ticklish", "Ticklish reaction animation"),
            ("celebration", "Celebration/joy animation"),
        ]

        for hotkey_name, description in animations_to_test:
            print(f"\n▶️ Testing: {description}")
            success = await self.trigger_hotkey_by_name(hotkey_name)
            if success:
                print(f"   ⏳ Waiting 3 seconds...")
                await asyncio.sleep(3)
            else:
                print(f"   ⚠️ Skipping '{hotkey_name}' (not configured)")

    async def run_all_tests(self):
        """すべてのテストを実行"""
        print("=" * 50)
        print("VTube Studio Integration Test")
        print("=" * 50)

        try:
            # 認証
            if not await self.authenticate():
                print("\n❌ Authentication failed. Please check VTube Studio API settings.")
                return

            # ホットキー一覧を取得
            await self.get_hotkeys()

            # 表情テスト
            await self.test_emotion_expressions()

            # アニメーションテスト
            await self.test_animations()

            print("\n\n✅ All tests completed!")
            print("\n" + "=" * 50)
            print("📝 Setup Instructions for VTube Studio:")
            print("=" * 50)
            print("If some hotkeys were not found, please set them up in VTube Studio:")
            print("1. Open VTube Studio")
            print("2. Settings → Hotkeys")
            print("3. Create hotkeys with these names:")
            print("   - happy (expression for high joy)")
            print("   - smile (expression for moderate joy/fun)")
            print("   - angry (expression for high anger)")
            print("   - sad (expression for high sadness)")
            print("   - neutral (default/neutral expression)")
            print("   - ticklish (animation for ticklish reaction)")
            print("   - celebration (animation for success/celebration)")
            print("4. Assign appropriate expressions/animations to each hotkey")

        except websockets.exceptions.WebSocketException as e:
            print(f"\n❌ Connection error: {e}")
            print("Please make sure:")
            print("1. VTube Studio is running")
            print("2. API is enabled (Settings → Plugins → Enable API)")
            print("3. Port 8001 is accessible")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """メイン関数"""
    tester = VTubeStudioTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
