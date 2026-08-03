#!/usr/bin/env bash
set -euo pipefail

journalctl --user -u atrust-50-tunnel.service -n 100 -f
