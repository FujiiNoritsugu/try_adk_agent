from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Dict, List, Tuple

load_dotenv()


class TouchInput(BaseModel):
    """触覚入力のスキーマ"""

    data: float = Field(
        description="触覚の強度（0-1）。0は何も感じない、0.5は最も気持ち良い、1は痛い",
        ge=0.0,
        le=1.0,
    )
    touched_area: str = Field(description="触られた体の部位")


class EmotionInput(BaseModel):
    """感情パラメータ入力のスキーマ"""

    class Emotion(BaseModel):
        joy: int = Field(description="喜びの感情値", ge=0, le=5)
        fun: int = Field(description="楽しさの感情値", ge=0, le=5)
        anger: int = Field(description="怒りの感情値", ge=0, le=5)
        sad: int = Field(description="悲しみの感情値", ge=0, le=5)

    emotion: Emotion = Field(description="感情パラメータ")
    message: str = Field(description="絵文字を追加する対象のメッセージ")


with open("prompt/system_prompt", "r", encoding="utf-8") as f:
    system_prompt = f.read()

with open("prompt/emoji_prompt", "r", encoding="utf-8") as f:
    emoji_prompt = f.read()

with open("prompt/vibration_prompt", "r", encoding="utf-8") as f:
    vibration_prompt = f.read()


