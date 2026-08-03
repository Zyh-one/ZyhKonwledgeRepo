#!/usr/bin/env bash
set -euo pipefail

systemctl --user --no-pager --full status atrust-50-tunnel.service || true
echo
ss -ltnp '( sport = :6009 )' || true
