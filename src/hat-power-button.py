#!/usr/bin/env python3
"""HotSpotRadioHAT button, libgpiod v1 (Bookworm) and v2 (Trixie)."""
import argparse
import datetime
import logging
import os
from pathlib import Path
import subprocess
import time
import gpiod

LOG = logging.getLogger('hat-button')
SCRIPTS = Path('/usr/local/lib/hat-button')


def run_action(count, test):
    script = SCRIPTS / f'{count}tap.sh'
    if not script.is_file():
        LOG.info('No script for %d taps: %s', count, script)
        return
    if not os.access(script, os.X_OK):
        LOG.warning('Not executable: %s', script)
        return
    LOG.info('%d taps -> %s', count, script)
    if not test:
        try:
            subprocess.Popen(['/usr/bin/timeout', '--kill-after=5s', '120s', str(script)],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError:
            LOG.exception('Failed to launch %s', script)


def poweroff(test):
    LOG.warning('Shutdown hold detected')
    if not test:
        subprocess.Popen(['/usr/bin/systemctl', 'poweroff'],
                         stdin=subprocess.DEVNULL, start_new_session=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--chip', default='/dev/gpiochip0')
    p.add_argument('--line', type=int, default=17)
    p.add_argument('--hold', type=float, default=3.0)
    p.add_argument('--gap', type=float, default=0.65)
    p.add_argument('--debounce-ms', type=int, default=40)
    p.add_argument('--test', action='store_true')
    a = p.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    if hasattr(gpiod, 'request_lines'):
        from gpiod.line import Direction, Edge, Bias, Value
        settings = gpiod.LineSettings(direction=Direction.INPUT, edge_detection=Edge.BOTH,
                                     bias=Bias.PULL_UP, active_low=True,
                                     debounce_period=datetime.timedelta(milliseconds=a.debounce_ms))
        req = gpiod.request_lines(a.chip, consumer='hat-button', config={a.line: settings})
        def read():
            return req.get_value(a.line) == Value.ACTIVE
        version = 'v2'
    else:
        chip = gpiod.Chip(a.chip)
        line = chip.get_line(a.line)
        line.request(consumer='hat-button', type=gpiod.LINE_REQ_DIR_IN,
                     flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP | gpiod.LINE_REQ_FLAG_ACTIVE_LOW)
        def read():
            return line.get_value() == 1
        version = 'v1'

    LOG.info('Monitoring %s line %d; libgpiod %s; hold %.1fs; gap %.2fs; test=%s',
             a.chip, a.line, version, a.hold, a.gap, a.test)
    debounce = max(0, a.debounce_ms) / 1000.0
    stable = read()
    raw = stable
    raw_since = time.monotonic()
    press_since = time.monotonic() if stable else None
    release_at = None
    taps = 0
    hold_fired = False
    try:
        while True:
            now = time.monotonic()
            current = read()
            if current != raw:
                raw = current
                raw_since = now
            if raw != stable and now - raw_since >= debounce:
                stable = raw
                if stable:
                    press_since = now
                    hold_fired = False
                else:
                    if not hold_fired and press_since is not None:
                        if now - press_since >= a.hold:
                            poweroff(a.test)
                            hold_fired = True
                            taps = 0
                        else:
                            taps += 1
                            release_at = now
                    press_since = None
            if stable and not hold_fired and press_since is not None and now - press_since >= a.hold:
                poweroff(a.test)
                hold_fired = True
                taps = 0
            if not stable and taps and release_at is not None and now - release_at >= a.gap:
                run_action(taps, a.test)
                taps = 0
                release_at = None
            time.sleep(0.01)
    finally:
        if version == 'v1':
            line.release()
            chip.close()
        else:
            req.release()


if __name__ == '__main__':
    main()
