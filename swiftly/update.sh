#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Standalone updater; also installed at $XDG_CONFIG_HOME/swiftly/update.sh.
set -euo pipefail
[[ $EUID -ne 0 ]] || { echo '[Swiftly] Run as your normal user.' >&2; exit 1; }
exec python3 - "$@" <<'PY'
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

def main():
    parser = argparse.ArgumentParser(description='Update Swiftly and reload its app and widgets.')
    parser.add_argument('hyprland_config', nargs='?', type=Path,
                        help='Existing Hyprland config; omit after the first recorded install.')
    parser.add_argument('--reload-only', action='store_true', help='Reload installed files without downloading.')
    args = parser.parse_args()
    if args.reload_only and args.hyprland_config:
        parser.error('--reload-only does not accept a Hyprland config')
    root = Path(os.environ.get('XDG_CONFIG_HOME') or str(Path.home()/'.config'))
    if not root.is_absolute():
        raise ValueError('XDG_CONFIG_HOME must be absolute')
    target = root/'quickshell/swiftly'
    control = root/'swiftly'
    control.mkdir(parents=True, exist_ok=True)
    lock = os.open(control/'.update.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise ValueError('Another Swiftly update is already running')

    if not args.reload_only:
        gui = None
        hypr = args.hyprland_config
        if hypr is None:
            state_path = control/'install-state.json'
            if state_path.is_symlink() or not state_path.is_file():
                raise ValueError('Supply your Hyprland config once: bash update.sh /path/to/hyprland.conf')
            state = json.loads(state_path.read_text())
            if not isinstance(state, dict) or type(state.get('schemaVersion')) is not int or state['schemaVersion'] != 1:
                raise ValueError('Invalid install-state.json')
            if not isinstance(state.get('hyprlandConfig'), str):
                raise ValueError('Invalid recorded Hyprland config')
            hypr = Path(state['hyprlandConfig'])
            gui = state.get('guiDirectory')
            if gui is not None and (not isinstance(gui, str) or not (Path(gui)/'shell.qml').is_file()):
                raise ValueError('The recorded custom GUI directory is unavailable')
        hypr = hypr.expanduser().absolute()
        if hypr.is_symlink() or not hypr.is_file() or hypr.suffix not in {'.conf', '.lua'}:
            raise ValueError('Pass your existing regular .conf or .lua Hyprland config')
        with tempfile.TemporaryDirectory(prefix='swiftly-update-') as temporary:
            installer = Path(temporary)/'install.sh'
            subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location',
                            '--proto', '=https', '--tlsv1.2', '--connect-timeout', '20',
                            '--max-time', '120',
                            'https://raw.githubusercontent.com/laurentiu2013md-glitch/Swiftly/main/install.sh',
                            '--output', str(installer)], check=True)
            command = ['bash', str(installer), 'full']
            if gui is not None:
                command.append(gui)
            subprocess.run([*command, str(hypr)], check=True)

    if target.is_symlink() or (target/'shell.qml').is_symlink() or not (target/'shell.qml').is_file():
        raise ValueError('Swiftly is not installed')
    qs = shutil.which('qs')
    if not qs:
        raise ValueError('qs is not installed')
    def run(*command):
        return subprocess.run([qs, '-p', str(target), *command], capture_output=True,
                              text=True, timeout=15)
    last_status_reply = ''
    def status():
        nonlocal last_status_reply
        result = run('ipc', 'call', 'swiftly', 'status')
        last_status_reply = result.stdout + result.stderr
        try:
            value = json.loads(result.stdout)
            if result.returncode == 0 and isinstance(value, dict) and isinstance(value.get('generation'), str):
                return value
        except (ValueError, TypeError):
            pass
        return None

    previous = status()
    # Source-file watching can already be reloading the shell during an update.
    # A temporary IPC gap is not evidence that this is a legacy instance.
    grace = time.monotonic() + 5
    while previous is None and 'Not ready to accept queries' in last_status_reply:
        if time.monotonic() >= grace:
            raise ValueError('Swiftly is still busy reloading; no process was stopped')
        time.sleep(0.1)
        previous = status()
    if previous is not None:
        print('[Swiftly] Reloading active app and widgets…', flush=True)
        response = run('ipc', 'call', 'swiftly', 'reload')
        if response.returncode != 0 or response.stdout.strip() != 'reloading':
            raise ValueError('Swiftly rejected reload: '+(response.stderr or response.stdout).strip())
    else:
        print('[Swiftly] Starting Swiftly (or upgrading an older instance)…', flush=True)
        # Upgrade an old shell without reload IPC, or start an inactive shell.
        listing = run('list', '-j')
        if listing.returncode != 0:
            raise ValueError('Cannot inspect Swiftly in this desktop session: '+listing.stderr.strip())
        try:
            instances = json.loads(listing.stdout)
        except ValueError:
            if 'No running instances' not in listing.stdout + listing.stderr:
                raise ValueError('Cannot identify running Swiftly instances')
            instances = []
        if not isinstance(instances, list):
            raise ValueError('Invalid Quickshell instance list')
        for instance in instances:
            if (not isinstance(instance, dict) or type(instance.get('pid')) is not int
                    or instance['pid'] <= 0 or not isinstance(instance.get('config_path'), str)
                    or Path(instance['config_path']).resolve() != (target/'shell.qml').resolve()):
                raise ValueError('Refusing to restart an instance outside the Swiftly path')
        for instance in instances:
            stopped = run('kill', '--pid', str(instance['pid']))
            if stopped.returncode != 0:
                raise ValueError('Could not stop the old Swiftly instance')
        # no-duplicate handles the brief race while an old process exits.
        deadline = time.monotonic() + 5
        while True:
            listing = run('list', '-j')
            if 'No running instances' in listing.stdout + listing.stderr:
                break
            if not instances:
                break
            if time.monotonic() >= deadline:
                raise ValueError('The old Swiftly process did not exit')
            time.sleep(0.1)
        started = run('-n', '-d')
        if started.returncode != 0:
            raise ValueError('Could not start Swiftly: '+(started.stderr or started.stdout).strip())

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        current = status()
        if (current and current.get('ready') is True
                and (previous is None or current['generation'] != previous['generation'])):
            print('[Swiftly] App and widgets reloaded; config preserved.', flush=True)
            return
        time.sleep(0.1)
    raise ValueError('Reload readiness failed; inspect qs logs. The previous GUI/config backups remain available.')

try:
    main()
except (ValueError, OSError, subprocess.SubprocessError) as error:
    raise SystemExit('[Swiftly] ERROR: '+str(error))
PY
