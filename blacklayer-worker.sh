#!/usr/bin/env bash

set -u

BASE_DIR="$HOME/.config/blacklayer"
CONFIG="$BASE_DIR/blacklayer.conf"

BLACKLAYER_BIN="$BASE_DIR/blacklayer"
INPUT_ACTIVITY="$BASE_DIR/input-activity.py"

STATE_DIR="$BASE_DIR/.blacklayer_state"
PID_DIR="$STATE_DIR/pids"

GLOBAL_ACTIVITY="$BASE_DIR/.input_activity"

WORKER_PID_FILE="$BASE_DIR/blacklayer_worker.pid"
WORKER_LOCK_FILE="$BASE_DIR/.blacklayer_worker.lock"


mkdir -p "$STATE_DIR"
mkdir -p "$PID_DIR"

[ -f "$CONFIG" ] || exit 1

# shellcheck disable=SC1090
source "$CONFIG"


BLACKLAYER_DELAY="${BLACKLAYER_DELAY:-30}"
LOCK_DELAY="${LOCK_DELAY:-50}"
SLEEP_DELAY="${SLEEP_DELAY:-60}"

USE_INPUT_ACTIVITY="${USE_INPUT_ACTIVITY:-true}"

run_blacklayer="${run_blacklayer:-true}"
run_lock="${run_lock:-true}"
run_sleep="${run_sleep:-false}"

LOCK_COMMAND="${LOCK_COMMAND:-none}"
SLEEP_COMMAND="${SLEEP_COMMAND:-none}"

export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}"


# =========================================================
# SINGLE WORKER
# =========================================================

exec 9>"$WORKER_LOCK_FILE"

if ! flock -n 9 2>/dev/null; then
    exit 0
fi

echo "$$" > "$WORKER_PID_FILE"


# =========================================================
# TIME
# =========================================================

now() {
    date +%s
}


# =========================================================
# SAFE NAME
# =========================================================

safe_name() {
    printf '%s' "$1" |
        tr '/: ' '___'
}


# =========================================================
# ACTIVITY FILE
# =========================================================

activity_file() {
    printf '%s/.input_activity_%s\n' \
        "$BASE_DIR" \
        "$(safe_name "$1")"
}


# =========================================================
# PID FILE
# =========================================================

pid_file() {
    printf '%s/%s.pid\n' \
        "$PID_DIR" \
        "$(safe_name "$1")"
}


# =========================================================
# HYPRLAND MONITORS
# =========================================================

get_monitors() {
    hyprctl -j monitors 2>/dev/null |
        jq -r '.[].name' 2>/dev/null
}


monitor_count() {
    get_monitors |
        grep -c . ||
        true
}


focused_monitor() {
    hyprctl -j monitors 2>/dev/null |
        jq -r '.[] | select(.focused == true) | .name' 2>/dev/null |
        head -n1
}


# =========================================================
# WAYBAR
# =========================================================

waybar_running_for_monitor() {

    local monitor="$1"
    local config="$HOME/.config/waybar/config-$monitor"

    [ -f "$config" ] ||
        return 1

    local pid
    local cmdline

    while read -r pid; do

        [ -n "$pid" ] ||
            continue

        [ -r "/proc/$pid/cmdline" ] ||
            continue

        cmdline="$(
            tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null ||
            true
        )"

        case "$cmdline" in

            *"$config"*)
                return 0
                ;;

        esac

    done < <(
        pgrep -x waybar 2>/dev/null ||
        true
    )

    return 1
}


stop_waybar() {

    local monitor="$1"
    local config="$HOME/.config/waybar/config-$monitor"

    [ -f "$config" ] ||
        return 0

    local pid
    local cmdline

    while read -r pid; do

        [ -n "$pid" ] ||
            continue

        [ -r "/proc/$pid/cmdline" ] ||
            continue

        cmdline="$(
            tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null ||
            true
        )"

        case "$cmdline" in

            *"$config"*)

                kill "$pid" 2>/dev/null ||
                    true

                ;;

        esac

    done < <(
        pgrep -x waybar 2>/dev/null ||
        true
    )
}


restore_waybar() {

    local monitor="$1"
    local config="$HOME/.config/waybar/config-$monitor"

    [ -f "$config" ] ||
        return 0

    command -v waybar >/dev/null 2>&1 ||
        return 0

    if waybar_running_for_monitor "$monitor"; then
        return 0
    fi

    waybar \
        -c "$config" \
        >/dev/null 2>&1 &
}


# =========================================================
# BLACKLAYER RUNNING CHECK
# =========================================================

