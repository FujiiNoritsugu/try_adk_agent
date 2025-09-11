from google.adk.agents import Agent
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_session_manager import StdioServerParameters
from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class TouchInput(BaseModel):
    """触覚入力のスキーマ"""

    data: float = Field(
        description="触覚の強度（0-1）。0は何も感じない、0.5は最も気持ち良い、1は痛い",
        ge=0.0,
        le=1.0,
    )
    touched_area: str = Field(description="触られた体の部位")


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
    tools=[emoji_toolset, vibration_toolset, voicevox_toolset],  # 全てのMCPツールセットを使用
    input_schema=TouchInput,
)

# ADKフレームワーク用のエクスポート
agent = root_agent
