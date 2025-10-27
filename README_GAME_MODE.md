# ゲームモード起動ガイド

## 概要

エージェントをゲームモードで起動できます。通常の触覚応答ではなく、ゲームに特化したインタラクションが可能です。

## 起動方法

### 1. 通常モード（デフォルト）

```bash
adk run agent
```

触覚入力に対して感情的に応答する通常モード。

### 2. 感情シンクロゲームモード

```bash
./start_emotion_game.sh
```

または

```bash
export GAME_MODE=emotion_game
adk run agent
```

**ゲーム内容**:
- 目標となる感情値（joy, fun, anger, sad）が提示される
- ユーザーが触り方を調整して目標の感情を引き出す
- Perfect/Good判定でクリア

**難易度**: easy, normal, hard（デフォルト: normal）

### 3. リズムゲームモード

```bash
./start_rhythm_game.sh
```

または

```bash
export GAME_MODE=rhythm_game
adk run agent
```

**ゲーム内容**:
- 振動でリズムパターンが提示される
- ユーザーが同じリズムでタッチする
- タイミング精度でPerfect/Good/Close判定

**難易度**: easy, normal, hard（デフォルト: normal）

## Leap Motionとの組み合わせ

Leap Motionブリッジと組み合わせて使用可能：

```bash
# 感情シンクロゲーム
python agent/leap_to_adk_bridge.py --url http://192.168.43.162:8001 | ./start_emotion_game.sh

# リズムゲーム
python agent/leap_to_adk_bridge.py --url http://192.168.43.162:8001 | ./start_rhythm_game.sh
```

## テスト方法

### 感情シンクロゲームのテスト

```bash
./tests/test_emotion_game.sh | ./start_emotion_game.sh
```

### リズムゲームのテスト

```bash
./tests/test_rhythm_game.sh | ./start_rhythm_game.sh
```

## 実装詳細

### ゲームモード切り替え

`agent/agent.py`が環境変数`GAME_MODE`を読み取り、対応するプロンプトファイルを使用：

- `GAME_MODE=normal` → `prompt/system_prompt`（デフォルト）
- `GAME_MODE=emotion_game` → `prompt/system_prompt_game_emotion`
- `GAME_MODE=rhythm_game` → `prompt/system_prompt_game_rhythm`

### 使用ツール

両ゲームモードで以下のMCPツールを使用：

- **感情シンクロゲーム**:
  - `start_emotion_sync_game`: ゲーム開始、目標感情生成
  - `check_emotion_match`: 現在の感情と目標の一致度チェック
  - `add_emoji`: 絵文字追加
  - `generate_vibration_pattern` + `control_vibration`: 振動フィードバック
  - `text_to_speech`: 音声合成

- **リズムゲーム**:
  - `start_rhythm_game`: ゲーム開始、リズムパターン生成
  - `check_rhythm`: タイミング判定
  - `add_emoji`: 絵文字追加
  - `generate_vibration_pattern` + `control_vibration`: 振動フィードバック
  - `text_to_speech`: 音声合成

### ゲームフロー

1. **初回入力時**: 自動的に`start_*_game`を呼び出してゲーム開始
2. **各入力時**: 判定とフィードバック
3. **クリア時**: Perfect/Good判定で祝福の振動と音声
4. **次の入力**: 新しいゲームが自動的に開始

## 注意事項

- ゲームモードでは通常の感情応答は行われません
- ゲーム専用のシステムプロンプトを使用します
- セッション中にモードを変更する場合は、エージェントを再起動してください
