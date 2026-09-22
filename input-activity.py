#!/usr/bin/env python3

import json
import os
import select
import signal
import subprocess
import sys
import time

import evdev
from evdev import ecodes


BASE_DIR = os.path.expanduser("~/.config/blacklayer")

STATE_DIR = os.path.join(
    BASE_DIR,
    ".blacklayer_state"
)

PID_DIR = os.path.join(
    STATE_DIR,
    "pids"
)

GLOBAL_ACTIVITY = os.path.join(
    BASE_DIR,
    ".input_activity"
)

BLACKLAYER_BIN = os.path.join(
    BASE_DIR,
    "blacklayer"
)

WAYBAR_BIN = "/usr/bin/waybar"

WAYBAR_CONFIG_DIR = os.path.expanduser(
    "~/.config/waybar"
)


running = True


# =========================================================
# TARGET MONITOR
# =========================================================

# USE_INPUT_ACTIVITY=true olduğunda worker:
#
# python3 input-activity.py HDMI-A-2
#
# şeklinde çalıştırır.
#
# USE_INPUT_ACTIVITY=false olduğunda argüman yoktur.
#
TARGET_MONITOR = (
    sys.argv[1]
    if len(sys.argv) > 1
    else None
)


# =========================================================
# SIGNAL
# =========================================================

def signal_handler(signum, frame):
    global running
    running = False


signal.signal(
    signal.SIGTERM,
    signal_handler
)

signal.signal(
    signal.SIGINT,
    signal_handler
)


# =========================================================
# FILE HELPERS
# =========================================================

def safe_name(name):

    return (
        name
        .replace("/", "_")
        .replace(":", "_")
        .replace(" ", "_")
    )


def activity_file(monitor):

    return os.path.join(
        BASE_DIR,
        ".input_activity_" +
        safe_name(monitor)
    )


def pid_file(monitor):

    return os.path.join(
        PID_DIR,
        safe_name(monitor) +
        ".pid"
    )


# =========================================================
# HYPRLAND
# =========================================================

