#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Remote entry point: fetch a tested, immutable bundle and verify every file.
set -euo pipefail
umask 077
main() {
    [[ $EUID -ne 0 ]] || { echo '[Swiftly] Run as your normal user.' >&2; return 1; }
    local mode=${1:-}
    case "$mode" in
        config) [[ $# -eq 1 ]] || { echo 'Usage: bash install.sh config' >&2; return 1; } ;;
        full)
            if [[ $# -eq 2 ]]; then
                [[ -f $2 ]] || { echo 'Provide your existing Hyprland config.' >&2; return 1; }
            elif [[ $# -eq 3 ]]; then
                [[ -f $2/shell.qml && -f $3 ]] || { echo 'Provide your custom GUI directory and existing Hyprland config.' >&2; return 1; }
            else
                echo 'Usage: bash install.sh full [GUI_DIRECTORY] HYPRLAND_CONFIG' >&2; return 1
            fi ;;
        *) echo 'Usage: bash install.sh config | full [GUI_DIRECTORY] HYPRLAND_CONFIG' >&2; return 1 ;;
    esac
    command -v curl >/dev/null
    command -v sha256sum >/dev/null
    local revision=8ba3838d02f7969d5651ac66cefc96b7cec6a083
    local base="https://raw.githubusercontent.com/laurentiu2013md-glitch/Swiftly/$revision/swiftly"
    temporary=
    temporary=$(mktemp -d)
    # EXIT also cleans up failed downloads and installer failures.
    trap 'rm -rf -- "$temporary"' EXIT
    declare -A hashes=(
    [install-config.sh]=7bcd988aa4ebd20b630857570e7638593db9d5bb7a8372b52d3e8bb0dbcdf96a
    [config.json]=54706dd92753387f96df9466071bf1d6ad2a2f62d6ca37b0c09be8bc781bc59c
    [install-all.sh]=c372277116fc264f8859a37bdc3a6d38eb1ab812c08e4aa3d4a8cec1c6f06584
    [support.py]=e2d4a356fc2fe7a97b97f5e85f4e08b12d5dd3a145d4fd0e9a6c927c1b13498a
    [SwiftlyBridge.qml]=6fb7849cd209c2b4ef599d4343d25cc14f34bff47f51b63f0e7783914684822c
    [gui/shell.qml]=839bf63fc11787c47a22e141e173c6cd047ffb164369d4686ddeb3af43e4b56c
    [gui/SwiftlyCard.qml]=57bd7b487d0386a0b5ed5419b3ac28a39261ad18b07124e7101dfddad31388bf
    [gui/SwiftlySettings.qml]=7f011819af6ebd41327d3caeab91fc3ea50dccef94a113f258e06ddf067b8ffb
    [gui/WidgetFace.qml]=e2901f33c7e969a6075d1ebc5f5ae7d0d300839e785585912f723d2d791e652f
    [gui/SwiftlyPalette.qml]=ec3cb86ab36e3f3c756caee95b659b5901a7dd94845bbeb9bee7c2e149791c29
    )
    local files=(install-config.sh config.json)
    if [[ $mode = full ]]; then
        files+=(install-all.sh support.py SwiftlyBridge.qml)
        if [[ $# -eq 2 ]]; then
            files+=(gui/shell.qml gui/SwiftlyCard.qml gui/SwiftlySettings.qml gui/WidgetFace.qml gui/SwiftlyPalette.qml)
        fi
    fi
    local file
    for file in "${files[@]}"; do
        mkdir -p -- "$temporary/$(dirname -- "$file")"
        curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 "$base/$file" --output "$temporary/$file"
        printf '%s  %s\n' "${hashes[$file]}" "$temporary/$file" | sha256sum --check --status
    done
    if [[ $mode = config ]]; then
        bash "$temporary/install-config.sh"
    elif [[ $# -eq 2 ]]; then
        bash "$temporary/install-all.sh" "$2"
    else
        bash "$temporary/install-all.sh" "$2" "$3"
    fi
    rm -rf -- "$temporary"
    trap - EXIT
}
main "$@"
