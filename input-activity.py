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


def waybar_running_for_monitor(monitor):
    config = os.path.join(
        WAYBAR_CONFIG_DIR,
        f"config-{monitor}",
    )

    # Exact config check first.
    try:
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue

            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmdline = f.read().replace(
                        b"\0", b" "
                    ).decode(errors="ignore")

                if "waybar" in cmdline and config in cmdline:
                    return True
            except Exception:
                continue
    except Exception:
        pass

    # A Waybar for another monitor does not count. Restoration is always
    # decided independently for this monitor's exact config.
    return False


def restore_waybar(monitor):
    config = os.path.join(
        WAYBAR_CONFIG_DIR,
        f"config-{monitor}",
    )

    if not os.path.isfile(config):
        return

    if not os.path.isfile(WAYBAR_BIN):
        return

    # Always check immediately before starting.
    if waybar_running_for_monitor(monitor):
        return

    subprocess.Popen(
        [WAYBAR_BIN, "-c", config],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def process_monitor(pid):
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            parts = [x for x in f.read().split(b"\0") if x]

        if len(parts) > 1:
            return parts[1].decode(errors="ignore")
    except Exception:
        pass
    return ""


def close_blacklayer_on_activity():
    killed_monitors = []
    target = os.path.realpath(BLACKLAYER_BIN)

    # Scan every Blacklayer process, not only PID files. This guarantees that
    # a second instance with stale/overwritten state is also dismissed.
    try:
        entries = os.listdir("/proc")
    except Exception:
        entries = []

    for entry in entries:
        if not entry.isdigit():
            continue

        pid = int(entry)

        try:
            exe = os.path.realpath(f"/proc/{pid}/exe")
        except Exception:
            continue

        if exe != target:
            continue

        monitor = process_monitor(pid)

        if not is_blacklayer_process(pid, monitor):
            continue

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

        if killed and monitor:
            killed_monitors.append(monitor)

    # Remove stale PID state.
    if os.path.isdir(PID_DIR):
        for name in os.listdir(PID_DIR):
            if name.endswith(".pid"):
                try:
                    os.remove(os.path.join(PID_DIR, name))
                except FileNotFoundError:
                    pass

    # Only restore a monitor's Waybar if a Blacklayer on that monitor was
    # actually killed, and check the target Waybar immediately before launch.
    for monitor in sorted(set(killed_monitors)):
        restore_waybar(monitor)

    try:
        if os.path.exists(MAIN_MONITOR_FILE):
            os.remove(MAIN_MONITOR_FILE)
    except Exception:
        pass


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
