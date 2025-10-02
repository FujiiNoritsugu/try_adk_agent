from google.adk.agents import Agent
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, Dict

load_dotenv()


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
        description="Leap Motionで検出されたジェスチャータイプ（swipe, circle, tap, grab, pinch）",
    )
    hand_position: Optional[Dict[str, float]] = Field(
        default=None, description="手の3D位置座標（x, y, z）"
    )
    hand_velocity: Optional[float] = Field(default=None, description="手の移動速度")
    leap_confidence: Optional[float] = Field(
        default=None, description="Leap Motionの検出信頼度（0-1）"
    )


# プロンプトファイルの読み込み
with open("prompt/system_prompt", "r", encoding="utf-8") as f:
    system_prompt = f.read()

# エージェントの定義（通常のAgentクラスを使用）
# Leap Motion入力はleap_to_adk_bridge.pyから標準入力で受け取る
root_agent = Agent(
    name="emotion_agent",
    model="gemini-2.5-flash",
    description="Leap Motionからの入力を受け取り感情を検出し応答するエージェント",
    instruction=system_prompt,
    tools=[],  # MCPツールセットを全て削除（テスト用）
    input_schema=TouchInput,
)

# ADKフレームワーク用のエクスポート
agent = root_agent
