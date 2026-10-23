#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Install GUI assets and/or sync a single managed Hyprland gesture block."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import time


def say(message):
    print(f"[Swiftly] {message}", flush=True)


def backup(path):
    target = path.with_name(path.name + f".bak.{time.time_ns()}")
    shutil.copy2(path, target)
    say(f"Backup: {target}")
    return target


def write(path, data):
    if path.is_symlink():
        raise ValueError(f"Refusing symlink: {path}")
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".swiftly-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
            backup(path)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    say(f"Updated: {path}")
    return True


def snapshot(path):
    result = {}
    for entry in path.rglob("*"):
        if entry.is_symlink() or not (entry.is_file() or entry.is_dir()):
            raise ValueError(f"GUI must contain only regular files/directories: {entry}")
        result[str(entry.relative_to(path))] = (
            entry.read_bytes() if entry.is_file() else None,
            stat.S_IMODE(entry.stat().st_mode),
        )
    return result


def install_gui(source, target, bridge):
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".swiftly-", dir=target.parent))
    old = None
    try:
        shutil.copytree(source, stage, dirs_exist_ok=True)
        shutil.copy2(bridge, stage / "SwiftlyBridge.qml")
        if target.exists() and snapshot(stage) == snapshot(target):
            say("GUI unchanged.")
            return
        if target.exists():
            old = target.with_name(target.name + f".bak.{time.time_ns()}")
            target.rename(old)
            say(f"GUI backup: {old}")
        try:
            stage.rename(target)
        except BaseException:
            if old is not None:
                old.rename(target)
            raise
        say(f"GUI installed: {target}")
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def validate(config):
    if not isinstance(config, dict):
        raise ValueError("Config must be a JSON object")
    if type(config.get("schemaVersion")) is not int or config["schemaVersion"] != 1:
        raise ValueError("Expected schemaVersion 1")
    stacks = config["stacks"]
    if not isinstance(stacks, list) or not stacks:
        raise ValueError("stacks must be a nonempty array")
    if any(not isinstance(stack, dict) for stack in stacks):
        raise ValueError("Each stack must be an object")
    ids = [stack["id"] for stack in stacks]
    if any(not isinstance(i, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", i) for i in ids):
        raise ValueError("Stack IDs must contain only letters, numbers, _ or -")
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate stack IDs")
    supplied = config.get("gestures", {})
    if not isinstance(supplied, dict):
        raise ValueError("gestures must be an object")
    # Older configs may omit gesture fields. Resolve defaults in memory only;
    # never replace the user's JSON. Missing enabled stays disabled.
    g = {"enabled": False, "fingers": 4, "nextDirection": "left",
         "previousDirection": "right", "targetStack": ids[0], **supplied}
    if type(g["enabled"]) is not bool:
        raise ValueError("gestures.enabled must be boolean")
    if type(g["fingers"]) is not int or not 3 <= g["fingers"] <= 9:
        raise ValueError("gestures.fingers must be an integer from 3 to 9")
    directions = {"left", "right", "up", "down"}
    if g["nextDirection"] not in directions or g["previousDirection"] not in directions:
        raise ValueError("Gesture directions must be left/right/up/down")
    if g["nextDirection"] == g["previousDirection"] or g["targetStack"] not in ids:
        raise ValueError("Use distinct directions and an existing targetStack")
    return g


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gui", type=Path)
    parser.add_argument("hypr", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--gestures-only", action="store_true")
    parser.add_argument("--bundled-gui", action="store_true")
    args = parser.parse_args()
    root = Path(os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config"))
    if not root.is_absolute():
        raise ValueError("XDG_CONFIG_HOME must be absolute")
    base = Path(__file__).resolve().parent
    config_path = root / "swiftly/config.json"
    config = json.loads((config_path if config_path.exists() else base / "config.json").read_text())
    g = validate(config)
    hypr = args.hypr.expanduser().absolute()
    if hypr.is_symlink() or not hypr.is_file():
        raise ValueError("Pass a regular Hyprland config file, not a symlink")
    if hypr.suffix not in {".lua", ".conf"}:
        raise ValueError("Expected .lua or .conf config")
    version = subprocess.check_output(["hyprctl", "version"], text=True)
    match = re.search(r"\b(?:v)?(\d+)\.(\d+)\.(\d+)\b", version)
    if not match:
        raise ValueError("Cannot identify Hyprland version; run hyprctl version")
    numbers = tuple(map(int, match.groups()))
    if numbers < (0, 51, 0):
        raise ValueError("Built-in custom gestures require Hyprland >= 0.51")
    lua = hypr.suffix == ".lua"
    if lua and numbers < (0, 55, 0):
        raise ValueError("Lua support requires Hyprland >= 0.55")
    say(f"Hyprland {match.group(0)}; using {'Lua' if lua else 'hyprlang'} from config extension")
    # Use the actual file format: 0.55+ may still use deprecated .conf files.
    comment = "--" if lua else "#"
    begin, end = (f"{comment} {label} SWIFTLY GESTURES" for label in ("BEGIN", "END"))
    original = hypr.read_text()
    if original.count(begin) != original.count(end) or original.count(begin) > 1:
        raise ValueError("Malformed/duplicate Swiftly managed block; refusing edit")
    pattern = re.compile(r"(?m)^" + re.escape(begin) + r"\n[\s\S]*?^" + re.escape(end) + r"(?:\n|$)")
    outside, count = pattern.subn("", original)
    if original.count(begin) != count:
        raise ValueError("Managed markers are not complete lines")
    if outside.count("SWIFTLY GESTURES"):
        raise ValueError("Unexpected Swiftly markers outside managed block")
    # Catch gestures in this file; included configs/dynamic Lua need user review.
    if g["enabled"]:
        if lua:
            conflict = re.search(r"\bhl\s*\.\s*gesture\s*\(", outside)
        else:
            conflict = re.search(r"(?m)^\s*gesture\w*\s*=\s*" + str(g["fingers"]) + r"\s*,", outside)
        if conflict:
            raise ValueError("Existing gestures in selected file: resolve conflicts or choose a dedicated included file")
    gui = args.gui.expanduser().absolute()
    target = root / "quickshell/swiftly"
    qs = shutil.which("qs")
    if not qs:
        raise ValueError("qs is not installed")
    for path in (qs, str(target)):
        # Hyprlang treats # and $ specially; reject rather than misquote them.
        if not re.fullmatch(r"/[a-zA-Z0-9_./ -]+", path):
            raise ValueError(f"Unsupported command path characters: {path}")
    lines = [begin]
    if g["enabled"]:
        for direction in (g["nextDirection"], g["previousDirection"]):
            command = shlex.join([qs, "-p", str(target), "ipc", "call", "swiftly", "swipe", direction, str(g["fingers"])])
            if lua:
                lines.append(f'hl.gesture({{ fingers = {g["fingers"]}, direction = "{direction}", action = function() hl.exec_cmd({json.dumps(command)}) end }})')
            else:
                lines.append(f'gesture = {g["fingers"]}, {direction}, dispatcher, exec, {command}')
    lines.append(end)
    block = "\n".join(lines) + "\n"
    updated = pattern.sub(lambda _: block, original) if count else original + ("" if original.endswith("\n") else "\n") + block
    if not args.gestures_only:
        if not (gui / "shell.qml").is_file() or gui.is_symlink():
            raise ValueError("GUI must be a regular directory containing shell.qml")
        if target.is_symlink() or (target.exists() and not target.is_dir()):
            raise ValueError("GUI destination must be a regular directory")
        if gui.resolve() == target.resolve() or target.resolve() in gui.resolve().parents or gui.resolve() in target.resolve().parents:
            raise ValueError("Source and destination GUI trees must not overlap")
        snapshot(gui)
        if target.exists():
            snapshot(target)
        if (gui / "SwiftlyBridge.qml").exists() and (gui / "SwiftlyBridge.qml").read_bytes() != (base / "SwiftlyBridge.qml").read_bytes():
            raise ValueError("Reserved SwiftlyBridge.qml already differs in GUI source")
    if args.check:
        say("Preflight passed. Review gesture conflicts in included Hyprland files too.")
        return
    if not args.gestures_only:
        install_gui(gui, target, base / "SwiftlyBridge.qml")
        write(root / "swiftly/support.py", Path(__file__).read_bytes())
        write(root / "swiftly/update.sh", (base / "update.sh").read_bytes())
        write(root / "swiftly/uninstall.sh", (base / "uninstall.sh").read_bytes())
    if write(hypr, updated.encode()):
        say("Gesture config updated; run hyprctl reload after reviewing it.")
    else:
        say("Gesture config unchanged.")
    if not args.gestures_only:
        state = {"schemaVersion": 1, "hyprlandConfig": str(hypr),
                 "guiDirectory": None if args.bundled_gui else str(gui)}
        write(root / "swiftly/install-state.json", (json.dumps(state, indent=2) + "\n").encode())


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f"[Swiftly] ERROR: {error}")
