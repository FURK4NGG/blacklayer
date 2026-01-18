#!/usr/bin/env bash

# Ortam değişkenleri
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export WAYLAND_DISPLAY="wayland-1"

WAYBAR_BIN="/usr/bin/waybar"
CONFIG_DIR="$HOME/.config/waybar"

# Tüm config-* dosyalarını al
for CONFIG in "$CONFIG_DIR"/config-*; do
    echo "[waybar] starting with $CONFIG"
    "$WAYBAR_BIN" -c "$CONFIG" &
done
