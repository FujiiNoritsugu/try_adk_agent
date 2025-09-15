# ADK用Leap Motion 2統合ガイド

このガイドでは、Leap Motion 2を使用してADK webインターフェースにデータを入力する方法を説明します。

## 概要

Leap Motion統合により、`{"data": 0.5, "touched_area": "胸"}`を手動で入力する代わりに、ハンドジェスチャーを使用してADK入力を制御できます。システムは手の動きを適切なタッチ強度と体の部位に自動的に変換します。

## コンポーネント

1. **Leap Motion MCPサーバー** (`server_leapmotion/server.py`)
   - Leap Motionセンサーデータを処理
   - ジェスチャー検出を提供
   - ジェスチャーをADK入力形式に変換

2. **拡張TouchInputスキーマ** (`agent_mcp/agent.py`)
   - オプションのLeap Motionフィールドをサポート
   - 手動入力との後方互換性を維持

3. **Leap Motionブリッジ** (`leap_motion_bridge.py`)
   - Leap MotionとADK web間のリアルタイムブリッジ
   - ハンドジェスチャーを継続的に監視
   - 変換されたデータをADKに送信

## インストール

### 1. Leap Motion SDKのインストール

```bash
# セットアップスクリプトを実行
python server_leapmotion/setup_leap.py

# または手動でインストール：
# - https://developer.leapmotion.com/tracking-software-download からSDKをダウンロード
# - セットアップスクリプトの出力にあるプラットフォーム固有の手順に従う
```

### 2. Python依存関係のインストール

```bash
cd server_leapmotion
pip install -r requirements.txt
```

## 使用方法

### 方法1：直接MCP統合

Leap Motion MCPサーバーはすでにエージェントに統合されています。ADK webを通じてデータを入力すると、エージェントはLeap Motionツールにアクセスできるようになります。

### 方法2：リアルタイムブリッジ（推奨）

ブリッジを実行してLeap MotionデータをADKに継続的に送信：

```bash
# 実際のLeap Motionデバイスを使用
python leap_motion_bridge.py --adk-url http://localhost:8080

# デバイスなしでテスト（モックデータを使用）
python leap_motion_bridge.py --mock
```

### 方法3：デモモード

統合をテスト：

```bash
python leap_motion_demo.py
```

## ジェスチャーマッピング

| ジェスチャー | 説明 | 基本強度 | 実行方法 |
|---------|-------------|----------------|----------------|
| スワイプ | 素早い手の動き | 0.3 | 手を素早く動かす（速度>500） |
| サークル | 円運動 | 0.5 | 手を円形に動かす |
| タップ | 1本指タップ | 0.7 | 1本の指を伸ばす |
| グラブ | 拳を握る | 0.8 | 全ての指を閉じる |
| ピンチ | 2本指ピンチ | 0.6 | 2本の指を伸ばし、低速度 |

## 体の部位マッピング

手のY位置が触れた体の部位を決定：

- **250以上**: 頭
- **150-250**: 胸
- **50-150**: 腹
- **50未満**: 足

## 入力フォーマット

システムは自動的にADK入力フォーマットを生成：

```json
{
  "data": 0.5,           // タッチ強度（0-1）
  "touched_area": "胸",   // 体の部位
  "gesture_type": "tap",  // オプション：検出されたジェスチャー
  "hand_position": {...}, // オプション：3D位置
  "hand_velocity": 150.5, // オプション：手の速度
  "leap_confidence": 0.9  // オプション：検出信頼度
}
```

## カスタマイズ

### ジェスチャー感度の調整

`server_leapmotion/server.py`でジェスチャー検出を修正：

```python
# detect_gesture()メソッド内
if velocity > 500:  # このしきい値を調整
    return "swipe"
```

### カスタムジェスチャーマッピング

MCPツールを使用してカスタムマッピングを設定：

```python
# エージェントまたはデモ経由で
set_gesture_mapping(
    gesture="swipe",
    intensity=0.9,
    area="頭"
)
```

## トラブルシューティング

1. **「Leap Motion SDKが見つかりません」**
   - `python server_leapmotion/setup_leap.py`を実行
   - 公式ウェブサイトからSDKをインストール

2. **「手が検出されません」**
   - Leap Motionデバイスが接続されていることを確認
   - センサーの上10-40cmに手を置く
   - Leap Motionコントロールパネルを確認

3. **ブリッジ接続エラー**
   - ADK webが正しいポートで実行されていることを確認
   - `--adk-url`パラメータを確認

4. **テスト用モックモードの使用**
   - デバイスなしでテストするには`--mock`フラグで実行
   - 手の動きを自動的にシミュレート

## ADK Webとの統合

1. 通常通りADK webを起動
2. Leap Motionブリッジを実行
3. ADK webで`agent_mcp/agent.py`を選択
4. Leap Motionセンサーの上で手を動かす
5. 入力フィールドにジェスチャーデータが自動的に入力される

エージェントは手動タッチ入力と同様にLeap Motionデータを処理し、適切な感情反応、振動、音声出力を生成します。