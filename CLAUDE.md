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

# Leap Motion統合のテスト（etc/ディレクトリ内）
python etc/leap_motion_demo.py             # Leap Motion MCPサーバーのデモ
```

### Leap Motionブリッジの実行（リアルタイムジェスチャー入力用）
```bash
python agent/leap_to_adk_bridge.py | adk run .
# モックモード:
python agent/leap_to_adk_bridge.py --mock | adk run .
```

### Vector Searchのセットアップ
```bash
./etc/setup_vectorsearch.sh
```

### ログの確認
```bash
tail -F /tmp/agents_log/agent.latest.log
```

## ディレクトリ構成

```
.
├── agent/                   # メインエージェント実装
│   ├── agent.py            # ADKエージェントのエントリーポイント
│   └── leap_to_adk_bridge.py  # Leap MotionからADKへのブリッジ
│
├── mcp_servers/            # MCPサーバー群（stdioプロトコル）
│   ├── emoji_server.py     # 感情→絵文字変換
│   ├── vibration_server.py # 触覚フィードバック制御
│   ├── voicevox_server.py  # 音声合成（VOICEVOX）
│   └── vectorsearch_server.py  # インタラクション検索・保存
│
├── server_leapmotion/      # Leap Motion統合
│   ├── server.py           # Leap Motion MCPサーバー
│   └── server_http.py      # HTTP API版（代替実装）
│
├── src/                    # 共有ライブラリ
│   ├── devices/            # ハードウェア制御
│   │   ├── arduino_controller.py   # Arduino WiFi通信
│   │   └── vibration_patterns.py   # 振動パターン定義
│   └── vectorsearch/       # GCP Vector Search統合
│       ├── vector_search_client.py # Vector Search APIクライアント
│       └── embedder.py             # テキスト埋め込み生成
│
├── prompt/                 # システムプロンプト
│   └── system_prompt       # エージェントの振る舞い定義
│
├── arduino/                # Arduinoファームウェア
│   └── haptic_feedback_controller/  # Arduino Uno R4 WiFi用
│
├── tests/                  # テストスクリプト
├── docs/                   # ドキュメント
├── etc/                    # ユーティリティスクリプト
│   ├── leap_motion_demo.py     # Leap Motionデモツール
│   ├── play_audio.sh           # WSL2音声再生スクリプト
│   └── setup_vectorsearch.sh   # GCP Vector Searchセットアップ
│
├── .env                    # 環境変数（GCP設定等）
└── requirements.txt        # Python依存関係
```

## アーキテクチャ

### コアコンポーネント

1. **Agent System** (`agent/agent.py`)
   - Google ADKフレームワークを使用したメインエージェント
   - `TouchInput`スキーマで入力を受け取る（joy, fun, anger, sadの感情パラメータ）
   - 5つのMCPサーバーと統合（MCPToolset経由）:
     - **Vector Search**: 過去のインタラクション検索・保存
     - **Emoji**: 感情から絵文字生成
     - **Vibration**: 振動パターン制御
     - **VOICEVOX**: 日本語音声合成
     - **Leap Motion**: ジェスチャー検出とTouchInput変換

2. **MCP Servers** (`mcp_servers/`)
   - stdioプロトコルで別プロセスとして実行
   - 各サーバーはツール（関数）を提供
   - エージェントから必要に応じて呼び出される
   - Leap MotionサーバーのみMCPサーバーとHTTPサーバーの2実装あり

3. **Hardware Integration**
   - **Arduino Uno R4 WiFi**: 振動制御（Pin 9 PWM）、WiFi HTTP API経由で通信
   - **Leap Motion 2**: 手のジェスチャー入力デバイス
   - **VOICEVOX**: ローカルで動作する日本語音声合成エンジン

4. **Vector Search Integration** (`src/vectorsearch/`)
   - GCP Vertex AI Vector Searchを使用
   - 過去のインタラクションを埋め込みベクトル化して保存
   - 類似状況の検索により一貫性のある応答を実現
   - text-embedding-004モデルで768次元ベクトル生成

### データフロー

```
入力（Touch/Leap Motion）
  ↓
Agent（prompt/system_promptに従って処理）
  ↓
