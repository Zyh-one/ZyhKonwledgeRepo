#!/usr/bin/env bash
set -euo pipefail

exec /usr/bin/ssh \
    -F /home/cambricon/sshTool/ssh_config \
    -t atrust-50 \
    'command -v tmux >/dev/null 2>&1 || { echo "50机器未安装 tmux"; exit 127; }; tmux new-session -A -s claude'
