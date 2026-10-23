#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Standalone entry point: download the pinned, checksum-verified uninstaller.
set -euo pipefail
[[ $EUID -ne 0 ]] || { echo '[Swiftly] Run as your normal user.' >&2; exit 1; }
umask 077
temporary=$(mktemp -d)
trap 'rm -rf -- "$temporary"' EXIT
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
    --connect-timeout 20 --max-time 120 \
    'https://raw.githubusercontent.com/laurentiu2013md-glitch/Swiftly/a9f09f5560754c92bb104a5027377f2b1144eac5/swiftly/uninstall.sh' \
    --output "$temporary/uninstall.sh"
printf '%s  %s\n' ec8d21ff70a7f54c5ef1379e0b81b36b80c5915322f2b1628a1533f1fd389569 "$temporary/uninstall.sh" | sha256sum --check --status
bash "$temporary/uninstall.sh" "$@"
