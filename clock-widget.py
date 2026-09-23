#!/usr/bin/env python3
import os
import sys
import signal
import traceback
import ctypes.util
from datetime import datetime

LOG = "/tmp/blacklayer-clock.log"


def log(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    except Exception:
        pass


# gtk4-layer-shell MUST be loaded before libwayland-client.
# Python/GTK can load Wayland first, so preload the library and re-exec once.
# This is the exact situation reported by the warning from your system.
if not os.environ.get("BLACKLAYER_LAYER_SHELL_PRELOADED"):
    lib = ctypes.util.find_library("gtk4-layer-shell")
    if lib:
        os.environ["LD_PRELOAD"] = (
            lib + " " + os.environ.get("LD_PRELOAD", "")
        ).strip()
        os.environ["BLACKLAYER_LAYER_SHELL_PRELOADED"] = "1"
        os.execv(sys.executable, [sys.executable] + sys.argv)


try:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Gtk4LayerShell", "1.0")

    from gi.repository import Gtk, GLib, Gio, Gtk4LayerShell

except Exception:
    log("IMPORT ERROR:")
    log(traceback.format_exc())
    raise


class ClockWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)

        log("creating layer window")

        self.set_decorated(False)
        # Let layer-shell/compositor control the surface size.
        # Do not force a tiny GTK window here; with four opposite anchors
        # the layer surface itself must determine the full output size.

        # Must happen before the window is realized/presented.
        Gtk4LayerShell.init_for_window(self)

        # Bind this source instance to the exact monitor whose inactivity
        # timer fired. The worker supplies the Hyprland monitor name.
        target_monitor = os.environ.get("BLACKLAYER_MONITOR", "").strip()
        if target_monitor:
            try:
                display = self.get_display()
                monitors = display.get_monitors() if display else None
                if monitors:
                    for i in range(monitors.get_n_items()):
                        monitor = monitors.get_item(i)
                        try:
                            connector = monitor.get_connector()
                        except Exception:
                            connector = None
                        if connector == target_monitor:
                            Gtk4LayerShell.set_monitor(self, monitor)
                            log(f"bound layer surface to monitor={target_monitor}")
                            break
            except Exception:
                log("monitor binding failed:")
                log(traceback.format_exc())

        Gtk4LayerShell.set_layer(
            self,
            Gtk4LayerShell.Layer.OVERLAY
        )
        # Give this surface its own namespace so any unrelated Hyprland
        # layerrule for the generic gtk4-layer-shell namespace cannot resize it.
        Gtk4LayerShell.set_namespace(self, "blacklayer-clock")
        Gtk4LayerShell.set_exclusive_zone(self, 0)

        # Your installed Gtk4LayerShell exposes keyboard MODE,
        # not the old set_keyboard_interactivity() function.
        Gtk4LayerShell.set_keyboard_mode(
            self,
            Gtk4LayerShell.KeyboardMode.NONE
        )

        # Fill the complete monitor.
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, True)

        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.TOP, 0)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 0)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.LEFT, 0)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.RIGHT, 0)

        css = Gtk.CssProvider()
        css.load_from_data(b"""
        window {
            background: transparent;
        }

        .fullscreen-bg {
            background: rgba(0, 0, 0, 0.32);
            background-color: rgba(0, 0, 0, 0.32);
        }

        .clock-card {
            background-color: rgba(20, 20, 24, 0.72);
            border-radius: 18px;
            padding: 18px 28px;
        }

        .time {
            color: #ffffff;
            font-size: 42px;
            font-weight: 700;
        }

        .date {
            color: #ffffff;
            font-size: 15px;
        }
        """)

        display = self.get_display()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                css,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        # Full-surface root. The card is centered inside this surface.
        root = Gtk.Overlay()
        root.add_css_class("fullscreen-bg")
        root.set_hexpand(True)
        root.set_vexpand(True)

        card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=3
        )
        card.add_css_class("clock-card")

        self.time_label = Gtk.Label()
        self.time_label.add_css_class("time")

        self.date_label = Gtk.Label()
        self.date_label.add_css_class("date")

        card.append(self.time_label)
        card.append(self.date_label)

        card.set_halign(Gtk.Align.CENTER)
        card.set_valign(Gtk.Align.CENTER)
        root.set_child(card)
        self.set_child(root)

        self.update_clock()
        GLib.timeout_add(1000, self.update_clock)

        log("layer window created")

    def update_clock(self):
        now = datetime.now()
        self.time_label.set_text(now.strftime("%H:%M:%S"))
        self.date_label.set_text(now.strftime("%d.%m.%Y"))
        return True


class ClockApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.blacklayer.ClockWidget",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )

    def do_activate(self):
        log("activate()")

        window = ClockWindow(self)
        window.present()

        log("window.present()")


app = ClockApp()


def handle_signal(signum, frame):
    log(f"signal={signum}")
    app.quit()


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


try:
    log(
        "starting clock-widget "
        f"WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY')} "
        f"XDG_RUNTIME_DIR={os.environ.get('XDG_RUNTIME_DIR')} "
        f"preload={os.environ.get('LD_PRELOAD', '')}"
    )

    status = app.run(sys.argv)

    log(f"GTK exited with status={status}")
    sys.exit(status)

except Exception:
    log("RUNTIME ERROR:")
    log(traceback.format_exc())
    raise
