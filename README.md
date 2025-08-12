# 感情と触覚を持つチャットボット

システムプロンプトに基づいた、感情パラメータと触覚フィードバックを持つインタラクティブなチャットボットです。

## 機能

- 4つの感情パラメータ（joy, fun, anger, sad）を管理
- 触覚の強さ（0〜1）に応じた感情の変化
- JSON形式での入出力
- 性別設定に対応

## 使い方

### 基本的な実行

```bash
python chatbot.py
```

### テストの実行

```bash
python test_chatbot.py
```

## 入力形式

```json
{
  "data": 0.5,
  "touched_area": "頭",
  "gender": "女性"
}
```

- `data`: 触覚の強さ（0〜1）
  - 0: 何も感じない
  - 0.5付近: 最も心地良い
  - 1に近い: 痛みを感じる
- `touched_area`: 触れられた部位
- `gender`: 性別設定（オプション）

## 出力形式

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

## ファイル構成

- `chatbot.py`: メインのチャットボット実装
- `test_chatbot.py`: テストスクリプト
- `prompt/system_prompt`: 元のシステムプロンプト