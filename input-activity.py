#!/usr/bin/env python3

import os
import select
import signal
import subprocess
import sys
import time

import evdev
from evdev import ecodes


BASE_DIR = os.path.expanduser("~/.config/blacklayer")

ACTIVITY_FILE = os.path.join(BASE_DIR, ".input_activity")
MAIN_MONITOR_FILE = os.path.join(BASE_DIR, ".input_main_monitor")

STATE_DIR = os.path.join(BASE_DIR, ".blacklayer_state")
PID_DIR = os.path.join(STATE_DIR, "pids")

BLACKLAYER_BIN = os.path.join(BASE_DIR, "blacklayer")

WAYBAR_BIN = "/usr/bin/waybar"
WAYBAR_CONFIG_DIR = os.path.expanduser("~/.config/waybar")

running = True


def signal_handler(signum, frame):
    global running
    running = False


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def update_activity():
    os.makedirs(BASE_DIR, exist_ok=True)

    with open(ACTIVITY_FILE, "w") as f:
        f.write(str(time.time()))


def monitor_pid_file(monitor):
    safe = (
        monitor
        .replace("/", "_")
        .replace(":", "_")
        .replace(" ", "_")
    )

    return os.path.join(PID_DIR, safe + ".pid")


def is_blacklayer_process(pid, monitor):
    try:
        exe = os.readlink(f"/proc/{pid}/exe")

        if os.path.realpath(exe) == os.path.realpath(BLACKLAYER_BIN):
            return True
    except Exception:
        pass

    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cmdline = f.read().replace(b"\0", b" ").decode(
                errors="ignore"
            )

        if BLACKLAYER_BIN in cmdline:
            return True

        if f"{BLACKLAYER_BIN} {monitor}" in cmdline:
            return True

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

    # NEVER create a duplicate Waybar.
    try:
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue

            cmdline_file = f"/proc/{pid}/cmdline"

            try:
                with open(cmdline_file, "rb") as f:
                    cmdline = f.read().replace(
                        b"\0", b" "
                    ).decode(errors="ignore")

                if "waybar" in cmdline and config in cmdline:
                    return

            except Exception:
                continue

    except Exception:
        pass

    subprocess.Popen(
        [WAYBAR_BIN, "-c", config],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def close_blacklayer_on_activity():
    if not os.path.isfile(MAIN_MONITOR_FILE):
        return

    try:
        with open(MAIN_MONITOR_FILE) as f:
            monitor = f.read().strip()
    except Exception:
        return

    if not monitor:
        return

    pid_file = monitor_pid_file(monitor)

    if not os.path.isfile(pid_file):
        return

    try:
        with open(pid_file) as f:
            lines = [x.strip() for x in f.readlines()]

        pid = int(lines[0])

        stored_monitor = lines[1] if len(lines) > 1 else ""

    except Exception:
        return

    if stored_monitor != monitor:
        return

    try:
        os.kill(pid, 0)
    except OSError:
        try:
            os.remove(pid_file)
        except FileNotFoundError:
            pass
        return

    if not is_blacklayer_process(pid, monitor):
        return

    killed = False

    try:
        os.kill(pid, signal.SIGTERM)

        for _ in range(20):
            try:
                os.kill(pid, 0)
                time.sleep(0.05)
            except OSError:
                killed = True
                break

        if not killed:
            try:
                os.kill(pid, signal.SIGKILL)
                killed = True
            except OSError:
                pass

    except OSError:
        pass

    try:
        os.remove(pid_file)
    except FileNotFoundError:
        pass

    # IMPORTANT:
    # Waybar is restored ONLY when Blacklayer was actually killed.
    if killed:
        restore_waybar(monitor)


def register_activity():
    update_activity()
    close_blacklayer_on_activity()


def find_devices():
    devices = []

    for path in evdev.list_devices():
        try:
            device = evdev.InputDevice(path)
            caps = device.capabilities()

            if ecodes.EV_KEY in caps or ecodes.EV_REL in caps:
                devices.append(device)

        except Exception:
            continue

    return devices


def main():
    devices = find_devices()

    if not devices:
        print("No input devices found.", file=sys.stderr)

    while running:
        if not devices:
            time.sleep(2)
            devices = find_devices()
            continue

        try:
            r, _, _ = select.select(devices, [], [], 1.0)

        except Exception:
            devices = find_devices()
            continue

        for device in r:

            try:
                for event in device.read():

                    if event.type == ecodes.EV_KEY:
                        register_activity()

                    elif event.type == ecodes.EV_REL:
                        if event.code in (
                            ecodes.REL_X,
                            ecodes.REL_Y,
                            ecodes.REL_WHEEL,
                            ecodes.REL_HWHEEL,
                        ):
                            register_activity()

            except Exception:
                continue


if __name__ == "__main__":
    main()
