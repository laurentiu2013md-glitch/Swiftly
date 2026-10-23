# Swiftly cloud test report — 2026-10-23

This report preserves the original attachment tests. The new bundled GUI and its
additional validation are described in the GUI follow-up at the end.

## Result

The supplied Part 2 bundle was tested in scratch outside the baseline checkout.
After corrections, Bash syntax, JSON parsing, Python compilation, the supplied
verifier, all **19 extended installer checks**, **qmllint**, and all **8 real
headless runtime groups** passed. This is validation of the installers and bridge,
not a complete Swiftly GUI or a desktop gesture demonstration.

The original ZIP is preserved. Original sources were not executed as setup
instructions merely because they were attached. Installer execution used private
temporary HOME/XDG paths and mocks for desktop/package commands. The latest user
instruction separately authorized populating and pushing the GitHub repository.

## Exact environment and tools

- OS: Debian GNU/Linux 13 (trixie), amd64.
- Bash: GNU Bash 5.2.37(1)-release.
- Main `python3`: Python 3.12.14. Installer subprocess tests with the isolated
  `/usr/bin:/bin` mock PATH use `/usr/bin/python3` 3.13.5.
- Host Qt Core: `6.8.2+dfsg-9+deb13u2`; QML/Quick: `6.8.2+dfsg-7`.
- Real test runtime: official Debian unstable `quickshell 0.3.2-1`, reporting
  `Quickshell 0.3.2 (revision , distributed by Debian)`.
- Isolated Qt Core/Gui: `6.11.2+dfsg-6`; QML/Quick and declarative tools:
  `6.11.2+dfsg-3`; `qmllint --version`: `qmllint 6.11.2`.
- Rendering environment: `QT_QPA_PLATFORM=offscreen`, software Quick backend,
  Basic controls style. The fixture is nonvisual and does not test rendering.
- No Hyprland session, `hyprctl`, Arch/pacman, or Part 1 GUI was provided.

Quickshell is absent from the official Debian 13 stable index. The available
official unstable package needs Qt 6.11.2, so mixing it with the host Qt 6.8.2 was
avoided. 216 official packages (141 MB transferred) were downloaded into scratch
and extracted into a private runtime. APT verified signed repository metadata;
all 216 SHA256 hashes were independently matched to that metadata. No system
package upgrade, root access, package maintainer scripts, or verification bypass
was used. Wrappers select the private dynamic linker, Qt libraries, QML modules
and plugins. `tools/setup-cloud-runtime.sh` reproduced this preparation from its
package cache and printed the expected tool versions. The package/hash inventory
is included in the downloadable evidence archive.

## Commands and outcomes

Commands below run from the extracted bundle root, or the resulting repository
root, unless an absolute path is shown. The original verifier was also run
unaltered from `original/` as requested.

```bash
bash -n swiftly/install-all.sh swiftly/install-config.sh
python3 -m json.tool swiftly/config.json
python3 -m compileall -q verify_swiftly.py swiftly/support.py
python3 verify_swiftly.py
```

All four commands succeeded on the original attachment. The verifier prints its
PASS summary for config preservation, GUI backups, repeat installs, both output
formats, edits/disable, version gates, malformed JSON/markers and symlink refusal.
Its `qs`, `hyprctl`, `pacman`, and `sudo` are mocks, not installed desktop tools.
The GUI is only a `shell.qml` text fixture. The original verifier removes root
refusal guards in private copies even under a normal user; the corrected verifier
keeps them under this normal-user runtime. Production root refusal was inspected
but not executed as root here.

```bash
python3 tests/extended_tests.py "$PWD"
bash -n tools/setup-cloud-runtime.sh
bash tools/setup-cloud-runtime.sh /workspace/scratch/swiftly-cloudtest
/workspace/scratch/swiftly-cloudtest/bin/qmllint swiftly/SwiftlyBridge.qml
python3 tests/runtime_tests.py "$PWD" /workspace/scratch/swiftly-cloudtest/bin/qs /workspace/scratch/swiftly-cloudtest/logs/runtime-corrected
```

- Original extended installer checks: **16 passed, 3 failed**, exit 1. All three
  failures were tracebacks for non-object JSON roots. Rejected inputs left the
  Hyprland file untouched.
- Corrected extended installer checks: **19 passed, 0 failed**, exit 0.
- Bash check and private runtime setup: exit 0.
- Corrected `qmllint` 6.11.2: exit 0, no diagnostics.
- Original runtime: **6 groups passed, 2 failed**, exit 1: `__proto__` and fractional
  initial-index cases. An earlier harness also incorrectly assumed rejected IPC
  calls must exit nonzero; this was diagnosed and corrected before this result.
- Corrected runtime: **8 groups passed, 0 failed**, exit 0.
- Final corrected syntax/JSON/Python/verifier checks also passed. The extended and
  runtime scripts report their own status and exit nonzero when an assertion fails.

## Corrections

