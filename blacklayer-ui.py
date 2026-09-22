#!/usr/bin/env python3

import json
import os
import shutil
import subprocess

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib


BASE_DIR = Path.home() / ".config" / "blacklayer"
CONFIG_FILE = BASE_DIR / "blacklayer.conf"
WORKER = BASE_DIR / "blacklayer-worker.sh"
WORKER_PID = BASE_DIR / "blacklayer_worker.pid"

DEFAULTS = {
    "USE_INPUT_ACTIVITY": "true",
    "run_blacklayer": "true",
    "run_lock": "true",
    "run_sleep": "false",
    "BLACKLAYER_DELAY": "5",
    "EVENT_POLL_INTERVAL": "3",
    "LOCK_DELAY": "10",
    "SLEEP_DELAY": "20",
    "LOCK_COMMAND": "none",
    "SLEEP_COMMAND": "none",
    "resource": "",
    "WAYLAND_DISPLAY": "wayland-1",
    "dark_mode": "true",
}


def command_exists(name):
    return shutil.which(name) is not None


def shell_output(args):
    try:
        p = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
            check=False,
        )
        return p.stdout
    except Exception:
        return ""


def get_monitors():
    try:
        raw = shell_output(["hyprctl", "-j", "monitors"])
        data = json.loads(raw or "[]")
        return [str(m["name"]) for m in data if m.get("name")]
    except Exception:
        return []


def discover_lock_commands():
    options = [("Disabled", "none")]
    for label, command in (
        ("Hyprlock", "hyprlock"),
        ("Swaylock", "swaylock"),
        ("GTKLock", "gtklock"),
        ("Waylock", "waylock"),
    ):
        if command_exists(command):
            options.append((label, command))
    return options


def discover_sleep_commands():
    options = [("Disabled", "none")]
    if command_exists("systemctl"):
        options.append(("systemctl suspend", "systemctl suspend"))
    if command_exists("loginctl"):
        options.append(("loginctl suspend", "loginctl suspend"))
    return options


