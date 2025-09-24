# Leap Motion HTTP MCP Server

Leap Motionセンサーデータを外部からHTTP経由でアクセス可能にするサーバーです。

## 機能

- Leap Motionからリアルタイムでハンドトラッキングデータを取得
- ジェスチャー認識（swipe, circle, tap, grab, pinch）
- ADKエージェント用のタッチ入力フォーマットへの変換
- RESTful APIエンドポイント

## インストール

```bash
# 必要なパッケージをインストール
pip install fastapi uvicorn

# Leap Motion SDKもインストール（オプション）
pip install leapmotion
```

## 使用方法

### サーバー起動

```bash
# デフォルト設定で起動（ポート8001）
python server_http.py

# カスタム設定で起動
python server_http.py --host 0.0.0.0 --port 8001

# 開発モード（自動リロード有効）
python server_http.py --reload

# スクリプトを使用して起動
./run_http_server.sh
```

## APIエンドポイント

### GET /
サービス情報とエンドポイント一覧を取得

### GET /health
ヘルスチェック - Leap Motionの接続状態を確認

### GET /leap-data
現在のLeap Motionセンサーデータを取得
- ハンドポジション（x, y, z）
- 手の速度
- ジェスチャータイプ
- パームの向き
- 伸ばしている指の本数

**レスポンス例:**
```json
{
  "hand_position": {"x": 100.5, "y": 200.3, "z": 50.2},
  "hand_velocity": 150.5,
  "gesture_type": "tap",
  "confidence": 1.0,
  "palm_normal": {"x": 0.1, "y": 0.9, "z": 0.1},
  "fingers_extended": 2
}
```

### GET /touch-input
Leap MotionデータをADK用タッチ入力フォーマットに変換して取得

**レスポンス例:**
```json
{
  "data": 0.7,
  "touched_area": "頭",
  "gesture_type": "tap",
  "raw_leap_data": {...}
}
```

### POST /gesture-mapping
ジェスチャーマッピングをカスタマイズ

**リクエストボディ:**
```json
{
  "gesture": "tap",
  "intensity": 0.8,
  "area": "胸"
}
```

### GET /gesture-mappings
現在のジェスチャーマッピング設定を取得

## テスト

```bash
# ヘルスチェック
curl http://localhost:8001/health

# Leap Motionデータ取得
curl http://localhost:8001/leap-data

# タッチ入力フォーマット取得
curl http://localhost:8001/touch-input

# ジェスチャーマッピング更新
curl -X POST http://localhost:8001/gesture-mapping \
  -H "Content-Type: application/json" \
  -d '{"gesture": "tap", "intensity": 0.9, "area": "頭"}'
```

## ポート設定

デフォルトポート: **8001**

変更する場合:
```bash
python server_http.py --port 8080
```

## 注意事項

- Leap Motion SDKがインストールされていない場合、モックデータが返されます
- 外部からアクセス可能にするため、ファイアウォール設定の確認が必要な場合があります
- セキュリティを考慮する場合は、適切な認証機構を追加することを推奨します