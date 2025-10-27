#!/bin/bash
# リズムゲームモードで起動

echo "=== リズムゲーム起動 ===" >&2
echo "振動のリズムを覚えて、同じリズムでタッチしてください！" >&2
echo "" >&2

export GAME_MODE=rhythm_game
adk run agent
