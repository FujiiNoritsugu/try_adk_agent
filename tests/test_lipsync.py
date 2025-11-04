#!/usr/bin/env python3
"""
VTube Studioリップシンク機能のテストスクリプト

このスクリプトは以下をテストします：
1. VOICEVOXでテキストを音声合成してWAVファイルを取得
2. VTube StudioのリップシンクAPIで音声に合わせて口を動かす

前提条件:
- VTube Studioが起動している（ポート8001でAPI有効）
- VOICEVOXが起動している（ポート50021）
- VTube Studioで事前認証が完了している（~/.vtube_studio_token）
"""

import asyncio
import json
import logging
import sys
import os

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mcp_servers.voicevox_server import VoiceVoxServer
from mcp_servers.vtube_studio_server import VTubeStudioClient


async def test_lipsync():
    """リップシンク機能のテスト"""

    # テストメッセージ
    test_message = "こんにちは！今日はとても良い天気ですね。"

    logger.info("=" * 60)
    logger.info("VTube Studio リップシンクテスト開始")
    logger.info("=" * 60)

    # ステップ1: VOICEVOXで音声合成
    logger.info("\n[ステップ1] VOICEVOX音声合成")
    voicevox = VoiceVoxServer()
    await voicevox.initialize()

    tts_result = await voicevox.text_to_speech(test_message, speaker_id=1)

    if not tts_result.get("success"):
        logger.error(f"音声合成失敗: {tts_result.get('error')}")
        logger.error("VOICEVOXが起動しているか確認してください（http://localhost:50021）")
        return False

    audio_file_path = tts_result.get("audio_file")
    logger.info(f"✓ 音声合成成功")
    logger.info(f"  テキスト: {test_message}")
    logger.info(f"  音声ファイル: {audio_file_path}")
    logger.info(f"  スピーカーID: {tts_result.get('speaker_id')}")

    # ステップ2: VTube Studioでリップシンク
    logger.info("\n[ステップ2] VTube Studio リップシンク")
    vtube_client = VTubeStudioClient()

    try:
        # WebSocket接続
        await vtube_client.connect()
        logger.info("✓ VTube Studioに接続")

        # 認証（既存のトークンを使用）
        auth_result = await vtube_client.authenticate()
        if not auth_result.get("data", {}).get("authenticated"):
            logger.error("VTube Studio認証失敗")
            logger.error("先にVTube Studioで認証を完了してください")
            return False

        logger.info("✓ VTube Studio認証成功")

        # リップシンク実行
        logger.info("リップシンク開始...")
        lipsync_result = await vtube_client.sync_lipsync_with_audio(audio_file_path)

        if not lipsync_result.get("success"):
            logger.error(f"リップシンク失敗: {lipsync_result.get('error')}")
            return False

        logger.info("✓ リップシンク完了")
        logger.info(f"  再生時間: {lipsync_result.get('duration'):.2f}秒")
        logger.info(f"  フレーム数: {lipsync_result.get('frames')}")

    finally:
        await vtube_client.disconnect()
        logger.info("VTube Studio接続を切断")

    # 音声ファイルのクリーンアップ
    try:
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)
            logger.info(f"一時ファイル削除: {audio_file_path}")
    except Exception as e:
        logger.warning(f"一時ファイル削除失敗: {e}")

    logger.info("\n" + "=" * 60)
    logger.info("テスト成功！")
    logger.info("=" * 60)
    return True


async def test_expression_reset():
    """表情自動リセット機能のテスト"""

    logger.info("=" * 60)
    logger.info("表情自動リセット機能テスト")
    logger.info("=" * 60)

    vtube_client = VTubeStudioClient()
    await vtube_client.connect()

    try:
        # 認証
        auth_result = await vtube_client.authenticate()
        if not auth_result.get("data", {}).get("authenticated"):
            logger.error("VTube Studio認証失敗")
            return False

        logger.info("✓ VTube Studio認証成功")

        # テスト: 喜び表情を5秒後にリセット
        logger.info("\n[テスト] 喜び表情 → 5秒後に自動リセット")

        # 喜び表情を設定（手動でトリガー）
        await vtube_client.trigger_hotkey("Joy")
        logger.info("✓ 喜び表情に変更")
        logger.info("  5秒待機中...")

        await asyncio.sleep(5)

        # 中立表情に戻す
        await vtube_client.trigger_hotkey("Remove Expressions")
        logger.info("✓ 中立表情にリセット")

        logger.info("\n" + "=" * 60)
        logger.info("テスト成功！")
        logger.info("=" * 60)
        return True

    finally:
        await vtube_client.disconnect()


