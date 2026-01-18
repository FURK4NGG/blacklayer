#!/usr/bin/env bash
set -e

WAYBAR_DIR="$HOME/.config/waybar"
BASE_CONFIG="$WAYBAR_DIR/config"

if [ ! -f "$BASE_CONFIG" ]; then
    echo "[error] base config not found"
    exit 1
fi

command -v hyprctl >/dev/null || {
    echo "[error] hyprctl not found"
    exit 1
}

MONITORS=$(hyprctl -j monitors | jq -r '.[].name')

for MONITOR in $MONITORS; do
    TARGET="$WAYBAR_DIR/config-$MONITOR"

    {
        echo '{'
        echo "  \"output\": [\"$MONITOR\"],"
        sed '1s/^{//' "$BASE_CONFIG"
    } > "$TARGET"

    echo "[ok] generated $TARGET for $MONITOR"
done
