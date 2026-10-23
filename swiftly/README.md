# Swiftly — GUI and integration

Source files in this bundle are GPL-3.0-only; the complete GPLv3 text
is in COPYING. Runtime packages keep their respective licenses. Reference
artwork is not included or redistributed.

## Files

- config.json: defaults; installed to $XDG_CONFIG_HOME/swiftly/config.json
  (normally ~/.config/swiftly/config.json).
- install-config.sh: installs a missing config and always keeps an existing one.
- gui/: minimal widget cards and animation settings (Fade, Slide, Zoom, None).
- install-all.sh: installs runtime packages, copies the bundled or your custom GUI, installs the
  bridge/helper, and adds one managed gesture block to a selected Hyprland file.
- support.py: Python standard-library helper; stages/backups GUI replacements,
  writes gesture changes atomically and supports --gestures-only and --check.
- SwiftlyBridge.qml: live JSON adapter, transient widget indices and IPC handler.
- COPYING: complete GPLv3 license text.

The minimal GUI is included in gui/. Pass only your Hyprland config to use it:
`bash install-all.sh /path/to/hyprland.lua` (or .conf). A second, leading GUI
argument still selects a custom GUI directory. The installer copies the GUI to
$XDG_CONFIG_HOME/quickshell/swiftly and injects SwiftlyBridge.qml.

## Bundled GUI

The body is transparent and borderless, with no outer padding. The switching
strip is invisible and shares the widget window without reserving a side column.
New configs use the rightmost 10%; configs missing `interaction.clickEdgeStart`
retain a 5% strip. The area outside it is a click-through, read-only display.
There are no widget indicators or on-card settings controls. Open settings using
`qs -p ~/.config/quickshell/swiftly ipc call swiftly settings` or a launcher.
Settings can be dismissed with Escape. Existing dimensions and colors are kept.

The cards show a clock, today's date, and MPRIS media metadata. Media controls,
a month grid, arbitrary third-party widget types and monitor hotplug workflows
are outside this minimal implementation. Monitor names select an output; an
empty/unavailable name falls back to the first screen.

Settings offers Fade (default), Slide, Zoom, or None,
set a duration from 0 to 2000 ms, and press Save. Closing without Save discards
those edits. Missing/unknown animation presets fall back to Fade, so existing
configs need no migration. None or duration 0 disables transitions.

Click, wheel, and swipe switching use the configured right-edge strip. Up/left
advances and down/right reverses; scrollInvert reverses wheel input. There is no
switching MouseArea outside the configured strip. Compositor swipe IPC is also gated by
hovering over the target card's strip. Explicit next/previous IPC remains useful
for automation. Touchscreen and physical trackpad behavior need desktop testing.

## Integrating a custom GUI

Instantiate exactly one SwiftlyBridge in the main shell.qml. Bind the stack model
to bridge.config.stacks, style to bridge.config.theme, and widget selection to
bridge.indexFor(stack.id). Bind these values; do not copy them just at startup.
Connect bridge.settingsRequested to Part 1's settings window/launcher. A separate
settings process should edit config.json and should not instantiate a second
bridge/IpcHandler for the widget runtime.

For local wheel/swipe handling, honor config.interaction and call
bridge.step(stack.id, +1) or bridge.step(stack.id, -1). Local single-finger
touchscreen handling inside your QML surface is a Part 1 responsibility.

The included bridge uses FileView.watchChanges + onFileChanged: reload() and
JsonAdapter properties, so valid file edits reload without restarting Quickshell.
It deliberately saves only on explicit saveConfig(), avoiding automatic writes
back during file loads. Reassign a whole var object/array after editing nested
members, then save; nested mutation alone does not notify QML. Handle saveFailed
and saved in your settings GUI. Validate all fields before saving; the helper
only validates the schema version, stack identifiers and compositor gestures.
For external settings writers, save atomically using temp-file + rename.

Changing compositor fingers/directions requires regenerating Hyprland's block.
After a successful JSON save, the GUI can run the helper's --gestures-only mode,
then hyprctl reload if it succeeds. Use a debounce/explicit Apply button. The
bridge ignores stale swipe IPC messages while this is pending. Geometry, theme
and widget-list changes only require the live JSON reload.

## Field reference