def read_config():
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        for raw in CONFIG_FILE.read_text(errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key in cfg:
                cfg[key] = value.strip()
    return cfg


def write_config(cfg):
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    text = f"""# Blacklayer configuration

USE_INPUT_ACTIVITY={cfg["USE_INPUT_ACTIVITY"]}

run_blacklayer={cfg["run_blacklayer"]}
run_lock={cfg["run_lock"]}
run_sleep={cfg["run_sleep"]}

BLACKLAYER_DELAY={cfg["BLACKLAYER_DELAY"]}
EVENT_POLL_INTERVAL={cfg["EVENT_POLL_INTERVAL"]}
LOCK_DELAY={cfg["LOCK_DELAY"]}
SLEEP_DELAY={cfg["SLEEP_DELAY"]}

LOCK_COMMAND={cfg["LOCK_COMMAND"]}
SLEEP_COMMAND={cfg["SLEEP_COMMAND"]}

resource={cfg["resource"]}

WAYLAND_DISPLAY={cfg["WAYLAND_DISPLAY"]}

# HYPRLAND_INSTANCE_SIGNATURE=

dark_mode={cfg["dark_mode"]}
"""
    CONFIG_FILE.write_text(text)
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def worker_running():
    if not WORKER_PID.exists():
        return False
    try:
        return pid_alive(WORKER_PID.read_text().strip())
    except Exception:
        return False


def stop_worker():
    if WORKER_PID.exists():
        try:
            pid = int(WORKER_PID.read_text().strip())
            os.kill(pid, 15)
        except Exception:
            pass

    try:
        subprocess.run(
            ["pkill", "-f", str(WORKER)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        pass


def notify(title, body):
    if command_exists("notify-send"):
        try:
            subprocess.Popen(
                ["notify-send", title, body],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


def waybar_config_for_monitor(monitor):
    return Path.home() / ".config" / "waybar" / f"config-{monitor}"


def waybar_is_running_for_config(config):
    if not command_exists("pgrep"):
        return False

    try:
        pids = subprocess.run(
            ["pgrep", "-x", "waybar"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        ).stdout.splitlines()

        for pid in pids:
            if not pid.strip().isdigit():
                continue
            cmdline = Path(f"/proc/{pid.strip()}/cmdline")
            try:
                data = cmdline.read_bytes().replace(b"\0", b" ").decode(
                    errors="ignore"
                )
                if str(config) in data:
                    return True
            except Exception:
                continue
    except Exception:
        pass

    return False


def restore_waybars():
    waybar = Path("/usr/bin/waybar")
    if not waybar.exists():
        return

    waybar_dir = Path.home() / ".config" / "waybar"
    if not waybar_dir.exists():
        return

    for config in sorted(waybar_dir.glob("config-*")):
        if not config.is_file():
            continue
        if waybar_is_running_for_config(config):
            continue

        try:
            subprocess.Popen(
                [str(waybar), "-c", str(config)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


class BlacklayerWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)

        self.cfg = read_config()
        self.monitors = []
        self.dirty = False
        self._refreshing = False

        self.set_title("Blacklayer")
        self.set_default_size(1000, 850)
        self.set_size_request(760, 650)

        self.build_ui()
        self.connect("close-request", self.close_requested)
        self.apply_theme()
        self.refresh()
        notify("Blacklayer", "Settings opened.")

        GLib.timeout_add_seconds(2, self.refresh)

    def add_group(self, page, title, description=None):
        group = Adw.PreferencesGroup()
        group.set_title(title)
        if description:
            group.set_description(description)
        page.add(group)
        return group

    def add_action_row(self, group, title, subtitle=""):
        row = Adw.ActionRow()
        row.set_title(title)
        if subtitle:
            row.set_subtitle(subtitle)
        group.add(row)
        return row

    def build_ui(self):
        header = Adw.HeaderBar()

        self.status_badge = Gtk.Label(label="Stopped")
        self.status_badge.add_css_class("dim-label")
        header.set_title_widget(self.status_badge)

        self.dark_switch = Gtk.Switch()
        self.dark_switch.set_valign(Gtk.Align.CENTER)
        self.dark_switch.set_tooltip_text("Dark mode")
        self.dark_switch.set_active(
            self.cfg["dark_mode"].lower() == "true"
        )
        self.dark_switch.connect("notify::active", self.dark_changed)

        dark_label = Gtk.Label(label="Dark")
        dark_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        dark_box.set_valign(Gtk.Align.CENTER)
        dark_box.append(dark_label)
        dark_box.append(self.dark_switch)
        header.pack_end(dark_box)

        self.run_button = Gtk.Button(label="Run")
        self.run_button.add_css_class("suggested-action")
        self.run_button.connect("clicked", self.run_worker)

        self.stop_button = Gtk.Button(label="Stop")
        self.stop_button.add_css_class("destructive-action")
        self.stop_button.connect("clicked", self.stop_worker_clicked)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.append(header)

        # Use Adw.PreferencesPage directly instead of a manually nested
        # ScrolledWindow. Adw.PreferencesPage provides the correct scrolling
        # and sizing behavior for PreferencesGroup/ActionRow widgets.
        page = Adw.PreferencesPage()
        page.set_vexpand(True)
        page.set_hexpand(True)

        root.append(page)
        self.set_content(root)

        general = self.add_group(
            page,
            "General",
            "Blacklayer monitor and activity behavior",
        )

        self.monitor_row = Adw.ActionRow()
        self.monitor_row.set_title("Monitors")
        self.monitor_row.set_subtitle("Detecting Hyprland monitors…")

        self.refresh_button = Gtk.Button(label="Refresh")
        self.refresh_button.set_valign(Gtk.Align.CENTER)
        self.refresh_button.connect("clicked", self.refresh_clicked)
        self.monitor_row.add_suffix(self.refresh_button)
        general.add(self.monitor_row)

        self.input_row = Adw.SwitchRow()
        self.input_row.set_title("Use input activity")
        self.input_row.set_subtitle(
            "On a single monitor this is automatically enabled."
        )
        self.input_row.set_active(
            self.cfg["USE_INPUT_ACTIVITY"].lower() == "true"
        )
        self.input_row.connect("notify::active", self.input_changed)
        general.add(self.input_row)

        features = self.add_group(
            page,
            "Features",
            "Enable or disable the individual actions",
        )

        self.blacklayer_switch = Adw.SwitchRow()
        self.blacklayer_switch.set_title("Blacklayer")
        self.blacklayer_switch.set_subtitle(
            "Show Blacklayer after the configured inactivity delay."
        )
        self.blacklayer_switch.set_active(
            self.cfg["run_blacklayer"].lower() == "true"
        )
        self.blacklayer_switch.connect(
            "notify::active",
            lambda *_: self.save_bool(
                "run_blacklayer",
                self.blacklayer_switch.get_active(),
            ),
        )
        features.add(self.blacklayer_switch)

        self.lock_switch = Adw.SwitchRow()
        self.lock_switch.set_title("Lock")
        self.lock_switch.set_subtitle(
            "Run the selected lock application."
        )
        self.lock_switch.set_active(
            self.cfg["run_lock"].lower() == "true"
        )
        self.lock_switch.connect(
            "notify::active",
            lambda *_: self.save_bool(
                "run_lock",
                self.lock_switch.get_active(),
            ),
        )
        features.add(self.lock_switch)

        self.sleep_switch = Adw.SwitchRow()
        self.sleep_switch.set_title("Sleep")
        self.sleep_switch.set_subtitle(
            "Run the selected suspend method."
        )
        self.sleep_switch.set_active(
            self.cfg["run_sleep"].lower() == "true"
        )
        self.sleep_switch.connect(
            "notify::active",
            lambda *_: self.save_bool(
                "run_sleep",
                self.sleep_switch.get_active(),
            ),
        )
        features.add(self.sleep_switch)

        timing = self.add_group(
            page,
            "Timing",
            "All values are in seconds",
        )

        self.blacklayer_delay = self.add_spin(
            timing,
            "Blacklayer delay",
            "Delay before Blacklayer appears",
            self.cfg["BLACKLAYER_DELAY"],
            1,
            86400,
            lambda v: self.set_value("BLACKLAYER_DELAY", v),
        )

        self.lock_delay = self.add_spin(
            timing,
            "Lock delay",
            "Delay before the selected lock application starts",
            self.cfg["LOCK_DELAY"],
            1,
            86400,
            lambda v: self.set_value("LOCK_DELAY", v),
        )

        self.sleep_delay = self.add_spin(
            timing,
            "Sleep delay",
            "Delay before the selected sleep method starts",
            self.cfg["SLEEP_DELAY"],
            1,
            86400,
            lambda v: self.set_value("SLEEP_DELAY", v),
        )

        self.poll_delay = self.add_spin(
            timing,
            "Event polling interval",
            "Used by legacy multi-monitor event-driven mode",
            self.cfg["EVENT_POLL_INTERVAL"],
            1,
            3600,
            lambda v: self.set_value("EVENT_POLL_INTERVAL", v),
        )

        lock_page = self.add_group(
            page,
            "Lock",
            "Choose a lock program that is actually installed.",
        )

        self.lock_dropdown = self.add_dropdown(
            lock_page,
            "Lock application",
            "Only detected lock applications are shown.",
            discover_lock_commands(),
            self.cfg["LOCK_COMMAND"],
            self.lock_selected,
        )

        sleep_page = self.add_group(
            page,
            "Sleep",
            "Choose a suspend method available on this system.",
        )

        self.sleep_dropdown = self.add_dropdown(
            sleep_page,
            "Sleep method",
            "Only detected suspend methods are shown.",
            discover_sleep_commands(),
            self.cfg["SLEEP_COMMAND"],
            self.sleep_selected,
        )

        resource = self.add_group(
            page,
            "Resource",
            "Image or animation used by Blacklayer.",
        )

        resource_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        resource_box.set_margin_top(8)
        resource_box.set_margin_bottom(8)
        resource_box.set_margin_start(12)
        resource_box.set_margin_end(12)
        resource_box.set_hexpand(True)

        self.resource_entry = Gtk.Entry()
        self.resource_entry.set_hexpand(True)
        self.resource_entry.set_text(self.cfg["resource"])
        self.resource_entry.set_placeholder_text(
            "PNG, JPG, JPEG or GIF"
        )
        self.resource_entry.connect(
            "changed",
            lambda entry: self.set_value(
                "resource",
                entry.get_text(),
            ),
        )

        browse = Gtk.Button(label="Browse")
        browse.connect("clicked", self.choose_resource)

        resource_box.append(self.resource_entry)
        resource_box.append(browse)
        resource.add(resource_box)


        bottom = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )
        bottom.set_margin_top(8)
        bottom.set_margin_bottom(20)
        bottom.set_margin_start(24)
        bottom.set_margin_end(24)

        self.save_button = Gtk.Button(label="Save")
        self.save_button.set_hexpand(True)
        self.save_button.add_css_class("suggested-action")
        self.save_button.connect("clicked", self.save_clicked)

        run_stop = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10,
        )
        run_stop.set_hexpand(True)

        self.run_button.set_hexpand(True)
        self.stop_button.set_hexpand(True)

        run_stop.append(self.run_button)
        run_stop.append(self.stop_button)

        bottom.append(self.save_button)
        bottom.append(run_stop)

        root.append(bottom)

    def add_dropdown(
        self,
        group,
        title,
        subtitle,
        options,
        selected,
        callback,
    ):
        row = Adw.ActionRow()
        row.set_title(title)
        row.set_subtitle(subtitle)

        model = Gtk.StringList.new([label for label, _ in options])
        dropdown = Gtk.DropDown(model=model)
        dropdown.set_valign(Gtk.Align.CENTER)

        index = 0
        for i, (_, value) in enumerate(options):
            if value == selected:
                index = i
                break

        dropdown.set_selected(index)
        dropdown._blacklayer_options = options
        dropdown._blacklayer_callback = callback
        dropdown.connect(
            "notify::selected",
            self.dropdown_changed,
        )

        row.add_suffix(dropdown)
        row.set_activatable_widget(dropdown)
        group.add(row)

        return dropdown

    def dropdown_changed(self, dropdown, _pspec):
        options = dropdown._blacklayer_options
        index = dropdown.get_selected()

        if 0 <= index < len(options):
            dropdown._blacklayer_callback(
                options[index][1]
            )

    def add_spin(
        self,
        group,
        title,
        subtitle,
        value,
        minimum,
        maximum,
        callback,
    ):
        row = Adw.ActionRow()
        row.set_title(title)
        row.set_subtitle(subtitle)

        try:
            initial = int(value)
        except Exception:
            initial = minimum

        adjustment = Gtk.Adjustment(
            value=initial,
            lower=minimum,
            upper=maximum,
            step_increment=1,
            page_increment=10,
        )

        spin = Gtk.SpinButton(
            adjustment=adjustment,
            climb_rate=1,
            digits=0,
        )
        spin.set_width_chars(8)
        spin.set_valign(Gtk.Align.CENTER)
        spin.connect(
            "value-changed",
            lambda widget: callback(
                int(widget.get_value())
            ),
        )

        row.add_suffix(spin)
        row.set_activatable_widget(spin)
        group.add(row)

        return spin

    def mark_dirty(self):
        self.dirty = True
        self.save_button.set_label("Save*")

    def save(self):
        write_config(self.cfg)
        self.dirty = False
        if hasattr(self, "save_button"):
            self.save_button.set_label("Save")

    def save_clicked(self, _button):
        self.save()
        notify("Blacklayer", "Settings saved.")

    def save_bool(self, key, value):
        self.cfg[key] = "true" if value else "false"
        self.mark_dirty()

    def set_value(self, key, value):
        self.cfg[key] = str(value)
        self.mark_dirty()

    def input_changed(self, row, _pspec):
        if len(self.monitors) <= 1:
            if not row.get_active():
                row.set_active(True)
            self.cfg["USE_INPUT_ACTIVITY"] = "true"
        else:
            self.cfg["USE_INPUT_ACTIVITY"] = (
                "true" if row.get_active() else "false"
            )
        self.mark_dirty()

    def lock_selected(self, command):
        self.cfg["LOCK_COMMAND"] = command
        self.mark_dirty()

    def sleep_selected(self, command):
        self.cfg["SLEEP_COMMAND"] = command
        self.mark_dirty()

    def dark_changed(self, row, _pspec):
        self.cfg["dark_mode"] = (
            "true" if row.get_active() else "false"
        )
        self.apply_theme()
        self.mark_dirty()

    def apply_theme(self):
        manager = Adw.StyleManager.get_default()
        if self.cfg["dark_mode"].lower() == "true":
            manager.set_color_scheme(
                Adw.ColorScheme.FORCE_DARK
            )
        else:
            manager.set_color_scheme(
                Adw.ColorScheme.FORCE_LIGHT
            )

    def choose_resource(self, _button):
        dialog = Gtk.FileDialog()
        try:
            dialog.open(
                self,
                None,
                self.resource_chosen,
            )
        except Exception:
            pass

    def resource_chosen(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.resource_entry.set_text(
                    file.get_path() or ""
                )
        except Exception:
            pass

    def run_worker(self, _button):
        if self.dirty:
            self.save()

        if worker_running():
            self.status_badge.set_text("Running")
            notify("Blacklayer", "Worker is already running.")
            return

        if not WORKER.exists():
            self.status_badge.set_text("Worker not found")
            notify("Blacklayer", "Worker file was not found.")
            return

        try:
            WORKER.chmod(0o755)
            subprocess.Popen(
                ["bash", str(WORKER)],
                cwd=str(BASE_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self.status_badge.set_text("Running")
            notify("Blacklayer", "Started.")
        except Exception:
            self.status_badge.set_text("Error")
            notify("Blacklayer", "Could not start the worker.")

    def stop_worker_clicked(self, _button):
        stop_worker()
        restore_waybars()
        self.status_badge.set_text("Stopped")
        notify("Blacklayer", "Stopped.")

    def refresh_clicked(self, _button):
        self.refresh_button.set_sensitive(False)
        try:
            self.monitors = get_monitors()

            if not self.monitors:
                self.monitor_row.set_subtitle(
                    "No Hyprland monitors detected"
                )
            else:
                self.monitor_row.set_subtitle(
                    f"{len(self.monitors)} monitor(s): "
                    + ", ".join(self.monitors)
                )

            single = len(self.monitors) <= 1
            if single:
                if not self.input_row.get_active():
                    self.input_row.set_active(True)
                self.input_row.set_sensitive(False)
                self.cfg["USE_INPUT_ACTIVITY"] = "true"
            else:
                self.input_row.set_sensitive(True)

            # Rebuild detected lock/sleep lists so newly installed programs appear.
            lock_options = discover_lock_commands()
            lock_model = Gtk.StringList.new(
                [label for label, _ in lock_options]
            )
            self.lock_dropdown.set_model(lock_model)
            self.lock_dropdown._blacklayer_options = lock_options
            lock_index = next(
                (
                    i for i, (_, value) in enumerate(lock_options)
                    if value == self.cfg["LOCK_COMMAND"]
                ),
                0,
            )
            self.lock_dropdown.set_selected(lock_index)

            sleep_options = discover_sleep_commands()
            sleep_model = Gtk.StringList.new(
                [label for label, _ in sleep_options]
            )
            self.sleep_dropdown.set_model(sleep_model)
            self.sleep_dropdown._blacklayer_options = sleep_options
            sleep_index = next(
                (
                    i for i, (_, value) in enumerate(sleep_options)
                    if value == self.cfg["SLEEP_COMMAND"]
                ),
                0,
            )
            self.sleep_dropdown.set_selected(sleep_index)

            notify("Blacklayer", "Monitors and system options refreshed.")
        finally:
            self.refresh_button.set_sensitive(True)

    def close_requested(self, *_args):
        notify("Blacklayer", "Settings closed.")
        return False

    def refresh(self):
        self.monitors = get_monitors()

        if not self.monitors:
            self.monitor_row.set_subtitle(
                "No Hyprland monitors detected"
            )
        else:
            self.monitor_row.set_subtitle(
                f"{len(self.monitors)} monitor(s): "
                + ", ".join(self.monitors)
            )

        single = len(self.monitors) <= 1

        if single:
            if not self.input_row.get_active():
                self.input_row.set_active(True)
            self.input_row.set_sensitive(False)
        else:
            self.input_row.set_sensitive(True)

        self.status_badge.set_text(
            "Running" if worker_running() else "Stopped"
        )

        return True


class BlacklayerApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.blacklayer.Settings"
        )

    def do_activate(self):
        window = self.props.active_window
        if window is None:
            window = BlacklayerWindow(self)
        window.present()


if __name__ == "__main__":
    app = BlacklayerApp()
    raise SystemExit(app.run(None))
