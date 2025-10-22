# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

Google ADK Agentフレームワークを使用した、感情と触覚フィードバックを持つチャットボットシステム。
触覚入力（手動またはLeap Motion経由）を処理し、感情応答、振動フィードバック、音声合成を生成します。

## 主要コマンド

### エージェントの起動
```bash
source venv/bin/activate
adk run .
```

### テストの実行
```bash
# 各コンポーネントのテスト（tests/ディレクトリ内）
python tests/test_haptic_integration.py    # Arduino触覚フィードバックのテスト
python tests/test_voicevox.py              # 音声合成のテスト
python tests/test_emotion_debug.py         # 感情システムのテスト
python tests/test_embedding_check.py       # ベクトル検索の埋め込みテスト
python leap_motion_demo.py                 # Leap Motion統合のテスト
```

### Leap Motionブリッジの実行（リアルタイムジェスチャー入力用）
```bash
python leap_motion_bridge.py --adk-url http://localhost:8080
# デバイスなしのモックモード:
python leap_motion_bridge.py --mock
```

### Vector Searchのセットアップ
```bash
./setup_vectorsearch.sh
```

### ログの確認
```bash
tail -F /tmp/agents_log/agent.latest.log
```

## アーキテクチャ

### ディレクトリ構成

- `agent/`: メインエージェントの実装
  - `agent.py`: ADKエージェントのエントリーポイント（5つのMCPサーバーと連携）
  - `leap_to_adk_bridge.py`: Leap MotionからADKへのブリッジ

- `mcp_servers/`: MCPサーバー群（stdioプロトコル経由で通信）
  - `emoji_server.py`: 感情から絵文字への変換
  - `vibration_server.py`: 触覚フィードバック制御
  - `voicevox_server.py`: 音声合成（VOICEVOX）
  - `vectorsearch_server.py`: 過去のインタラクション検索・保存
  - (Note: Leap Motionサーバーは `server_leapmotion/server.py` にあります)

- `src/`: 共有ライブラリとユーティリティ
  - `devices/`: ハードウェア制御
    - `arduino_controller.py`: Arduino通信（WiFi HTTP API経由）
    - `vibration_patterns.py`: 振動パターン定義
  - `vectorsearch/`: GCP Vector Search統合
    - `vector_search_client.py`: Vector Search APIクライアント
    - `embedder.py`: テキスト埋め込み生成

- `server_leapmotion/`: Leap Motion統合
  - `server.py`: Leap Motion MCPサーバー
  - `server_http.py`: HTTP API版（代替実装）

- `prompt/`: システムプロンプト定義
  - `system_prompt`: エージェントの振る舞いとワークフロー定義

- `tests/`: テストスクリプト
- `docs/`: ドキュメント（README_MCP.md、LEAP_MOTION_GUIDE_JP.md等）
- `arduino/`: Arduinoファームウェア

### コアコンポーネント

1. **Agent System** (`agent/agent.py`)
   - Google ADKフレームワークを使用したメインエージェント
   - TouchInput（joy, fun, anger, sadの感情パラメータ付き）を処理
   - 5つのMCPサーバーとMCPToolset経由で統合:
     - Vector Search（過去のインタラクション検索）
     - Emoji（絵文字生成）
     - Vibration（振動制御）
     - VOICEVOX（音声合成）
     - Leap Motion（ジェスチャー検出）

2. **MCP Servers** (stdioプロトコルで別プロセスとして実行)
   - 各サーバーはToolとして機能を提供
   - エージェントから必要に応じて呼び出される

3. **Hardware Integration**
   - Arduino Uno R4 WiFi: 振動制御（Pin 9 PWM）、WiFi HTTP API経由で通信
   - Leap Motion 2: ジェスチャー入力
   - VOICEVOX: 日本語音声合成

4. **Vector Search Integration**
   - GCP Vertex AI Vector Searchを使用
   - 過去のインタラクションを埋め込みベクトル化して保存
   - 類似状況の検索により一貫性のある応答を実現

### データフロー

```
入力（Touch/Leap Motion）→ Agent → 感情処理 →
  ├→ Vector Search（類似状況検索・保存）
  ├→ 絵文字生成
  ├→ 振動パターン（Arduino経由WiFi）
  └→ 音声合成（VOICEVOX）
```

### エージェントのワークフロー（prompt/system_promptで定義）

1. **過去の類似状況を検索**: `search_similar_interactions` ツールで類似インタラクションを取得
2. **触覚を感じて感情的に反応**: 触覚強度と過去データを基に感情値を決定
3. **感情値を決定**: joy, fun, anger, sad（各0-5）
4. **絵文字を追加**: `add_emoji` ツールで感情に合った絵文字を選択
5. **振動フィードバック**: `send_arduino_vibration` で触覚フィードバックを送信
6. **音声合成**: `text_to_speech` で応答を音声化
7. **インタラクション保存**: `save_interaction` で今回のやり取りを保存

## 入出力フォーマット

### 入力スキーマ（TouchInput）
```json
{
  "data": 0.5,              // 触覚強度（0-1）
  "touched_area": "頭",     // 触られた体の部位
  "gesture_type": "tap",    // オプション: Leap Motionジェスチャー
  "hand_position": {...},   // オプション: 3D座標
  "hand_velocity": 150.5,   // オプション: 手の速度
  "leap_confidence": 0.9    // オプション: 検出信頼度
}
```

### 出力スキーマ
```json
{
  "emotion": {
    "joy": 3.2,
    "fun": 2.8,
    "anger": 0.5,
    "sad": 0.3
  },
  "message": "応答メッセージ"
}
```

## 重要なファイル

- `agent/agent.py`: メインエージェント定義（5つのMCPツールセット統合）
- `prompt/system_prompt`: システム動作定義（ワークフローと感情ルール）
- `requirements.txt`: Python依存関係
- `.env`: 環境変数（GCPプロジェクトID、Vector Search設定等）
- `play_audio.sh`: WSL2/Linux用音声再生スクリプト

## 環境固有の設定

- Pythonバーチャル環境: `venv/`
- WSL2環境: PulseAudio経由で音声再生（`play_audio.sh`で設定）
- Arduino接続: WiFi HTTP API経由（環境変数で設定）
- MCPサーバー: stdioパイプ経由で通信
- Vector Search: GCP Vertex AI（`.env`で認証情報設定が必要）

## ドキュメント

詳細なドキュメントは`docs/`ディレクトリを参照:
- `docs/README_MCP.md`: MCPサーバーの詳細
- `docs/LEAP_MOTION_GUIDE_JP.md`: Leap Motion統合ガイド
- `docs/README_VECTOR_SEARCH.md`: Vector Search設定ガイド
- `docs/README_VOICEVOX.md`: VOICEVOX統合ガイド
- `docs/README_haptic_integration.md`: Arduino触覚統合ガイド
