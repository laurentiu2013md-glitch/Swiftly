#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
[[ $EUID -ne 0 ]] || { echo '[Swiftly] Run as your normal user.' >&2; exit 1; }
exec python3 - "$@" <<'PY'
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description='Uninstall Swiftly; keep settings and backups by default.')
    parser.add_argument('hyprland_config', nargs='?', type=Path, help='Needed for older installs without saved install state.')
    parser.add_argument('--purge', action='store_true', help='Also remove config.json. Backups and unrelated files are kept.')
    args = parser.parse_args()
    root = Path(os.environ.get('XDG_CONFIG_HOME') or str(Path.home()/'.config'))
    if not root.is_absolute():
        raise ValueError('XDG_CONFIG_HOME must be absolute')
    control = root/'swiftly'
    target = root/'quickshell/swiftly'
    for path in (control, root/'quickshell', target):
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise ValueError('Refusing non-directory or symlink: '+str(path))
    control.mkdir(parents=True, exist_ok=True)
    lock = os.open(control/'.update.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise ValueError('Another Swiftly update/uninstall is running')
    statefile = control/'install-state.json'
    hypr = args.hyprland_config
    if hypr is None and statefile.exists():
        if statefile.is_symlink():
            raise ValueError('Refusing symlink install state')
        state = json.loads(statefile.read_text())
        if (not isinstance(state, dict) or type(state.get('schemaVersion')) is not int
                or state['schemaVersion'] != 1 or not isinstance(state.get('hyprlandConfig'), str)
                or not Path(state['hyprlandConfig']).is_absolute()):
            raise ValueError('Invalid install-state.json; pass your Hyprland config explicitly')
        hypr = Path(state['hyprlandConfig'])
    if hypr is None and target.exists():
        raise ValueError('Pass your Hyprland .conf or .lua path for this older install')
    updated = None
    if hypr is not None:
        hypr = hypr.expanduser().absolute()
        if hypr.is_symlink() or not hypr.is_file() or hypr.suffix not in {'.conf', '.lua'}:
            raise ValueError('Pass an existing regular Hyprland .conf or .lua file')
        original = hypr.read_bytes()
        text = original.decode('utf-8')
        comment = '--' if hypr.suffix == '.lua' else '#'
        begin, end = (f'{comment} {word} SWIFTLY GESTURES' for word in ('BEGIN', 'END'))
        pattern = re.compile(r'(?m)^'+re.escape(begin)+r'\r?\n[\s\S]*?^'+re.escape(end)+r'(?:\r?\n|$)')
        clean, count = pattern.subn('', text)
        if text.count(begin) != count or text.count(end) != count or count > 1 or 'SWIFTLY GESTURES' in clean:
            raise ValueError('Malformed/duplicate Swiftly markers; no files were changed')
        updated = clean.encode('utf-8') if count else None
    # Preflight every known file before stopping processes or changing anything.
    names = ['support.py', 'update.sh', 'uninstall.sh', 'install-state.json']
    if args.purge:
        names.append('config.json')
    for name in names:
        path = control/name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError('Refusing non-regular file: '+str(path))
    qs = shutil.which('qs')
    if (target/'shell.qml').is_symlink():
        raise ValueError('Refusing symlink Swiftly shell.qml')
    if target.exists() and not qs:
        raise ValueError('qs is required to stop only the installed Swiftly instance')
    def instances():
        result = subprocess.run([qs, '-p', str(target), 'list', '-j'], capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            raise ValueError('Cannot inspect running Swiftly: '+result.stderr.strip())
        if 'No running instances' in result.stdout + result.stderr:
            return []
        value = json.loads(result.stdout)
        if not isinstance(value, list):
            raise ValueError('Invalid Quickshell instance list')
        for item in value:
            if (not isinstance(item, dict) or type(item.get('pid')) is not int or item['pid'] <= 0
                    or not isinstance(item.get('config_path'), str)
                    or Path(item['config_path']).resolve() != (target/'shell.qml').resolve()):
                raise ValueError('Refusing to stop an instance outside Swiftly')
        return value
    if qs and target.exists():
        for item in instances():
            subprocess.run([qs, '-p', str(target), 'kill', '--pid', str(item['pid'])], check=True, capture_output=True, text=True, timeout=15)
        deadline = time.monotonic()+5
        while instances():
            if time.monotonic() >= deadline:
                raise ValueError('Swiftly did not exit; installed files were kept')
            time.sleep(.1)
    if updated is not None:
        backup = hypr.with_name(hypr.name+f'.bak.{time.time_ns()}')
        shutil.copy2(hypr, backup)
        fd, temporary = tempfile.mkstemp(prefix='.swiftly-', dir=hypr.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(updated)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, stat.S_IMODE(hypr.stat().st_mode))
            os.replace(temporary, hypr)
        finally:
            Path(temporary).unlink(missing_ok=True)
        print('[Swiftly] Removed managed gestures; backup: '+str(backup))
        print('[Swiftly] Run hyprctl reload to apply the gesture removal.')
    if target.exists():
        saved = target.with_name('swiftly.bak.'+str(time.time_ns()))
        target.rename(saved)
        print('[Swiftly] Removed active GUI; backup: '+str(saved))
    for name in names:
        (control/name).unlink(missing_ok=True)
    print('[Swiftly] Uninstalled. Backups and unrelated files kept; settings '+('removed.' if args.purge else 'preserved.'))


try:
    main()
except (ValueError, OSError, subprocess.SubprocessError) as error:
    raise SystemExit('[Swiftly] ERROR: '+str(error))
PY
