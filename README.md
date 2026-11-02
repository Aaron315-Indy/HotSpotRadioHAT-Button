# HotSpotRadioHAT-Button

A Raspberry Pi GPIO button controller for the HotSpotRadios HAT, intended for AllStarLink 3 systems. One to five taps run administrator-defined scripts; holding the button for three seconds requests a graceful operating-system shutdown.

## Features

- Monitors GPIO line offset 17 on `/dev/gpiochip0` by default.
- Uses an active-low input with pull-up bias.
- Runs separate scripts for one, two, three, four, or five taps.
- Requests `systemctl poweroff` on a configurable long press (default: 3 seconds).
- Supports the Python libgpiod v1 API on Debian Bookworm and v2 API on Debian Trixie.
- Uses a systemd service with automatic restart.
- Preserves existing tap scripts and configuration on installation or upgrade.
- Provides a `--test` mode that logs actions without executing scripts or shutting down.

## Tested platforms

| Platform | Python GPIO API | Verification |
| --- | --- | --- |
| Debian 12 Bookworm, AllStarLink node 520352 | libgpiod v1 | 1–5 taps, 3-second hold, service startup after reboot |
| Debian 13 Trixie, AllStarLink node 520355 | libgpiod v2 | 1–5 taps, 3-second hold, service startup after cold boot |

These results describe tests on the listed systems, not a guarantee for every Raspberry Pi or HAT revision.

## Requirements

- Raspberry Pi with a compatible HotSpotRadios HAT and button wired to the selected GPIO line.
- Debian Bookworm or Trixie with systemd and Python 3.
- `python3-libgpiod` and `gpiod` packages; `install.sh` installs them using APT.
- Root privileges for installation, GPIO access, script execution, and shutdown.

GPIO line **offset** 17 is the default, not physical header pin 17. Confirm the correct `/dev/gpiochip*` device and line offset for your board.

## Installation

Clone the repository and run its installer:

```bash
sudo git clone https://github.com/Aaron315-Indy/HotSpotRadioHAT-Button.git /opt/HotSpotRadioHAT-Button
cd /opt/HotSpotRadioHAT-Button
sudo bash install.sh
```

If the repository is already cloned, skip `git clone` and use the existing checkout.

The installer installs the Python handler at `/usr/local/sbin/hat-power-button.py`, the service at `/etc/systemd/system/hat-power-button.service`, the default configuration at `/etc/hat-button/config`, and example tap scripts in `/usr/local/lib/hat-button/`. It enables and restarts the service. Existing configuration and tap scripts are not overwritten. Existing handler and service files receive timestamped backups before replacement.

### Upgrade

```bash
cd /opt/HotSpotRadioHAT-Button
sudo git pull --ff-only
sudo bash install.sh
```

For checkouts using a dedicated GitHub SSH deploy key, retain your configured SSH remote rather than switching it to HTTPS.

## Configuration

Edit `/etc/hat-button/config`:

```ini
CHIP=/dev/gpiochip0
LINE=17
HOLD=3.0
GAP=0.65
DEBOUNCE_MS=40
```

| Variable | Meaning |
| --- | --- |
| `CHIP` | GPIO chip device path |
| `LINE` | Line offset within the selected chip |
| `HOLD` | Seconds of continuous press required to request shutdown |
| `GAP` | Seconds after the final release before dispatching a tap sequence |
| `DEBOUNCE_MS` | Software debounce interval in milliseconds |

The v2 API also requests GPIO-line debounce from the kernel. Restart the service after editing configuration:

```bash
sudo systemctl restart hat-power-button.service
```

## Button actions

| Input | Action |
| --- | --- |
| 1 tap | `/usr/local/lib/hat-button/1tap.sh` |
| 2 taps | `/usr/local/lib/hat-button/2tap.sh` |
| 3 taps | `/usr/local/lib/hat-button/3tap.sh` |
| 4 taps | `/usr/local/lib/hat-button/4tap.sh` |
| 5 taps | `/usr/local/lib/hat-button/5tap.sh` |
| Hold for 3 seconds (default) | Request graceful system shutdown |

