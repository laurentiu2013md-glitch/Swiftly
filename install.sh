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
    local revision=a9f09f5560754c92bb104a5027377f2b1144eac5
    local base="https://raw.githubusercontent.com/laurentiu2013md-glitch/Swiftly/$revision/swiftly"
    temporary=
    temporary=$(mktemp -d)
    # EXIT also cleans up failed downloads and installer failures.
    trap 'rm -rf -- "$temporary"' EXIT
    declare -A hashes=(
    [uninstall.sh]=ec8d21ff70a7f54c5ef1379e0b81b36b80c5915322f2b1628a1533f1fd389569
    [install-config.sh]=7bcd988aa4ebd20b630857570e7638593db9d5bb7a8372b52d3e8bb0dbcdf96a
    [config.json]=54706dd92753387f96df9466071bf1d6ad2a2f62d6ca37b0c09be8bc781bc59c
    [install-all.sh]=b36ae3953bb98cfe0e2861a7df14c48186376c46d682bd76fa35c23d20fc52d4
    [support.py]=ee66b6669bc76c44a1f76d88e1e2ba32f8dbbe8d78f9bc56f3f346715a3f7a0a
    [SwiftlyBridge.qml]=341b3c52b353c5c68c83afb23a2c1f600c66d8145710e7ea3760a38eca829f1b
    [update.sh]=8c33880fab784a61c49593586260750b7f6371cc854ad97d1704a2118dd9ef7f
    [gui/shell.qml]=ccdb2f6fecc3c75c965139eef5949940a5b3728e07ad7f4774de2e79c5665d77
    [gui/SwiftlyCard.qml]=23ef56dc0ac2624aad749dc3706b2430d8458f81bd39bc5f31fef2736859d8d0
    [gui/SwiftlySettings.qml]=7f011819af6ebd41327d3caeab91fc3ea50dccef94a113f258e06ddf067b8ffb
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
