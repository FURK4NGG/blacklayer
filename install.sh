#!/usr/bin/env bash
set -e

echo "[blacklayer] installing..."

# -------------------------
# Detect package manager & install jq
# -------------------------
install_jq() {
    if command -v jq >/dev/null 2>&1 \
        && command -v hypridle >/dev/null 2>&1 \
        && ldconfig -p 2>/dev/null | grep -q libgtk-3 \
        && ldconfig -p 2>/dev/null | grep -q gdk_pixbuf \
        && ldconfig -p 2>/dev/null | grep -q gtk-layer-shell; then
        echo "[blacklayer] all runtime dependencies already installed"
        return
    fi

    echo "[blacklayer] missing dependencies, installing..."


    if command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --noconfirm gtk3 gdk-pixbuf2 gtk-layer-shell jq hypridle

    elif command -v apt >/dev/null 2>&1; then
        sudo apt update
        sudo apt install -y \
        libgtk-3-0 \
        libgdk-pixbuf-2.0-0 \
        libgtk-layer-shell0 \
        jq

        echo "[blacklayer] unsupported package – please install hypridle manually"


    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y \
        gtk3 \
        gdk-pixbuf2 \
        gtk-layer-shell \
        jq \
        hypridle


    else
        echo "[blacklayer] Unsupported distro."
        echo "Please install required packages manually."

        read -rp "Did you install all required packages? (y/n): " answer

        case "$answer" in
            y|Y|yes|YES)
                echo "[blacklayer] Continuing..."
                ;;
            *)
                echo "[blacklayer] Please install the packages and run this script again."
                exit 1
                ;;
        esac
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
cp blacklayer event-driven.sh blacklayer.conf blacklayer-worker.sh call-blacklayer.sh start-waybars.sh generate-waybar-configs.sh idle-lock.sh idle-sleep.sh idle-resume.sh "$BASE_DIR/" 2>/dev/null
cp "/pending-relocation/hypridle.conf" "~/.config/hypr/" 2>/dev/null
cp "/pending-relocation/hypridle.service" "~/.config/systemd/user/" 2>/dev/null


# -------------------------
# Permissions
# -------------------------
echo "[blacklayer] setting permissions"

sudo chown -R bob:bob "$BASE_DIR"
chmod 700 "$BASE_DIR"
chmod +x "$BASE_DIR"/*.sh 2>/dev/null || true
chmod 600 "$BASE_DIR"/*.conf 2>/dev/null || true
[ -f "$BASE_DIR/blacklayer" ] && chmod +x "$BASE_DIR/blacklayer"
systemctl --user daemon-reload
systemctl --user enable hypridle.service



echo "What is yours status bar?"
echo "1 - Waybar"
echo
read -rp "Seçim (1): " CHOICE

case "$CHOICE" in
    1)
        echo "[+] Waybar yapılandırması hazırlanıyor"

        cd "$HOME/.config/blacklayer/" || {
            echo "HATA: ~/.config/blacklayer bulunamadı"
            exit 1
        }

        sudo chown -R "$USER:$USER" "$HOME/.config/waybar"
        chmod 700 "$HOME/.config/waybar"

        ./generate-waybar-configs.sh
        ;;
    *)
        echo "Geçersiz seçim"
        exit 1
        ;;
esac

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
