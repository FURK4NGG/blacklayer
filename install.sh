#!/usr/bin/env bash
set -euo pipefail

APP_NAME="blacklayer"
BASE_DIR="${HOME}/.config/blacklayer"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

log() {
    printf '[blacklayer] %s\n' "$*"
}

die() {
    printf '[blacklayer] ERROR: %s\n' "$*" >&2
    exit 1
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# ---------------------------------------------------------
# Package installation
#
# Blacklayer does NOT use hypridle.
# Inactivity is handled by input-activity.py + worker.
# ---------------------------------------------------------

install_packages() {
    local pm=""

    if command_exists pacman; then
        pm="pacman"
    elif command_exists apt-get; then
        pm="apt"
    elif command_exists dnf; then
        pm="dnf"
    else
        return 1
    fi

    log "Installing runtime/build dependencies using ${pm}..."

    case "$pm" in
        pacman)
            sudo pacman -S --needed --noconfirm \
                gtk3 \
                gdk-pixbuf2 \
                gtk-layer-shell \
                jq \
                python \
                python-gobject \
                python-evdev \
                libadwaita \
                gcc \
                pkgconf
            ;;

        apt)
            sudo apt-get update
            sudo apt-get install -y \
                python3 \
                python3-gi \
                python3-evdev \
                gir1.2-gtk-3.0 \
                gir1.2-adwaita-1 \
                libgtk-3-0 \
                libgdk-pixbuf-2.0-0 \
                libgtk-layer-shell0 \
                libadwaita-1-0 \
                jq \
                gcc \
                pkg-config \
                libgtk-3-dev \
                libgdk-pixbuf-2.0-dev \
                libgtk-layer-shell-dev
            ;;

        dnf)
            sudo dnf install -y \
                python3 \
                python3-gobject \
                python3-evdev \
                gtk3 \
                gdk-pixbuf2 \
                gtk-layer-shell \
                libadwaita \
                jq \
                gcc \
                pkgconf-pkg-config \
                gtk3-devel \
                gdk-pixbuf2-devel \
                gtk-layer-shell-devel
            ;;
    esac
}

# ---------------------------------------------------------
# Check / optionally install dependencies
# ---------------------------------------------------------

missing=()

for cmd in bash jq hyprctl python3; do
    command_exists "$cmd" || missing+=("$cmd")
done

python3 - <<'PY' >/dev/null 2>&1 || missing+=("python-gobject")
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
PY

python3 - <<'PY' >/dev/null 2>&1 || missing+=("python-evdev")
import evdev
PY

if [ "${#missing[@]}" -gt 0 ]; then
    log "Missing dependencies: ${missing[*]}"
    install_packages || die \
        "Could not automatically install dependencies. Install the required packages and run install.sh again."
fi

# ---------------------------------------------------------
# Verify dependencies after installation
# ---------------------------------------------------------

command_exists jq || die "jq is required."
command_exists hyprctl || die "Hyprland/hyprctl was not found."
command_exists python3 || die "python3 is required."

python3 - <<'PY'
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
import evdev
PY

# ---------------------------------------------------------
# Stop an existing Blacklayer session before replacing files
# ---------------------------------------------------------

if [ -f "$BASE_DIR/blacklayer-worker.sh" ]; then
    log "Stopping existing Blacklayer session..."

    pkill -f "${BASE_DIR}/blacklayer-worker.sh" 2>/dev/null || true
    pkill -f "${BASE_DIR}/input-activity.py" 2>/dev/null || true
fi

# ---------------------------------------------------------
# Install active project files only
# ---------------------------------------------------------

mkdir -p "$BASE_DIR"

files=(
    blacklayer
    blacklayer.c
    blacklayer.conf
    blacklayer-worker.sh
    input-activity.py
    blacklayer-ui.py
    start-waybars.sh
    generate-waybar-configs.sh
    LICENSE
    README.md
)

for file in "${files[@]}"; do
    [ -f "$SCRIPT_DIR/$file" ] || die "Repository file missing: $file"
    install -m 0644 "$SCRIPT_DIR/$file" "$BASE_DIR/$file"
done

