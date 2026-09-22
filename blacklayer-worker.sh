#!/usr/bin/env bash

set -u

BASE_DIR="$HOME/.config/blacklayer"

CONFIG="$BASE_DIR/blacklayer.conf"
BLACKLAYER_BIN="$BASE_DIR/blacklayer"

INPUT_ACTIVITY="$BASE_DIR/input-activity.py"
EVENT_DRIVEN="$BASE_DIR/event-driven.sh"

STATE_DIR="$BASE_DIR/.blacklayer_state"
PID_DIR="$STATE_DIR/pids"

INPUT_FILE="$BASE_DIR/.input_activity"
MAIN_MONITOR_FILE="$BASE_DIR/.input_main_monitor"

WORKER_PID_FILE="$BASE_DIR/blacklayer_worker.pid"

mkdir -p "$STATE_DIR" "$PID_DIR"

[ -f "$CONFIG" ] || exit 1

# shellcheck disable=SC1090
source "$CONFIG"

BLACKLAYER_DELAY="${BLACKLAYER_DELAY:-30}"
LOCK_DELAY="${LOCK_DELAY:-50}"
SLEEP_DELAY="${SLEEP_DELAY:-60}"
EVENT_POLL_INTERVAL="${EVENT_POLL_INTERVAL:-3}"

USE_INPUT_ACTIVITY="${USE_INPUT_ACTIVITY:-true}"
run_blacklayer="${run_blacklayer:-true}"
run_lock="${run_lock:-true}"
run_sleep="${run_sleep:-false}"

LOCK_COMMAND="${LOCK_COMMAND:-none}"
SLEEP_COMMAND="${SLEEP_COMMAND:-none}"

export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}"

echo "$$" > "$WORKER_PID_FILE"

cleanup() {
    rm -f "$WORKER_PID_FILE"

    if [ -n "${INPUT_PID:-}" ]; then
        kill "$INPUT_PID" 2>/dev/null || true
    fi

    if [ -n "${EVENT_PID:-}" ]; then
        kill "$EVENT_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

now() {
    date +%s
}

get_monitors() {
    hyprctl -j monitors 2>/dev/null |
        jq -r '.[].name' 2>/dev/null
}

monitor_count() {
    get_monitors | grep -c . || true
}

focused_monitor() {
    hyprctl -j monitors 2>/dev/null |
        jq -r '.[] | select(.focused == true) | .name' |
        head -n1
}

get_activity() {
    if [ -f "$INPUT_FILE" ]; then
        awk '{print int($1)}' "$INPUT_FILE" 2>/dev/null || echo 0
    else
        echo 0
    fi
}

is_valid_pid() {
    [[ "${1:-}" =~ ^[0-9]+$ ]]
}

blacklayer_pid_file() {
    local monitor="$1"

    local safe
    safe="$(
        printf '%s' "$monitor" |
        tr '/: ' '___'
    )"

    echo "$PID_DIR/$safe.pid"
}

blacklayer_running() {
    local monitor="$1"

    local pid_file
    pid_file="$(blacklayer_pid_file "$monitor")"

    [ -f "$pid_file" ] || return 1

    local pid
    pid="$(sed -n '1p' "$pid_file" 2>/dev/null || true)"

    is_valid_pid "$pid" || return 1

    kill -0 "$pid" 2>/dev/null || return 1

    [ -r "/proc/$pid/cmdline" ] || return 1

    local cmdline
    cmdline="$(
        tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true
    )"

    case "$cmdline" in
        *"$BLACKLAYER_BIN"*)
            return 0
            ;;
    esac

    return 1
}

stop_waybar() {
    local monitor="$1"

    local config="$HOME/.config/waybar/config-$monitor"

    pgrep -x waybar 2>/dev/null |
    while read -r pid; do
        [ -r "/proc/$pid/cmdline" ] || continue

        local cmdline
        cmdline="$(
            tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true
        )"

        case "$cmdline" in
            *"$config"*)
                kill "$pid" 2>/dev/null || true
                ;;
        esac
    done
}

start_blacklayer() {
    local monitor="$1"

    [ "$run_blacklayer" = "true" ] || return 0
    [ -x "$BLACKLAYER_BIN" ] || return 1

    if blacklayer_running "$monitor"; then
        return 0
    fi

    stop_waybar "$monitor"

    printf '%s\n%s\n' "$$" "$monitor" >/dev/null

    "$BLACKLAYER_BIN" "$monitor" &

    local pid=$!

    local pid_file
    pid_file="$(blacklayer_pid_file "$monitor")"

    {
        echo "$pid"
        echo "$monitor"
    } > "$pid_file"

    echo "$monitor" > "$MAIN_MONITOR_FILE"
}

