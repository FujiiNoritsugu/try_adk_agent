# Leap Motion HTTPサーバー統合ガイド

## 概要
Leap Motion HTTPサーバーを使用して、別PCからジェスチャー入力を受け取る方法です。

## セットアップ手順

### 1. Leap Motion HTTPサーバーの起動（別PC）

```bash
# 別のミニPCで実行
cd /path/to/project/server_leapmotion
python server_http.py --host 0.0.0.0 --port 8001
```

### 2. 環境変数の設定（エージェント側PC）

```bash
# Leap Motion HTTPサーバーのURLを設定
export LEAP_MOTION_SERVER_URL=http://[別PCのIPアドレス]:8001
```

### 3. エージェントの変更

#### 方法1: agent_with_leap_http.pyを直接使用

`agent_mcp/__init__.py`を編集：
```python
# from .agent import agent  # コメントアウト
from .agent_with_leap_http import agent  # 追加
```

#### 方法2: 環境変数でモジュールを切り替え

```bash
export ADK_AGENT_MODULE=agent_with_leap_http
```

### 4. エージェントの実行

```bash
source venv/bin/activate
adk run .
```

## 動作確認

1. Leap Motion HTTPサーバーが正常に起動していることを確認：
```bash
curl http://[別PCのIP]:8001/health
```

2. 手の検出テスト：
```bash
python test_leap_http_updated.py http://[別PCのIP]:8001
```

3. エージェントのログでLeap Motion入力が処理されていることを確認

## トラブルシューティング

### 手が検出されない場合
- Leap Motionデバイスが接続されていることを確認
- Leap Motion Control Panelでデバイスが認識されていることを確認
- `server_http.py`のログでトラッキングイベントが発生していることを確認

### 接続できない場合
- ファイアウォール設定を確認（ポート8001を開放）
- 両PCが同じネットワーク上にあることを確認
- pingでネットワーク接続を確認

## 設定可能なパラメータ

環境変数で以下を設定可能：
- `LEAP_MOTION_SERVER_URL`: HTTPサーバーのURL（デフォルト: http://localhost:8001）

agent_with_leap_http.py内で調整可能：
- `leap_poll_interval`: ポーリング間隔（デフォルト: 0.1秒）
- `leap_min_process_interval`: 最小処理間隔（デフォルト: 0.5秒）