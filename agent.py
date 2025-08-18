from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from dotenv import load_dotenv

load_dotenv()

with open("prompt/system_prompt", "r", encoding="utf-8") as f:
    system_prompt = f.read()

with open("prompt/emoji_prompt", "r", encoding="utf-8") as f:
    emoji_prompt = f.read()


# 絵文字追加関数の定義
def add_emoji(message: str, joy: int, fun: int, anger: int, sad: int) -> dict:
    """感情パラメータに基づいて適切な絵文字を文章に追加します

    Args:
        message: 絵文字を追加する文章
        joy: 喜びの感情値 (0-5)
        fun: 楽しさの感情値 (0-5)
        anger: 怒りの感情値 (0-5)
        sad: 悲しみの感情値 (0-5)

    Returns:
        絵文字が追加された文章を含む辞書
    """
    # 最も高い感情を特定
    emotions = {"joy": joy, "fun": fun, "anger": anger, "sad": sad}

    # 感情と絵文字のマッピング
    emoji_map = {
        "joy": ["😊", "😄", "😃", "😁", "🥰", "😍"],
        "fun": ["🎉", "🎊", "✨", "🌟", "🎈", "🎯"],
        "anger": ["😠", "😡", "💢", "😤", "🔥", "⚡"],
        "sad": ["😢", "😭", "💔", "😞", "😔", "🥺"],
    }

    # 最も強い感情を見つける
    max_emotion = max(emotions.items(), key=lambda x: x[1])
    emotion_name, emotion_value = max_emotion

    # 感情値が0の場合は絵文字を追加しない
    if emotion_value == 0:
        return {"message_with_emoji": message}

    # 感情の強さに応じて絵文字を選択（0-5の値を0-5のインデックスに変換）
    emoji_index = min(emotion_value - 1, 5)
    emoji = emoji_map[emotion_name][emoji_index]

    # 複数の高い感情がある場合は追加の絵文字を付ける
    additional_emojis = []
    for emo_name, emo_value in emotions.items():
        if emo_name != emotion_name and emo_value >= 3:
            additional_emojis.append(emoji_map[emo_name][min(emo_value - 1, 5)])

    # 絵文字を文章に追加
    emoji_str = emoji + "".join(additional_emojis[:2])  # 最大3つまで

    return {
        "message_with_emoji": f"{message} {emoji_str}",
        "dominant_emotion": emotion_name,
        "emoji_used": emoji_str,
    }


# FunctionToolで関数をラップ
add_emoji_tool = FunctionTool(add_emoji)

sub_agent = Agent(
    name="sub_agent",
    model="gemini-1.5-flash",
    description="感情に基づいて適切な絵文字を追加する専門エージェント",
    instruction=emoji_prompt,
    tools=[add_emoji_tool],
)

root_agent = Agent(
    name="emotion_agent",
    model="gemini-1.5-flash",
    description="触覚を通じて感情を検出し応答するエージェント",
    instruction=system_prompt,
    sub_agents=[sub_agent],
)
