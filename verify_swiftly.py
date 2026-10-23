import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

with tempfile.TemporaryDirectory(prefix="swiftly-tests-") as temporary:
    root = Path(temporary)
    root.chmod(0o755)
    bundle = root / "bundle"
    shutil.copytree("swiftly", bundle)
    home = root / "user home"
    home.mkdir()
    gui = root / "gui"
    gui.mkdir()
    (gui / "shell.qml").write_text("// Part 1 fixture\n")
    mock = root / "bin"
    mock.mkdir()
    for name, text in {
        "hyprctl": '#!/bin/bash\nprintf "Hyprland %s built from branch main\\n" "${TEST_VERSION:-0.55.0}"\n',
        "qs": '#!/bin/bash\necho "quickshell 0.3.2"\n',
        "pacman": '#!/bin/bash\n[[ $1 = -T || $1 = -Si ]] || exit 99\n',
        "sudo": '#!/bin/bash\necho "unexpected sudo" >&2\nexit 99\n',
    }.items():
        (mock / name).write_text(text)
        (mock / name).chmod(0o755)
    hypr = home / "hyprland.lua"
    hypr.write_text("-- User config\n")
    # Keep production guards as a normal user. Under root, check refusal first,
    # then bypass only that guard in private test copies to test install logic.
    for name in ("install-config.sh", "install-all.sh"):
        if os.geteuid() == 0:
            denied = subprocess.run(["bash", str(bundle / name)], capture_output=True)
            assert denied.returncode != 0
            script = bundle / name
            script.write_text("\n".join(line for line in script.read_text().splitlines() if not line.startswith("[[ $EUID")) + "\n")
    env = os.environ.copy()
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"), PATH=str(mock)+":/usr/bin:/bin")
    def run(*args, success=True, version="0.55.0"):
        result = subprocess.run(["env", *[f"{k}={v}" for k,v in env.items()], "TEST_VERSION="+version, *map(str,args)], text=True, capture_output=True)
        assert (result.returncode == 0) == success, (args, result.stdout, result.stderr)
        return result
    config = home / ".config/swiftly/config.json"
    run("bash", bundle / "install-config.sh")
    custom = json.loads(config.read_text())
    custom["theme"]["accent"] = "#FF123456"
    config.write_text(json.dumps(custom))
    before = config.read_bytes()
    run("bash", bundle / "install-config.sh")
    assert config.read_bytes() == before
    run("bash", bundle / "install-all.sh", gui, hypr)
    assert "hl.gesture" in hypr.read_text() and "hl.exec_cmd" in hypr.read_text()
    assert "-p" in hypr.read_text() and "swiftly swipe left 4" in hypr.read_text()
    assert len(list(home.glob("hyprland.lua.bak.*"))) == 1
    before = hypr.read_bytes()
    run("bash", bundle / "install-all.sh", gui, hypr)
    assert hypr.read_bytes() == before
    assert len(list(home.glob("hyprland.lua.bak.*"))) == 1
    assert len(list((home / ".config/quickshell").glob("swiftly.bak.*"))) == 0
    (gui / "shell.qml").write_text("// Updated Part 1 fixture\n")
    run("bash", bundle / "install-all.sh", gui, hypr)
    assert len(list((home / ".config/quickshell").glob("swiftly.bak.*"))) == 1
    helper = home / ".config/swiftly/support.py"
    custom["gestures"]["fingers"] = 3
    custom["gestures"]["nextDirection"] = "up"
    custom["gestures"]["previousDirection"] = "down"
    config.write_text(json.dumps(custom))
    run("python3", helper, gui, hypr, "--gestures-only")
    assert 'fingers = 3, direction = "up"' in hypr.read_text()
    assert hypr.read_text().count("BEGIN SWIFTLY GESTURES") == 1
    custom["gestures"]["enabled"] = False
    config.write_text(json.dumps(custom))
    run("python3", helper, gui, hypr, "--gestures-only")
    assert "hl.gesture" not in hypr.read_text()
    custom["gestures"]["enabled"] = True
    config.write_text(json.dumps(custom))
    conf = home / "hyprland.conf"
    conf.write_text("# Hyprlang fixture\n")
    run("python3", helper, gui, conf, "--gestures-only", version="0.54.0")
    assert "gesture = 3, up, dispatcher, exec," in conf.read_text()
    run("python3", helper, gui, conf, "--gestures-only", version="0.55.0")
    run("python3", helper, gui, hypr, "--gestures-only", version="0.54.0", success=False)
    run("python3", helper, gui, conf, "--gestures-only", version="0.50.0", success=False)
    original = hypr.read_bytes()
    config.write_text("not json")
    run("python3", helper, gui, hypr, "--gestures-only", success=False)
    assert hypr.read_bytes() == original
    config.write_text(json.dumps(custom))
    hypr.write_text("-- BEGIN SWIFTLY GESTURES\n")
    run("python3", helper, gui, hypr, "--gestures-only", success=False)
    assert hypr.read_text() == "-- BEGIN SWIFTLY GESTURES\n"
    config.unlink()
    config.symlink_to(bundle / "config.json")
    run("bash", bundle / "install-config.sh", success=False)
    print("PASS: config preservation, GUI backups, repeat installs, both formats, gesture edits/disable, version gates, malformed JSON/markers, symlink refusal; no sudo/package changes.")
