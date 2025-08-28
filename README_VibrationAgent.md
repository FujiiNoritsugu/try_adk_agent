# Vibration Agent System (Serial Communication Version)

Arduino振動センサーをシリアル通信(USB)経由で制御し、リアルタイムでデータを取得・処理するPythonシステムです。

## ファイル構成

### Python コード
- `vibration_sensor_controller.py` - メインの振動センサーコントローラー
- `vibration_websocket_server.py` - リアルタイムデータ配信用WebSocketサーバー
- `vibration_agent_example.py` - 使用例とデモコード

### Arduino コード
- `VibrationSensorArduino/VibrationSensorArduino.ino` - Arduino用スケッチ

## 主な機能

### 振動センサーコントローラー
- シリアル通信によるArduino接続（pyserial使用）
- Arduinoポートの自動検出機能
- 非同期処理によるノンブロッキング通信
- 振動レベル判定（NONE, LOW, MEDIUM, HIGH, EXTREME）
- センサーキャリブレーション機能
- 閾値設定機能
- JSONベースのメッセージプロトコル

### 振動パターンジェネレーター
- 振動レベルに応じた触覚フィードバックパターン生成
- 地震、機械故障、接近警告などのアラートパターン
- カスタマイズ可能な振動パターン定義

### WebSocketサーバー
- リアルタイムセンサーデータストリーミング
- 複数クライアント同時接続対応
- センサー制御コマンド（閾値設定、キャリブレーション）
- JSONベースの双方向通信

## セットアップ

### Arduino側
1. 任意のArduinoボード（Uno、Nano、Mega等）を準備
2. 振動センサーをA0ピンに接続
3. VibrationSensorArduino.inoスケッチをアップロード
4. シリアルモニターで115200ボーレートに設定して動作確認

### Python側
1. 必要なライブラリをインストール：
   ```bash
   pip install pyserial websockets
   ```

2. Arduinoを接続してポートを確認（自動検出も可能）

## 使用方法

### 基本的な使用例
```python
import asyncio
from vibration_sensor_controller import VibrationSensorController

async def main():
    # センサーに接続（ポート自動検出）
    sensor = VibrationSensorController("sensor1")
    # sensor = VibrationSensorController("sensor1", "COM3")  # Windows
    # sensor = VibrationSensorController("sensor1", "/dev/ttyUSB0")  # Linux/Mac
    
    await sensor.connect()
    
    # データ読み取り
    data = await sensor.read_sensor_data()
    print(f"振動値: {data['vibration_value']}")
    
    # 切断
    await sensor.disconnect()

asyncio.run(main())
```

### 振動監視の実行
```bash
python vibration_agent_example.py monitoring
```

### WebSocketサーバーの起動
```bash
python vibration_websocket_server.py
```

## シリアル通信プロトコル

### コマンド（Python→Arduino）
```json
{"action": "status"}  // ステータス取得
{"action": "read_sensor"}  // センサー値読み取り
{"action": "calibrate"}  // キャリブレーション実行
{"action": "set_threshold", "value": 150}  // 閾値設定
{"action": "start_monitoring", "interval": 100}  // 継続監視開始
{"action": "stop_monitoring"}  // 継続監視停止
```

### レスポンス例（Arduino→Python）
```json
{
    "value": 245,
    "level": "medium",
    "detected": true,
    "threshold": 100,
    "timestamp": 123456
}
```

## カスタマイズ

### 振動レベルの調整
`_calculate_vibration_level`メソッドで閾値を変更：
```python
if value < 50:      # より敏感にする場合は値を下げる
    return VibrationLevel.NONE
```

### 新しいアラートパターンの追加
```python
"custom_alert": {
    "steps": [
        {"intensity": 0.9, "duration_ms": 100},
        {"intensity": 0.0, "duration_ms": 50}
    ],
    "interval_ms": 25,
    "repeat_count": 15
}
```

## トラブルシューティング

### 接続できない場合
- ArduinoのUSBケーブルが正しく接続されているか確認
- デバイスマネージャー（Windows）でCOMポートを確認
- `ls /dev/tty*`（Linux/Mac）でポートを確認
- Arduino IDEがポートを使用していないか確認

### センサー値が安定しない場合
- キャリブレーションを実行
- 閾値を調整
- センサーの取り付けを確認