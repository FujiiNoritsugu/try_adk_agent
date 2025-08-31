# 振動センサー Arduino WiFi セットアップ

このガイドでは、シリアル/USB通信の代わりにWiFi通信を使用して振動センサーを使用する方法を説明します。

## ハードウェア要件

- **ESP8266**（NodeMCU、Wemos D1 Miniなど）または **ESP32** ボード
- 振動センサーモジュール
- LED（オプション）

## ソフトウェア要件

- ESP8266/ESP32ボードサポート付きArduino IDE
- Python 3.8以上と必要なパッケージ（`aiohttp`、`asyncio`）

## Arduinoセットアップ

1. **ボードサポートのインストール**
   - ESP8266の場合：ボードマネージャーのURLに `http://arduino.esp8266.com/stable/package_esp8266com_index.json` を追加
   - ESP32の場合：`https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json` を追加

2. **ライブラリのインストール**
   - ArduinoJson（ライブラリマネージャー経由）

3. **WiFi認証情報の設定**
   `VibrationSensorArduinoWiFi.ino` を開いて更新：
   ```cpp
   const char* ssid = "あなたのWiFi_SSID";
   const char* password = "あなたのWiFiパスワード";
   ```

4. **スケッチのアップロード**
   - ボードを選択（例：「NodeMCU 1.0」または「ESP32 Dev Module」）
   - スケッチをアップロード
   - シリアルモニターを開いてIPアドレスを確認

## Pythonセットアップ

1. **依存関係のインストール**
   ```bash
   pip install aiohttp asyncio
   ```

2. **IPアドレスの更新**
   Pythonスクリプトで、ArduinoのIPアドレスを更新：
   ```python
   ARDUINO_IP = "192.168.1.100"  # あなたのArduinoのIP
   ```

## HTTP REST APIエンドポイント

Arduinoは以下のHTTPエンドポイントを提供します：

- **GET /status** - デバイスのステータスと情報を取得
- **GET /sensor** - 現在のセンサー値を読み取り
- **POST /calibrate** - センサーをキャリブレーション
- **POST /threshold** - 検出しきい値を設定
  ```json
  {"value": 150}
  ```
- **GET /monitor** - 継続的なデータのロングポーリング

## 使用例

### 基本的な接続テスト
```python
from vibration_sensor_controller_wifi import VibrationSensorControllerWiFi

controller = VibrationSensorControllerWiFi("sensor1", "192.168.1.100")
await controller.connect()
status = await controller.send_command({"action": "status"})
print(status)
```

### MCPサーバーと共に使用
`agent_mcp/agent.py` を更新してWiFiバージョンを使用：
```python
# WiFiベースの振動サーバーを使用
"vibration_agent": {
    "command": "python",
    "args": ["-m", "mcp_servers.vibration_server_wifi"],
    "env": {}
}
```

### MCPでArduinoを初期化
```python
# エージェント内で、IPアドレスを指定して初期化
result = await mcp.call_tool(
    "vibration_agent",
    "initialize_arduino",
    arguments={"host": "192.168.1.100", "port": 80}
)
```

## トラブルシューティング

1. **接続できない場合**
   - WiFi認証情報を確認
   - ArduinoとコンピュータがBgじネットワーク上にあることを確認
   - ArduinoのIPにpingを試行
   - ファイアウォール設定を確認

2. **応答が遅い場合**
   - WiFi信号強度（ステータスでRSSIを確認）
   - ネットワークの混雑
   - タイムアウト値を増やす

3. **接続が切れる場合**
   - WiFi再接続ロジックを追加
   - 電源供給の安定性を確認
   - ESP8266のヒープメモリを監視

## シリアル通信に対するWiFiの利点

- ワイヤレス動作
- 複数デバイスのサポート
- リモート監視
- USBケーブル不要
- 複数のクライアントからアクセス可能

## 制限事項

- WiFiネットワークが必要
- シリアルより高いレイテンシ
- 電力消費
- ネットワーク帯域幅による制限

## セキュリティに関する注意

この実装は暗号化なしのHTTPを使用しています。本番環境での使用には以下を検討してください：
- SSL/TLSを使用したHTTPS
- 認証の追加
- ネットワークアクセスの制限
- 専用のIoTネットワークの使用