run_lock() {
    [ "$run_lock" = "true" ] || return 0
    [ "$LOCK_COMMAND" != "none" ] || return 0
    [ -n "$LOCK_COMMAND" ] || return 0

    # Do not start multiple lock processes.
    if pgrep -x "$(basename "${LOCK_COMMAND%% *}")" >/dev/null 2>&1; then
        return 0
    fi

    bash -c "$LOCK_COMMAND" >/dev/null 2>&1 &
}

run_sleep() {
    [ "$run_sleep" = "true" ] || return 0
    [ "$SLEEP_COMMAND" != "none" ] || return 0
    [ -n "$SLEEP_COMMAND" ] || return 0

    bash -c "$SLEEP_COMMAND" >/dev/null 2>&1 &
}

start_input_activity() {
    [ -f "$INPUT_ACTIVITY" ] || return 0

    pkill -f "$INPUT_ACTIVITY" 2>/dev/null || true

    python3 "$INPUT_ACTIVITY" >/dev/null 2>&1 &

    INPUT_PID=$!
}

start_event_driven() {
    local monitor="$1"

    [ -f "$EVENT_DRIVEN" ] || return 0

    bash "$EVENT_DRIVEN" "$monitor" "$EVENT_POLL_INTERVAL" \
        >/dev/null 2>&1 &

    EVENT_PID=$!
}

# Make sure an initial activity timestamp exists.
if [ ! -f "$INPUT_FILE" ]; then
    now > "$INPUT_FILE"
fi

LAST_LOCK=0
LAST_SLEEP=0

while true; do

    COUNT="$(monitor_count)"

    if [ "$COUNT" -le 0 ]; then
        sleep 1
        continue
    fi

    if [ "$COUNT" -eq 1 ]; then

        MONITOR="$(get_monitors | head -n1)"

        # Single monitor always uses input activity.
        if [ -z "${INPUT_PID:-}" ] ||
           ! kill -0 "$INPUT_PID" 2>/dev/null; then
            start_input_activity
        fi

    else

        if [ "$USE_INPUT_ACTIVITY" = "true" ]; then

            if [ -z "${INPUT_PID:-}" ] ||
               ! kill -0 "$INPUT_PID" 2>/dev/null; then
                start_input_activity
            fi

        else

            MONITOR="$(focused_monitor)"

            if [ -n "$MONITOR" ]; then
                start_event_driven "$MONITOR"
            fi
        fi
    fi

    ACTIVITY="$(get_activity)"
    CURRENT="$(now)"

    if ! [[ "$ACTIVITY" =~ ^[0-9]+$ ]]; then
        ACTIVITY="$CURRENT"
    fi

    IDLE=$((CURRENT - ACTIVITY))

    MONITOR="$(focused_monitor)"

    if [ -z "$MONITOR" ]; then
        MONITOR="$(get_monitors | head -n1)"
    fi

    # -----------------------------
    # BLACKLAYER
    # -----------------------------

    if [ "$run_blacklayer" = "true" ] &&
       [ "$IDLE" -ge "$BLACKLAYER_DELAY" ] &&
       [ -n "$MONITOR" ]; then

        start_blacklayer "$MONITOR"
    fi

    # -----------------------------
    # LOCK
    # -----------------------------

    if [ "$run_lock" = "true" ] &&
       [ "$LOCK_COMMAND" != "none" ] &&
       [ "$IDLE" -ge "$LOCK_DELAY" ]; then

        if [ "$LAST_LOCK" -eq 0 ]; then
            run_lock
            LAST_LOCK=1
        fi
    fi

    # -----------------------------
    # SLEEP
    # -----------------------------

    if [ "$run_sleep" = "true" ] &&
       [ "$SLEEP_COMMAND" != "none" ] &&
       [ "$IDLE" -ge "$SLEEP_DELAY" ]; then

        if [ "$LAST_SLEEP" -eq 0 ]; then
            run_sleep
            LAST_SLEEP=1
        fi
    fi

    # New activity resets one-shot actions.
    if [ "$IDLE" -lt "$LOCK_DELAY" ]; then
        LAST_LOCK=0
    fi

    if [ "$IDLE" -lt "$SLEEP_DELAY" ]; then
        LAST_SLEEP=0
    fi

    sleep 1
done
