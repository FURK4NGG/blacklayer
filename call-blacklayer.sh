#!/usr/bin/env bash

# -------------------------
# Base paths (EN BAŞTA)
# -------------------------
BASE_DIR="$HOME/.config/blacklayer"
CONF_FILE="$BASE_DIR/blacklayer.conf"
[ -f "$CONF_FILE" ] && source "$CONF_FILE"
PID_FILE="$BASE_DIR/blacklayer_worker.pid"
STATE_DIR="$BASE_DIR/blacklayer_state"
COUNT_FILE="$BASE_DIR/blacklayer_count"

WORKER="$BASE_DIR/blacklayer-worker.sh"
BLACKLAYER_BIN="$BASE_DIR/blacklayer"


NEED_HYPRIDLE=false

if [ "$run_lock" = "true" ] || [ "$run_sleep" = "true" ]; then
    NEED_HYPRIDLE=true
else
    notify-send "Hypridle" "hypridle is disabled via config"
    echo "[hypridle] disabled via config"
fi

HYPRIDLE_RUNNING=false
if systemctl --user --quiet is-active hypridle.service; then
    HYPRIDLE_RUNNING=true
fi

case "$NEED_HYPRIDLE:$HYPRIDLE_RUNNING" in
    true:false)
        # Gerekli ama çalışmıyor → BAŞLAT
        notify-send "Hypridle" "hypridle is enabled"
        systemctl --user start hypridle.service
        ;;

    true:true)
        # Gerekli fakat çalışıyor → KAPAT
        notify-send "Hypridle" "hypridle is disabled"
        systemctl --user stop hypridle.service
        ;;

    false:true)
        # Gerekli değil fakat çalışıyor → KAPAT
        #If you try to start hypridle.service and its closed by own this >
        notify-send "Hypridle" "hypridle is disabled"
        systemctl --user stop hypridle.service
        ;;


    *)
        ;;
esac

# eğer blacklayer kapalıysa çık
if [ "$run_blacklayer" != "true" ]; then
    notify-send "Blacklayer" "blacklayer is disabled via config"
    echo "[blacklayer] disabled via config"
    kill "$(cat "$PID_FILE")" 2>/dev/null
    rm -f "$PID_FILE"

    # Tüm blacklayer processlerini kapat
    pkill -f "$BLACKLAYER_BIN" 2>/dev/null

    # State & count temizliği
    rm -rf "$STATE_DIR"
    rm -f "$COUNT_FILE"
    exit 0
fi


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
