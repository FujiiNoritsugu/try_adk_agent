from google.adk.agents import Agent
from dotenv import load_dotenv

load_dotenv()

with open("prompt/system_prompt", "r", encoding="utf-8") as f:
    system_prompt = f.read()

agent = Agent(
    name="emotion_agent",
    model="gemini-2.0-flash",
    description="An agent that detects and responds to emotions in text.",
    instruction=system_prompt,
)
