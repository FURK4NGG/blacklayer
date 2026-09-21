#!/usr/bin/env bash

BASE_DIR="$HOME/.config/blacklayer"
CONF_FILE="$BASE_DIR/blacklayer.conf"
[ -f "$CONF_FILE" ] && source "$CONF_FILE"

# -------------------------
# Config / defaults
# -------------------------
LOOP_INTERVAL="${LOOP_INTERVAL:-60}"
COUNT_THRESHOLD="${COUNT_THRESHOLD:-5}"
WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}"
EVENT_POLL_INTERVAL="${EVENT_POLL_INTERVAL:-3}"
EVENT_DRIVEN="${EVENT_DRIVEN:-$HOME/.config/blacklayer/event-driven.sh}"
USE_INPUT_ACTIVITY="${USE_INPUT_ACTIVITY:-false}"

BLACKLAYER_BIN="$BASE_DIR/blacklayer"
COUNT_FILE="$BASE_DIR/.blacklayer_count"
STATE_DIR="$BASE_DIR/.blacklayer_state"
WAYBAR_BIN="/usr/bin/waybar"
WAYBAR_CONFIG_DIR="$HOME/.config/waybar"

# Input-activity mode files
INPUT_ACTIVITY_FILE="$BASE_DIR/.input_activity"
INPUT_ACTIVITY_PID_FILE="$BASE_DIR/.input_activity.pid"
INPUT_MAIN_MONITOR_FILE="$BASE_DIR/.input_main_monitor"
INPUT_ACTIVITY_SCRIPT="$BASE_DIR/input-activity.py"
INPUT_ACTIVITY_LOG="$BASE_DIR/input-activity.log"

# Runtime state. These are intentionally kept in the worker so that
# switching between modes does not depend on stale files from an older run.
INPUT_MODE_ACTIVE=false
INPUT_MAIN_MONITOR=""

# -------------------------
# Input activity daemon
# -------------------------
stop_input_activity() {
    if [ -f "$INPUT_ACTIVITY_PID_FILE" ]; then
        local pid
        pid="$(cat "$INPUT_ACTIVITY_PID_FILE" 2>/dev/null)"

        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true

            for _ in 1 2 3 4 5; do
                kill -0 "$pid" 2>/dev/null || break
                sleep 0.1
            done

            kill -9 "$pid" 2>/dev/null || true
        fi
    fi

    rm -f "$INPUT_ACTIVITY_PID_FILE"
}

start_input_activity() {
    # The worker owns this listener. Always start a fresh listener when
    # entering input-activity mode so an old timestamp can never trigger
    # Blacklayer immediately after a worker restart/mode switch.
    stop_input_activity
    rm -f "$INPUT_ACTIVITY_FILE"

    if [ ! -f "$INPUT_ACTIVITY_SCRIPT" ]; then
        echo "[Blacklayer] Missing: $INPUT_ACTIVITY_SCRIPT" >&2
        return 1
    fi

    mkdir -p "$BASE_DIR"

    nohup python3 "$INPUT_ACTIVITY_SCRIPT" \
        >> "$INPUT_ACTIVITY_LOG" 2>&1 &

    local pid=$!
    echo "$pid" > "$INPUT_ACTIVITY_PID_FILE"

    # input-activity.py writes the first timestamp on startup.
    for _ in $(seq 1 40); do
        if [ -s "$INPUT_ACTIVITY_FILE" ]; then
            break
        fi
        sleep 0.05
    done

    # Do not allow a missing timestamp to create an immediate activation.
    if [ ! -s "$INPUT_ACTIVITY_FILE" ]; then
        date +%s.%N > "$INPUT_ACTIVITY_FILE"
    fi

    return 0
}

cleanup() {
    stop_input_activity
    rm -f "$INPUT_MAIN_MONITOR_FILE"
}
trap cleanup EXIT
trap 'exit 0' INT TERM

# -------------------------
# Blacklayer helpers
# -------------------------
blacklayer_is_running() {
    local monitor="$1"
    pgrep -f -- "$BLACKLAYER_BIN $monitor" >/dev/null 2>&1
}

