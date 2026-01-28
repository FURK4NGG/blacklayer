#!/bin/bash

CONF="$HOME/.config/blacklayer/blacklayer.conf"
[ -f "$CONF" ] && source "$CONF"

# hypridle çağırdı ama lock kapalıysa → çık
[ "$run_lock" != "true" ] && exit 0

# zaten kilitliyse tekrar kilitleme
pgrep -x hyprlock >/dev/null && exit 0

hyprlock
