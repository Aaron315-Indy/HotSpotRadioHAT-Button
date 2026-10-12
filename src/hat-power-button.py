#!/usr/bin/env python3
"""GPIO17 active-low button: multi-tap scripts and 3-second shutdown."""
import argparse
import logging
import os
import pathlib
import subprocess
import time
import gpiod
from gpiod.line import Direction, Edge, Bias, Value

LOG = logging.getLogger('hat-button')
SCRIPTS = pathlib.Path('/usr/local/lib/hat-button')


def run_action(count, dry_run):
    script = SCRIPTS / f'{count}tap.sh'
    if not script.is_file():
        LOG.info('No script for %d taps: %s', count, script)
        return
    if not os.access(script, os.X_OK):
        LOG.warning('Not executable: %s', script)
        return
    LOG.info('%d taps -> %s', count, script)
    if dry_run:
        return
    try:
        subprocess.Popen(['/usr/bin/timeout', '--kill-after=5s', '120s', str(script)],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        LOG.exception('Failed to launch %s', script)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--chip', default='/dev/gpiochip0')
    p.add_argument('--line', type=int, default=17)
    p.add_argument('--hold', type=float, default=3.0)
    p.add_argument('--gap', type=float, default=0.65)
    p.add_argument('--debounce-ms', type=int, default=40)
    p.add_argument('--test', action='store_true', help='Log actions without executing')
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    settings = gpiod.LineSettings(direction=Direction.INPUT, edge_detection=Edge.BOTH,
                                  bias=Bias.PULL_UP, active_low=True,
                                  debounce_period=__import__('datetime').timedelta(milliseconds=args.debounce_ms))
    with gpiod.request_lines(args.chip, consumer='hat-button', config={args.line: settings}) as request:
        LOG.info('Monitoring %s line %d; hold %.1fs; gap %.2fs; test=%s',
                 args.chip, args.line, args.hold, args.gap, args.test)
        pressed = request.get_value(args.line) == Value.ACTIVE
        press_since = time.monotonic() if pressed else None
        release_at = None
        taps = 0
        hold_fired = False
        while True:
            now = time.monotonic()
            if pressed and not hold_fired and now - press_since >= args.hold:
                LOG.warning('Shutdown hold detected')
                hold_fired = True
                taps = 0
                if not args.test:
                    subprocess.Popen(['/usr/bin/systemctl', 'poweroff'],
                                     stdin=subprocess.DEVNULL, start_new_session=True)
            if not pressed and taps and release_at is not None and now - release_at >= args.gap:
                run_action(taps, args.test)
                taps = 0
                release_at = None
            if request.wait_edge_events(timeout=0.05):
                for event in request.read_edge_events():
                    # Use current logical state to avoid assumptions about edge polarity.
                    state = request.get_value(args.line) == Value.ACTIVE
                    if state == pressed:
                        continue
                    pressed = state
                    now = time.monotonic()
                    if pressed:
                        press_since = now
                        hold_fired = False
                    else:
                        if not hold_fired and press_since is not None:
                            duration = now - press_since
                            if duration >= args.hold:
                                LOG.warning('Shutdown hold detected on release')
                                taps = 0
                                if not args.test:
                                    subprocess.Popen(['/usr/bin/systemctl', 'poweroff'],
                                                     stdin=subprocess.DEVNULL, start_new_session=True)
                            else:
                                taps += 1
                                release_at = now
                        press_since = None


if __name__ == "__main__":
    main()
