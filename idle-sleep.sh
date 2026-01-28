#!/bin/bash

CONF="$HOME/.config/blacklayer/blacklayer.conf"
[ -f "$CONF" ] && source "$CONF"

# sleep kapalıysa → çık
[ "$run_sleep" != "true" ] && exit 0

hyprctl dispatch dpms off
