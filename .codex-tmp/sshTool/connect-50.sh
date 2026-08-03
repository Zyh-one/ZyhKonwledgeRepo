#!/usr/bin/env bash
set -euo pipefail

exec /usr/bin/ssh -F /home/cambricon/sshTool/ssh_config atrust-50 "$@"