感情処理ワークフロー:
  1. Vector Search: 過去の類似状況を検索
  2. 感情値決定: joy, fun, anger, sad（各0-5）
  3. Emoji生成: 感情に合った絵文字選択
  4. 振動制御: Arduinoに振動パターン送信
  5. 音声合成: VOICEVOXで応答を音声化
  6. インタラクション保存: 今回のやり取りを保存
  ↓
出力（emotion + message）
```

### エージェントのワークフロー（prompt/system_promptで定義）

1. **過去の類似状況を検索**: `search_similar_interactions` - 似た触覚入力での過去応答を参照
2. **触覚を感じて感情的に反応**: 触覚強度（0=感じない、0.5=心地良い、1.0=痛い）に応じて反応
3. **感情値を決定**: joy, fun, anger, sad（各0-5）を過去データ参考に決定
4. **絵文字を追加**: `add_emoji` - 感情値に合った絵文字を選択
5. **振動フィードバック**: `send_arduino_vibration` - 触覚フィードバックを送信
6. **音声合成**: `text_to_speech` - 応答メッセージを音声化
7. **インタラクション保存**: `save_interaction` - 今回のやり取りをVector Searchに保存

## 入出力フォーマット

### 入力スキーマ（TouchInput）
```json
{
  "data": 0.5,              // 触覚強度（0-1）
  "touched_area": "頭",     // 触られた体の部位
  "gesture_type": "tap",    // オプション: Leap Motionジェスチャー
  "hand_position": {...},   // オプション: 3D座標（x, y, z）
  "hand_velocity": 150.5,   // オプション: 手の速度
  "leap_confidence": 0.9    // オプション: 検出信頼度（0-1）
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
- `prompt/system_prompt`: システム動作定義（7ステップワークフローと感情ルール）
- `requirements.txt`: Python依存関係
- `.env`: 環境変数（GCPプロジェクトID、Vector Search設定、Arduino URL等）
- `etc/play_audio.sh`: WSL2/Linux用音声再生スクリプト（PulseAudio設定）

## 環境固有の設定

- **Pythonバーチャル環境**: `venv/`
- **WSL2環境**: PulseAudio経由で音声再生（`etc/play_audio.sh`で設定）
- **Arduino接続**: WiFi HTTP API経由（環境変数`ARDUINO_URL`で指定）
- **MCPサーバー**: stdioパイプ経由で通信（ADKフレームワークが自動管理）
- **Vector Search**: GCP Vertex AI（`.env`で認証情報とIndex/Endpoint ID設定が必要）
- **VOICEVOX**: ローカルホスト（通常 http://localhost:50021）で実行

## ドキュメント

詳細なドキュメントは`docs/`ディレクトリを参照:
- `docs/README_MCP.md`: MCPサーバーの詳細
- `docs/LEAP_MOTION_GUIDE_JP.md`: Leap Motion統合ガイド（日本語）
- `docs/README_VECTOR_SEARCH.md`: Vector Search設定ガイド
- `docs/README_VOICEVOX.md`: VOICEVOX統合ガイド
- `docs/README_haptic_integration.md`: Arduino触覚統合ガイド
- `docs/VECTOR_SEARCH_DESIGN.md`: Vector Search設計ドキュメント
- `docs/エージェントへの入力例.txt`: サンプル入力データ

## 開発時の注意点

### テストの実行場所
- すべてのテストファイルは`tests/`ディレクトリに配置
- Leap Motionデモのみ`etc/`に配置（ユーティリティツール扱い）

### Leap Motion統合の2つの方法
1. **MCPツールとして**: エージェントが直接`server_leapmotion/server.py`を呼び出し
2. **パイプ入力として**: `agent/leap_to_adk_bridge.py`でHTTPサーバーからポーリングして標準入力に流す

### 音声再生（WSL2環境）
- `etc/play_audio.sh`を使用してPulseAudio経由で再生
- スクリプトは再生後に自動的にWAVファイルを削除

### Vector Searchの初回セットアップ
1. `etc/setup_vectorsearch.sh`を実行してGCPリソース作成
2. 出力された環境変数を`.env`に追加
3. GCP認証情報（サービスアカウントキー等）を設定