blacklayer_running() {

    local monitor="$1"

    local target
    target="$(
        realpath "$BLACKLAYER_BIN" 2>/dev/null ||
        true
    )"

    [ -n "$target" ] ||
        return 1


    # -----------------------------------------------------
    # PID FILE
    # -----------------------------------------------------

    local file
    file="$(pid_file "$monitor")"

    if [ -f "$file" ]; then

        local pid
        pid="$(
            sed -n '1p' "$file" 2>/dev/null ||
            true
        )"

        if [[ "$pid" =~ ^[0-9]+$ ]] &&
           kill -0 "$pid" 2>/dev/null; then

            local exe
            exe="$(
                realpath "/proc/$pid/exe" 2>/dev/null ||
                true
            )"

            if [ "$exe" = "$target" ]; then
                return 0
            fi

        fi

    fi


    # -----------------------------------------------------
    # PROCESS SCAN
    # -----------------------------------------------------

    local pid
    local exe
    local cmdline

    while read -r pid; do

        [ -n "$pid" ] ||
            continue

        [ -r "/proc/$pid/exe" ] ||
            continue

        exe="$(
            realpath "/proc/$pid/exe" 2>/dev/null ||
            true
        )"

        [ "$exe" = "$target" ] ||
            continue

        [ -r "/proc/$pid/cmdline" ] ||
            continue

        cmdline="$(
            tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null ||
            true
        )"

        case " $cmdline " in

            *" $monitor "*)
                return 0
                ;;

        esac

    done < <(
        pgrep -f "$BLACKLAYER_BIN" 2>/dev/null ||
        true
    )

    return 1
}


# =========================================================
# START BLACKLAYER
# =========================================================

start_blacklayer() {

    local monitor="$1"

    [ "$run_blacklayer" = "true" ] ||
        return 0

    [ -x "$BLACKLAYER_BIN" ] ||
        return 1

    [ -n "$monitor" ] ||
        return 0


    # Aynı monitörde zaten açıksa
    # kesinlikle tekrar açma.
    if blacklayer_running "$monitor"; then
        return 0
    fi


    rm -f "$(pid_file "$monitor")"


    # Sadece hedef monitorun Waybar'ını kapat.
    stop_waybar "$monitor"


    "$BLACKLAYER_BIN" "$monitor" \
        >/dev/null 2>&1 &

    local pid=$!


    {
        echo "$pid"
        echo "$monitor"
    } > "$(pid_file "$monitor")"
}


# =========================================================
# LOCK
# =========================================================

run_lock() {

    [ "$run_lock" = "true" ] ||
        return 0

    [ "$LOCK_COMMAND" != "none" ] ||
        return 0

    [ -n "$LOCK_COMMAND" ] ||
        return 0

    bash -c "$LOCK_COMMAND" \
        >/dev/null 2>&1 &
}


# =========================================================
# SLEEP
# =========================================================

run_sleep() {

    [ "$run_sleep" = "true" ] ||
        return 0

    [ "$SLEEP_COMMAND" != "none" ] ||
        return 0

    [ -n "$SLEEP_COMMAND" ] ||
        return 0

    case "$SLEEP_COMMAND" in

        "systemctl suspend")

            systemctl suspend

            ;;

        "loginctl suspend")

            loginctl suspend

            ;;

        *)

            bash -c "$SLEEP_COMMAND"

            ;;

    esac
}


# =========================================================
# INPUT ACTIVITY
# =========================================================

INPUT_PID=""


start_input_activity() {

    [ -f "$INPUT_ACTIVITY" ] ||
        return 0


    # Eski input watcher'ı kapat.
    while read -r pid; do

        [ -n "$pid" ] ||
            continue

        [ "$pid" = "$$" ] &&
            continue

        kill "$pid" 2>/dev/null ||
            true

    done < <(
        pgrep -f "python3.*input-activity\.py" 2>/dev/null ||
        true
    )


    if [ "$USE_INPUT_ACTIVITY" = "true" ]; then

        # TRUE:
        # Yalnızca TARGET_MONITOR.
        python3 "$INPUT_ACTIVITY" "$TARGET_MONITOR" \
            >/dev/null 2>&1 &

    else

        # FALSE:
        # Tüm monitorler bağımsız.
        python3 "$INPUT_ACTIVITY" \
            >/dev/null 2>&1 &

    fi

    INPUT_PID=$!
}


# =========================================================
# CLEANUP
# =========================================================

cleanup() {

    if [ -n "${INPUT_PID:-}" ]; then

        kill "$INPUT_PID" 2>/dev/null ||
            true

    fi

    rm -f "$WORKER_PID_FILE"
}

trap cleanup EXIT INT TERM


# =========================================================
# NEW RUN SESSION
# =========================================================

START_TIME="$(now)"


# Eski session activity'lerini temizle.
rm -f "$BASE_DIR"/.input_activity* 2>/dev/null ||
    true


# Global başlangıç.
echo "$START_TIME" > "$GLOBAL_ACTIVITY"


MONITORS="$(get_monitors)"

MONITOR_COUNT="$(
    printf '%s\n' "$MONITORS" |
    grep -c . ||
    true
)"


# =========================================================
# MODE
# =========================================================

# Tek monitor varsa Input Activity zorunlu.
if [ "$MONITOR_COUNT" -le 1 ]; then

    USE_INPUT_ACTIVITY=true

fi


TARGET_MONITOR=""


