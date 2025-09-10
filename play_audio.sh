#!/bin/bash

# デバッグログファイル
LOG_FILE="/tmp/play_audio.log"

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "Script started with args: $@"

# 引数チェック
if [ $# -eq 0 ]; then
    log "Error: No arguments provided"
    echo "Usage: $0 <wav_file_path>"
    exit 1
fi

WAV_FILE="$1"
log "WAV_FILE: $WAV_FILE"

# ファイルの存在確認
if [ ! -f "$WAV_FILE" ]; then
    log "Error: File not found: $WAV_FILE"
    echo "Error: File not found: $WAV_FILE"
    exit 1
fi

log "File exists. Size: $(stat -c%s "$WAV_FILE") bytes"

# WSL2でPulseAudioサーバーに接続するための設定
if [ -z "$PULSE_SERVER" ]; then
    # WSLgのPulseServerを使用
    if [ -e "/mnt/wslg/PulseServer" ]; then
        export PULSE_SERVER="unix:/mnt/wslg/PulseServer"
        log "Setting PULSE_SERVER to WSLg: $PULSE_SERVER"
    else
        # フォールバック: Windows側のPulseAudioサーバーに接続
        WINDOWS_IP=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
        export PULSE_SERVER="tcp:${WINDOWS_IP}:4713"
        log "Setting PULSE_SERVER to Windows: $PULSE_SERVER"
    fi
else
    log "PULSE_SERVER already set to: $PULSE_SERVER"
fi

# 再生関数を定義
play_and_cleanup() {
    log "Starting paplay with file: $1"
    paplay "$1" 2>>"$LOG_FILE"
    PLAY_RESULT=$?
    log "paplay finished with exit code: $PLAY_RESULT"
    
    # 再生完了後にファイルを削除
    rm -f "$1"
    log "File deleted: $1"
}

# バックグラウンドで音声を再生し、完了後にファイルを削除
play_and_cleanup "$WAV_FILE" &

PID=$!
log "Background process started with PID: $PID"

# プロセスIDを出力（必要に応じて）
echo $!