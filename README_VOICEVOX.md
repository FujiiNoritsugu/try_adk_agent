# VOICEVOX音声出力機能セットアップガイド

## 必要なソフトウェア

### 1. VOICEVOX本体のインストール

VOICEVOXは無料の音声合成ソフトウェアです。以下の手順でインストールしてください：

1. [VOICEVOX公式サイト](https://voicevox.hiroshiba.jp/)からダウンロード
2. お使いのOSに合わせてインストール：
   - **Windows**: インストーラー版またはZIP版
   - **Mac**: DMGファイル
   - **Linux**: AppImage版

### 2. VOICEVOXの起動

1. VOICEVOXを起動
2. 初回起動時は利用規約に同意
3. VOICEVOXがポート50021で起動していることを確認

## Pythonパッケージのインストール

```bash
pip install pygame requests
```

## 動作確認

### 1. VOICEVOXが正しく起動しているか確認

```bash
curl http://localhost:50021/speakers
```

スピーカーリストのJSONが返ってくれば正常に動作しています。

### 2. 音声合成テスト

```python
import requests
import pygame
from io import BytesIO

# 音声合成クエリの作成
response = requests.post(
    "http://localhost:50021/audio_query",
    params={"text": "こんにちは", "speaker": 1}
)
query = response.json()

# 音声合成
response = requests.post(
    "http://localhost:50021/synthesis",
    params={"speaker": 1},
    json=query
)

# 再生
pygame.mixer.init()
pygame.mixer.music.load(BytesIO(response.content))
pygame.mixer.music.play()
```

## トラブルシューティング

### VOICEVOXに接続できない場合

1. VOICEVOXが起動しているか確認
2. ファイアウォールの設定を確認
3. ポート50021が他のアプリケーションで使用されていないか確認

### 音声が再生されない場合

1. システムの音量設定を確認
2. 音声出力デバイスが正しく設定されているか確認
3. pygameが正しくインストールされているか確認

## 使用可能なスピーカー

VOICEVOXには複数のキャラクターボイスが含まれています。
スピーカーIDを変更することで、異なる声色を使用できます。

利用可能なスピーカーリストは以下のコマンドで確認できます：

```python
python -c "import requests; import json; print(json.dumps(requests.get('http://localhost:50021/speakers').json(), ensure_ascii=False, indent=2))"
```

## エージェントでの使用方法

emotion_agentは自動的にVOICEVOXを使用して応答を音声で出力します。
特別な設定は不要で、VOICEVOXが起動していれば自動的に音声が再生されます。