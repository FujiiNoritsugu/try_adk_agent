# Vector Search Integration

## 概要

感情履歴ベクトル検索機能により、過去の触覚入力と感情応答を学習し、一貫性のあるパーソナライズされた応答を実現します。

## 機能

### 1. **感情履歴の記録**
- 触覚入力（部位、強度、ジェスチャー）
- 感情値（喜び、楽しさ、怒り、悲しみ）
- 生成された応答テキスト
- これらをベクトル化してGCP Vector Searchに保存

### 2. **類似状況の検索**
- 現在の入力に似た過去の状況を検索
- 過去の応答を参考に一貫性のある反応を生成
- コサイン類似度による高精度なマッチング

### 3. **パーソナライゼーション**
- セッションごとのインタラクション履歴
- ユーザーの好みの触り方を学習
- 時間経過による応答の変化

## アーキテクチャ

```
TouchInput → Embedder (768次元ベクトル化)
                ↓
         Vector Search (類似検索)
                ↓
         System Prompt + 過去の履歴
                ↓
         Gemini 2.5 Flash → 応答生成
                ↓
         Vector Search (新規保存)
```

## セットアップ

### 1. 依存関係のインストール

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. GCP認証設定

```bash
# サービスアカウントキーを設定
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# プロジェクトIDを設定
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

### 3. Vector Search Indexの作成

```bash
# セットアップスクリプトを実行
./setup_vectorsearch.sh
```

スクリプト実行後、出力された環境変数を `.env` ファイルに追加してください：

```bash
# .env に追加
GOOGLE_CLOUD_PROJECT=your-project-id
VECTOR_SEARCH_INDEX_ID=generated-index-id
VECTOR_SEARCH_ENDPOINT_ID=generated-endpoint-id
VECTOR_SEARCH_DEPLOYED_INDEX_ID=emotion_history_deployed
VECTOR_SEARCH_INDEX_REGION=us-central1
```

## 使用方法

### 基本的な実行

Vector Search機能を有効にした状態でエージェントを実行：

```bash
source venv/bin/activate
python agent/leap_to_adk_bridge.py --url http://192.168.43.162:8001 | adk run agent
```

または、モックモードでテスト：

```bash
python agent/leap_to_adk_bridge.py --mock | adk run agent
```

### ワークフロー

1. **入力受信**: Leap Motionから触覚入力を受け取る
2. **類似検索**: `search_similar_interactions` で過去の類似状況を検索
3. **応答生成**: 過去の履歴を参考にしながら応答を生成
4. **履歴保存**: `save_interaction` で今回の応答を保存

### 利用可能なツール

#### `search_similar_interactions`
類似した過去のインタラクションを検索

**パラメータ:**
- `touched_area`: 触られた体の部位
- `data`: 触覚の強度（0-1）
- `gesture_type`: ジェスチャータイプ
- `joy`, `fun`, `anger`, `sad`: 感情値（0-5）
- `top_k`: 取得する結果数（デフォルト: 5）

**レスポンス例:**
```json
{
  "found": true,
  "count": 2,
  "similar_interactions": [
    {
      "similarity": 0.85,
      "timestamp": "2025-10-09T05:00:00Z",
      "input": {
        "touched_area": "頭",
        "data": 0.6,
        "gesture_type": "tap"
      },
      "emotion": {
        "joy": 4.0,
        "fun": 3.0,
        "anger": 0.5,
        "sad": 0.3
      },
      "response": "優しく頭を触ってくれて嬉しいな"
    }
  ]
}
```

#### `save_interaction`
新しいインタラクションを保存

**パラメータ:**
- `touched_area`, `data`, `gesture_type`, `hand_velocity`: 入力データ
- `joy`, `fun`, `anger`, `sad`: 感情値
- `response_text`: 生成した応答テキスト
- `session_id`: セッションID（オプション）

#### `get_interaction_stats`
統計情報を取得

## モックモード

GCP設定なしでテスト可能なモックモードを実装済み：

- Vector Search未設定時は自動的にモックモードに切り替わります
- モックデータで動作確認が可能
- 開発・デバッグに便利

## ファイル構成

```
├── src/vectorsearch/
│   ├── embedder.py              # Embedding生成
│   ├── vector_search_client.py  # Vector Search操作
│   └── __init__.py
├── mcp_servers/
│   └── vectorsearch_server.py   # MCPサーバー
├── docs/
│   └── VECTOR_SEARCH_DESIGN.md  # 詳細設計書
├── setup_vectorsearch.sh        # GCPセットアップスクリプト
└── README_VECTOR_SEARCH.md      # このファイル
```

## トラブルシューティング

### Vector Search接続エラー

```
Vector Search not configured. Using mock mode.
```

**解決方法:**
1. `.env` ファイルに必要な環境変数が設定されているか確認
2. GCP認証が正しく設定されているか確認
3. Vector Search Indexが作成されているか確認

### Embedding生成エラー

```
Failed to generate embedding
```

**解決方法:**
1. Vertex AI APIが有効になっているか確認
2. サービスアカウントに必要な権限があるか確認
3. プロジェクトIDが正しいか確認

## コスト見積もり

### Vertex AI Vector Search
- Index維持費: ~$50/月 (10GBまで)
- Query費: ~$0.0001/クエリ

### Text Embedding API
- ~$0.0001/1000文字

### 想定コスト
月間10,000インタラクション: **約$5-10/月**

## 今後の拡張案

1. **セッション管理**: ユーザーごとの履歴分離
2. **感情遷移分析**: 時系列での感情変化の学習
3. **統計ダッシュボード**: インタラクション分析UI
4. **自動クリーンアップ**: 古い履歴の自動削除
5. **マルチモーダル**: 音声・振動パターンの統合学習

## 関連ドキュメント

- [詳細設計書](docs/VECTOR_SEARCH_DESIGN.md)
- [GCP Vector Search ドキュメント](https://cloud.google.com/vertex-ai/docs/vector-search/overview)
- [Text Embedding API](https://cloud.google.com/vertex-ai/docs/generative-ai/embeddings/get-text-embeddings)

## ライセンス

このプロジェクトの一部として同じライセンスが適用されます。
