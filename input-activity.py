#!/usr/bin/env python3

import os
import select
import subprocess
import sys
import time

from evdev import InputDevice, list_devices, ecodes

BASE_DIR = os.path.expanduser("~/.config/blacklayer")
ACTIVITY_FILE = os.path.join(BASE_DIR, ".input_activity")
MAIN_MONITOR_FILE = os.path.join(BASE_DIR, ".input_main_monitor")
STATE_DIR = os.path.join(BASE_DIR, ".blacklayer_state")
BLACKLAYER_BIN = os.path.join(BASE_DIR, "blacklayer")


def update_activity():
    try:
        with open(ACTIVITY_FILE, "w") as f:
            f.write(f"{time.time():.6f}\n")
    except Exception as e:
        print(f"[ERROR] activity: {e}", file=sys.stderr, flush=True)


def close_blacklayer_on_activity():
    """Close Blacklayer immediately when input arrives in input-activity mode."""
    try:
        with open(MAIN_MONITOR_FILE, "r") as f:
            monitor = f.read().strip()
    except OSError:
        return

    if not monitor:
        return

    state_file = os.path.join(STATE_DIR, monitor)

    try:
        with open(state_file, "r") as f:
            working = f.read().strip()
    except OSError:
        working = "false"

    if working != "true":
        return

    # Use the same process matching convention as the existing repository.
    try:
        subprocess.run(
            ["pkill", "-f", "--", f"{BLACKLAYER_BIN} {monitor}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return

    try:
        with open(state_file, "w") as f:
            f.write("false\n")
    except OSError:
        pass


def register_activity():
    update_activity()
    close_blacklayer_on_activity()


def find_devices():
    devices = []

    for path in list_devices():
        try:
            device = InputDevice(path)
            capabilities = device.capabilities()

            if (
                ecodes.EV_KEY in capabilities
                or ecodes.EV_REL in capabilities
            ):
                devices.append(device)
                print(
                    f"[INPUT] {path} -> {device.name}",
                    flush=True,
                )

        except PermissionError as e:
            print(
                f"[PERMISSION] {path}: {e}",
                file=sys.stderr,
                flush=True,
            )
        except Exception:
            pass

    return devices


def main():
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(STATE_DIR, exist_ok=True)

    print(
        "[Blacklayer] Input activity monitor started",
        flush=True,
    )

    devices = find_devices()

    if not devices:
        print(
            "[ERROR] No input devices found.",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)

    # A freshly started listener always begins with current time. This is
    # important because an old .input_activity file must never trigger
    # Blacklayer immediately after entering input-activity mode.
    update_activity()

    while True:
        try:
            readable, _, _ = select.select(
                devices,
                [],
                [],
                1.0,
            )

            for device in readable:
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

                except BlockingIOError:
                    pass
                except OSError:
                    pass

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(
                f"[ERROR] input loop: {e}",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(1)

    for device in devices:
        try:
            device.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
