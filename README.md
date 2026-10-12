# HotSpotRadios HAT Multi-Tap Button

GPIO17 active-low, pull-up button dispatcher for Debian Trixie / Raspberry Pi using **libgpiod v2**.

**Verified on node520355 (2026-10-12):** 1–5 tap recognition and scripts, 3-second shutdown, and automatic startup after a power cycle. The packaged installer/configuration layout is new and should be tested before release.

## Install

```sudo apt update
sudo apt install -y git
git clone https://github.com/Aaron315-Indy/HotSpotRadioHAT-Button.git
cd HotSpotRadioHAT-Button
sudo bash install.sh
```

The installer installs `python3-libgpiod` and `gpiod`, backs up the previous Python handler and service unit, preserves existing tap scripts and config, and restarts the service. It does not run `apt upgrade`.

## Scripts

Put executable shell scripts at `/usr/local/lib/hat-button/1tap.sh`, `2tap.sh`, etc. The dispatcher supports any positive tap count if a corresponding executable script exists. Default 1–5 scripts simply log a message. Example:

```bash
#!/usr/bin/env bash
set -euo pipefail
/usr/sbin/asterisk -rx 'rpt fun <URNODE> *31600'
```

The service launches actions detached, with a 120-second timeout and 5-second kill grace. **Actions can overlap** if invoked repeatedly; the dispatcher does not serialize them. Script stdout/stderr are discarded; use `logger` inside scripts for diagnostics. Scripts execute as root; only trusted administrators should edit them.

## Button behavior

- Tap sequences end after 0.65 seconds without another press.
- Holding the button for 3 seconds invokes `systemctl poweroff`, cancelling pending taps.
- Debounce: 40 ms, using kernel line settings.
- Device: `/dev/gpiochip0`, line 17, active-low with pull-up.
- Configuration: `/etc/hat-button/config`. Restart service after changes.

## Verify

```bash
systemctl status hat-power-button.service --no-pager -l
journalctl -fu hat-power-button.service
```

To dry-run without executing scripts or shutdown, stop the service first (GPIO lines are exclusive), then run:

```bash
sudo systemctl stop hat-power-button.service
sudo /usr/bin/python3 -u /usr/local/sbin/hat-power-button.py --test
sudo systemctl start hat-power-button.service
```

## Uninstall

```bash
sudo bash uninstall.sh
```

Leaves scripts, configuration, and timestamped backups intact. Does not automatically restore an older handler; choose the backup you want before restoring.

## Caveats

The Python handler is copied **unchanged** from the previously tested installer. This project is not yet a published release or independently tested across other HATs. If GPIO17 is used by another process, this service cannot acquire it. Do not test shutdown until you have physical access to restore power.

## License

AGPL-3.0-or-later (intended project license; add an official `LICENSE` file before publishing).
