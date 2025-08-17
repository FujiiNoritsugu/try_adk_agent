from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from dotenv import load_dotenv

load_dotenv()

with open("prompt/system_prompt", "r", encoding="utf-8") as f:
    system_prompt = f.read()

# 感情分析関数の定義
def analyze_emotion(data: float, touched_area: str) -> dict:
    """触覚データから詳細な感情状態を分析します
    
    Args:
        data: 触覚データの強度 (0.0-1.0)
        touched_area: 触れられた部位
        
    Returns:
        分析結果と推奨感情パラメータを含む辞書
    """
    return {
        "analysis": f"{touched_area}への{data}の強さの刺激を分析しました",
        "recommended_emotion": {
            "joy": max(0, min(5, 5 * (1 - abs(data - 0.5) * 2))),
            "fun": max(0, min(5, 3 * (1 - abs(data - 0.5)))),
            "anger": max(0, min(5, 5 * (data - 0.7) if data > 0.7 else 0)),
            "sad": max(0, min(5, 2 * (data - 0.8) if data > 0.8 else 0))
        }
    }

# FunctionToolで関数をラップ
emotion_analysis_tool = FunctionTool(analyze_emotion)

sub_agent = Agent(
    name="sub_agent",
    model="gemini-1.5-flash",
    description="触覚データを分析して感情状態を計算する専門エージェント",
    instruction="""あなたは触覚データから感情を分析する専門家です。
    与えられたdataとtouched_areaから、4つの感情パラメータ（joy, fun, anger, sad）を計算します。
    
    計算ルール:
    - data=0.5付近: joy と fun が最大
    - data=0.7以上: anger が上昇
    - data=0.8以上: sad も上昇
    - data=0に近い: すべての感情が低下
    
    analyze_emotionツールを使用して分析を行ってください。""",
    tools=[emotion_analysis_tool]
)

root_agent = Agent(
    name="emotion_agent",
    model="gemini-1.5-flash",
    description="An agent that detects and responds to emotions in text.",
    instruction=system_prompt,
    sub_agents=[sub_agent],
)
