# Swiftly — Part 2

Original source files in this bundle are GPL-3.0-only; the complete GPLv3 text
is in COPYING. Runtime packages keep their respective licenses. Reference
artwork is not included or redistributed.

## Files

- config.json: defaults; installed to $XDG_CONFIG_HOME/swiftly/config.json
  (normally ~/.config/swiftly/config.json).
- install-config.sh: installs a missing config and always keeps an existing one.
- install-all.sh: installs runtime packages, copies your Part 1 GUI, installs the
  bridge/helper, and adds one managed gesture block to a selected Hyprland file.
- support.py: Python standard-library helper; stages/backups GUI replacements,
  writes gesture changes atomically and supports --gestures-only and --check.
- SwiftlyBridge.qml: live JSON adapter, transient widget indices and IPC handler.
- COPYING: complete GPLv3 license text.

Part 1 is not included. Provide its complete GUI directory, containing shell.qml,
including its separate settings GUI and all local imports/assets. The installer
copies this directory to $XDG_CONFIG_HOME/quickshell/swiftly. It does not rewrite
your shell.qml. SwiftlyBridge.qml is a reserved name in that directory.

## Integration with Part 1

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
| theme.background | Card surface color. All colors use Qt #AARRGGBB (alpha first). |
| theme.foreground | Main text color. |
| theme.muted | Secondary text color. |
| theme.accent | Selection/active indicator color. |
| theme.border | Card outline color. |
| interaction.wrap | Continue from final widget to first, and reverse. |
| interaction.scrollEnabled | Allow wheel/two-finger scrolling over a card. |
| interaction.scrollInvert | Reverse the local wheel switching direction. |
| interaction.swipeEnabled | Allow local QML pointer/touch swipes over a card. |
| interaction.swipeThreshold | Local swipe recognition distance in logical pixels; positive. |
| interaction.animationMs | Part 1 transition duration in milliseconds; zero disables animation. |
| gestures.enabled | Enable compositor trackpad gestures; independent of local QML input. |
| gestures.fingers | Integer 3–9; four defaults to leaving common three-finger workspace gestures available. Hardware may support fewer. |
| gestures.nextDirection | left/right/up/down gesture that advances the target stack. |
| gestures.previousDirection | Distinct direction that goes back. |
| gestures.targetStack | Explicit stack ID controlled by global trackpad gestures; default daily. |
| stacks | Ordered stack definitions; IDs must be unique. |
| stacks[].id | Stable letters/numbers/underscore/hyphen identifier, also used by IPC. |
| stacks[].enabled | Show/operate this stack. |
| stacks[].monitor | Hyprland output name, e.g. eDP-1; empty means Part 1 chooses the focused output when creating the surface. |
| stacks[].position.anchor | top-left/top-right/bottom-left/bottom-right relative to the selected output's usable area. |
| stacks[].position.x/y | Nonnegative inward horizontal/vertical margins in logical pixels. |
| stacks[].size.width/height | Positive card dimensions in logical pixels. |
| stacks[].cornerRadius | Nonnegative logical pixels; clamp to half the shorter dimension. |
| stacks[].initialIndex | Zero-based starting widget; bridge clamps it to the current widget list. Current indices are transient. |
| stacks[].widgets | Ordered nonempty widget list; IDs unique within the stack. |
| stacks[].widgets[].id | Stable widget instance ID. |
| stacks[].widgets[].type | Part 1 registry key; clock/calendar/media are proposed keys, not built-in Quickshell widget types. |
| stacks[].widgets[].options | Widget-specific data. Clock format HH:mm; calendar firstDayOfWeek 1 means Monday; media has no options in this example. Part 1 must implement these keys. |

Size, radius and position semantics are the Swiftly contract, not automatic
properties of Quickshell. Part 1 must implement/clamp them. Use a suitable
layer-shell PanelWindow for anchored desktop cards; compositor-managed floating
windows cannot be assumed to accept arbitrary absolute desktop positions.

## Install and test from fish

Run these commands as your normal user. No chmod is necessary with bash.

```fish
hyprctl version
qs --version
bash install-config.sh
# Put Part 1 in ./gui; pass the actual loaded config file.
bash install-all.sh ./gui ~/.config/hypr/hyprland.lua
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
and touch animations within cards remain part of Part 1.

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
Part 1, a Hyprland session and physical gesture hardware are not supplied.
No full GUI, compositor parsing/reload or hardware gesture validation is claimed.
Direct documentation sites were proxy-blocked; current official documentation
sources were checked through their GitHub mirrors. See ../TEST_REPORT.md.
