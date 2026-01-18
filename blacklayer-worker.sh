#!/usr/bin/env bash

BASE_DIR="$HOME/.config/blacklayer"
CONF_FILE="$BASE_DIR/blacklayer.conf"
[ -f "$CONF_FILE" ] && source "$CONF_FILE"

# -------------------------
# .conf dan gelen degerler/Default değerler
# -------------------------
LOOP_INTERVAL="${LOOP_INTERVAL:-60}"
COUNT_THRESHOLD="${COUNT_THRESHOLD:-5}"
WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}"
EVENT_POLL_INTERVAL="${EVENT_POLL_INTERVAL:-3}"
EVENT_DRIVEN="${EVENT_DRIVEN:-$HOME/.config/blacklayer/event-driven.sh}"

BLACKLAYER_BIN="$BASE_DIR/blacklayer"
COUNT_FILE="$BASE_DIR/.blacklayer_count"
STATE_DIR="$BASE_DIR/.blacklayer_state"
WAYBAR_BIN="/usr/bin/waybar"
WAYBAR_CONFIG_DIR="$HOME/.config/waybar"


# -------------------------
# Sonsuz döngü
# -------------------------
while true; do
    export XDG_RUNTIME_DIR="/run/user/$(id -u)"
    [ -z "$HYPRLAND_INSTANCE_SIGNATURE" ] && \
        export HYPRLAND_INSTANCE_SIGNATURE="$(ls "$XDG_RUNTIME_DIR/hypr/" 2>/dev/null | head -n1)"
    export WAYLAND_DISPLAY


    mkdir -p "$STATE_DIR"
    [ ! -f "$COUNT_FILE" ] && echo "0" > "$COUNT_FILE"
    chmod 600 "$STATE_DIR"/* 2>/dev/null || true

    JSON="$(hyprctl -j monitors 2>/dev/null)"
    echo "$JSON" | jq empty >/dev/null 2>&1 || { sleep "$LOOP_INTERVAL"; continue; }

    # -------------------------
    # Focused kontrol ve state update
    # -------------------------
    echo "$JSON" | jq -r '.[] | .name + " " + (.focused|tostring)' | while read -r MONITOR_NAME FOCUSED; do
        STATE_FILE="$STATE_DIR/$MONITOR_NAME"
        [ ! -f "$STATE_FILE" ] && echo "false" > "$STATE_FILE"
        ISWORKING=$(<"$STATE_FILE")
        [ "$FOCUSED" = "true" ] && echo "true" > "$STATE_FILE"
    done

    # -------------------------
    # Count artır
    # -------------------------
    COUNT=$(<"$COUNT_FILE")
    COUNT=$((COUNT + 1))
    echo "$COUNT" > "$COUNT_FILE"

    # -------------------------
    # 5. çağrıda blacklayer açma
    # -------------------------
    if [ "$COUNT" -ge "$COUNT_THRESHOLD" ]; then
        echo "$JSON" | jq -r '.[] | .name' | while read -r MONITOR_NAME; do
            STATE_FILE="$STATE_DIR/$MONITOR_NAME"
            ISWORKING=$(<"$STATE_FILE")

            if [ "$ISWORKING" = "false" ] && ! pgrep -f "$BLACKLAYER_BIN $MONITOR_NAME" >/dev/null 2>&1; then
                pkill -f "waybar.*$MONITOR_NAME" 2>/dev/null
            
                "$BLACKLAYER_BIN" "$MONITOR_NAME" &
                nohup bash -c "$EVENT_DRIVEN $MONITOR_NAME $EVENT_POLL_INTERVAL" >/dev/null 2>&1 &
                echo "true" > "$STATE_FILE"
            fi
        done

        # 5. okumadan sonra tüm state ve count sıfırlama
        echo "0" > "$COUNT_FILE"
        for STATE in "$STATE_DIR"/*; do
            echo "false" > "$STATE"
        done
    fi

    sleep "$LOOP_INTERVAL"
done
