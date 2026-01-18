#!/usr/bin/env bash

# -------------------------
# Base paths (EN BAŞTA)
# -------------------------
BASE_DIR="$HOME/.config/blacklayer"
PID_FILE="$BASE_DIR/blacklayer_worker.pid"
STATE_DIR="$BASE_DIR/blacklayer_state"
COUNT_FILE="$BASE_DIR/blacklayer_count"

WORKER="$BASE_DIR/blacklayer-worker.sh"
BLACKLAYER_BIN="$BASE_DIR/blacklayer"

# Dizini garanti altına al
mkdir -p "$STATE_DIR"

# -------------------------
# Worker çalışıyorsa → KAPAT
# -------------------------
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    notify-send "Blacklayer" "blacklayer is stopping"
    echo "[blacklayer] stopping..."

    # Worker'ı kapat
    kill "$(cat "$PID_FILE")" 2>/dev/null
    rm -f "$PID_FILE"

    # Tüm blacklayer processlerini kapat
    pkill -f "$BLACKLAYER_BIN" 2>/dev/null

    # State & count temizliği
    rm -rf "$STATE_DIR"
    rm -f "$COUNT_FILE"

    exit 0
fi

# -------------------------
# Çalışmıyorsa → BAŞLAT
# -------------------------
notify-send "Blacklayer" "blacklayer is starting"
echo "[blacklayer] starting..."

nohup bash "$WORKER" >/dev/null 2>&1 &
echo $! > "$PID_FILE"
