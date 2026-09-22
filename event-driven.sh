#!/usr/bin/env bash

# Usage:
# event-driven.sh <MONITOR_NAME> [EVENT_POLL_INTERVAL]

set -u

MONITOR="${1:-}"
EVENT_POLL_INTERVAL="${2:-3}"

if [ -z "$MONITOR" ]; then
    echo "Monitor arg missing"
    exit 1
fi

BASE_DIR="$HOME/.config/blacklayer"

BLACKLAYER_BIN="$BASE_DIR/blacklayer"

STATE_DIR="$BASE_DIR/.blacklayer_state"
STATE_FILE="$STATE_DIR/$MONITOR"

PID_DIR="$STATE_DIR/pids"

WAYBAR_BIN="/usr/bin/waybar"
WAYBAR_CONFIG_DIR="$HOME/.config/waybar"

WAYBAR_CONFIG="$WAYBAR_CONFIG_DIR/config-$MONITOR"

mkdir -p \
    "$STATE_DIR" \
    "$PID_DIR"

# =========================================================
# Safe monitor filename
# =========================================================

SAFE_MONITOR="$(
    printf '%s' "$MONITOR" |
    tr '/: ' '___'
)"

PID_FILE="$PID_DIR/$SAFE_MONITOR.pid"

# =========================================================
# Find Waybar using this monitor config
# =========================================================

find_waybar() {

    [ -x "$WAYBAR_BIN" ] || return 1
    [ -f "$WAYBAR_CONFIG" ] || return 1

    local pid
    local cmdline

    while read -r pid; do

        [ -n "$pid" ] || continue
        [ -r "/proc/$pid/cmdline" ] || continue

        cmdline="$(
            tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true
        )"

        case "$cmdline" in
            *"$WAYBAR_CONFIG"*)
                echo "$pid"
                return 0
                ;;
        esac

    done < <(pgrep -x waybar 2>/dev/null || true)

    return 1
}

# =========================================================
# Restore Waybar
# =========================================================

restore_waybar() {

    [ -f "$WAYBAR_CONFIG" ] || return 0
    [ -x "$WAYBAR_BIN" ] || return 0

    # Always check this monitor immediately before starting.
    if find_waybar >/dev/null 2>&1; then
        return 0
    fi

    "$WAYBAR_BIN" \
        -c "$WAYBAR_CONFIG" \
        >/dev/null 2>&1 &
}

# =========================================================
# Main loop
# =========================================================

while true; do

    sleep "$EVENT_POLL_INTERVAL"

    JSON="$(
        hyprctl -j monitors 2>/dev/null
    )"

    echo "$JSON" |
        jq empty >/dev/null 2>&1 ||
        continue

    FOCUSED="$(
        echo "$JSON" |
        jq -r \
        ".[] | select(.name==\"$MONITOR\") | .focused"
    )"

    if [ "$FOCUSED" = "true" ]; then

        if [ -f "$PID_FILE" ]; then

            PID="$(
                sed -n '1p' "$PID_FILE" 2>/dev/null
            )"

            STORED_MONITOR="$(
                sed -n '2p' "$PID_FILE" 2>/dev/null
            )"

            if [[ "$PID" =~ ^[0-9]+$ ]] &&
               [ "$STORED_MONITOR" = "$MONITOR" ] &&
               kill -0 "$PID" 2>/dev/null; then

                CMDLINE="$(
                    tr '\0' ' ' < "/proc/$PID/cmdline" 2>/dev/null || true
                )"

                case "$CMDLINE" in

                    *"$BLACKLAYER_BIN $MONITOR"|\
                    *"$BLACKLAYER_BIN $MONITOR "*|\
                    *"/bin/bash $BLACKLAYER_BIN $MONITOR"|\
                    *"/bin/bash $BLACKLAYER_BIN $MONITOR "*|\
                    *"/usr/bin/bash $BLACKLAYER_BIN $MONITOR"|\
                    *"/usr/bin/bash $BLACKLAYER_BIN $MONITOR "*)

                        kill "$PID" 2>/dev/null || true

                        for _ in \
                            1 2 3 4 5 \
                            6 7 8 9 10
                        do

                            kill -0 "$PID" 2>/dev/null ||
                                break

                            sleep 0.05
                        done

                        if kill -0 "$PID" 2>/dev/null; then
                            kill -9 "$PID" 2>/dev/null || true
                        fi

                        ;;

                esac
            fi

            rm -f "$PID_FILE"
        fi

        echo "false" > "$STATE_FILE"

        # -------------------------------------------------
        # Restore Waybar ONLY if it is absent.
        # -------------------------------------------------

        restore_waybar

        exit 0
    fi

done