if [ "$USE_INPUT_ACTIVITY" = "true" ]; then

    # =====================================================
    # TRUE
    #
    # Run'a basıldığı andaki focused monitor
    # tek hedef monitor olur.
    # =====================================================

    TARGET_MONITOR="$(focused_monitor)"


    if [ -z "$TARGET_MONITOR" ]; then

        TARGET_MONITOR="$(
            printf '%s\n' "$MONITORS" |
            head -n1
        )"

    fi


    [ -n "$TARGET_MONITOR" ] ||
        exit 0


    # Yalnızca bu monitor için başlangıç zamanı.
    echo "$START_TIME" > \
        "$(activity_file "$TARGET_MONITOR")"


else

    # =====================================================
    # FALSE
    #
    # Her monitor kendi timer'ına sahip.
    # =====================================================

    while read -r monitor; do

        [ -n "$monitor" ] ||
            continue

        echo "$START_TIME" > \
            "$(activity_file "$monitor")"

    done <<EOF
$MONITORS
EOF

fi


# =========================================================
# LOCK / SLEEP STATE
# =========================================================

LAST_GLOBAL_ACTIVITY="$START_TIME"

LOCK_DONE=0
SLEEP_DONE=0


# =========================================================
# START INPUT WATCHER
# =========================================================

start_input_activity


# =========================================================
# MAIN LOOP
# =========================================================

while :; do

    CURRENT="$(now)"


    # =====================================================
    # INPUT ACTIVITY = TRUE
    #
    # SADECE TEK MONITOR
    # =====================================================

    if [ "$USE_INPUT_ACTIVITY" = "true" ]; then

        monitor="$TARGET_MONITOR"

        FILE="$(activity_file "$monitor")"


        if [ ! -f "$FILE" ]; then

            echo "$CURRENT" > "$FILE"

        fi


        ACTIVITY="$(
            awk '{print int($1)}' "$FILE" \
            2>/dev/null ||
            echo "$CURRENT"
        )"


        if ! [[ "$ACTIVITY" =~ ^[0-9]+$ ]]; then

            ACTIVITY="$CURRENT"

        fi


        IDLE=$((CURRENT - ACTIVITY))


        if [ "$run_blacklayer" = "true" ] &&
           [ "$IDLE" -ge "$BLACKLAYER_DELAY" ]; then

            start_blacklayer "$monitor"

        fi


    else

        # =================================================
        # INPUT ACTIVITY = FALSE
        #
        # HER MONITOR BAĞIMSIZ
        # =================================================

        while read -r monitor; do

            [ -n "$monitor" ] ||
                continue


            FILE="$(activity_file "$monitor")"


            if [ ! -f "$FILE" ]; then

                echo "$CURRENT" > "$FILE"

            fi


            ACTIVITY="$(
                awk '{print int($1)}' "$FILE" \
                2>/dev/null ||
                echo "$CURRENT"
            )"


            if ! [[ "$ACTIVITY" =~ ^[0-9]+$ ]]; then

                ACTIVITY="$CURRENT"

            fi


            IDLE=$((CURRENT - ACTIVITY))


            if [ "$run_blacklayer" = "true" ] &&
               [ "$IDLE" -ge "$BLACKLAYER_DELAY" ]; then

                start_blacklayer "$monitor"

            fi

        done < <(
            get_monitors
        )

    fi


    # =====================================================
    # GLOBAL ACTIVITY
    #
    # Lock / sleep.
    # =====================================================

    GLOBAL_TIME="$(
        awk '{print int($1)}' "$GLOBAL_ACTIVITY" \
        2>/dev/null ||
        echo "$START_TIME"
    )"


    if ! [[ "$GLOBAL_TIME" =~ ^[0-9]+$ ]]; then

        GLOBAL_TIME="$START_TIME"

    fi


    # Yeni keyboard/mouse input geldi.
    if [ "$GLOBAL_TIME" -ne "$LAST_GLOBAL_ACTIVITY" ]; then

        LOCK_DONE=0
        SLEEP_DONE=0

        LAST_GLOBAL_ACTIVITY="$GLOBAL_TIME"

    fi


    GLOBAL_IDLE=$((CURRENT - GLOBAL_TIME))


    # =====================================================
    # LOCK
    # =====================================================

    if [ "$run_lock" = "true" ] &&
       [ "$LOCK_COMMAND" != "none" ] &&
       [ "$LOCK_DONE" -eq 0 ] &&
       [ "$GLOBAL_IDLE" -ge "$LOCK_DELAY" ]; then

        run_lock

        LOCK_DONE=1

    fi


    # =====================================================
    # SLEEP
    # =====================================================

    if [ "$run_sleep" = "true" ] &&
       [ "$SLEEP_COMMAND" != "none" ] &&
       [ "$SLEEP_DONE" -eq 0 ] &&
       [ "$GLOBAL_IDLE" -ge "$SLEEP_DELAY" ]; then

        run_sleep

        SLEEP_DONE=1

    fi


    sleep 1

done
