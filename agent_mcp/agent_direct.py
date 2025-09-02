from google.adk.agents import Agent
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_session_manager import StdioServerParameters
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# 直接実装したツールをインポート
from vibration_tool import vibration_tools

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
with open("prompt/system_prompt_direct", "r", encoding="utf-8") as f:
    system_prompt = f.read()

# MCPサーバーの接続設定
# 絵文字用MCPサーバー
emoji_mcp_params = StdioConnectionParams(
    server_params=StdioServerParameters(
        command='python',
        args=['mcp_servers/emoji_server.py'],
    ),
    timeout=5.0
)

# MCPToolsetの作成
emoji_toolset = MCPToolset(
    connection_params=emoji_mcp_params,
    tool_filter=['add_emoji'],
)

# エージェントの定義
root_agent = Agent(
    name="emotion_agent",
    model="gemini-1.5-flash",
    description="触覚を通じて感情を検出し応答するエージェント",
    instruction=system_prompt,
    tools=[emoji_toolset] + vibration_tools,  # MCPツールと直接実装ツールを組み合わせ
    input_schema=TouchInput,
)

# ADKフレームワーク用のエクスポート
agent = root_agent