# Swiftly

Swiftly Part 2 provides a JSON configuration, a Quickshell bridge with IPC,
and installers for an existing Hyprland setup. **The Part 1 GUI is not included.**
This repository is a tested integration bundle, not a complete desktop GUI.

## Quick setup with curl

Download the small installer (works from Bash or fish):

```bash
curl -fL https://raw.githubusercontent.com/laurentiu2013md-glitch/Swiftly/main/install.sh -o swiftly-install.sh
```

**Config only** — install defaults and keep any existing config:

```bash
bash swiftly-install.sh config
```

**GUI + config** — on Arch Linux with Hyprland running, use your existing Part 1
GUI directory containing `shell.qml` and your actual loaded Hyprland config:

```bash
bash swiftly-install.sh full /path/to/gui ~/.config/hypr/hyprland.lua
# Or use ~/.config/hypr/hyprland.conf for an existing .conf setup.
```

The GUI must instantiate `SwiftlyBridge` once. Review the generated gesture block
before `hyprctl reload`. Then start `qs -p ~/.config/quickshell/swiftly` (adjust
for a custom `XDG_CONFIG_HOME`). Existing JSON is preserved; replaced GUI trees
and changed files receive backups. Full setup copies your GUI; it cannot supply
the missing Part 1. See [integration details](swiftly/README.md).

Optional network bootstrap check: `python3 tests/bootstrap_tests.py "$PWD"`.
It downloads real pinned files and mocks desktop/package commands.

The downloader pins a tested source revision and checks each downloaded file's
SHA256 before running it. Run it as your normal user.

## Tests

From the repository root:

```bash
bash -n install.sh swiftly/install-all.sh swiftly/install-config.sh tools/setup-cloud-runtime.sh
python3 -m json.tool swiftly/config.json >/dev/null
python3 -m compileall -q verify_swiftly.py swiftly/support.py tests
python3 verify_swiftly.py
python3 tests/extended_tests.py "$PWD"
```

For the Debian cloud workspace, prepare an isolated official-package runtime
without modifying system packages:

```bash
bash tools/setup-cloud-runtime.sh /workspace/scratch/swiftly-cloudtest
/workspace/scratch/swiftly-cloudtest/bin/qmllint swiftly/SwiftlyBridge.qml
python3 tests/runtime_tests.py "$PWD" /workspace/scratch/swiftly-cloudtest/bin/qs /workspace/scratch/swiftly-cloudtest/logs/repo-runtime
```

The cloud setup uses Debian unstable packages privately because Quickshell is
not in Debian 13 stable. It requires network access to `deb.debian.org`, APT,
`dpkg-deb`, Python 3, and the Debian archive keyring. It resolves current official
packages; recorded versions are in [the test report](TEST_REPORT.md).

Installer tests mock compositor and package commands. Runtime tests launch two
real offscreen minimal shells and exercise IPC and live JSON reload. They do not
validate the missing GUI, a real Hyprland session, or physical gestures.
Quickshell 0.3.2 may return exit code 0 for a rejected IPC call; inspect its output.

Original source: GPL-3.0-only; see [LICENSE](LICENSE).
