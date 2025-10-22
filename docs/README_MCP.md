# MCP版エージェント実装

## 概要
元の`agent/agent.py`をMCP（Model Context Protocol）を使用するように書き換えました。

## 変更点

### 1. MCPサーバーの実装
- `mcp_servers/emoji_server.py`: 絵文字生成用MCPサーバー
- `mcp_servers/vibration_server.py`: 振動制御用MCPサーバー

### 2. エージェントの変更
- `agent/agent_mcp.py`: MCP対応版のエージェント実装
- `FunctionTool`の代わりに`MCPToolset`を使用
- MCPサーバーとStdio接続で通信

## 必要な依存関係

```bash
pip install mcp
```

## 使用方法

1. MCPサーバーを起動可能な状態にする：
   ```bash
   chmod +x mcp_servers/*.py
   ```

2. エージェントを実行：
   ```bash
   # 環境変数でMCP版を指定
   export ADK_AGENT_FILE=agent/agent_mcp.py
   adk run
   ```

   または、直接実行：
   ```python
   from agent.agent_mcp import agent
   # エージェントを使用
   ```

## アーキテクチャの違い

### 元の実装（FunctionTool）
- Pythonの関数を直接ラップ
- 同一プロセス内で実行
- シンプルだが拡張性に制限

### MCP実装
- 独立したプロセスとして実行
- 標準入出力で通信
- 言語に依存しない（他の言語でも実装可能）
- より柔軟な拡張が可能

## メリット
1. **分離性**: ツールロジックが独立したサーバーとして動作
2. **再利用性**: MCPサーバーは他のエージェントからも利用可能
3. **拡張性**: 新しいツールの追加が容易
4. **標準化**: MCP仕様に準拠した実装

## 注意点
- MCPサーバーが別プロセスで動作するため、起動時間がやや長い
- デバッグ時はMCPサーバーのログも確認が必要