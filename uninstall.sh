#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo' >&2; exit 1; }
systemctl disable --now hat-power-button.service || true
rm -f /etc/systemd/system/hat-power-button.service /usr/local/sbin/hat-power-button.py
systemctl daemon-reload
printf 'Service removed. User tap scripts and config preserved under /usr/local/lib/hat-button and /etc/hat-button.\n'
printf 'Earlier backups (*.bak.TIMESTAMP) were not modified.\n'