stop_blacklayer_for_monitor() {
    local monitor="$1"

    pkill -f -- "$BLACKLAYER_BIN $monitor" 2>/dev/null || true

    local state_file="$STATE_DIR/$monitor"
    echo "false" > "$state_file"
}

reset_other_input_monitors() {
    local main_monitor="$1"
    local json="$2"

    echo "$json" |
    jq -r '.[].name' |
    while read -r monitor_name; do
        [ -z "$monitor_name" ] && continue
        [ "$monitor_name" = "$main_monitor" ] && continue

        # Input-activity mode is strictly single-monitor mode.
        stop_blacklayer_for_monitor "$monitor_name"
    done
}

# -------------------------
# Main worker
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
    echo "$JSON" | jq empty >/dev/null 2>&1 || {
        sleep "$LOOP_INTERVAL"
        continue
    }

    MONITOR_COUNT="$(echo "$JSON" | jq 'length')"

    # =========================================================
    # INPUT-ACTIVITY MODE
    # =========================================================
    # Rule:
    #   1 monitor  -> input activity is ALWAYS forced.
    #   2+ monitors -> input activity follows USE_INPUT_ACTIVITY.
    # =========================================================
    INPUT_MODE=false

    if [ "$MONITOR_COUNT" -eq 1 ]; then
        INPUT_MODE=true
    elif [ "$MONITOR_COUNT" -ge 2 ] && [ "$USE_INPUT_ACTIVITY" = "true" ]; then
        INPUT_MODE=true
    fi

    if [ "$INPUT_MODE" = "true" ]; then
        # Entering input mode starts a fresh listener/timestamp.
        if [ "$INPUT_MODE_ACTIVE" != "true" ]; then
            if ! start_input_activity; then
                sleep "$LOOP_INTERVAL"
                continue
            fi
            INPUT_MODE_ACTIVE=true
            INPUT_MAIN_MONITOR=""
        fi

        # 1 monitor: that monitor is automatically the main monitor.
        # 2+ monitors: focused=true is the main monitor.
        if [ "$MONITOR_COUNT" -eq 1 ]; then
            MAIN_MONITOR="$(echo "$JSON" | jq -r '.[0].name')"
        else
            MAIN_MONITOR="$(echo "$JSON" | jq -r '.[] | select(.focused == true) | .name' | head -n1)"

            # Hyprland normally always has a focused monitor. Keep a safe
            # fallback so the worker does not silently stop if the JSON is
            # temporarily unusual.
            if [ -z "$MAIN_MONITOR" ] || [ "$MAIN_MONITOR" = "null" ]; then
                MAIN_MONITOR="$(echo "$JSON" | jq -r '.[0].name')"
            fi
        fi

        # If the main monitor changes, the old monitor must no longer be
        # allowed to run Blacklayer.
        if [ -n "$INPUT_MAIN_MONITOR" ] && [ "$INPUT_MAIN_MONITOR" != "$MAIN_MONITOR" ]; then
            stop_blacklayer_for_monitor "$INPUT_MAIN_MONITOR"
        fi

        INPUT_MAIN_MONITOR="$MAIN_MONITOR"
        printf '%s\n' "$MAIN_MONITOR" > "$INPUT_MAIN_MONITOR_FILE"

        # Strictly enforce that only MAIN_MONITOR can be used in input mode.
        reset_other_input_monitors "$MAIN_MONITOR" "$JSON"

        STATE_FILE="$STATE_DIR/$MAIN_MONITOR"
        [ ! -f "$STATE_FILE" ] && echo "false" > "$STATE_FILE"

        # If the process disappeared externally, repair stale state.
        ISWORKING="$(<"$STATE_FILE")"
        if [ "$ISWORKING" = "true" ] && ! blacklayer_is_running "$MAIN_MONITOR"; then
            echo "false" > "$STATE_FILE"
            ISWORKING="false"
        fi

        if [ ! -s "$INPUT_ACTIVITY_FILE" ]; then
            date +%s.%N > "$INPUT_ACTIVITY_FILE"
        fi

        LAST_ACTIVITY="$(cat "$INPUT_ACTIVITY_FILE" 2>/dev/null)"
        NOW="$(date +%s.%N)"

        INACTIVE_SECONDS="$(
            awk \
               -v now="$NOW" \
               -v last="$LAST_ACTIVITY" \
               'BEGIN {
                diff = now - last;
                if (diff < 0)
                    diff = 0;
                printf "%.3f", diff;
               }'
        )"

        REQUIRED_SECONDS="$(
            awk \
               -v interval="$LOOP_INTERVAL" \
               -v threshold="$COUNT_THRESHOLD" \
               'BEGIN {
                printf "%.3f", interval * threshold;
               }'
        )"

        SHOULD_ACTIVATE="$(
            awk \
               -v inactive="$INACTIVE_SECONDS" \
               -v required="$REQUIRED_SECONDS" \
               'BEGIN {
                if (inactive >= required)
                    print "true";
                else
                    print "false";
               }'
        )"

        if [ "$SHOULD_ACTIVATE" = "true" ]; then
            if [ "$ISWORKING" = "false" ] && ! blacklayer_is_running "$MAIN_MONITOR"; then
                pkill -f -- "waybar.*$MAIN_MONITOR" 2>/dev/null || true
                "$BLACKLAYER_BIN" "$MAIN_MONITOR" &
                echo "true" > "$STATE_FILE"
            fi
        else
            # Any keyboard/mouse activity updates .input_activity.
            # On the next worker check, Blacklayer is closed.
            if [ "$ISWORKING" = "true" ] || blacklayer_is_running "$MAIN_MONITOR"; then
                stop_blacklayer_for_monitor "$MAIN_MONITOR"
            fi
        fi

    else
        # Leaving input mode: the input daemon belongs only to that mode.
        if [ "$INPUT_MODE_ACTIVE" = "true" ]; then
            stop_input_activity
            INPUT_MODE_ACTIVE=false
            INPUT_MAIN_MONITOR=""
            rm -f "$INPUT_MAIN_MONITOR_FILE"
        fi

        # =====================================================
        # EXISTING REPOSITORY MULTI-MONITOR BEHAVIOR
        # =====================================================
        # This branch intentionally keeps the existing focused/unfocused,
        # COUNT_THRESHOLD and event-driven.sh behavior.
        # =====================================================
        echo "$JSON" |
        jq -r '.[] | .name + " " + (.focused|tostring)' |
        while read -r MONITOR_NAME FOCUSED; do
            STATE_FILE="$STATE_DIR/$MONITOR_NAME"
            [ ! -f "$STATE_FILE" ] && \
                echo "false" > "$STATE_FILE"
            ISWORKING=$(<"$STATE_FILE")
            [ "$FOCUSED" = "true" ] && \
                echo "true" > "$STATE_FILE"
        done

        COUNT=$(<"$COUNT_FILE")
        COUNT=$((COUNT + 1))
        echo "$COUNT" > "$COUNT_FILE"

        if [ "$COUNT" -ge "$COUNT_THRESHOLD" ]; then
            echo "$JSON" |
            jq -r '.[] | .name' |
            while read -r MONITOR_NAME; do
                STATE_FILE="$STATE_DIR/$MONITOR_NAME"
                ISWORKING=$(<"$STATE_FILE")
                if [ "$ISWORKING" = "false" ] &&
                   ! pgrep -f -- "$BLACKLAYER_BIN $MONITOR_NAME" >/dev/null 2>&1; then
                    pkill -f -- "waybar.*$MONITOR_NAME" 2>/dev/null || true
                    "$BLACKLAYER_BIN" "$MONITOR_NAME" &
                    nohup bash \
                       -c "$EVENT_DRIVEN $MONITOR_NAME $EVENT_POLL_INTERVAL" \
                       >/dev/null 2>&1 &
                    echo "true" > "$STATE_FILE"
                fi
            done
            echo "0" > "$COUNT_FILE"
            for STATE in "$STATE_DIR"/*; do
                [ -f "$STATE" ] && echo "false" > "$STATE"
            done
        fi
    fi

    sleep "$LOOP_INTERVAL"
done
