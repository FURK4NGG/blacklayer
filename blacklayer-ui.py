#!/usr/bin/env python3
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib


BASE_DIR = Path.home() / ".config" / "blacklayer"
CONF_FILE = BASE_DIR / "blacklayer.conf"
CALL_SCRIPT = BASE_DIR / "call-blacklayer.sh"

DEFAULT = {
    "run_blacklayer": "true",
    "run_lock": "true",
    "run_sleep": "true",
    "LOOP_INTERVAL": "60",
    "COUNT_THRESHOLD": "5",
    "EVENT_POLL_INTERVAL": "3",
    "USE_INPUT_ACTIVITY": "true",
    "resource": "",
    "dark_mode": "true",
}


class BlacklayerUI(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="me.furk4ngg.BlacklayerUI",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.connect("activate", self.on_activate)

    def on_activate(self, _app):
        if hasattr(self, "window"):
            self.window.present()
            return

        self.window = Adw.ApplicationWindow(
            application=self,
            title="Blacklayer Settings",
        )
        self.window.set_default_size(680, 820)
        self.monitor_count = 0
        self.monitor_config_value = True
        self.previous_monitor_count = 0

        self.build_ui()
        self.load_config()
        self.window.present()

    def build_ui(self):
        toolbar = Adw.ToolbarView()

        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Blacklayer Settings"))

        # Dark mode: top-right, default ON.
        dark_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6,
        )
        dark_box.append(Gtk.Label(label="Dark"))

        self.dark_mode = Gtk.Switch()
        self.dark_mode.set_valign(Gtk.Align.CENTER)
        self.dark_mode.set_tooltip_text("Dark mode")
        self.dark_mode.connect(
            "notify::active",
            self.on_dark_mode_changed,
        )

        dark_box.append(self.dark_mode)
        header.pack_end(dark_box)
        toolbar.add_top_bar(header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
        )
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)

        # -------------------------------------------------
        # Detected monitors
        # -------------------------------------------------

        self.monitor_group = Adw.PreferencesGroup(
            title="Detected Monitors",
            description="Monitors currently reported by Hyprland.",
        )

        monitor_header = Adw.ActionRow(
            title="Monitor list",
            subtitle="Refresh after connecting or disconnecting a display.",
        )

        refresh_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_button.set_valign(Gtk.Align.CENTER)
        refresh_button.set_tooltip_text("Refresh monitor list")
        refresh_button.connect("clicked", self.on_refresh_monitors)
        monitor_header.add_suffix(refresh_button)

        self.monitor_group.add(monitor_header)

        self.monitor_list = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )
        self.monitor_group.add(self.monitor_list)

        content.append(self.monitor_group)

        # -------------------------------------------------
        # Blacklayer
        # -------------------------------------------------

        blacklayer_group = Adw.PreferencesGroup()
        blacklayer_group.set_title("Blacklayer")

        self.run_blacklayer = Adw.SwitchRow(
            title="Enable Blacklayer",
            subtitle="Enable per-monitor blacklayer.",
        )

        self.run_lock = Adw.SwitchRow(
            title="Lock session",
            subtitle="Lock the session after inactivity.",
        )

        self.run_sleep = Adw.SwitchRow(
            title="Turn off displays",
            subtitle="Turn off displays after longer inactivity.",
        )

        self.use_input_activity = Adw.SwitchRow(
            title="Use input activity with a single monitor",
            subtitle=(
                "When only one monitor is connected, use keyboard and "
                "mouse activity instead of monitor focus."
            ),
        )
        self.use_input_activity.connect(
            "notify::active",
            self.on_input_activity_switch_changed,
        )

        blacklayer_group.add(self.run_blacklayer)
        blacklayer_group.add(self.run_lock)
        blacklayer_group.add(self.run_sleep)
        blacklayer_group.add(self.use_input_activity)

        content.append(blacklayer_group)

        # -------------------------------------------------
        # Timing
        # -------------------------------------------------

        timing_group = Adw.PreferencesGroup()
        timing_group.set_title("Timing")

        self.loop_row, self.loop_spin = self.make_spin_row(
            "Main loop interval",
            "Main worker loop interval in seconds.",
            1,
            86400,
        )

        self.threshold_row, self.threshold_spin = self.make_spin_row(
            "Inactivity threshold",
            "Number of inactivity intervals before activation.",
            1,
            100000,
        )

        self.poll_row, self.poll_spin = self.make_spin_row(
            "Event polling interval",
            "Event-driven polling interval in seconds.",
            1,
            3600,
        )

        timing_group.add(self.loop_row)
        timing_group.add(self.threshold_row)
        timing_group.add(self.poll_row)

        content.append(timing_group)

        # -------------------------------------------------
        # Resource
        # -------------------------------------------------

        resource_group = Adw.PreferencesGroup(
            title="Background resource",
            description="PNG, JPG/JPEG or animated GIF.",
        )

        resource_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        resource_box.set_margin_top(8)
        resource_box.set_margin_bottom(8)
        resource_box.set_margin_start(12)
        resource_box.set_margin_end(12)

        self.resource_entry = Gtk.Entry()
        self.resource_entry.set_hexpand(True)
        self.resource_entry.set_placeholder_text(
            "/home/user/Resimler/wallpapers/background.gif"
        )

        browse_button = Gtk.Button(label="Browse…")
        browse_button.connect("clicked", self.on_browse)

        resource_box.append(self.resource_entry)
        resource_box.append(browse_button)

        resource_group.add(resource_box)
        content.append(resource_group)

        # -------------------------------------------------
        # Save
        # -------------------------------------------------

        self.save_button = Gtk.Button(label="Save Settings")
        self.save_button.set_size_request(-1, 46)
        self.save_button.add_css_class("suggested-action")
        self.save_button.connect("clicked", self.save_config)

        content.append(self.save_button)

        self.status_label = Gtk.Label()
        self.status_label.set_xalign(0.5)
        self.status_label.set_wrap(True)

        content.append(self.status_label)

        # -------------------------------------------------
        # Run / Stop
        # -------------------------------------------------

        control_group = Adw.PreferencesGroup(
            title="Blacklayer Control",
            description=(
                "Runs the existing call-blacklayer.sh script. "
                "The repository's existing toggle behavior is preserved."
            ),
        )

        control_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )
        control_box.set_margin_top(8)
        control_box.set_margin_bottom(8)
        control_box.set_margin_start(12)
        control_box.set_margin_end(12)

        self.run_button = Gtk.Button(
            label="Run / Stop Blacklayer"
        )
        self.run_button.set_size_request(-1, 52)
        self.run_button.add_css_class("suggested-action")
        self.run_button.connect(
            "clicked",
            self.run_blacklayer_script,
        )

        control_box.append(self.run_button)
        control_group.add(control_box)

        content.append(control_group)

        scroll.set_child(content)
        toolbar.set_content(scroll)
        self.window.set_content(toolbar)

    def make_spin_row(self, title, subtitle, minimum, maximum):
        row = Adw.ActionRow(
            title=title,
            subtitle=subtitle,
        )

        adjustment = Gtk.Adjustment(
            value=minimum,
            lower=minimum,
            upper=maximum,
            step_increment=1,
            page_increment=10,
            page_size=0,
        )

        spin = Gtk.SpinButton.new(
            adjustment,
            1,
            0,
        )
        spin.set_width_chars(8)
        spin.set_valign(Gtk.Align.CENTER)

        row.add_suffix(spin)
        row.set_activatable_widget(spin)

        return row, spin

    # -------------------------------------------------
    # Hyprland monitor detection
    # -------------------------------------------------

    def get_hyprland_monitors(self):
        try:
            result = subprocess.run(
                ["hyprctl", "-j", "monitors"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )

            if result.returncode != 0:
                return []

            data = json.loads(result.stdout)
            return data if isinstance(data, list) else []
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return []

    def refresh_monitors(self, _button=None):
        monitors = self.get_hyprland_monitors()
        self.monitor_count = len(monitors)

        while child := self.monitor_list.get_first_child():
            self.monitor_list.remove(child)

        if not monitors:
            row = Adw.ActionRow(
                title="No monitors detected",
                subtitle="hyprctl did not report any Hyprland monitors.",
            )
            self.monitor_list.append(row)
            self.use_input_activity.set_sensitive(False)
            self.use_input_activity.set_subtitle(
                "No monitor detected. Refresh after Hyprland reports a monitor."
            )
            self.previous_monitor_count = 0
            return

        for monitor in monitors:
            name = str(monitor.get("name", "Unknown"))
            width = monitor.get("width", "?")
            height = monitor.get("height", "?")
            refresh = monitor.get("refreshRate", "?")

            try:
                refresh_text = f"{float(refresh):.2f} Hz"
            except (TypeError, ValueError):
                refresh_text = f"{refresh} Hz"

            focused = bool(monitor.get("focused", False))
            main_text = "MAIN / focused" if focused else "not focused"

            row = Adw.ActionRow(
                title=name,
                subtitle=f"{width} × {height}  •  {refresh_text}  •  {main_text}",
            )
            self.monitor_list.append(row)

        if self.monitor_count == 1:
            # Single-monitor mode is mandatory. The user cannot disable it.
            self.use_input_activity.set_active(True)
            self.use_input_activity.set_sensitive(False)
            self.use_input_activity.set_subtitle(
                "Required because Hyprland currently reports exactly one monitor."
            )
        else:
            # With 2+ monitors the user controls the input-activity mode.
            # If we just transitioned from forced single-monitor mode, restore
            # the saved config value. Otherwise keep the user's current switch.
            self.use_input_activity.set_sensitive(True)
            if self.previous_monitor_count == 1:
                self.use_input_activity.set_active(
                    self.monitor_config_value
                )
            else:
                self.monitor_config_value = (
                    self.use_input_activity.get_active()
                )

            self.use_input_activity.set_subtitle(
                "When enabled, only the focused MAIN monitor uses input activity; "
                "other monitors are ignored."
            )

        self.previous_monitor_count = self.monitor_count

    def on_input_activity_switch_changed(self, switch, _param):
        if self.monitor_count >= 2 and switch.get_sensitive():
            self.monitor_config_value = switch.get_active()

    def on_refresh_monitors(self, _button):
        self.refresh_monitors()
        self.set_status(
            f"Detected {self.monitor_count} monitor(s).",
            error=False,
        )

    # -------------------------------------------------
    # Config read
    # -------------------------------------------------

    def read_config(self):
        config = DEFAULT.copy()

        if not CONF_FILE.exists():
            return config

        try:
            text = CONF_FILE.read_text(encoding="utf-8")
        except OSError:
            return config

        for line in text.splitlines():
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            match = re.match(
                r"^([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$",
                line,
            )

            if not match:
                continue

            key, value = match.groups()
            value = value.strip()

            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in ("'", '"')
            ):
                value = value[1:-1]

            if key in config:
                config[key] = value

        return config

    def load_config(self):
        config = self.read_config()

        self.run_blacklayer.set_active(
            config["run_blacklayer"].lower() == "true"
        )

        self.run_lock.set_active(
            config["run_lock"].lower() == "true"
        )

        self.run_sleep.set_active(
            config["run_sleep"].lower() == "true"
        )

        self.monitor_config_value = (
            config["USE_INPUT_ACTIVITY"].lower() == "true"
        )
        self.use_input_activity.set_active(
            self.monitor_config_value
        )
        self.refresh_monitors()

        try:
            self.loop_spin.set_value(
                max(1, int(config["LOOP_INTERVAL"]))
            )
        except ValueError:
            self.loop_spin.set_value(60)

        try:
            self.threshold_spin.set_value(
                max(1, int(config["COUNT_THRESHOLD"]))
            )
        except ValueError:
            self.threshold_spin.set_value(5)

        try:
            self.poll_spin.set_value(
                max(1, int(config["EVENT_POLL_INTERVAL"]))
            )
        except ValueError:
            self.poll_spin.set_value(3)

        self.resource_entry.set_text(config["resource"])

        self.dark_mode.set_active(
            config["dark_mode"].lower() != "false"
        )
        self.apply_dark_mode(
            self.dark_mode.get_active()
        )

        self.set_status(
            f"Loaded: {CONF_FILE}",
            error=False,
        )

    # -------------------------------------------------
    # Config write
    # -------------------------------------------------

    def get_values(self):
        return {
            "run_blacklayer": (
                "true"
                if self.run_blacklayer.get_active()
                else "false"
            ),
            "run_lock": (
                "true"
                if self.run_lock.get_active()
                else "false"
            ),
            "run_sleep": (
                "true"
                if self.run_sleep.get_active()
                else "false"
            ),
            "LOOP_INTERVAL": str(
                self.loop_spin.get_value_as_int()
            ),
            "COUNT_THRESHOLD": str(
                self.threshold_spin.get_value_as_int()
            ),
            "EVENT_POLL_INTERVAL": str(
                self.poll_spin.get_value_as_int()
            ),
            # A single detected monitor always forces input activity.
            "USE_INPUT_ACTIVITY": (
                "true"
                if self.monitor_count == 1
                else (
                    "true"
                    if self.use_input_activity.get_active()
                    else "false"
                )
            ),
            "resource": self.resource_entry.get_text().strip(),
            "dark_mode": (
                "true"
                if self.dark_mode.get_active()
                else "false"
            ),
        }

    def make_config_text(self):
        values = self.get_values()

        existing = ""

        if CONF_FILE.exists():
            try:
                existing = CONF_FILE.read_text(
                    encoding="utf-8"
                )
            except OSError:
                existing = ""

        if not existing.strip():
            return (
                "# Blacklayer configuration\n\n"
                f"run_blacklayer={values['run_blacklayer']}\n"
                f"run_lock={values['run_lock']}\n"
                f"run_sleep={values['run_sleep']}\n\n"
                f"LOOP_INTERVAL={values['LOOP_INTERVAL']}\n"
                f"EVENT_POLL_INTERVAL={values['EVENT_POLL_INTERVAL']}\n"
                f"COUNT_THRESHOLD={values['COUNT_THRESHOLD']}\n"
                f"USE_INPUT_ACTIVITY={values['USE_INPUT_ACTIVITY']}\n\n"
                f"resource={values['resource']}\n\n"
                f"dark_mode={values['dark_mode']}\n"
            )

        output = []
        found = set()

        for line in existing.splitlines():
            stripped = line.strip()

            match = re.match(
                r"^([A-Za-z_][A-Za-z0-9_]*)\s*=",
                stripped,
            )

            key = match.group(1) if match else None

            if key in values:
                output.append(
                    f"{key}={values[key]}"
                )
                found.add(key)
            else:
                output.append(line)

        missing = [
            key for key in values
            if key not in found
        ]

        if missing:
            output.append("")

            for key in missing:
                output.append(
                    f"{key}={values[key]}"
                )

        return "\n".join(output).rstrip() + "\n"

    def save_config(self, _button=None):
        try:
            BASE_DIR.mkdir(
                parents=True,
                exist_ok=True,
            )

            data = self.make_config_text()

            fd, tmp_path = tempfile.mkstemp(
                prefix=".blacklayer.conf.",
                dir=str(BASE_DIR),
                text=True,
            )

            try:
                with os.fdopen(
                    fd,
                    "w",
                    encoding="utf-8",
                ) as file:
                    file.write(data)
                    file.flush()
                    os.fsync(file.fileno())

                os.replace(
                    tmp_path,
                    CONF_FILE,
                )

            finally:
                try:
                    os.unlink(tmp_path)
                except FileNotFoundError:
                    pass

            self.set_status(
                "Settings saved.",
                error=False,
            )

        except Exception as exc:
            self.set_status(
                f"Could not save settings: {exc}",
                error=True,
            )

    # -------------------------------------------------
    # Resource picker
    # -------------------------------------------------

    def on_browse(self, _button):
        dialog = Gtk.FileDialog(
            title="Select background resource"
        )

        file_filter = Gtk.FileFilter()
        file_filter.set_name(
            "Images (PNG, JPG, JPEG, GIF)"
        )

        for pattern in (
            "*.png", "*.PNG",
            "*.jpg", "*.JPG",
            "*.jpeg", "*.JPEG",
            "*.gif", "*.GIF",
        ):
            file_filter.add_pattern(pattern)

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(file_filter)

        dialog.set_filters(filters)

        dialog.open(
            self.window,
            None,
            self.on_file_selected,
        )

    def on_file_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return

        if file:
            path = file.get_path()

            if path:
                self.resource_entry.set_text(path)

    # -------------------------------------------------
    # Run / Stop
    # -------------------------------------------------

    def run_blacklayer_script(self, _button):
        if not CALL_SCRIPT.exists():
            self.set_status(
                f"Not found: {CALL_SCRIPT}",
                error=True,
            )
            return

        if not os.access(CALL_SCRIPT, os.X_OK):
            self.set_status(
                "call-blacklayer.sh is not executable.\n"
                f"Run: chmod +x {CALL_SCRIPT}",
                error=True,
            )
            return

        # Save first so call-blacklayer.sh receives the
        # settings currently shown by the UI.
        self.save_config()

        try:
            subprocess.Popen(
                ["bash", str(CALL_SCRIPT)],
                cwd=str(BASE_DIR),
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            self.set_status(
                "call-blacklayer.sh executed.",
                error=False,
            )

        except Exception as exc:
            self.set_status(
                f"Could not execute call-blacklayer.sh: {exc}",
                error=True,
            )

    # -------------------------------------------------
    # Dark mode
    # -------------------------------------------------

    def on_dark_mode_changed(self, switch, _param):
        self.apply_dark_mode(
            switch.get_active()
        )

    def apply_dark_mode(self, enabled):
        manager = Adw.StyleManager.get_default()

        if enabled:
            manager.set_color_scheme(
                Adw.ColorScheme.FORCE_DARK
            )
        else:
            manager.set_color_scheme(
                Adw.ColorScheme.FORCE_LIGHT
            )

    # -------------------------------------------------
    # Status
    # -------------------------------------------------

    def set_status(self, text, error=False):
        self.status_label.set_text(text)
        self.status_label.remove_css_class("error")

        if error:
            self.status_label.add_css_class("error")


def main():
    app = BlacklayerUI()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
