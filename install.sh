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
    local revision=ab49911cc497188d96a8f3ebad943d04c902ed0b
    local base="https://raw.githubusercontent.com/laurentiu2013md-glitch/Swiftly/$revision/swiftly"
    temporary=
    temporary=$(mktemp -d)
    # EXIT also cleans up failed downloads and installer failures.
    trap 'rm -rf -- "$temporary"' EXIT
    declare -A hashes=(
    [uninstall.sh]=ec8d21ff70a7f54c5ef1379e0b81b36b80c5915322f2b1628a1533f1fd389569
    [install-config.sh]=7bcd988aa4ebd20b630857570e7638593db9d5bb7a8372b52d3e8bb0dbcdf96a
    [config.json]=e893c201f5227a5282534d5045ef51753b074887a64cd63a38ec32172e4a1b74
    [install-all.sh]=b36ae3953bb98cfe0e2861a7df14c48186376c46d682bd76fa35c23d20fc52d4
    [support.py]=ee66b6669bc76c44a1f76d88e1e2ba32f8dbbe8d78f9bc56f3f346715a3f7a0a
    [SwiftlyBridge.qml]=ab57f35f13dac83b0556bc2093fc4e338c9fd726927ff1e3ea1fe1b28c2fbd61
    [update.sh]=8c33880fab784a61c49593586260750b7f6371cc854ad97d1704a2118dd9ef7f
    [gui/shell.qml]=ccdb2f6fecc3c75c965139eef5949940a5b3728e07ad7f4774de2e79c5665d77
    [gui/SwiftlyCard.qml]=fcfdc9d20f2752ea03ab3b438b399702e636167ea3d67970a1f46aa49e9e85bb
    [gui/SwiftlySettings.qml]=e2c387bc3519f30626151acfa1eb1622805cdc292db0bb643d17144fd28a1e16
    [gui/WidgetFace.qml]=e2901f33c7e969a6075d1ebc5f5ae7d0d300839e785585912f723d2d791e652f
    [gui/SwiftlyPalette.qml]=ec3cb86ab36e3f3c756caee95b659b5901a7dd94845bbeb9bee7c2e149791c29
    )
    local files=(install-config.sh config.json)
    if [[ $mode = full ]]; then
        files+=(install-all.sh support.py SwiftlyBridge.qml update.sh uninstall.sh)
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