| Field | Meaning |
| --- | --- |
| schemaVersion | Contract version; currently integer 1. |
| theme.mode | dark or light; GUI preset selector. Colors below are explicit; switching mode alone does not calculate a palette. |
| theme.background | Custom GUI surface color; the bundled card body is always transparent. All colors use Qt #AARRGGBB (alpha first). |
| theme.foreground | Main text color. |
| theme.muted | Secondary text color. |
| theme.accent | Selection/active indicator color. |
| theme.border | Custom GUI outline color; the bundled card has no outer border. |
| interaction.wrap | Continue from final widget to first, and reverse. |
| interaction.scrollEnabled | Allow wheel/two-finger scrolling over a card. |
| interaction.scrollInvert | Reverse the local wheel switching direction. |
| interaction.swipeEnabled | Allow local QML pointer/touch swipes over a card. |
| interaction.swipeThreshold | Local swipe recognition distance in logical pixels; positive. |
| interaction.animationMs | Transition duration, 0–2000 ms; zero disables animation. |
| interaction.animationPreset | fade (default), slide, zoom, or none. Missing/unknown values use fade. |
| gestures.enabled | Enable compositor trackpad gestures; independent of local QML input. |
| gestures.fingers | Integer 3–9; four defaults to leaving common three-finger workspace gestures available. Hardware may support fewer. |
| gestures.nextDirection | left/right/up/down gesture that advances the target stack. |
| gestures.previousDirection | Distinct direction that goes back. |
| gestures.targetStack | Explicit stack ID controlled by global trackpad gestures; default daily. |
| stacks | Ordered stack definitions; IDs must be unique. |
| stacks[].id | Stable letters/numbers/underscore/hyphen identifier, also used by IPC. |
| stacks[].enabled | Show/operate this stack. |
| stacks[].monitor | Output name, e.g. eDP-1; bundled GUI defaults to the first screen. |
| stacks[].position.anchor | top-left/top-right/bottom-left/bottom-right relative to the selected output's usable area. |
| stacks[].position.x/y | Nonnegative inward horizontal/vertical margins in logical pixels. |
| stacks[].size.width/height | Positive card dimensions in logical pixels. |
| stacks[].cornerRadius | Custom GUI corner radius; bundled pill radii follow their geometry. |
| stacks[].initialIndex | Zero-based starting widget; bridge clamps it to the current widget list. Current indices are transient. |
| stacks[].widgets | Ordered nonempty widget list; IDs unique within the stack. |
| stacks[].widgets[].id | Stable widget instance ID. |
| stacks[].widgets[].type | Bundled GUI supports clock, calendar (today’s date), and media (MPRIS metadata). |
| stacks[].widgets[].options | Widget-specific data. Clock format HH:mm; calendar firstDayOfWeek 1 means Monday; media has no options in this example. The minimal date widget does not use firstDayOfWeek. |

Size, radius and position semantics are the Swiftly contract, not automatic
properties of Quickshell. The bundled card clamps geometry; a custom GUI must do so too. Use a suitable
layer-shell PanelWindow for anchored desktop cards; compositor-managed floating
windows cannot be assumed to accept arbitrary absolute desktop positions.

## Install and test from fish

Run these commands as your normal user. No chmod is necessary with bash.

```fish
hyprctl version
qs --version
bash install-config.sh
# Use the bundled GUI; pass the actual loaded config file.
bash install-all.sh ~/.config/hypr/hyprland.lua
# For an existing hyprlang configuration instead:
# bash install-all.sh ./gui ~/.config/hypr/hyprland.conf
hyprctl reload
hyprctl configerrors
qs -p ~/.config/quickshell/swiftly
```

In another terminal:

```fish
qs -p ~/.config/quickshell/swiftly ipc show
qs -p ~/.config/quickshell/swiftly ipc call swiftly index daily
qs -p ~/.config/quickshell/swiftly ipc call swiftly next daily
qs -p ~/.config/quickshell/swiftly ipc call swiftly previous daily
qs -p ~/.config/quickshell/swiftly ipc call swiftly swipe left 4
qs -p ~/.config/quickshell/swiftly ipc call swiftly settings
```

Change the accent or width in config.json while running to check live bindings.
After changing the gesture settings, regenerate the managed block:

```fish
python3 ~/.config/swiftly/support.py ~/.config/quickshell/swiftly ~/.config/hypr/hyprland.lua --gestures-only
# Only reload if the helper succeeds:
and hyprctl reload
hyprctl configerrors
```

Replace ~/.config with $XDG_CONFIG_HOME in the commands above if it is customized.
Use exactly the same -p path when starting and sending IPC. Explicit path
selection also works when another Quickshell shell lives at the base config root.

## Install behavior and limits

The scripts use Bash, set -euo pipefail, normal-user writes and temporary files.
Existing JSON is always kept. Replaced GUI trees, support.py and Hyprland files
get .bak.<nanoseconds> backups alongside them. Identical content creates no new
backup. Replacing a GUI tree preserves its complete previous tree in a backup,
including locally added files; it does not merge old assets into the new GUI.
If staging fails, the current GUI remains in place; if final rename fails,
the previous GUI is restored. The entire install is not a single transaction:
successfully installed packages/files remain if a later step fails.

Dependencies: python (helper), qt6-declarative (QtQuick/Controls), qt6-svg (SVG),
qt6-imageformats (WebP/other image formats), quickshell (runtime/IPC). Pacman
resolves transitive dependencies. No extra gesture daemon is used. Already
installed qs is preserved. The default release package uses pacman; only when
it is unavailable does the installer use an already detected paru or yay.
Neither an AUR helper nor hyprgrass is installed by default. No sudo is used
for user files; pacman gets sudo only when packages are missing. If Part 1
uses other modules/programs, add those packages to install-all.sh's dependency
list; they cannot be inferred from an unseen GUI.

Hyprland >=0.51 is required. The helper reads hyprctl version and the selected
file's extension: .lua needs >=0.55; .conf uses deprecated hyprlang even on
newer Hyprland. It never migrates an existing config. No shell autostart is
added. The selected Hyprland file must already be loaded and must be writable,
regular, top-level configuration. Symlink destinations and GUI trees containing
symlinks/special files are refused; edit the real dotfile source or supply an
ordinary copy. Command paths accept letters/numbers, slash, underscore, dot,
hyphen and spaces; other characters are refused instead of risking expansion.

Existing same-finger hyprlang gestures, or any other direct hl.gesture call in
the selected Lua file, cause a safe refusal. Review included files and dynamic
Lua bindings too: this helper does not evaluate/arbitrarily rewrite your config
tree. Resolve collisions or select a dedicated already-loaded include file.
Do not bind the same fingers/directions both to workspace switching and Swiftly.
Generated gestures are global, always targeting gestures.targetStack; they are
discrete next/previous changes, not interactive 1:1 card animation. Mouse/scroll
and swipe transitions in the bundled cards use the selected preset; custom GUIs implement their own transitions.

## Optional touchscreen gestures

Touch swipes entirely within a Swiftly QML surface can be handled in Part 1
without a compositor plugin. Global desktop touchscreen gestures need another
input integration such as hyprgrass; trackpad gestures alone do not provide it.
For a hyprgrass revision compatible with your exact Hyprland build, optional
installation from fish is:

```fish
sudo pacman -S --needed base-devel cpio cmake git meson ninja glm
hyprpm add https://github.com/horriblename/hyprgrass
hyprpm enable hyprgrass
hyprpm reload
```

Check hyprpm list and the upstream docs for the pinned plugin revision. Its
current main documentation uses hl.plugin.hyprgrass.gesture with a swipe
pattern and a Lua callback, which can execute the same qs IPC command. Older
plugin revisions use different binding syntax; do not apply current Lua
examples to those. Plugin/Hyprland ABI compatibility is not guaranteed here.
To load enabled plugins at login, use exec-once = hyprpm reload in hyprlang,
or hl.on("hyprland.start", function() hl.exec_cmd("hyprpm reload") end) in Lua.

## Reference URLs from the supplied bundle

- Hyprland 0.51/0.54 hyprlang gestures:
  https://wiki.hypr.land/0.51.0/Configuring/Gestures/
  https://wiki.hypr.land/0.54.0/Configuring/Gestures/
- Hyprland 0.55 Lua gestures:
  https://wiki.hypr.land/0.55.0/Configuring/Advanced-and-Cool/Gestures/
