#!/usr/bin/env python3
"""
エージェントをLeap Motionポーリングと共に実行するスクリプト
"""
import asyncio
import os
import sys
import signal
import logging
from agent_mcp.agent_http import agent, leap_poller

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# グローバル変数でポーリングタスクを管理
polling_task = None

def signal_handler(signum, frame):
    """終了シグナルのハンドラー"""
    logger.info("Received shutdown signal, stopping Leap Motion polling...")
    leap_poller.stop_polling()
    if polling_task:
        polling_task.cancel()
    sys.exit(0)

async def main():
    """メイン関数"""
    global polling_task
    
    # Leap Motion HTTPサーバーのURLを環境変数から取得
    leap_server_url = os.getenv("LEAP_MOTION_SERVER_URL", "http://localhost:8001")
    logger.info(f"Connecting to Leap Motion server at: {leap_server_url}")
    
    # サーバーURLを更新
    leap_poller.server_url = leap_server_url
    
    # Leap Motionポーリングを開始
    logger.info("Starting Leap Motion polling...")
    polling_task = asyncio.create_task(leap_poller.start_polling())
    
    try:
        # ポーリングタスクを実行し続ける
        await polling_task
    except asyncio.CancelledError:
        logger.info("Polling task cancelled")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        leap_poller.stop_polling()

if __name__ == "__main__":
    # シグナルハンドラーを設定
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 使用方法を表示
    print("Leap Motion統合エージェント")
    print("="*50)
    print("使用方法:")
    print("1. 別のPCでLeap Motion HTTPサーバーを起動:")
    print("   python server_leapmotion/server_http.py --host 0.0.0.0 --port 8001")
    print("")
    print("2. 環境変数でサーバーURLを設定:")
    print("   export LEAP_MOTION_SERVER_URL=http://[別PCのIP]:8001")
    print("")
    print("3. このスクリプトを実行:")
    print("   python run_agent_with_leap.py")
    print("")
    print("4. 別のターミナルでADKエージェントを起動:")
    print("   adk run .")
    print("="*50)
    print("")
    
    # Leap Motionポーリングを実行
    asyncio.run(main())