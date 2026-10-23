#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
umask 077
trap 'printf "[Swiftly] ERROR at line %s; stopping.\n" "$LINENO" >&2' ERR
die() { printf '[Swiftly] %s\n' "$*" >&2; exit 1; }
[[ $EUID -ne 0 ]] || die 'Run as your normal user; sudo is used only for pacman.'
base=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
case $# in
    1) gui=$base/gui; hypr=$1 ;;
    2) gui=$1; hypr=$2 ;;
    *) die 'Usage: bash install-all.sh [GUI_DIRECTORY] HYPRLAND_MAIN_CONFIG' ;;
esac
[[ -f $gui/shell.qml ]] || die 'GUI_DIRECTORY must contain Part 1 shell.qml.'
[[ -f $hypr ]] || die 'Pass your actual, existing Hyprland main config.'
[[ $hypr = *.lua || $hypr = *.conf ]] || die 'Expected .lua or .conf Hyprland config.'
for file in config.json install-config.sh support.py SwiftlyBridge.qml; do
    [[ -f $base/$file ]] || die "Missing $base/$file"
done
command -v pacman >/dev/null || die 'This installer requires Arch/pacman.'
command -v hyprctl >/dev/null || die 'Install and start Hyprland first.'
# Qt Quick Controls for settings, SVG/WebP support for widget assets.
missing=()
for package in python qt6-declarative qt6-svg qt6-imageformats; do
    pacman -T "$package" >/dev/null 2>&1 || missing+=("$package")
done
if ((${#missing[@]})); then
    printf '[Swiftly] Installing repository dependencies: %s\n' "${missing[*]}"
    sudo pacman -S --needed -- "${missing[@]}"
fi
if ! command -v qs >/dev/null; then
    if pacman -Si quickshell >/dev/null 2>&1; then
        printf '[Swiftly] Installing Quickshell from pacman.\n'
        sudo pacman -S --needed -- quickshell
    elif command -v paru >/dev/null; then
        printf '[Swiftly] Repository package unavailable; using detected paru.\n'
        paru -S --needed -- quickshell
    elif command -v yay >/dev/null; then
        printf '[Swiftly] Repository package unavailable; using detected yay.\n'
        yay -S --needed -- quickshell
    else
        die 'Quickshell unavailable; no paru/yay detected. No helper was installed.'
    fi
fi
command -v qs >/dev/null || die 'Quickshell installation did not provide qs.'
qs --version
# Preflight validates config, version, paths and managed-block boundaries.
python3 "$base/support.py" "$gui" "$hypr" --check
bash "$base/install-config.sh"
python3 "$base/support.py" "$gui" "$hypr"
printf '[Swiftly] Ready. Start with: qs -p "%s/quickshell/swiftly"\n' \
    "${XDG_CONFIG_HOME:-$HOME/.config}"
