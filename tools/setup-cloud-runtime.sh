#!/usr/bin/env bash
# Extract authenticated official Debian packages into an isolated test runtime.
# No root, system package upgrades, or maintainer scripts are used.
set -euo pipefail
umask 022
cloud_home=${1:-/workspace/scratch/swiftly-cloudtest}
[[ $cloud_home = /* ]] || { echo 'Pass an absolute runtime directory.' >&2; exit 1; }
mkdir -p "$cloud_home"/{apt/lists/partial,apt/cache/archives/partial,apt/etc,packages,logs,bin}
printf '%s\n' 'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian sid main' > "$cloud_home/apt/etc/sources.list"
touch "$cloud_home/apt/empty-status"
apt_options=(-o Dir::Etc::parts=- -o Dir::Etc::main=-
    -o "Dir::Etc::sourcelist=$cloud_home/apt/etc/sources.list"
    -o Dir::Etc::sourceparts=- -o "Dir::State::lists=$cloud_home/apt/lists"
    -o "Dir::Cache=$cloud_home/apt/cache")
apt-get "${apt_options[@]}" update
apt-get "${apt_options[@]}" -s -o "Dir::State::status=$cloud_home/apt/empty-status" \
    --no-install-recommends install quickshell qt6-declarative-dev-tools \
    qml6-module-qtqml-workerscript qml6-module-qtqml-models > "$cloud_home/logs/apt-isolated-plan.txt"
python3 - "$cloud_home" <<'PY'
import hashlib
from pathlib import Path
import re
import subprocess
import sys
root=Path(sys.argv[1])
packages=[]
for line in (root/'logs/apt-isolated-plan.txt').read_text().splitlines():
    match=re.match(r'Inst (\S+) \((\S+)',line)
    if match: packages.append(f'{match[1]}={match[2]}')
if not packages: raise SystemExit('APT selected no packages')
options=['-o','Dir::Etc::parts=-','-o','Dir::Etc::main=-',
         '-o','Dir::Etc::sourcelist='+str(root/'apt/etc/sources.list'),
         '-o','Dir::Etc::sourceparts=-','-o','Dir::State::lists='+str(root/'apt/lists')]
subprocess.run(['apt-get',*options,'download',*packages],cwd=root/'packages',check=True)
expected={}
for index in (root/'apt/lists').glob('*Packages.lz4'):
    data=subprocess.check_output(['/usr/lib/apt/apt-helper','cat-file',str(index)],text=True)
    for stanza in data.split('\n\n'):
        fields=dict(line.split(': ',1) for line in stanza.splitlines() if ': ' in line and not line.startswith(' '))
        if 'SHA256' in fields: expected[fields['SHA256']]=fields
selected=set(packages)
verified=[]
for package in sorted((root/'packages').glob('*.deb')):
    digest=hashlib.sha256(package.read_bytes()).hexdigest()
    metadata=expected.get(digest)
    if not metadata: continue  # Old cached packages are never extracted.
    identity=metadata['Package']+'='+metadata['Version']
    if identity in selected:
        verified.append((package,digest));selected.remove(identity)
if selected: raise SystemExit('Missing verified packages: '+repr(sorted(selected)))
with (root/'logs/package-sha256.txt').open('w') as output:
    for package,digest in verified:
        output.write(f'{digest}  {package.name}\n')
        subprocess.run(['dpkg-deb','-x',str(package),str(root/'runtime-root')],check=True)
print(f'Extracted {len(verified)} official packages; hashes matched signed APT metadata.')
PY
# Wrappers load only this runtime's Qt, QML modules, plugins and dynamic linker.
for tool in qs qmllint qmlformat; do
    case "$tool" in
        qs) executable=usr/bin/qs ;;
        *) executable=usr/lib/qt6/bin/$tool ;;
    esac
    cat > "$cloud_home/bin/$tool" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cloud_home=\$(cd -- "\$(dirname -- "\${BASH_SOURCE[0]}")/.." && pwd -P)
runtime_root=\$cloud_home/runtime-root
export QT_PLUGIN_PATH="\$runtime_root/usr/lib/x86_64-linux-gnu/qt6/plugins"
export QML_IMPORT_PATH="\$runtime_root/usr/lib/x86_64-linux-gnu/qt6/qml"
export QML2_IMPORT_PATH="\$QML_IMPORT_PATH"
export QT_QPA_PLATFORM="\${QT_QPA_PLATFORM:-offscreen}"
export QT_QUICK_BACKEND="\${QT_QUICK_BACKEND:-software}"
exec "\$runtime_root/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2" --library-path "\$runtime_root/usr/lib/x86_64-linux-gnu" "\$runtime_root/$executable" "\$@"
EOF
    chmod +x "$cloud_home/bin/$tool"
done
"$cloud_home/bin/qs" --version
"$cloud_home/bin/qmllint" --version
