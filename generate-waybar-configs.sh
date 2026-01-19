#!/usr/bin/env bash
set -e

WAYBAR_DIR="$HOME/.config/waybar"
BASE_CONFIG="$WAYBAR_DIR/config"

command -v hyprctl >/dev/null || { echo "[error] hyprctl not found"; exit 1; }
command -v jq >/dev/null || { echo "[error] jq not found"; exit 1; }

cd "$WAYBAR_DIR"

# -----------------------------
# 1) MONITORLER
# -----------------------------
MONITORS=$(hyprctl -j monitors | jq -r '.[].name')

[ -z "$MONITORS" ] && {
    echo "[info] no monitors found, skipping"
    exit 0
}

# -----------------------------
# 2) BASE CONFIG BELLEĞE AL
#    (output temizlenmiş halde)
# -----------------------------
BASE_CONTENT=""

strip_output() {
    sed \
        -e 's/"output"[[:space:]]*:[[:space:]]*\[[^]]*\],[[:space:]]*//' \
        -e '1s/^{//' \
        "$1"
}

if [ -f "$BASE_CONFIG" ]; then
    echo "[info] base config: config"
    BASE_CONTENT="$(strip_output "$BASE_CONFIG")"
else
    FIRST_MONITOR_CONFIG=$(ls config-* 2>/dev/null | head -n 1 || true)

    [ -z "$FIRST_MONITOR_CONFIG" ] && {
        echo "[error] no base config found"
        exit 1
    }

    echo "[info] base config: $FIRST_MONITOR_CONFIG"
    BASE_CONTENT="$(strip_output "$FIRST_MONITOR_CONFIG")"
fi

# -----------------------------
# 3) TEMİZLİK (MONITOR VARSA)
# -----------------------------
rm -f config
rm -f config-*

# -----------------------------
# 4) YENİ CONFIGLER
# -----------------------------
for MONITOR in $MONITORS; do
    TARGET="config-$MONITOR"

    {
        echo '{'
        echo "  \"output\": [\"$MONITOR\"],"
        echo "$BASE_CONTENT"
    } > "$TARGET"

    echo "[ok] generated $TARGET"
done
