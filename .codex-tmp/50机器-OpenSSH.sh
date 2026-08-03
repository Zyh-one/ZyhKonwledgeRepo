#!/usr/bin/env bash
set -euo pipefail

tool_dir=/home/cambricon/sshTool
title='SSH — 50机器（aTrust/OpenSSH）'

if [[ ${ATRUST_50_TERMINAL_WINDOW:-0} != 1 ]] && command -v gnome-terminal >/dev/null 2>&1; then
    exec env ATRUST_50_TERMINAL_WINDOW=1 \
        gnome-terminal \
        --window \
        --profile=SSH \
        --title="$title" \
        -- "$tool_dir/50机器-OpenSSH.sh"
fi

# OSC 10/11 are supported by GNOME Terminal/VTE. The color applies only to
# this window and disappears with it; the shared SSH profile is not changed.
printf '\033]10;#F4EFFF\007'
printf '\033]11;#301A4B\007'
printf '\033]0;%s\007' "$title"

exec "$tool_dir/connect-50.sh"
