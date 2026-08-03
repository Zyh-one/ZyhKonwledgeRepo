#!/usr/bin/env bash
set -euo pipefail

tool_dir=/home/cambricon/sshTool
title='Claude — 50机器（aTrust/OpenSSH）'

if [[ ${ATRUST_50_CLAUDE_WINDOW:-0} != 1 ]] && command -v gnome-terminal >/dev/null 2>&1; then
    exec env ATRUST_50_CLAUDE_WINDOW=1 \
        gnome-terminal \
        --window \
        --profile=SSH \
        --title="$title" \
        -- "$tool_dir/Claude-50机器.sh"
fi

printf '\033]10;#F4EFFF\007'
printf '\033]11;#301A4B\007'
printf '\033]0;%s\007' "$title"

exec "$tool_dir/claude-50.sh"
