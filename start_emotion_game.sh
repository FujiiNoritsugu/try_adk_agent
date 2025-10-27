#!/bin/bash
# 感情シンクロゲームモードで起動

echo "=== 感情シンクロゲーム起動 ===" >&2
echo "ゲームの目標感情を提示します。触り方を調整して目標に合わせてください！" >&2
echo "" >&2

export GAME_MODE=emotion_game
adk run agent