- Quickshell 0.3.2 FileView/JsonAdapter/IpcHandler:
  https://quickshell.org/docs/v0.3.2/types/Quickshell.Io/FileView/
  https://quickshell.org/docs/v0.3.2/types/Quickshell.Io/JsonAdapter/
  https://quickshell.org/docs/v0.3.2/types/Quickshell.Io/IpcHandler/
- Quickshell path/config selection and Arch install guide:
  https://quickshell.org/docs/v0.3.1/guide/introduction/
  https://quickshell.org/docs/v0.3.1/guide/install-setup/
- Plugin manager and hyprgrass:
  https://wiki.hypr.land/Plugins/Using-Plugins/
  https://github.com/horriblename/hyprgrass
  https://github.com/horriblename/hyprgrass/blob/main/docs/configuration.md
- Official HyperOS 4 page and widget-stack reference image:
  https://hyperos.mi.com/
  https://cia.hyperos.mi.com/hyperos4homepage/aesthetics_widgetStack_2-poster.jpg
- Samsung stack behavior/images:
  https://www.samsung.com/ca/support/mobile-devices/use-widgets-on-your-galaxy-phone/

Validation in this cloud workspace (2026-10-23): Bash syntax, JSON parsing,
Python compilation, the supplied installer verifier, 19 extended installer
checks, qmllint 6.11.2, and 8 real headless Quickshell 0.3.2 runtime groups passed
after the fixes described in ../TEST_REPORT.md. Package/Hyprland commands in
installer tests are mocked; runtime IPC and FileView tests use real Quickshell.
The original bundle did not supply Part 1. The new minimal GUI has separate
real headless Wayland/input tests recorded in ../TEST_REPORT.md; a real Hyprland
session and physical gesture hardware are not supplied.
No full GUI, compositor parsing/reload or hardware gesture validation is claimed.
Direct documentation sites were proxy-blocked; current official documentation
sources were checked through their GitHub mirrors. See ../TEST_REPORT.md.

## Automatic reload after updating

Full installs record their Hyprland config and optional custom GUI source in
$XDG_CONFIG_HOME/swiftly/install-state.json, and install update.sh beside it.
Run `bash ~/.config/swiftly/update.sh` to fetch the latest verified bundle and
reload the app/widgets. Older installs need the Hyprland config path once; giving
a path explicitly selects the bundled GUI. For a custom GUI, reinstall once with
`install-all.sh GUI_DIRECTORY HYPRLAND_CONFIG` to record that source, then omit
paths when updating. State and config live outside the replaceable GUI tree.

`--reload-only` skips downloading. Reload IPC uses Quickshell.reload(true), waits
for a new generation and real widget readiness, and preserves JSON. Selections
are transient and reset to initialIndex on hard reload. A brief busy-IPC response
is retried; it does not trigger a legacy restart. An old shell without reload
IPC is restarted only after matching its exact config path and PID. No global
pkill or all-shell kill is used. A stopped app is started with no-duplicate mode.

A failed download stops before installation. Installation retains its documented
nontransactional behavior; a failure is reported without an explicit reload, and
existing backups remain available. Gesture changes still need review and a
Hyprland reload; the updater reloads the app/widgets. Custom GUIs can bind the
bridge's widgetsReady property to their own widget creation readiness.

## Widget size controls

Settings includes editable Width and Height fields (logical pixels) for the selected
enabled stack. Save updates `stacks[].size` and the animation fields together in one
explicit write; Close discards drafts. Width must be an integer from 120 to 8192;
height must be an integer from 100 to 8192. Invalid dimensions leave the config
unchanged. Existing widget definitions and stack placement are preserved.

The card has no indicator dots or settings button. Use the settings IPC command
or a desktop launcher to open settings. `interaction.clickEdgeStart` defaults to
0.9 in new configs and falls back to 0.95 for older configs. Click advances one
widget; recognized swipes do not also count as clicks.

## Location controls

Select Top left, Top right, Bottom left, or Bottom right and edit horizontal/vertical
insets in pixels. Insets are nonnegative integers up to 32768, measured inward
from the selected screen edges. Size, location, and animation are saved together;
closing without Save discards the changes. Settings scrolls within a fixed window
while its Save and Close buttons stay visible.
