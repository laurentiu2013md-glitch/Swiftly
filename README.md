# Swiftly

A minimal Quickshell widget GUI for Hyprland: clock, date, and media status.
Choose **Fade**, **Slide**, **Zoom**, or **None** in settings. **Fade is the default.**

Switch widgets by scrolling or starting a swipe in the **rightmost 10% of each
card**. The rest of the card does not switch. Compositor swipe bindings also
require the pointer to be over that strip. Click the gear for animation settings;
changes persist only when you press Save. Media status uses your MPRIS player.

## Setup with curl

Download the installer as your normal user:

```bash
curl -fL https://raw.githubusercontent.com/laurentiu2013md-glitch/Swiftly/main/install.sh -o swiftly-install.sh
```

**Config only** (keeps any existing config):

```bash
bash swiftly-install.sh config
```

**GUI + config**, on Arch Linux with Hyprland running:

```bash
bash swiftly-install.sh full ~/.config/hypr/hyprland.lua
# Or pass ~/.config/hypr/hyprland.conf if that is your loaded config.
```

Review the generated gesture block, then run `hyprctl reload` and:

```bash
qs -p ~/.config/quickshell/swiftly
```

Adjust paths for a custom `XDG_CONFIG_HOME`. Existing JSON is preserved; older
configs without an animation preset use Fade. Changed files and GUI trees get
backups. The downloader verifies every companion file against a pinned source
revision and SHA256 hashes. To use a separate GUI, the previous form still works:
`bash swiftly-install.sh full /path/to/gui /path/to/hyprland.lua`.

## Development and tests

```bash
bash -n install.sh swiftly/install-all.sh swiftly/install-config.sh tools/setup-cloud-runtime.sh
python3 -m json.tool swiftly/config.json >/dev/null
python3 -m compileall -q verify_swiftly.py swiftly/support.py tests
python3 verify_swiftly.py
python3 tests/extended_tests.py "$PWD"
```

Debian cloud workspace (official packages extracted privately, no system upgrade):

```bash
bash tools/setup-cloud-runtime.sh /workspace/scratch/swiftly-cloudtest
python3 tests/runtime_tests.py "$PWD" /workspace/scratch/swiftly-cloudtest/bin/qs /workspace/scratch/swiftly-cloudtest/logs/bridge
python3 tests/gui_tests.py "$PWD" /workspace/scratch/swiftly-cloudtest /workspace/scratch/swiftly-cloudtest/logs/gui
```

The GUI tests launch real headless Sway/Wayland and Quickshell, synthesize Qt input,
and check animation progress, settings saves, and the switching zone. Installer
checks mock desktop/package commands. Physical gestures and playback with a real
media player still need desktop validation. Optional network bootstrap check:
`python3 tests/bootstrap_tests.py "$PWD"`.

See [configuration and integration](swiftly/README.md) and [test evidence](TEST_REPORT.md).
Quickshell 0.3.2 can return exit code 0 for rejected IPC calls; inspect its output.
Source: GPL-3.0-only; see [LICENSE](LICENSE).