1. `support.py`: explicitly reject non-object JSON roots, non-object stacks and
   non-object gesture settings with a clean error. Original `null`, `[]` and `42`
   roots raised uncaught AttributeError tracebacks. The fix preserves no-write
   behavior and gives a useful diagnostic.
2. `SwiftlyBridge.qml`: use own-property lookup and a null-prototype index copy.
   `__proto__` satisfies the documented stack-ID rules but could not advance in
   the original bridge. It now works in the real runtime.
3. `SwiftlyBridge.qml`: floor externally supplied fractional indices before
   clamping, keeping widget selection an integer. The default config was already
   valid; this hardens malformed external input.
4. The verifier retains the real normal-user guards, and the documentation now
   distinguishes real runtime evidence from mocks and missing desktop coverage.

## Installer inspection and additional checks

- Idempotence: rerunning unchanged installation preserves JSON and Hyprland bytes,
  does not add duplicate managed blocks or unnecessary GUI/file backups.
- Backups: original Hyprland bytes and mode are preserved; replacing a GUI keeps
  the complete previous tree, including locally added files and nested assets.
- Failure recovery: an injected final GUI rename failure restores the old tree
  and removes staging data. This is fault injection, not a real filesystem outage.
- Quoting: paths containing spaces round-trip through generated shell arguments
  and Lua JSON string escaping. Unsupported shell-special command-path characters
  are refused by inspection of the whitelist. Installer Bash expansions are quoted.
- Malformed data: schema/type errors, duplicate IDs and malformed/reversed/partial/
  duplicated markers are rejected; existing gesture conflicts and GUI/Hyprland
  symlinks are refused. Rejected cases preserve the selected Hyprland file.
- `.conf`: mocked 0.54 and 0.55 versions generate `gesture = ..., dispatcher, exec,`.
- `.lua`: mocked 0.55 generates `hl.gesture({... action = function()
  hl.exec_cmd(...) end })`; 0.54 Lua and <0.51 gesture configurations are rejected.
- Gesture updates and disabling are tested, with one managed block retained.
- Full installation is deliberately not one transaction: successful package/file
  operations can remain if a later operation fails. Version/package interactions
  are simulated; actual Arch package installation was not run on Debian.
- Conflict detection is limited to the selected file. Included configs and dynamic
  Lua are not evaluated. The installer is not a complete JSON GUI-schema validator.
- Filesystem checks are not a security boundary against a concurrently hostile
  user swapping symlinks/paths; concurrent installer writers are not serialized.

## What the real runtime exercised

Two independent minimal ShellRoot fixtures instantiate the real supplied bridge
and add a test-only observation IPC target. No bridge APIs are mocked.

1. CLI `-p` selects the child Swiftly shell separately from a base-root shell;
   an unstarted path fails selection.
2. Typed `IpcHandler` calls execute next/previous wrap, index reads, bound-index
   updates, settings signals and finger/direction-filtered swipe actions.
3. `FileView` + `JsonAdapter` reload in-place edits and repeated atomic rename
   replacements without restarting the runtime.
4. Nonwrapping clamp, widget-list shrink/empty, missing and disabled stacks.
5. Explicit `writeAdapter()` save reaches disk and reloads the second real shell.
6. Malformed JSON syntax preserves previous adapter data; a valid atomic edit
   recovers. The expected `unterminated object` warning is present in server logs.
7. A valid `__proto__` stack can advance after the fix.
8. Fractional external initialIndex normalizes to an integer after the fix.

Quickshell 0.3.2 rejects `not-int` for a typed int argument with `Unable to parse
argument 2 as "int"` and rejects unknown calls with `Function not found.` but
returns **exit status 0** for these server-side errors. Tests assert the actual
diagnostic and unchanged state rather than using exit status alone. This is an
upstream CLI behavior, not a Swiftly patch.

## Official documentation checks and blockers

Direct HTTPS requests to `quickshell.org` and `wiki.hypr.land` failed with proxy
403 / CONNECT tunnel denial. Their two hostnames were added to the saved network
draft, but a retry still failed: draft saving does not change runtime access.
Direct live website retrieval therefore remains blocked; it is not claimed.

Current official documentation/source mirrors were read successfully via the
existing read-only Git proxy:

- Quickshell source and type documentation, commit
  `9b0f339b19057f4731bf3b48293307d7ef241671`:
  <https://github.com/quickshell-mirror/quickshell>. `src/io/fileview.hpp/.cpp`
  document and implement watch/reload and directory watching for replacements;
  `jsonadapter.hpp/.cpp` cover adapters; `ipchandler.hpp` specifies typed IPC;
  `src/launch/parsecommand.cpp` documents `-p,--path` selection.
- Official website source, commit `ec7601fc67593c2ad0b352e4497555cfe809903b`:
  <https://github.com/quickshell-mirror/quickshell-web>.
  `src/guide/v0_2_0/install-setup.md` documents official Arch packages and Debian
  unstable/testing availability, consistent with the package-index results.
