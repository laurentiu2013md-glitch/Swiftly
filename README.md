# Swiftly

A compact Material 3 widget GUI for Hyprland: clock, date, and media status.
The card body is transparent and borderless, with no outer padding. Pill labels
stay visible; the narrow switcher is an overlay that reveals on hover or briefly
after a switch. It uses the same card window and reserves no content space.
New cards default to 340 × 144 pixels.
Choose **Fade**, **Slide**, **Zoom**, or **None** in settings. **Fade is the default.**

Switch widgets by scrolling or starting a swipe in the **rightmost 5% of each
card**. The rest of the card does not switch. Compositor swipe bindings also
require the pointer to be over that strip. Tap the rail menu for animation settings;
changes persist only when you press Save. The read-only area outside the rail
lets clicks through to the desktop. Media status uses your MPRIS player.

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

Older configs with missing gesture fields use four fingers, left/right for
next/previous, and the first stack as the target. Existing values are retained;
missing `enabled` leaves gestures disabled. These defaults apply in memory and
do not rewrite your JSON. Explicit invalid values still produce an error.

## Update and reload

For the first update from an older installation:

```bash
curl -fL https://raw.githubusercontent.com/laurentiu2013md-glitch/Swiftly/main/swiftly/update.sh -o swiftly-update.sh
bash swiftly-update.sh ~/.config/hypr/hyprland.lua
```

Use your existing `.conf` instead if appropriate. Future updates remember the
installation and need no paths:

```bash
bash ~/.config/swiftly/update.sh
```

The script installs the latest verified bundle, keeps your JSON/backups, then
reloads the app and recreates its widgets. It checks a new app generation and
widget readiness before reporting success. An inactive app starts automatically;
older versions without reload IPC get a restart scoped to Swiftly's config path.
Other Quickshell shells are left running. Adjust paths for `XDG_CONFIG_HOME`.
To reload installed files without downloading: `bash ~/.config/swiftly/update.sh --reload-only`.

## Uninstall

```bash
bash ~/.config/swiftly/uninstall.sh
```

For older installs, download the standalone script and pass your Hyprland config:

```bash
curl -fL https://raw.githubusercontent.com/laurentiu2013md-glitch/Swiftly/main/uninstall.sh -o swiftly-uninstall.sh
bash swiftly-uninstall.sh ~/.config/hypr/hyprland.lua
```

Use your `.conf` path if appropriate. The script stops only Swiftly, removes its
managed gesture block, and saves the GUI and changed Hyprland file as backups.
Settings, previous backups, custom GUI source, and installed system packages stay.
Add `--purge` to also remove Swiftly's `config.json`. Run `hyprctl reload` afterward.

## Development and tests

```bash
bash -n install.sh swiftly/update.sh swiftly/install-all.sh swiftly/install-config.sh tools/setup-cloud-runtime.sh
python3 -m json.tool swiftly/config.json >/dev/null
python3 -m compileall -q verify_swiftly.py swiftly/support.py tests
python3 verify_swiftly.py
python3 tests/extended_tests.py "$PWD"
python3 tests/update_tests.py "$PWD"
python3 tests/uninstall_tests.py "$PWD"
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
media player still need desktop validation. The updater unit tests mock curl/qs; GUI tests exercise real reloads and cold starts.
Optional complete network update check: add `--network-update` to the GUI test command
(real downloads, checksums and app/widgets; mocked Hyprland/package commands).
Optional network bootstrap check:
`python3 tests/bootstrap_tests.py "$PWD"`.

See [configuration and integration](swiftly/README.md) and [test evidence](TEST_REPORT.md).
Quickshell 0.3.2 can return exit code 0 for rejected IPC calls; inspect its output.
Source: GPL-3.0-only; see [LICENSE](LICENSE).
