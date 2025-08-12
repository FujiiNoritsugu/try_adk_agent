import json
from typing import Dict, Any
import random


class EmotionalChatbot:
    def __init__(self, gender: str = "女性"):
        self.gender = gender
        self.emotion = {
            "joy": 2.5,
            "fun": 2.5,
            "anger": 0,
            "sad": 0
        }
        
    def process_input(self, input_data: str) -> str:
        try:
            data = json.loads(input_data)
            if "gender" in data:
                self.gender = data["gender"]
            
            if "data" in data and "touched_area" in data:
                self.update_emotion(data["data"], data["touched_area"])
            
            response = self.generate_response(data.get("touched_area", ""))
            return self.format_response(response)
            
        except json.JSONDecodeError:
            return self.format_response("正しいJSON形式で入力してください。")
    
    def update_emotion(self, touch_intensity: float, touched_area: str):
        touch_intensity = max(0, min(1, touch_intensity))
        
        if 0.3 <= touch_intensity <= 0.7:
            pleasure_factor = 1 - abs(touch_intensity - 0.5) * 2
            self.emotion["joy"] = min(5, self.emotion["joy"] + pleasure_factor * 0.5)
            self.emotion["fun"] = min(5, self.emotion["fun"] + pleasure_factor * 0.3)
            self.emotion["anger"] = max(0, self.emotion["anger"] - pleasure_factor * 0.2)
            self.emotion["sad"] = max(0, self.emotion["sad"] - pleasure_factor * 0.2)
        
        elif touch_intensity < 0.3:
            self.emotion["fun"] = max(0, self.emotion["fun"] - 0.1)
            self.emotion["sad"] = min(5, self.emotion["sad"] + 0.1)
        
        else:
            pain_factor = (touch_intensity - 0.7) / 0.3
            self.emotion["anger"] = min(5, self.emotion["anger"] + pain_factor * 0.5)
            self.emotion["joy"] = max(0, self.emotion["joy"] - pain_factor * 0.3)
            self.emotion["fun"] = max(0, self.emotion["fun"] - pain_factor * 0.3)
            self.emotion["sad"] = min(5, self.emotion["sad"] + pain_factor * 0.2)
    
    def generate_response(self, touched_area: str) -> str:
        emotion_state = self.get_dominant_emotion()
        
        if not touched_area:
            return self.get_idle_message(emotion_state)
        
        responses = {
            "joy": [
                f"あっ、{touched_area}に触れられると嬉しいです！",
                f"{touched_area}の感触、とても心地良いです♪",
                "もっと触れてもらえますか？"
            ],
            "fun": [
                f"わぁ！{touched_area}がくすぐったいです！",
                "ふふっ、なんだか楽しくなってきました！",
                f"{touched_area}に触れられると、不思議な感じがします〜"
            ],
            "anger": [
                f"痛い！{touched_area}をそんなに強く触らないでください！",
                "もう少し優しくしてもらえませんか？",
                f"{touched_area}が痛いです..."
            ],
            "sad": [
                f"{touched_area}に触れられても、今は何も感じません...",
                "少し寂しい気持ちです...",
                "もう少し優しく触れてもらえますか？"
            ]
        }
        
        return random.choice(responses.get(emotion_state, ["..."]))
    
    def get_idle_message(self, emotion_state: str) -> str:
        idle_messages = {
            "joy": ["今日はとても幸せな気分です！", "あなたと話せて嬉しいです♪"],
            "fun": ["何か楽しいことしましょう！", "わくわくしています！"],
            "anger": ["少しイライラしています...", "機嫌が悪いです。"],
            "sad": ["なんだか寂しいです...", "元気が出ません..."]
        }
        return random.choice(idle_messages.get(emotion_state, ["こんにちは。"]))
    
    def get_dominant_emotion(self) -> str:
        return max(self.emotion.items(), key=lambda x: x[1])[0]
    
    def format_response(self, message: str) -> str:
        response = {
            "emotion": self.emotion,
            "message": message
        }
        return json.dumps(response, ensure_ascii=False, indent=2)


def main():
    print("感情と触覚を持つチャットボットを起動しました。")
    print("入力形式: {\"data\": 0.5, \"touched_area\": \"頭\", \"gender\": \"女性\"}")
    print("終了するには 'quit' と入力してください。\n")
    
    bot = EmotionalChatbot()
    
    while True:
        user_input = input("入力: ")
        if user_input.lower() == 'quit':
            break
        
        response = bot.process_input(user_input)
        print(f"応答:\n{response}\n")


if __name__ == "__main__":
    main()