async def test_emotions_and_lipsync():
    """感情表情とリップシンクの統合テスト"""

    logger.info("=" * 60)
    logger.info("感情表情 + リップシンク 統合テスト")
    logger.info("=" * 60)

    # テストケース（reset_after_secondsを含む）
    test_cases = [
        {
            "emotion": {"joy": 5, "fun": 3, "anger": 0, "sad": 0},
            "message": "わぁ！すごく嬉しい！",
            "reset_after": 4
        },
        {
            "emotion": {"joy": 0, "fun": 0, "anger": 5, "sad": 0},
            "message": "もう！本当に怒ったから！",
            "reset_after": 5
        },
        {
            "emotion": {"joy": 0, "fun": 0, "anger": 0, "sad": 5},
            "message": "悲しいよ...どうしてこんなことに...",
            "reset_after": 3
        }
    ]

    voicevox = VoiceVoxServer()
    await voicevox.initialize()

    vtube_client = VTubeStudioClient()
    await vtube_client.connect()

    try:
        # 認証
        auth_result = await vtube_client.authenticate()
        if not auth_result.get("data", {}).get("authenticated"):
            logger.error("VTube Studio認証失敗")
            return False

        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n[テストケース {i}]")
            emotion = test_case["emotion"]
            message = test_case["message"]
            reset_after = test_case.get("reset_after", 0)

            # 感情表情を更新
            logger.info(f"感情: {emotion}")
            # 最も高い感情を取得
            dominant = max(emotion, key=emotion.get)
            hotkey_map = {
                "joy": "Joy",
                "fun": "Pleasure",
                "anger": "Anger",
                "sad": "Sadness"
            }
            hotkey = hotkey_map.get(dominant)

            await vtube_client.trigger_hotkey(hotkey)
            logger.info(f"✓ 表情更新: {hotkey}")
            if reset_after > 0:
                logger.info(f"  {reset_after}秒後に自動リセット設定")

            # 音声合成
            tts_result = await voicevox.text_to_speech(message)
            if not tts_result.get("success"):
                logger.error(f"音声合成失敗: {tts_result.get('error')}")
                continue

            audio_file = tts_result.get("audio_file")
            logger.info(f"✓ 音声合成: {message}")

            # リップシンク
            lipsync_result = await vtube_client.sync_lipsync_with_audio(audio_file)
            if lipsync_result.get("success"):
                logger.info(f"✓ リップシンク完了 ({lipsync_result.get('duration'):.2f}秒)")
            else:
                logger.error(f"リップシンク失敗: {lipsync_result.get('error')}")

            # クリーンアップ
            if os.path.exists(audio_file):
                os.remove(audio_file)

            # 自動リセット待機
            if reset_after > 0:
                logger.info(f"  {reset_after}秒後にリセット...")
                await asyncio.sleep(reset_after)
                await vtube_client.trigger_hotkey("Remove Expressions")
                logger.info("  ✓ 中立表情にリセット")

            # 次のテストケースまで少し待機
            await asyncio.sleep(2)

        logger.info("\n" + "=" * 60)
        logger.info("統合テスト成功！")
        logger.info("=" * 60)
        return True

    finally:
        await vtube_client.disconnect()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="VTube Studioリップシンクテスト")
    parser.add_argument(
        "--integrated",
        action="store_true",
        help="感情表情とリップシンクの統合テストを実行"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="表情自動リセット機能のテストを実行"
    )
    args = parser.parse_args()

    if args.reset:
        success = asyncio.run(test_expression_reset())
    elif args.integrated:
        success = asyncio.run(test_emotions_and_lipsync())
    else:
        success = asyncio.run(test_lipsync())

    sys.exit(0 if success else 1)
