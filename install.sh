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
    local revision=98d250c8382615f5b14db8a3602b8d367b87b148
    local base="https://raw.githubusercontent.com/laurentiu2013md-glitch/Swiftly/$revision/swiftly"
    temporary=
    temporary=$(mktemp -d)
    # EXIT also cleans up failed downloads and installer failures.
    trap 'rm -rf -- "$temporary"' EXIT
    declare -A hashes=(
    [install-config.sh]=7bcd988aa4ebd20b630857570e7638593db9d5bb7a8372b52d3e8bb0dbcdf96a
    [config.json]=696570a48b7c582e02546c75ec02897d6fa69c070bad2400055e3825be676f07
    [install-all.sh]=c372277116fc264f8859a37bdc3a6d38eb1ab812c08e4aa3d4a8cec1c6f06584
    [support.py]=e2d4a356fc2fe7a97b97f5e85f4e08b12d5dd3a145d4fd0e9a6c927c1b13498a
    [SwiftlyBridge.qml]=6fb7849cd209c2b4ef599d4343d25cc14f34bff47f51b63f0e7783914684822c
    [gui/shell.qml]=bb160e58cfa93c620f3fae844282775d11508dd7da4fa863d89a2e806e200b04
    [gui/SwiftlyCard.qml]=daa152ada91875b4d3be0dee99a02487c460dfe761970685b29ea11639c558f9
    [gui/SwiftlySettings.qml]=408076260d1d96c8d6be155652c0308392b5ff2995e058041d3f84a28cfe5976
    [gui/WidgetFace.qml]=2c8893b501f9a1c5080be760297bcf59747d88b903d21e8fa8c6333ef020cd53
    )
    local files=(install-config.sh config.json)
    if [[ $mode = full ]]; then
        files+=(install-all.sh support.py SwiftlyBridge.qml)
        if [[ $# -eq 2 ]]; then
            files+=(gui/shell.qml gui/SwiftlyCard.qml gui/SwiftlySettings.qml gui/WidgetFace.qml)
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
