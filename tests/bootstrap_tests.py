"""Exercise curl bootstrap with real HTTPS downloads and isolated installer mocks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

script=Path(sys.argv[1]).resolve()/'install.sh'
if os.geteuid()==0:
    raise SystemExit('Run as a normal user to exercise the production guards.')
with tempfile.TemporaryDirectory(prefix='swiftly-bootstrap-') as d:
    root=Path(d);home=root/'user home';home.mkdir()
    downloads=root/'downloads';downloads.mkdir()
    env=dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(home/'.config'),TMPDIR=str(downloads))
    def run(*args,success=True,extra=None):
        result=subprocess.run(['bash',str(script),*map(str,args)],env=env | (extra or {}),text=True,capture_output=True)
        assert (result.returncode==0)==success,(result.returncode,result.stdout,result.stderr)
        assert not list(downloads.iterdir()),list(downloads.iterdir())
        return result
    run('config')
    cfg=home/'.config/swiftly/config.json'
    value=json.loads(cfg.read_text());value['theme']['accent']='#FF123456'
    cfg.write_text(json.dumps(value));before=cfg.read_bytes()
    run('config');assert cfg.read_bytes()==before
    print('PASS: real pinned HTTPS config download, checksums, repeat config preservation and cleanup')
    binpath=root/'bin';binpath.mkdir()
    for name,text in {
        'hyprctl':'#!/bin/bash\necho "Hyprland 0.55.0"\n',
        'qs':'#!/bin/bash\necho "Quickshell mock"\n',
        'pacman':'#!/bin/bash\n[[ $1 = -T ]]\n',
        'sudo':'#!/bin/bash\nexit 99\n',
    }.items():
        (binpath/name).write_text(text);(binpath/name).chmod(0o755)
    gui=root/'GUI with spaces';gui.mkdir();(gui/'shell.qml').write_text('// Part 1 fixture\n')
    hypr=home/'hyprland.lua';hypr.write_text('-- user\n')
    run('full',gui,hypr,extra={'PATH':str(binpath)+':'+env['PATH']})
    assert 'hl.gesture' in hypr.read_text()
    assert (home/'.config/quickshell/swiftly/SwiftlyBridge.qml').is_file()
    assert cfg.read_bytes()==before
    print('PASS: full-mode real pinned downloads/checksums; mocked desktop/package installation')
    run('full',hypr,extra={'PATH':str(binpath)+':'+env['PATH']})
    for name in ['shell.qml','SwiftlyCard.qml','SwiftlySettings.qml','WidgetFace.qml','SwiftlyPalette.qml','SwiftlyBridge.qml']:
        assert (home/'.config/quickshell/swiftly'/name).is_file(),name
    assert cfg.read_bytes()==before
    assert (home/'.config/swiftly/update.sh').is_file()
    assert (home/'.config/swiftly/uninstall.sh').is_file()
    assert json.loads((home/'.config/swiftly/install-state.json').read_text())['guiDirectory'] is None
    print('PASS: default full-mode real pinned GUI downloads/checksums; config preserved')
    run('bad',success=False)
    run('full',success=False)
    run('full',root/'missing',hypr,success=False)
    print('PASS: invalid mode/arguments and missing GUI rejected before download')
    curl=binpath/'curl'
    curl.write_text('#!/bin/bash\nexit 22\n');curl.chmod(0o755)
    result=run('config',success=False,extra={'PATH':str(binpath)+':'+env['PATH']})
    assert cfg.read_bytes()==before
    print('PASS: injected HTTP failure stops without config changes and removes temporary files')
    curl.write_text('#!/bin/bash\nwhile (($#)); do\n if [[ $1 = --output ]]; then printf "bad artifact" > "$2"; exit 0; fi\n shift\ndone\nexit 99\n')
    run('config',success=False,extra={'PATH':str(binpath)+':'+env['PATH']})
    assert cfg.read_bytes()==before
    print('PASS: injected corrupted download rejected by SHA256; config preserved and cleanup complete')
print('RESULT: 6 bootstrap groups passed')
