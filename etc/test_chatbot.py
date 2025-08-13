import json
from chatbot import EmotionalChatbot


def test_basic_functionality():
    print("=== 基本機能テスト ===")
    bot = EmotionalChatbot("女性")
    
    test_cases = [
        {"data": 0.5, "touched_area": "頭", "gender": "女性"},
        {"data": 0.1, "touched_area": "肩", "gender": "女性"},
        {"data": 0.9, "touched_area": "腕", "gender": "女性"},
        {"data": 0.3, "touched_area": "手", "gender": "男性"},
        {"data": 0.7, "touched_area": "背中", "gender": "男性"},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nテストケース {i}: {test_case}")
        input_json = json.dumps(test_case, ensure_ascii=False)
        response = bot.process_input(input_json)
        print(f"応答:\n{response}")


def test_emotion_transitions():
    print("\n=== 感情遷移テスト ===")
    bot = EmotionalChatbot("女性")
    
    print("\n初期状態:")
    response = bot.process_input('{}')
    print(response)
    
    print("\n優しい触れ方 (data=0.5) を3回:")
    for i in range(3):
        response = bot.process_input('{"data": 0.5, "touched_area": "頭"}')
        emotion = json.loads(response)["emotion"]
        print(f"  {i+1}回目 - joy: {emotion['joy']:.1f}, fun: {emotion['fun']:.1f}, anger: {emotion['anger']:.1f}, sad: {emotion['sad']:.1f}")
    
    print("\n強い触れ方 (data=0.95) を3回:")
    for i in range(3):
        response = bot.process_input('{"data": 0.95, "touched_area": "腕"}')
        emotion = json.loads(response)["emotion"]
        print(f"  {i+1}回目 - joy: {emotion['joy']:.1f}, fun: {emotion['fun']:.1f}, anger: {emotion['anger']:.1f}, sad: {emotion['sad']:.1f}")


def test_invalid_inputs():
    print("\n=== 不正な入力のテスト ===")
    bot = EmotionalChatbot()
    
    invalid_inputs = [
        "これはJSONではありません",
        '{"data": "文字列"}',
        '{"invalid_key": 123}',
        '{}',
    ]
    
    for invalid_input in invalid_inputs:
        print(f"\n入力: {invalid_input}")
        response = bot.process_input(invalid_input)
        print(f"応答: {response}")


def interactive_demo():
    print("\n=== インタラクティブデモ ===")
    print("様々な強さで触れてみましょう:")
    
    bot = EmotionalChatbot("女性")
    demo_touches = [
        {"description": "そっと触れる", "data": 0.2, "touched_area": "頬"},
        {"description": "優しく撫でる", "data": 0.5, "touched_area": "頭"},
        {"description": "少し強めに触れる", "data": 0.8, "touched_area": "肩"},
        {"description": "もう一度優しく", "data": 0.4, "touched_area": "手"},
    ]
    
    for touch in demo_touches:
        print(f"\n{touch['description']} (強さ: {touch['data']})")
        input_data = {"data": touch["data"], "touched_area": touch["touched_area"]}
        response = bot.process_input(json.dumps(input_data, ensure_ascii=False))
        result = json.loads(response)
        print(f"感情状態: joy={result['emotion']['joy']:.1f}, fun={result['emotion']['fun']:.1f}, anger={result['emotion']['anger']:.1f}, sad={result['emotion']['sad']:.1f}")
        print(f"応答: {result['message']}")


if __name__ == "__main__":
    test_basic_functionality()
    test_emotion_transitions()
    test_invalid_inputs()
    interactive_demo()