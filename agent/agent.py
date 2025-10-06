from google.adk.agents import Agent
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_session_manager import StdioServerParameters
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, Dict
import warnings
import logging

# Suppress experimental feature warnings
warnings.filterwarnings("ignore", message=".*EXPERIMENTAL.*")

# Suppress MCP server INFO logs
logging.getLogger("mcp.server.lowlevel.server").setLevel(logging.WARNING)

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

# MCPサーバーの接続設定
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

# Leap Motion用MCPサーバー
leapmotion_mcp_params = StdioConnectionParams(
    server_params=StdioServerParameters(
        command="python",
        args=["server_leapmotion/server.py"],
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

leapmotion_toolset = MCPToolset(
    connection_params=leapmotion_mcp_params,
    tool_filter=["get_leap_motion_data", "convert_to_touch", "set_gesture_mapping"],
)

# エージェントの定義
# Arduino、VOICEVOX、Leap Motionの全てと連携
root_agent = Agent(
    name="emotion_agent",
    model="gemini-2.5-flash",
    description="Arduino振動、VOICEVOX音声、Leap Motion入力を統合した感情応答エージェント",
    instruction=system_prompt,
    tools=[emoji_toolset, vibration_toolset, voicevox_toolset, leapmotion_toolset],
    input_schema=TouchInput,
)

# ADKフレームワーク用のエクスポート
agent = root_agent
