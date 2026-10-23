"""Exercise actual Qt resize inputs and saves with an isolated offscreen shell.

Usage: python3 tests/size_controls_tests.py [REPOSITORY] [QS_BINARY]
Needs Quickshell, Qt Quick Controls Material, and QtTest. Never edits user config.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
qs = sys.argv[2] if len(sys.argv) > 2 else "qs"
with tempfile.TemporaryDirectory(prefix="swiftly-size-test-") as tmp:
    work = Path(tmp)
    shutil.copytree(repo / "swiftly/gui", work / "gui")
    shutil.copy2(repo / "swiftly/SwiftlyBridge.qml", work / "gui/SwiftlyBridge.qml")
    shutil.copy2(repo / "tests/size_controls.qml", work / "test.qml")
    config = work / "config/swiftly"
    config.mkdir(parents=True)
    data = json.loads((repo / "swiftly/config.json").read_text())
    data["stacks"][0]["size"] = {"width": 400, "height": 240}
    (config / "config.json").write_text(json.dumps(data))
    runtime = work / "run"
    runtime.mkdir(mode=0o700)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
               XDG_CONFIG_HOME=str(work / "config"), XDG_RUNTIME_DIR=str(runtime))
    result = subprocess.run([qs, "--no-color", "-p", str(work / "test.qml")], env=env,
                            capture_output=True, text=True, timeout=15)
    output = result.stdout + result.stderr
    print(output)
    assert result.returncode == 0 and "PASS: typed dimensions" in output and "FAIL" not in output
    saved = json.loads((config / "config.json").read_text())
    assert saved["stacks"][0]["size"] == {"width": 640, "height": 320}
    assert saved["stacks"][0]["position"] == {"anchor": "bottom-left", "x": 24, "y": 60}
    saved["stacks"][0]["size"] = data["stacks"][0]["size"]
    saved["stacks"][0]["position"] = data["stacks"][0]["position"]
    assert saved == data, "Unrelated settings changed"
    print("PASS: dimensions persisted; unrelated configuration preserved")