# 絵文字追加関数の定義
def add_emoji(joy: int, fun: int, anger: int, sad: int) -> str:
    """感情パラメータに基づいて適切な絵文字を返却します

    Args:
        joy: 喜びの感情値 (0-5)
        fun: 楽しさの感情値 (0-5)
        anger: 怒りの感情値 (0-5)
        sad: 悲しみの感情値 (0-5)

    Returns:
        絵文字
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
        print("絵文字なし")
        return ""

    # 感情の強さに応じて絵文字を選択（0-5の値を0-5のインデックスに変換）
    emoji_index = min(emotion_value - 1, 5)
    emoji = emoji_map[emotion_name][emoji_index]

    # 複数の高い感情がある場合は追加の絵文字を付ける
    additional_emojis = []
    for emo_name, emo_value in emotions.items():
        if emo_name != emotion_name and emo_value >= 3:
            additional_emojis.append(emoji_map[emo_name][min(emo_value - 1, 5)])

    # 絵文字を追加
    emoji_str = emoji + "".join(additional_emojis[:2])  # 最大3つまで
    print(f"絵文字: {emoji_str}")
    return emoji_str


# 振動パターン生成関数の定義
def generate_vibration_pattern(joy: int, fun: int, anger: int, sad: int) -> dict:
    """感情パラメータに基づいて振動パターンを生成します

    Args:
        joy: 喜びの感情値 (0-5)
        fun: 楽しさの感情値 (0-5)
        anger: 怒りの感情値 (0-5)
        sad: 悲しみの感情値 (0-5)

    Returns:
        振動パターンの設定を含む辞書
    """
    # 基本振動パターンの定義
    vibration_patterns = {
        "joy": {
            "pattern": "pulse",
            "intensity_base": 1.0,  # 100%最大強度
            "frequency_base": 5.0,  # 5回繰り返し
            "duration_base": 10.0,  # 10秒に延長
            "description": "軽快でリズミカルな振動",
        },
        "fun": {
            "pattern": "wave",
            "intensity_base": 1.0,  # 100%最大強度
            "frequency_base": 6.0,  # 6回繰り返し
            "duration_base": 8.0,  # 8秒に延長
            "description": "楽しい波打つような振動",
        },
        "anger": {
            "pattern": "burst",
            "intensity_base": 1.0,  # 100%最大値
            "frequency_base": 8.0,  # 8回繰り返し
            "duration_base": 6.0,  # 6秒に延長
            "description": "強く断続的な振動",
        },
        "sad": {
            "pattern": "fade",
            "intensity_base": 1.0,  # 100%に増加
            "frequency_base": 4.0,  # 4回繰り返し
            "duration_base": 12.0,  # 12秒に延長
            "description": "ゆっくりとした弱い振動",
        },
    }

    # 感情値の辞書
    emotions = {"joy": joy, "fun": fun, "anger": anger, "sad": sad}

    # 最も強い感情を見つける
    max_emotion = max(emotions.items(), key=lambda x: x[1])
    dominant_emotion, emotion_value = max_emotion

    # 感情値が0の場合は振動なし
    if emotion_value == 0:
        return {
            "vibration_enabled": False,
            "pattern": "none",
            "intensity": 0,
            "frequency": 0,
            "duration": 0,
            "description": "振動なし",
        }

    # 基本パターンを取得
    base_pattern = vibration_patterns[dominant_emotion]

    # 感情の強さに応じて調整（1-5を0.2-1.0にマッピング）
    emotion_multiplier = 0.2 + (emotion_value / 5) * 0.8

    # 複数の感情が高い場合の調整
    mixed_emotions = [
        emo for emo, val in emotions.items() if emo != dominant_emotion and val >= 3
    ]

    # 混合パターンの作成
    if mixed_emotions:
        # 複数の感情が強い場合は、パターンを複雑にする
        pattern_type = f"{base_pattern['pattern']}_mixed"
        intensity_adjustment = 1.1
        frequency_adjustment = 1.2
    else:
        pattern_type = base_pattern["pattern"]
        intensity_adjustment = 1.0
        frequency_adjustment = 1.0

    # 最終的な強度と持続時間を計算
    final_intensity = min(
        base_pattern["intensity_base"] * emotion_multiplier * intensity_adjustment,
        1.0,
    )
    final_duration_ms = int(base_pattern["duration_base"] * emotion_multiplier * 1000)
    
    # Arduino形式のパターンを作成（より強く長い振動パターン）
    # 複数ステップで強い振動を継続
    vibration_pattern = {
        "steps": [
            {"intensity": 100, "duration": 2000},  # 100%強度で2秒
            {"intensity": 0, "duration": 200},      # 0.2秒休止
            {"intensity": 100, "duration": 2000},  # 100%強度で2秒
            {"intensity": 0, "duration": 200},      # 0.2秒休止
            {"intensity": 100, "duration": 2000},  # 100%強度で2秒
        ],
        "interval": 0,
        "repeat_count": max(3, int(base_pattern["frequency_base"] * emotion_multiplier * frequency_adjustment))  # 最低3回繰り返し
    }
    
    # 最終的な振動設定
    return {
        "vibration_enabled": True,
        "pattern": pattern_type,
        "intensity": final_intensity,
        "frequency": base_pattern["frequency_base"] * emotion_multiplier * frequency_adjustment,
        "duration": base_pattern["duration_base"] * emotion_multiplier,
        "dominant_emotion": dominant_emotion,
        "mixed_emotions": mixed_emotions,
        "description": base_pattern["description"],
        "emotion_level": emotion_value,
        "vibration_pattern": vibration_pattern
    }


# 振動制御関数の定義
def control_vibration(vibration_settings: dict) -> dict:
    """振動設定に基づいて実際の振動制御コマンドを生成します

    Args:
        vibration_settings: generate_vibration_patternから返される設定

    Returns:
        振動制御コマンドを含む辞書
    """
    if not vibration_settings.get("vibration_enabled", False):
        return {"command": "STOP", "message": "振動を停止します"}

    # パターンに応じたコマンドの生成
    pattern = vibration_settings["pattern"]
    # 強度を100%スケールに変換（test_arduino_max_vibration.pyと同じ形式）
    intensity = int(vibration_settings["intensity"] * 100)  # 0-100の範囲に変換
    frequency = vibration_settings["frequency"]
    duration = int(vibration_settings["duration"] * 1000)  # ミリ秒に変換

    command_map = {
        "pulse": f"PULSE:{intensity},{frequency},{duration}",
        "wave": f"WAVE:{intensity},{frequency},{duration}",
        "burst": f"BURST:{intensity},{frequency},{duration}",
        "fade": f"FADE:{intensity},{frequency},{duration}",
        "pulse_mixed": f"MIXED_PULSE:{intensity},{frequency},{duration}",
        "wave_mixed": f"MIXED_WAVE:{intensity},{frequency},{duration}",
        "burst_mixed": f"MIXED_BURST:{intensity},{frequency},{duration}",
        "fade_mixed": f"MIXED_FADE:{intensity},{frequency},{duration}",
    }

    command = command_map.get(pattern, f"DEFAULT:{intensity},{frequency},{duration}")

    return {
        "command": command,
        "message": f"{vibration_settings['description']}を実行します",
        "details": {
            "pattern": pattern,
            "intensity": intensity,
            "frequency": frequency,
            "duration": duration,
            "emotion": vibration_settings.get("dominant_emotion", "unknown"),
        },
    }


# FunctionToolで関数をラップ
add_emoji_tool = FunctionTool(add_emoji)
generate_vibration_tool = FunctionTool(generate_vibration_pattern)
control_vibration_tool = FunctionTool(control_vibration)

emoji_agent = Agent(
    name="emoji_agent",
    model="gemini-1.5-flash",
    description="感情に基づいて適切な絵文字を提案する専門エージェント",
    instruction=emoji_prompt,
    tools=[add_emoji_tool],
)

vibration_agent = Agent(
    name="vibration_agent",
    model="gemini-1.5-flash",
    description="感情に基づいて振動パターンを制御する専門エージェント",
    instruction=vibration_prompt,
    tools=[generate_vibration_tool, control_vibration_tool],
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