Customize each executable shell script to perform the desired action. For example, `/usr/local/lib/hat-button/1tap.sh` can contain:

```bash
#!/usr/bin/env bash
logger -t hat-button 'Single tap detected'
```

Then run `sudo chmod 755 /usr/local/lib/hat-button/1tap.sh`. Scripts are launched asynchronously with `/usr/bin/timeout --kill-after=5s 120s`; their standard output and standard error are discarded. Use `logger` or your own logging if an action needs diagnostics. Scripts must be executable. A missing or non-executable script is logged and skipped.

**Current limitation:** The handler builds a filename from the tap count. Six or more taps do not have predefined scripts; the handler logs that the corresponding script is missing. Explicitly rejecting counts outside 1–5 is a planned improvement.

## Shutdown

A continuous press of at least `HOLD` seconds requests shutdown using `/usr/bin/systemctl poweroff`. It does not cut power electrically. Allow the Pi to finish shutting down before removing power. There is currently **no spoken AllStarLink shutdown announcement**.

## Service management

```bash
systemctl status hat-power-button.service --no-pager
journalctl -b -u hat-power-button.service -n 50 --no-pager
sudo systemctl restart hat-power-button.service
sudo systemctl enable --now hat-power-button.service
```

The service runs as root. Restrict write access to its configuration and tap scripts to trusted administrators.

## Safe test mode

Stop the normal service first to release the GPIO line, then run the handler with `--test`:

```bash
sudo systemctl stop hat-power-button.service
sudo python3 /usr/local/sbin/hat-power-button.py \
  --chip /dev/gpiochip0 --line 17 --hold 3.0 \
  --gap 0.65 --debounce-ms 40 --test
```

Tap or hold the button and watch the log messages. Test mode does **not** launch tap scripts or power off. Press Ctrl+C when finished, then restore the service:

```bash
sudo systemctl start hat-power-button.service
```

## Troubleshooting

**Service inactive after reboot:**

```bash
systemctl is-enabled hat-power-button.service
systemctl is-active hat-power-button.service
journalctl -b -u hat-power-button.service -n 50 --no-pager
systemctl list-jobs --no-pager
```

The repository service file does not use `After=multi-user.target`. If the system is still `starting`, inspect unrelated pending jobs rather than assuming the GPIO handler is at fault.

**GPIO line busy:** Stop any other process using the same GPIO line; do not run the test command alongside the systemd service.

**GPIO API mismatch:** Confirm `python3-libgpiod` is installed and inspect the startup log for `libgpiod v1` or `libgpiod v2`:

```bash
dpkg-query -W python3-libgpiod gpiod
journalctl -b -u hat-power-button.service --no-pager
```

**Tap action not executed:** Check script permissions and the service log:

```bash
ls -l /usr/local/lib/hat-button/
journalctl -u hat-power-button.service -n 30 --no-pager
```

## Uninstall

```bash
cd /opt/HotSpotRadioHAT-Button
sudo bash uninstall.sh
```

This disables the service and removes the installed handler and systemd unit. User configuration, tap scripts, and timestamped backups remain in place.

## Repository layout

```text
src/hat-power-button.py   GPIO monitor (libgpiod v1/v2)
examples/tap.sh           Example user action
config.example            Default settings
hat-power-button.service  systemd unit
install.sh                Installer and upgrade path
uninstall.sh              Uninstaller
README.md                 Documentation
LICENSE                   License text
.gitignore                Python cache exclusions
```

## Planned work

- Automated tests for debounce, tap sequences, holds, and v1/v2 compatibility.
- Announce the LAN IP address and AllStarLink node number after Asterisk becomes ready.
- Play an AllStarLink announcement before shutdown.
- Explicitly ignore tap sequences outside the supported 1–5 range.

These features are **not implemented** in the current release.

## License

GNU Affero General Public License, version 3 (AGPL-3.0). See [LICENSE](LICENSE).
