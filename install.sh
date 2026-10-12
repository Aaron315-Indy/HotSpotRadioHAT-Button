#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo' >&2; exit 1; }
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
apt-get update
apt-get install -y python3-libgpiod gpiod
install -d -m 755 /usr/local/lib/hat-button /usr/local/sbin /etc/hat-button
stamp="$(date +%Y%m%d-%H%M%S)"
for f in /usr/local/sbin/hat-power-button.py /etc/systemd/system/hat-power-button.service; do
  [[ ! -e "$f" ]] || cp -a "$f" "${f}.bak.${stamp}"
done
install -m 755 "$ROOT/src/hat-power-button.py" /usr/local/sbin/hat-power-button.py
if [[ ! -e /etc/hat-button/config ]]; then
  install -m 644 "$ROOT/config.example" /etc/hat-button/config
fi
for n in {1..5}; do
  target="/usr/local/lib/hat-button/${n}tap.sh"
  [[ -e "$target" ]] || install -m 755 "$ROOT/examples/tap.sh" "$target"
done
install -m 644 "$ROOT/hat-power-button.service" /etc/systemd/system/hat-power-button.service
systemctl daemon-reload
systemctl enable hat-power-button.service
systemctl restart hat-power-button.service
systemctl --no-pager --full status hat-power-button.service
