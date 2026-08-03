#!/usr/bin/env bash
set -euo pipefail

tool_dir=/home/cambricon/sshTool
user_unit_dir=/home/cambricon/.config/systemd/user
unit_name=atrust-50-tunnel.service

mkdir -p "$user_unit_dir"
ln -sfn "$tool_dir/$unit_name" "$user_unit_dir/$unit_name"
systemctl --user daemon-reload
systemctl --user enable --now "$unit_name"
systemctl --user --no-pager --full status "$unit_name"
