#!/usr/bin/env bash
set -euo pipefail

systemctl --user start atrust-50-tunnel.service
systemctl --user --no-pager --full status atrust-50-tunnel.service
