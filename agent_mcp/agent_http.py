from google.adk.agents import Agent
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_session_manager import StdioServerParameters
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, Dict
import asyncio
import httpx
import logging
import os
from datetime import datetime

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TouchInput(BaseModel):
    """触覚入力のスキーマ"""

    data: float = Field(
        description="触覚の強度（0-1）。0は何も感じない、0.5は最も気持ち良い、1は痛い",
        ge=0.0,
        le=1.0,
    )
    touched_area: str = Field(description="触られた体の部位")
    
    # Leap Motion拡張フィールド（オプション）
    gesture_type: Optional[str] = Field(
        default=None,
        description="Leap Motionで検出されたジェスチャータイプ（swipe, circle, tap, grab, pinch）"
    )
    hand_position: Optional[Dict[str, float]] = Field(
        default=None,
        description="手の3D位置座標（x, y, z）"
    )
    hand_velocity: Optional[float] = Field(
        default=None,
        description="手の移動速度"
    )
    leap_confidence: Optional[float] = Field(
        default=None,
        description="Leap Motionの検出信頼度（0-1）"
    )


class LeapMotionPoller:
    """Leap Motion HTTPサーバーからデータをポーリングするクラス"""
    
    def __init__(self, server_url: str, agent):
        self.server_url = server_url
        self.agent = agent
        self.is_running = False
        self.last_processed_time = None
        self.min_interval = 0.5  # 最小処理間隔（秒）
        
    async def start_polling(self):
        """ポーリングを開始"""
        self.is_running = True
        logger.info(f"Starting Leap Motion polling from {self.server_url}")
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            while self.is_running:
                try:
                    # Touch input形式でデータを取得
                    response = await client.get(f"{self.server_url}/touch-input")
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # モックデータでない、実際の手の検出があった場合のみ処理
                        if not data.get("mock", False) and data.get("gesture_type") != "none":
                            # 最小間隔チェック
                            current_time = datetime.now()
                            if self.last_processed_time is None or \
                               (current_time - self.last_processed_time).total_seconds() >= self.min_interval:
                                
                                # TouchInput形式に変換
                                touch_input = TouchInput(
                                    data=data.get("data", 0.5),
                                    touched_area=data.get("touched_area", "空中"),
                                    gesture_type=data.get("gesture_type"),
                                    hand_position=data.get("raw_leap_data", {}).get("hand_position") if data.get("raw_leap_data") else None,
                                    hand_velocity=data.get("raw_leap_data", {}).get("hand_velocity") if data.get("raw_leap_data") else None,
                                    leap_confidence=data.get("raw_leap_data", {}).get("confidence") if data.get("raw_leap_data") else None
                                )
                                
                                logger.info(f"Processing Leap Motion input: {touch_input.gesture_type} at {touch_input.touched_area} (intensity: {touch_input.data})")
                                
                                # エージェントに入力を送信
                                try:
                                    result = await self.agent.run(touch_input)
                                    logger.info(f"Agent response: {result}")
                                except Exception as e:
                                    logger.error(f"Error processing agent input: {e}")
                                
                                self.last_processed_time = current_time
                    
                    # 短い間隔でポーリング
                    await asyncio.sleep(0.1)
                    
                except httpx.RequestError as e:
                    logger.error(f"Error polling Leap Motion server: {e}")
                    await asyncio.sleep(1)  # エラー時は少し長めに待機
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    await asyncio.sleep(1)
    
    def stop_polling(self):
        """ポーリングを停止"""
        self.is_running = False
        logger.info("Stopping Leap Motion polling")


# プロンプトファイルの読み込み
with open("prompt/system_prompt", "r", encoding="utf-8") as f:
    system_prompt = f.read()

# MCPサーバーの接続設定（Leap Motion以外）
# 絵文字用MCPサーバー
emoji_mcp_params = StdioConnectionParams(
    server_params=StdioServerParameters(
        command="python",
        args=["mcp_servers/emoji_server.py"],
    ),
    timeout=30.0,
)

# 振動制御用MCPサーバー
vibration_mcp_params = StdioConnectionParams(
    server_params=StdioServerParameters(
        command="python",
        args=["mcp_servers/vibration_server.py"],
    ),
    timeout=30.0,
)

# VOICEVOX用MCPサーバー
voicevox_mcp_params = StdioConnectionParams(
    server_params=StdioServerParameters(
        command="python",
        args=["mcp_servers/voicevox_server.py"],
    ),
    timeout=30.0,
)

# MCPToolsetの作成
emoji_toolset = MCPToolset(
    connection_params=emoji_mcp_params,
    tool_filter=["add_emoji"],
)

vibration_toolset = MCPToolset(
    connection_params=vibration_mcp_params,
    tool_filter=["generate_vibration_pattern", "control_vibration", "initialize_arduino", "send_arduino_vibration"],
)

voicevox_toolset = MCPToolset(
    connection_params=voicevox_mcp_params,
    tool_filter=["text_to_speech", "set_speaker", "get_speakers"],
)

# エージェントの定義
root_agent = Agent(
    name="emotion_agent",
    model="gemini-1.5-flash",
    description="触覚を通じて感情を検出し応答するエージェント",
    instruction=system_prompt,
    tools=[emoji_toolset, vibration_toolset, voicevox_toolset],  # Leap Motion MCPを除外
    input_schema=TouchInput,
)

# Leap Motion HTTPサーバーのURL（環境変数または設定ファイルから取得）
LEAP_MOTION_SERVER_URL = os.getenv("LEAP_MOTION_SERVER_URL", "http://localhost:8001")

# Leap Motionポーラーの作成
leap_poller = LeapMotionPoller(LEAP_MOTION_SERVER_URL, root_agent)

# バックグラウンドでポーリングを開始する関数
async def start_leap_polling():
    """バックグラウンドでLeap Motionのポーリングを開始"""
    asyncio.create_task(leap_poller.start_polling())

# ADKフレームワーク用のエクスポート
agent = root_agent

# 注意: ADKでエージェントを実行する際、Leap Motionポーリングを開始するには
# 別途 start_leap_polling() を呼び出す必要があります