- Hyprland wiki source, commit `c66e8de21f5ecdc4bc5e278e7d94800ea10957af`:
  <https://github.com/hyprwm/hyprland-wiki>.
  `content/configuring/core/binds/gestures.md` documents `hl.gesture`, directions,
  2–9 fingers and Lua callback examples using `hl.exec_cmd`. Swiftly deliberately
  limits configured finger counts to 3–9. Generated Lua matches these examples.

The supplied historical `.conf` reference URLs remain in `swiftly/README.md`;
the current wiki source is Lua-based. Neither generated format was parsed or
reloaded by an actual Hyprland compositor here. No complete Part 1 GUI, real
windows, monitor placement, touchscreen input or physical trackpad/hardware
behavior was tested. Those require the missing GUI and a desktop session.

No environment publication was performed. Reusable setup/start instructions are
saved separately after validating the repository workflow; saved configuration
and this running-instance evidence do not prove restoration in a future task.

## Curl setup follow-up

Added root `install.sh` with two modes: `config` and
`full GUI_DIRECTORY HYPRLAND_CONFIG`. It downloads companion files from immutable
commit `ba0f55b8b3101ddfa985f6b7e903a2f0b79e385f`, checks each SHA256, then runs
the existing tested installer. Full mode still requires the user's Part 1 GUI.

`bash -n install.sh` and `python3 tests/bootstrap_tests.py "$PWD"` passed.
All five bootstrap groups passed: real HTTPS downloads/checksums for config-only,
repeat config preservation, real full-mode downloads with mocked compositor and
package commands, argument rejection, and injected HTTP/corrupt-download failures
with cleanup and no config changes. No new full GUI or hardware claims are made.

## Bundled GUI and animations follow-up

The user requested a new minimal GUI, four animation presets, Fade by default,
and switching only in the rightmost 10% of each card. `swiftly/gui/` now supplies
clock/date/MPRIS metadata cards, a settings window with Fade/Slide/Zoom/None and
explicit Save, and anchored layer-shell panels. Old configs without a preset use
Fade. Local wheel events and swipe start positions are restricted to a physical
10%-wide MouseArea; compositor swipe IPC additionally requires strip hover in the
bundled GUI. Explicit next/previous IPC remains available for automation.

`install-all.sh HYPRLAND_CONFIG` now installs the included GUI; its previous
`install-all.sh GUI_DIRECTORY HYPRLAND_CONFIG` form still accepts a custom GUI.
Config-only installation keeps existing JSON and needs no migration.

Cloud runtime preparation was refreshed and reproduced with 263 authenticated
official packages, adding Sway **1.12**, Qt 6.11.2 Wayland plugins and QtTest.
No system packages or user desktop files were changed. Sway runs with the
headless backend, pixman renderer, no Xwayland/background children, and a private
Wayland socket. Quickshell **0.3.2** renders the actual production PanelWindow,
card and settings components. No GUI handlers or animations are mocked.

Commands from the repository root:

```bash
bash -n install.sh swiftly/install-all.sh swiftly/install-config.sh tools/setup-cloud-runtime.sh
python3 -m json.tool swiftly/config.json
python3 -m compileall -q swiftly/support.py tests verify_swiftly.py
python3 verify_swiftly.py
python3 tests/extended_tests.py "$PWD"
python3 tests/runtime_tests.py "$PWD" /workspace/scratch/swiftly-cloudtest/bin/qs /workspace/scratch/swiftly-cloudtest/logs/gui-bridge
python3 tests/gui_tests.py "$PWD" /workspace/scratch/swiftly-cloudtest /workspace/scratch/swiftly-cloudtest/logs/gui
```

All passed: supplied verifier, **20 extended installer checks**, **8 real bridge
runtime groups**, and **7 real GUI groups**. The extra installer check exercises
bundled-GUI selection, config preservation and a repeat install with no extra
backup. The GUI suite stages production files and adds only a QtTest/IPC probe.
It tests:

1. Real panel/card/settings creation, Fade default and strip geometry.
2. Qt-generated wheel events in the left 90% do nothing; right-strip events
   advance/reverse. Test coordinates account for integer pointer pixel rounding.
3. Qt-generated mouse drags must start inside the strip to switch.
4. Real compositor swipe IPC ignores hover outside the strip and works inside.
5. Real settings ComboBox key events and Save-button clicks persist all presets.
6. Measured opacity/position/scale during running Fade/Slide/Zoom animations,
   immediate None transitions, and correct settled states.
7. Missing-preset live config falls back to Fade; a real rendered card PNG is saved.

An initial offscreen launch failed because PanelWindow has no offscreen backend;
the required GUI checks therefore use real headless Wayland, not a fake panel.
qmllint's private-prefix import lookup and upstream type metadata produce import/
unresolved metadata warnings; it is not claimed as a clean GUI type check. The
real engine compiled and ran all production components in the tests above.
The session has no DBus media player: the expected no-bus MPRIS warning and
no-player fallback were observed; real playback/metadata updates are untested.
Hardware touch/trackpad gestures and a real Hyprland session remain desktop
validation items. This adds a minimal GUI, not the previously missing full Part 1
or a complete third-party widget registry.
