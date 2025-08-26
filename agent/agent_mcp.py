from google.adk.agents import Agent
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams, StdioServerParameters
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

with open("prompt/emoji_prompt", "r", encoding="utf-8") as f:
    emoji_prompt = f.read()

with open("prompt/vibration_prompt", "r", encoding="utf-8") as f:
    vibration_prompt = f.read()

# MCPサーバーの接続設定
# 絵文字用MCPサーバー（別途実装が必要）
emoji_mcp_params = StdioConnectionParams(
    server_params=StdioServerParameters(
        command='python',
        args=['mcp_servers/emoji_server.py'],
    ),
    timeout=5.0
)

# 振動制御用MCPサーバー（別途実装が必要）
vibration_mcp_params = StdioConnectionParams(
    server_params=StdioServerParameters(
        command='python',
        args=['mcp_servers/vibration_server.py'],
    ),
    timeout=5.0
)

# MCPToolsetの作成
emoji_toolset = MCPToolset(
    connection_params=emoji_mcp_params,
    tool_filter=['add_emoji'],  # 特定のツールのみ使用
)

vibration_toolset = MCPToolset(
    connection_params=vibration_mcp_params,
    tool_filter=['generate_vibration_pattern', 'control_vibration'],
)

# エージェントの定義
emoji_agent = Agent(
    name="emoji_agent",
    model="gemini-1.5-flash",
    description="感情に基づいて適切な絵文字を提案する専門エージェント",
    instruction=emoji_prompt,
    tools=[emoji_toolset],
)

vibration_agent = Agent(
    name="vibration_agent",
    model="gemini-1.5-flash",
    description="感情に基づいて振動パターンを制御する専門エージェント",
    instruction=vibration_prompt,
    tools=[vibration_toolset],
)

root_agent = Agent(
    name="emotion_agent",
    model="gemini-1.5-flash",
    description="触覚を通じて感情を検出し応答するエージェント",
    instruction=system_prompt,
    sub_agents=[emoji_agent, vibration_agent],
    input_schema=TouchInput,
)

# ADKフレームワーク用のエクスポート
agent = root_agent