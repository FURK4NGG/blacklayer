#!/usr/bin/env bash
# Kullanım: event-driven.sh <MONITOR_NAME> <POLL_INTERVAL>
MONITOR="$1"
POLL_INTERVAL="${2:-3}"  # default 3s
[ -z "$MONITOR" ] && { echo "Monitor arg missing"; exit 1; }

BASE_DIR="$HOME/.config/blacklayer"
BLACKLAYER_BIN="$BASE_DIR/blacklayer"
STATE_DIR="$BASE_DIR/.blacklayer_state"
STATE_FILE="$STATE_DIR/$MONITOR"

WAYBAR_BIN="/usr/bin/waybar"
WAYBAR_CONFIG_DIR="$HOME/.config/waybar"
WAYBAR_CONFIG="$WAYBAR_CONFIG_DIR/config-$MONITOR"

while true; do
    sleep "$POLL_INTERVAL"

    JSON="$(hyprctl -j monitors 2>/dev/null)"
    echo "$JSON" | jq empty >/dev/null 2>&1 || continue

    FOCUSED=$(echo "$JSON" | jq -r ".[] | select(.name==\"$MONITOR\") | .focused")
    if [ "$FOCUSED" = "true" ]; then
        # Blacklayer kapat
        pkill -f "$BLACKLAYER_BIN $MONITOR" >/dev/null 2>&1
        echo "false" > "$STATE_FILE"

        # Waybar tekrar aç
        if [ -f "$WAYBAR_CONFIG" ]; then
            "$WAYBAR_BIN" -c "$WAYBAR_CONFIG" >/dev/null 2>&1 &
        fi

        exit 0
    fi
done
