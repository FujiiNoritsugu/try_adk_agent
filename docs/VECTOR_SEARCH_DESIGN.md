# Vector Search Integration Design

## Overview
感情履歴ベクトル検索による応答パーソナライゼーション機能の設計書

## Architecture

### Data Flow
```
TouchInput → Embedding → Vector Search (類似履歴検索)
                ↓
         System Prompt + 履歴
                ↓
        LLM (Gemini) → 応答生成
                ↓
         Vector Search (保存)
```

### Components

1. **Embedding Generator** (src/vectorsearch/embedder.py)
   - TouchInputとEmotionを統合テキストに変換
   - Vertex AI Text Embedding APIでベクトル化
   - Model: `textembedding-gecko@003` (768次元)

2. **Vector Search MCP Server** (mcp_servers/vectorsearch_server.py)
   - ツール:
     - `search_similar_interactions`: 類似履歴検索
     - `save_interaction`: 新しい応答を保存
     - `get_interaction_stats`: 統計情報取得

3. **GCP Vector Search Index**
   - Vertex AI Vector Search
   - Index Type: Streaming Index (リアルタイム更新)
   - Distance Metric: Cosine Similarity

## Data Schema

### Interaction Record
```json
{
  "id": "interaction_20251009_050000_abc123",
  "timestamp": "2025-10-09T05:00:00Z",
  "session_id": "session_xyz",
  "input": {
    "data": 0.5,
    "touched_area": "頭",
    "gesture_type": "tap",
    "hand_position": {"x": 0, "y": 100, "z": 50},
    "hand_velocity": 150.5,
    "leap_confidence": 0.9
  },
  "emotion": {
    "joy": 3.2,
    "fun": 2.8,
    "anger": 0.5,
    "sad": 0.3
  },
  "response_text": "優しく頭を触ってくれて嬉しいな",
  "vibration_pattern": "pulse",
  "embedding": [0.123, -0.456, ...],  // 768次元
  "metadata": {
    "dominant_emotion": "joy",
    "intensity_level": "medium"
  }
}
```

### Embedding Text Format
```
触覚入力: 部位={touched_area}, 強度={data}, ジェスチャー={gesture_type}, 速度={hand_velocity}
感情: 喜び={joy}, 楽しさ={fun}, 怒り={anger}, 悲しみ={sad}
応答: {response_text}
```

## Vector Search Configuration

### Index Parameters
- **Dimensions**: 768
- **Distance Measure**: COSINE_DISTANCE
- **Algorithm**: Tree-AH (Approximate Nearest Neighbor)
- **Shard Size**: SHARD_SIZE_SMALL (10GB未満のデータ向け)

### Search Parameters
- **Top K**: 5 (最も類似した5件を取得)
- **Threshold**: 0.7 (類似度70%以上)

## Integration with Agent

### System Prompt Enhancement
```
## 過去の類似した状況での応答履歴:

1. [3分前] 頭を軽くタップ (強度: 0.6, joy: 4.0)
   応答: 「ぽんぽんって優しいね、嬉しい」

2. [10分前] 頭を撫でる (強度: 0.4, joy: 3.5)
   応答: 「気持ちいいなぁ...もっと撫でて」

上記の過去の応答を参考に、一貫性のある反応をしてください。
```

## Environment Variables

```bash
# .env に追加
GOOGLE_CLOUD_PROJECT=your-project-id
VECTOR_SEARCH_INDEX_ID=emotion_history_index
VECTOR_SEARCH_ENDPOINT_ID=emotion_history_endpoint
VECTOR_SEARCH_INDEX_REGION=us-central1
```

## Implementation Plan

### Phase 1: Basic Setup
1. GCP Vector Search Indexの作成
2. Embedding Generator実装
3. Vector Search MCP Server実装

### Phase 2: Integration
4. Agentへの統合
5. System Promptの更新
6. テスト実行

### Phase 3: Enhancement
7. セッション管理機能
8. 統計情報の可視化
9. パフォーマンス最適化

## Costs Estimation

### Vertex AI Vector Search
- Index維持費: ~$50/月 (10GBまで)
- Query費: ~$0.0001/クエリ

### Text Embedding API
- ~$0.0001/1000文字

### Total (想定)
月間10,000インタラクション: ~$5-10/月

## Testing Strategy

### Unit Tests
- Embedding生成のテスト
- Vector Search操作のテスト

### Integration Tests
- End-to-endフローのテスト
- 類似度検証

### Manual Tests
- 実際のLeap Motion入力でのテスト
- 応答の一貫性確認
