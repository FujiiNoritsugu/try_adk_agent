from google.adk.agents import Agent
from dotenv import load_dotenv

load_dotenv()

with open("prompt/system_prompt", "r", encoding="utf-8") as f:
    system_prompt = f.read()

sub_agent = Agent(
    name="sub_agent",
    model="gemini-1.5-flash",
    description="emotion_agentのサブエージェントです。感情を検出し、テキストに応じて応答します。",
    instruction="あなたは感情を検出し、テキストに応じて応答するサブエージェントです。あなたの役割は、与えられたテキストから感情を分析し、それに基づいて適切な応答を生成することです。",
)

root_agent = Agent(
    name="emotion_agent",
    model="gemini-1.5-flash",
    description="An agent that detects and responds to emotions in text.",
    instruction=system_prompt,
    sub_agents=[sub_agent],
)