chmod 0755 \
    "$BASE_DIR/blacklayer" \
    "$BASE_DIR/blacklayer-worker.sh" \
    "$BASE_DIR/input-activity.py" \
    "$BASE_DIR/blacklayer-ui.py" \
    "$BASE_DIR/start-waybars.sh" \
    "$BASE_DIR/generate-waybar-configs.sh"

chmod 0600 "$BASE_DIR/blacklayer.conf"

mkdir -p "$BASE_DIR/.blacklayer_state/pids"
mkdir -p "$BASE_DIR/.blacklayer_state/waybar"

chmod 0700 "$BASE_DIR/.blacklayer_state"
chmod 0700 "$BASE_DIR/.blacklayer_state/pids"
chmod 0700 "$BASE_DIR/.blacklayer_state/waybar"

# ---------------------------------------------------------
# Remove obsolete files from older installations
# ---------------------------------------------------------

rm -f \
    "$BASE_DIR/event-driven.sh" \
    "$BASE_DIR/.blacklayer_idle.py" \
    "$BASE_DIR/hypridle.conf" \
    "$BASE_DIR/hypridle.service" \
    "$BASE_DIR/call-blacklayer.sh" \
    "$BASE_DIR/start-waybars-old.sh" \
    "$BASE_DIR/idle-lock.sh" \
    "$BASE_DIR/idle-sleep.sh" \
    "$BASE_DIR/idle-resume.sh"

# ---------------------------------------------------------
# Compile native binary only when needed
# ---------------------------------------------------------

if [ ! -x "$BASE_DIR/blacklayer" ] || \
   [ "$SCRIPT_DIR/blacklayer.c" -nt "$BASE_DIR/blacklayer" ]; then

    log "Compiling native Blacklayer binary..."

    pkg-config --exists gtk+-3.0 gdk-pixbuf-2.0 ||
        die "GTK3/GDK-Pixbuf development packages are missing."

    pkg-config --exists gtk-layer-shell-0.1 ||
        die "gtk-layer-shell development package is missing."

    gcc \
        -O2 \
        -Wall \
        -Wextra \
        -o "$BASE_DIR/blacklayer" \
        "$BASE_DIR/blacklayer.c" \
        $(pkg-config --cflags --libs gtk+-3.0 gdk-pixbuf-2.0) \
        -lgtk-layer-shell
fi

# ---------------------------------------------------------
# Optional Waybar configuration generation
# ---------------------------------------------------------

if command_exists waybar && [ -d "$HOME/.config/waybar" ]; then
    read -r -p "Generate per-monitor Waybar configs now? [Y/n]: " answer
    answer="${answer:-Y}"

    case "$answer" in
        y|Y|yes|YES)
            "$BASE_DIR/generate-waybar-configs.sh"
            ;;
        *)
            log "Skipping Waybar config generation."
            ;;
    esac
fi

# ---------------------------------------------------------
# Validation
# ---------------------------------------------------------

bash -n "$BASE_DIR/blacklayer-worker.sh"
bash -n "$BASE_DIR/start-waybars.sh"
bash -n "$BASE_DIR/generate-waybar-configs.sh"

python3 -m py_compile \
    "$BASE_DIR/input-activity.py" \
    "$BASE_DIR/blacklayer-ui.py"

log "Installation complete."

echo
echo "Configuration:"
echo "  $BASE_DIR/blacklayer.conf"

echo
echo "GUI:"
echo "  python3 $BASE_DIR/blacklayer-ui.py"

echo
echo "Waybar:"
echo "  $BASE_DIR/start-waybars.sh"

echo
echo "Worker is normally started/stopped from the GUI."

echo
echo "Architecture:"
echo "  USE_INPUT_ACTIVITY=true  -> one target monitor per Run session"
echo "  USE_INPUT_ACTIVITY=false -> independent inactivity per monitor"
echo "  1 monitor                -> Input Activity is forced on"

echo
echo "Inactivity:"
echo "  input-activity.py -> blacklayer-worker.sh -> Blacklayer"
echo "  hypridle is NOT required."

echo
echo "Waybar:"
echo "  start-waybars.sh starts per-monitor Waybar instances."
echo "  Blacklayer controls Waybar independently per monitor."
