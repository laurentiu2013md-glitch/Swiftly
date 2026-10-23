#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
umask 077
trap 'printf "[Swiftly] ERROR at line %s\n" "$LINENO" >&2' ERR
die() { printf '[Swiftly] %s\n' "$*" >&2; exit 1; }
[[ $EUID -ne 0 ]] || die 'Run as your normal user, without sudo.'
[[ $# -eq 0 ]] || die 'Usage: bash install-config.sh'
base=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=${XDG_CONFIG_HOME:-"$HOME/.config"}
[[ $root = /* ]] || die 'XDG_CONFIG_HOME must be absolute.'
source_file=$base/config.json
target=$root/swiftly/config.json
[[ -f $source_file ]] || die "Missing $source_file"
mkdir -p -- "$root/swiftly"
[[ ! -L $target ]] || die "Refusing config symlink: $target"
if [[ -e $target ]]; then
    [[ -f $target ]] || die "Not a regular file: $target"
    printf '[Swiftly] Keeping existing config: %s\n' "$target"
    exit 0
fi
temporary=$(mktemp "$root/swiftly/.config.XXXXXXXX")
trap 'rm -f -- "$temporary"' EXIT
cp -- "$source_file" "$temporary"
# A hard link publishes atomically without clobbering a concurrent creation.
if ln -- "$temporary" "$target"; then
    printf '[Swiftly] Installed config: %s\n' "$target"
else
    die 'Could not publish config; existing files were left untouched.'
fi
