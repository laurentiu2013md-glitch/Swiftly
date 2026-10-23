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
        full) [[ $# -eq 3 ]] || { echo 'Usage: bash install.sh full GUI_DIRECTORY HYPRLAND_CONFIG' >&2; return 1; }
              [[ -f $2/shell.qml && -f $3 ]] || { echo 'Provide your Part 1 GUI directory and existing Hyprland config.' >&2; return 1; } ;;
        *) echo 'Usage: bash install.sh config | full GUI_DIRECTORY HYPRLAND_CONFIG' >&2; return 1 ;;
    esac
    command -v curl >/dev/null
    command -v sha256sum >/dev/null
    local revision=ba0f55b8b3101ddfa985f6b7e903a2f0b79e385f
    local base="https://raw.githubusercontent.com/laurentiu2013md-glitch/Swiftly/$revision/swiftly"
    temporary=
    temporary=$(mktemp -d)
    # EXIT also cleans up failed downloads and installer failures.
    trap 'rm -rf -- "$temporary"' EXIT
    declare -A hashes=(
    [install-config.sh]=7bcd988aa4ebd20b630857570e7638593db9d5bb7a8372b52d3e8bb0dbcdf96a
    [config.json]=a9e8a8b62002e26ac6627e8f82607e2824ee482815489e3485b462b8295629d3
    [install-all.sh]=03940517ae826898fa34a66a29928bf687660db006c533395cf81a56fa945cfa
    [support.py]=e2d4a356fc2fe7a97b97f5e85f4e08b12d5dd3a145d4fd0e9a6c927c1b13498a
    [SwiftlyBridge.qml]=80c69a87c6a21d2af9ebbadca0f489452b134244f0f334f4c07f18ad7ad81153
    )
    local files=(install-config.sh config.json)
    if [[ $mode = full ]]; then
        files+=(install-all.sh support.py SwiftlyBridge.qml)
    fi
    local file
    for file in "${files[@]}"; do
        curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 "$base/$file" --output "$temporary/$file"
        printf '%s  %s\n' "${hashes[$file]}" "$temporary/$file" | sha256sum --check --status
    done
    if [[ $mode = config ]]; then
        bash "$temporary/install-config.sh"
    else
        bash "$temporary/install-all.sh" "$2" "$3"
    fi
    rm -rf -- "$temporary"
    trap - EXIT
}
main "$@"
