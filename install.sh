#!/usr/bin/env bash
set -e

echo "[blacklayer] installing..."

# -------------------------
# Detect package manager & install jq
# -------------------------
install_jq() {
    if command -v jq >/dev/null 2>&1; then
        echo "[blacklayer] jq already installed"
        return
    fi

    echo "[blacklayer] jq not found, installing..."

    if command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --noconfirm jq

    elif command -v apt >/dev/null 2>&1; then
        sudo apt update
        sudo apt install -y jq

    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y jq

    else
        echo "[blacklayer] unsupported distro – please install jq manually"
        exit 1
    fi
}

install_jq

# -------------------------
# Paths
# -------------------------
BASE_DIR="$HOME/.config/blacklayer"

# -------------------------
# Create directory
# -------------------------
mkdir -p "$BASE_DIR"

# -------------------------
# Copy files
# -------------------------
echo "[blacklayer] copying files to $BASE_DIR"
cp blacklayer event-driven.sh blacklayer.conf blacklayer-worker.sh call-blacklayer.sh "$BASE_DIR/" 2>/dev/null


# -------------------------
# Permissions
# -------------------------
echo "[blacklayer] setting permissions"

chmod +x "$BASE_DIR"/*.sh 2>/dev/null || true
chmod 600 "$BASE_DIR"/*.conf 2>/dev/null || true
[ -f "$BASE_DIR/blacklayer" ] && chmod +x "$BASE_DIR/blacklayer"
chmod 700 "$BASE_DIR"

# -------------------------
# Done
# -------------------------
echo
echo "[blacklayer] installation complete"
echo
echo "Run with:"
echo "  $BASE_DIR/call-blacklayer.sh"
echo "Stop with:"
echo "  $BASE_DIR/call-blacklayer.sh"
echo
