# ハプティックフィードバック統合ガイド

このガイドでは、Arduino Uno R4 WiFiを使用したハプティックフィードバックシステムの統合方法を説明します。

## システム概要

```
TouchInput → emotion_agent → vibration_agent → MCP Server → Arduino → Vibration Module
```

## セットアップ手順

### 1. Arduinoハードウェア設定

**必要な機器:**
- Arduino Uno R4 WiFi
- 振動モジュール（例：Youmile GR-YM-222-2）
- ジャンパーワイヤー

**接続:**
- 振動モジュール制御ピン → Arduino Pin 9 (PWM)
- 振動モジュール電源 → Arduino 5V
- 振動モジュールGND → Arduino GND

### 2. Arduinoソフトウェア設定

1. **ライブラリのインストール**
   ```
   Arduino IDE → ライブラリマネージャー
   - ArduinoJson (最新版)
   ```

2. **WiFi設定**
   `arduino/haptic_feedback_controller/config.h`を編集：
   ```cpp
   #define WIFI_SSID "あなたのWiFi_SSID"
   #define WIFI_PASSWORD "あなたのWiFiパスワード"
   ```

3. **スケッチのアップロード**
   `arduino/haptic_feedback_controller/haptic_feedback_controller.ino`をアップロード

4. **IPアドレスの確認**
   シリアルモニターでArduinoのIPアドレスを確認

### 3. Python環境設定

1. **依存関係のインストール**
   ```bash
   pip install aiohttp asyncio
   ```

2. **テスト実行**
   ```bash
   python test_haptic_integration.py
   ```

### 4. エージェント設定

1. **Arduino初期化**
   エージェント内でArduinoを初期化：
   ```python
   await mcp.call_tool(
       "vibration_agent",
       "initialize_arduino",
       arguments={"host": "192.168.1.100", "port": 80}
   )
   ```

2. **感情ベース振動**
   ```python
   # 感情値から振動パターンを生成
   pattern = await mcp.call_tool(
       "vibration_agent",
       "generate_vibration_pattern",
       arguments={"joy": 4, "fun": 2, "anger": 0, "sad": 1}
   )
   
   # 振動を実行
   result = await mcp.call_tool(
       "vibration_agent",
       "control_vibration",
       arguments={"vibration_settings": pattern}
   )
   ```

## API仕様

### Arduino HTTP API

- **GET /status** - デバイス状態取得
- **POST /pattern** - 振動パターン実行
- **POST /stop** - 振動停止

### MCP ツール

1. **initialize_arduino**
   - ArduinoデバイスをWiFi経由で初期化
   - 引数: `host`, `port`

2. **generate_vibration_pattern**
   - 感情値から振動パターンを生成
   - 引数: `joy`, `fun`, `anger`, `sad` (0-5)

3. **control_vibration**
   - 振動パターンをArduinoに送信
   - 引数: `vibration_settings`

4. **send_arduino_vibration**
   - 直接振動パターンを送信
   - 引数: `pattern_type`, `intensity`, `duration_ms`, `repeat_count`

## 振動パターン仕様

### パターンタイプ

1. **pulse** - ON/OFF繰り返し
2. **wave** - 段階的強弱変化
3. **burst** - 短い強い振動
4. **fade** - 徐々に弱まる振動

### 感情マッピング

- **喜び (Joy)**: 軽快なパルスパターン
- **怒り (Anger)**: 強い断続パターン
- **悲しみ (Sorrow)**: ゆっくりした弱いパターン
- **楽しさ (Fun/Pleasure)**: なめらかな波形パターン

## 使用例

### 基本的な振動制御

```python
from src.devices import ArduinoController, VibrationPatternGenerator

# Arduinoに接続
controller = ArduinoController("haptic_device", "192.168.1.100")
await controller.connect()

# カスタムパターン作成
pattern = VibrationPatternGenerator.create_custom_pattern(
    pattern_type="pulse",
    intensity=0.7,
    duration_ms=1000,
    repeat_count=3
)

# パターン送信
success = await controller.send_pattern(pattern)

# 切断
await controller.disconnect()
```

### 感情ベースパターン

```python
# 感情値から自動生成
pattern = VibrationPatternGenerator.from_emotion_values(
    joy=4, fun=2, anger=0, sad=1
)

# Arduinoに送信
await controller.send_pattern(pattern)
```

## トラブルシューティング

### Arduino接続エラー
1. WiFi設定を確認
2. IPアドレスが正しいか確認
3. ファイアウォール設定を確認
4. Arduinoの電源を確認

### 振動しない場合
1. 配線を確認（特にPin 9）
2. 振動モジュールの電源を確認
3. パターンの強度値を確認（0.0より大きい値）
4. シリアルモニターでエラーメッセージを確認

### MCP通信エラー
1. vibration_server.pyが起動しているか確認
2. パスの設定を確認（src/devicesが見つかるか）
3. 依存関係がインストールされているか確認

## セキュリティ注意事項

- 現在の実装は暗号化されていないHTTP通信を使用
- 本番環境では以下を検討：
  - HTTPS/TLSの使用
  - 認証機能の追加
  - ネットワークアクセス制限
  - 専用IoTネットワークの使用