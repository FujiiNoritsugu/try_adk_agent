# Vibration Agent Arduino Integration

このドキュメントでは、`agent_mcp/agent.py`の`vibration_agent`がArduino振動センサーを制御する統合について説明します。

## 統合概要

### アーキテクチャ
```
TouchInput → emotion_agent → vibration_agent → MCP Server → Arduino
```

1. **TouchInput**: 触覚入力データ（強度0-1、触れられた部位）
2. **emotion_agent**: 触覚から感情を判断するルートエージェント
3. **vibration_agent**: 感情に基づいて振動パターンを制御する専門エージェント
4. **MCP Server**: Arduino通信を管理するMCPサーバー
5. **Arduino**: 振動センサー付きArduinoデバイス

### 新機能
- Arduinoセンサーの自動検出・接続
- 感情レベルに基づいた振動パターン生成
- リアルタイム振動制御
- センサーキャリブレーション

## セットアップ手順

### 1. Arduinoの準備
```bash
# Arduino側の準備
# 1. VibrationSensorArduino.ino をアップロード
# 2. シリアルポートでPCに接続
# 3. シリアルモニター(115200)で動作確認
```

### 2. Python依存関係のインストール
```bash
cd /home/fujii/try_adk_agent
pip install pyserial websockets
```

### 3. MCPサーバーの設定確認
```bash
# vibration_server.py の動作確認
cd mcp_servers
python vibration_server.py
```

### 4. エージェントの実行
```bash
cd agent_mcp
python test_vibration_agent.py
```

## 利用可能なツール

### MCPツール（vibration_server.py）

#### 1. `generate_vibration_pattern`
感情パラメータから振動パターンを生成
```json
{
  "tool": "generate_vibration_pattern",
  "arguments": {
    "joy": 4,     // 喜び (0-5)
    "fun": 2,     // 楽しさ (0-5) 
    "anger": 0,   // 怒り (0-5)
    "sad": 0      // 悲しさ (0-5)
  }
}
```

#### 2. `control_vibration`
振動設定でArduinoを制御
```json
{
  "tool": "control_vibration", 
  "arguments": {
    "vibration_settings": {
      "vibration_enabled": true,
      "pattern": "pulse",
      "intensity": 0.7,
      "frequency": 2.0,
      "duration": 0.5,
      "emotion_level": 4
    }
  }
}
```

#### 3. `send_arduino_vibration`
直接的な振動パターン送信
```json
{
  "tool": "send_arduino_vibration",
  "arguments": {
    "pattern_type": "wave",    // pulse, wave, burst, fade
    "intensity": 0.6,          // 0.0-1.0
    "duration_ms": 1000,       // ミリ秒
    "repeat_count": 3          // 繰り返し回数
  }
}
```

#### 4. `initialize_arduino`
Arduinoセンサーの初期化
```json
{
  "tool": "initialize_arduino",
  "arguments": {}
}
```

## 触覚入力と振動応答のマッピング

### TouchInputの解釈
```python
TouchInput(data=0.1, touched_area="cheek")   # → 穏やか(sad) → ゆっくり弱い振動
TouchInput(data=0.3, touched_area="hand")    # → 喜び(joy) → リズミカルな振動  
TouchInput(data=0.5, touched_area="shoulder") # → 楽しい(fun) → 波打つ振動
TouchInput(data=0.9, touched_area="arm")     # → 痛み(anger) → 強い断続振動
```

### 振動レベルマッピング
```python
感情値 0-1 → VibrationLevel.LOW      # 弱い振動
感情値 2   → VibrationLevel.MEDIUM   # 中程度の振動
感情値 3   → VibrationLevel.MEDIUM   # 中程度の振動  
感情値 4   → VibrationLevel.HIGH     # 強い振動
感情値 5   → VibrationLevel.EXTREME  # 最大振動
```

## テストとデバッグ

### 1. Arduino接続テスト
```bash
cd agent_mcp
python test_vibration_agent.py
```

### 2. MCPサーバー単体テスト
```bash
cd mcp_servers
python -c "
import asyncio
from vibration_server import initialize_arduino
print(asyncio.run(initialize_arduino()))
"
```

### 3. シリアル通信確認
```bash
# Pythonでポート確認
python -c "
import serial.tools.list_ports
for port in serial.tools.list_ports.comports():
    print(f'{port.device}: {port.description}')
"
```

## トラブルシューティング

### Arduino接続エラー
```python
# エラー: "Arduinoに接続できませんでした"
# 解決方法:
# 1. USBケーブル確認
# 2. Arduino IDEでポート確認
# 3. 他のソフトウェア（シリアルモニター）を閉じる
# 4. Arduinoを再接続
```

### MCPサーバーエラー
```bash
# エラー: "Unknown tool: send_arduino_vibration"
# 解決方法:
# 1. agent.py のtool_filterを確認
# 2. vibration_server.py の@app.list_tools()を確認
# 3. MCPサーバーを再起動
```

### 振動が実行されない
```python
# 確認項目:
# 1. Arduino の振動機能実装確認
# 2. シリアル通信のJSONフォーマット確認  
# 3. コマンド処理のデバッグログ確認
```

## カスタマイズ

### 新しい感情パターンの追加
```python
# vibration_server.py に追加
vibration_patterns["excitement"] = {
    "pattern": "rapid_pulse",
    "intensity_base": 0.8,
    "frequency_base": 4.0,
    "duration_base": 0.25,
    "description": "興奮した急速な振動"
}
```

### Arduino側パターン拡張
```cpp
// VibrationSensorArduino.ino に追加
else if (action == "custom_pattern") {
    // カスタム振動パターンの実装
    sendCustomVibration(doc["pattern"]);
}
```

## 今後の拡張可能性

1. **複数Arduino対応**: 複数の振動デバイス同時制御
2. **機械学習統合**: 触覚パターンからの感情学習
3. **WebUI**: リアルタイム振動制御ダッシュボード
4. **音声連携**: 音声感情と振動の同期
5. **VR/AR統合**: バーチャル環境での触覚フィードバック