def hyprland_monitors():

    try:

        result = subprocess.run(
            [
                "hyprctl",
                "-j",
                "monitors"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2
        )

        return json.loads(
            result.stdout or "[]"
        )

    except Exception:

        return []


def focused_monitor():

    for monitor in hyprland_monitors():

        if monitor.get("focused") is True:

            return monitor.get(
                "name",
                ""
            )

    return ""


def cursor_monitor():

    try:

        result = subprocess.run(
            [
                "hyprctl",
                "cursorpos",
                "-j"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2
        )

        pos = json.loads(
            result.stdout or "{}"
        )

        cx = float(
            pos.get("x", 0)
        )

        cy = float(
            pos.get("y", 0)
        )


        for monitor in hyprland_monitors():

            x = float(
                monitor.get("x", 0)
            )

            y = float(
                monitor.get("y", 0)
            )

            width = float(
                monitor.get("width", 0)
            )

            height = float(
                monitor.get("height", 0)
            )


            if (
                x <= cx < x + width
                and
                y <= cy < y + height
            ):

                return monitor.get(
                    "name",
                    ""
                )

    except Exception:
        pass


    return focused_monitor()


# =========================================================
# ACTIVITY
# =========================================================

def write_activity(monitor):

    if not monitor:
        return


    os.makedirs(
        BASE_DIR,
        exist_ok=True
    )


    timestamp = str(
        time.time()
    )


    # Global activity:
    #
    # lock/sleep reset.
    #
    with open(
        GLOBAL_ACTIVITY,
        "w"
    ) as f:

        f.write(timestamp)


    # Monitor activity:
    #
    # sadece ilgili monitor.
    #
    with open(
        activity_file(monitor),
        "w"
    ) as f:

        f.write(timestamp)


# =========================================================
# PROCESS HELPERS
# =========================================================

def process_cmdline(pid):

    try:

        with open(
            f"/proc/{pid}/cmdline",
            "rb"
        ) as f:

            parts = [
                x
                for x in f.read().split(b"\0")
                if x
            ]


        return [
            x.decode(errors="ignore")
            for x in parts
        ]

    except Exception:

        return []


def process_monitor(pid):

    parts = process_cmdline(pid)

    if len(parts) >= 2:
        return parts[1]

    return ""


# =========================================================
# BLACKLAYER
# =========================================================

def blacklayer_running_for_monitor(
    monitor
):

    target = os.path.realpath(
        BLACKLAYER_BIN
    )


    try:

        entries = os.listdir(
            "/proc"
        )

    except Exception:

        return False


    for entry in entries:

        if not entry.isdigit():
            continue


        pid = int(entry)


        try:

            exe = os.path.realpath(
                f"/proc/{pid}/exe"
            )


            if exe != target:
                continue


            if (
                process_monitor(pid)
                ==
                monitor
            ):

                return True


        except Exception:

            continue


    return False


# =========================================================
# WAYBAR
# =========================================================

def waybar_running_for_monitor(
    monitor
):

    config = os.path.join(
        WAYBAR_CONFIG_DIR,
        f"config-{monitor}"
    )


    if not os.path.isfile(config):
        return False


    try:

        for entry in os.listdir(
            "/proc"
        ):

            if not entry.isdigit():
                continue


            try:

                parts = process_cmdline(
                    int(entry)
                )

                cmdline = " ".join(parts)


                if (
                    "waybar" in cmdline
                    and
                    config in cmdline
                ):

                    return True


            except Exception:

                continue


    except Exception:

        pass


    return False


def restore_waybar(monitor):

    config = os.path.join(
        WAYBAR_CONFIG_DIR,
        f"config-{monitor}"
    )


    if not os.path.isfile(config):
        return


    if not os.path.isfile(WAYBAR_BIN):
        return


    if waybar_running_for_monitor(
        monitor
    ):

        return


    subprocess.Popen(
        [
            WAYBAR_BIN,
            "-c",
            config
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


# =========================================================
# CLOSE BLACKLAYER
# =========================================================

def close_blacklayer(monitor):

    if not monitor:
        return


    target = os.path.realpath(
        BLACKLAYER_BIN
    )

    killed = False


    try:

        entries = os.listdir(
            "/proc"
        )

    except Exception:

        entries = []


    for entry in entries:

        if not entry.isdigit():
            continue


        pid = int(entry)


        try:

            exe = os.path.realpath(
                f"/proc/{pid}/exe"
            )


            if exe != target:
                continue


            if (
                process_monitor(pid)
                != monitor
            ):

                continue


            os.kill(
                pid,
                signal.SIGTERM
            )

            killed = True


        except Exception:

            continue


    try:

        os.remove(
            pid_file(monitor)
        )

    except FileNotFoundError:

        pass


    if killed:

        restore_waybar(
            monitor
        )


# =========================================================
# ACTIVITY EVENT
# =========================================================

def register_activity(kind):

    # =====================================================
    # TRUE
    #
    # Sadece Run'da seçilmiş TARGET_MONITOR.
    # =====================================================

    if TARGET_MONITOR:

        if kind == "mouse":

            monitor = cursor_monitor()

        else:

            monitor = focused_monitor()


        # Başka monitördeki input tamamen yok sayılır.
        if monitor != TARGET_MONITOR:

            return


    # =====================================================
    # FALSE
    #
    # Her monitor bağımsız.
    # =====================================================

    else:

        if kind == "mouse":

            monitor = cursor_monitor()

        else:

            monitor = focused_monitor()


    if not monitor:
        return


    write_activity(
        monitor
    )


    # Sadece input gelen monitorun
    # Blacklayer'ını kapat.
    close_blacklayer(
        monitor
    )


# =========================================================
# DEVICES
# =========================================================

def find_devices():

    devices = []


    for path in evdev.list_devices():

        try:

            device = evdev.InputDevice(
                path
            )


            caps = device.capabilities()


            if (
                ecodes.EV_KEY in caps
                or
                ecodes.EV_REL in caps
            ):

                devices.append(
                    device
                )


        except Exception:

            continue


    return devices


# =========================================================
# MAIN
# =========================================================

def main():

    os.makedirs(
        BASE_DIR,
        exist_ok=True
    )

    os.makedirs(
        STATE_DIR,
        exist_ok=True
    )

    os.makedirs(
        PID_DIR,
        exist_ok=True
    )


    devices = find_devices()


    while running:

        if not devices:

            time.sleep(2)

            devices = find_devices()

            continue


        try:

            readable, _, _ = select.select(
                devices,
                [],
                [],
                1.0
            )


        except Exception:

            devices = find_devices()

            continue


        for device in readable:

            try:

                for event in device.read():

                    # =====================================
                    # KEYBOARD
                    # =====================================

                    if (
                        event.type
                        ==
                        ecodes.EV_KEY
                    ):

                        if event.value in (
                            1,
                            2
                        ):

                            register_activity(
                                "keyboard"
                            )


                    # =====================================
                    # MOUSE
                    # =====================================

                    elif (
                        event.type
                        ==
                        ecodes.EV_REL
                    ):

                        if event.code in (
                            ecodes.REL_X,
                            ecodes.REL_Y,
                            ecodes.REL_WHEEL,
                            ecodes.REL_HWHEEL
                        ):

                            register_activity(
                                "mouse"
                            )


            except Exception:

                continue


if __name__ == "__main__":

    main()
