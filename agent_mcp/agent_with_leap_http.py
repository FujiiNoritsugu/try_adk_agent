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
import threading
import time
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


class LeapMotionHTTPAgent(Agent):
    """Leap Motion HTTPサーバーと連携するエージェント"""
    
    def __init__(self, *args, **kwargs):
        # Leap Motion関連の設定を抽出
        self.leap_server_url = kwargs.pop('leap_server_url', os.getenv("LEAP_MOTION_SERVER_URL", "http://localhost:8001"))
        self.leap_enabled = kwargs.pop('leap_enabled', True)
        self.leap_poll_interval = kwargs.pop('leap_poll_interval', 0.1)
        self.leap_min_process_interval = kwargs.pop('leap_min_process_interval', 0.5)
        
        # 親クラスの初期化
        super().__init__(*args, **kwargs)
        
        # Leap Motionポーリング用の属性
        self.polling_thread = None
        self.is_polling = False
        self.last_processed_time = None
        
        # Leap Motionポーリングを自動開始
        if self.leap_enabled:
            self.start_leap_polling()
    
    def start_leap_polling(self):
        """Leap Motionポーリングを開始"""
        if not self.is_polling:
            self.is_polling = True
            self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
            self.polling_thread.start()
            logger.info(f"Started Leap Motion polling from {self.leap_server_url}")
    
    def stop_leap_polling(self):
        """Leap Motionポーリングを停止"""
        self.is_polling = False
        if self.polling_thread:
            self.polling_thread.join(timeout=2.0)
        logger.info("Stopped Leap Motion polling")
    
    def _polling_loop(self):
        """ポーリングループ（別スレッドで実行）"""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._async_polling_loop())
    
    async def _async_polling_loop(self):
        """非同期ポーリングループ"""
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            while self.is_polling:
                try:
                    # Touch input形式でデータを取得
                    response = await client.get(f"{self.leap_server_url}/touch-input")
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # モックデータでない、実際の手の検出があった場合のみ処理
                        if not data.get("mock", False) and data.get("gesture_type") != "none":
                            # 最小間隔チェック
                            current_time = datetime.now()
                            if self.last_processed_time is None or \
                               (current_time - self.last_processed_time).total_seconds() >= self.leap_min_process_interval:
                                
                                # TouchInput形式に変換
                                touch_input = TouchInput(
                                    data=data.get("data", 0.5),
                                    touched_area=data.get("touched_area", "空中"),
                                    gesture_type=data.get("gesture_type"),
                                    hand_position=data.get("raw_leap_data", {}).get("hand_position") if data.get("raw_leap_data") else None,
                                    hand_velocity=data.get("raw_leap_data", {}).get("hand_velocity") if data.get("raw_leap_data") else None,
                                    leap_confidence=data.get("raw_leap_data", {}).get("confidence", 1.0) if data.get("raw_leap_data") else None
                                )
                                
                                logger.info(f"Processing Leap Motion input: {touch_input.gesture_type} at {touch_input.touched_area} (intensity: {touch_input.data})")
                                
                                # エージェントのrunメソッドを直接呼び出し
                                # 注意: これはメインループで実行される
                                try:
                                    # 新しいイベントループで実行
                                    result = await self.run(touch_input)
                                    logger.info(f"Agent response: {result}")
                                except Exception as e:
                                    logger.error(f"Error processing agent input: {e}")
                                
                                self.last_processed_time = current_time
                    
                    # 短い間隔でポーリング
                    await asyncio.sleep(self.leap_poll_interval)
                    
                except httpx.RequestError as e:
                    logger.error(f"Error polling Leap Motion server: {e}")
                    await asyncio.sleep(1)  # エラー時は少し長めに待機
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    await asyncio.sleep(1)
    
    def __del__(self):
        """デストラクタでポーリングを停止"""
        self.stop_leap_polling()


# プロンプトファイルの読み込み
with open("prompt/system_prompt", "r", encoding="utf-8") as f:
    system_prompt = f.read()

# エージェントの定義（カスタムクラスを使用）
# LeapMotion入力確認用にMCPツールセットを省略
root_agent = LeapMotionHTTPAgent(
    name="emotion_agent",
    model="gemini-1.5-flash",
    description="Leap Motionからの入力を受け取り感情を検出し応答するエージェント",
    instruction=system_prompt,
    tools=[],  # MCPツールセットを全て削除
    input_schema=TouchInput,
    # Leap Motion specific settings
    leap_server_url=os.getenv("LEAP_MOTION_SERVER_URL", "http://localhost:8001"),
    leap_enabled=True,
    leap_poll_interval=0.1,
    leap_min_process_interval=0.5,
)

# ADKフレームワーク用のエクスポート
agent = root_agent