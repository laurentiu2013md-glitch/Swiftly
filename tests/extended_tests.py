import copy
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

BUNDLE = Path(sys.argv[1]).resolve()
passed = []
failed = []

def test(name, fn):
    try:
        fn()
        passed.append(name)
        print('PASS:', name)
    except Exception as e:
        failed.append(name)
        print('FAIL:', name, repr(e))

with tempfile.TemporaryDirectory(prefix='swiftly-extended-', dir=BUNDLE.parent) as d:
    root = Path(d)
    home = root / 'user home'
    home.mkdir()
    cfgroot = home / '.config'
    (cfgroot / 'swiftly').mkdir(parents=True)
    cfg = cfgroot / 'swiftly/config.json'
    default = json.loads((BUNDLE / 'swiftly/config.json').read_text())
    cfg.write_text(json.dumps(default))
    gui = root / 'GUI with spaces'
    gui.mkdir()
    (gui / 'shell.qml').write_text('// fixture, not Part 1\n')
    (gui / 'assets').mkdir()
    (gui / 'assets/a').write_bytes(b'asset')
    hypr = home / 'hyprland.conf'
    hypr.write_text('# user\n')
    hypr.chmod(0o640)
    binpath = root / 'bin with spaces'
    binpath.mkdir()
    for name, script in {
        'hyprctl': '#!/bin/bash\necho "Hyprland 0.55.0"\n',
        'qs': '#!/bin/bash\nexit 0\n',
    }.items():
        (binpath/name).write_text(script)
        (binpath/name).chmod(0o755)
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(cfgroot), PATH=str(binpath)+':/usr/bin:/bin')
    def helper(*flags, success=True):
        r = subprocess.run(['python3', str(BUNDLE/'swiftly/support.py'), str(gui), str(hypr), *flags], env=env, capture_output=True, text=True)
        assert (r.returncode == 0) == success, (r.returncode, r.stdout, r.stderr)
        return r
    def backup_preserved():
        helper()
        assert hypr.stat().st_mode & 0o777 == 0o640
        backups = list(home.glob('hyprland.conf.bak.*'))
        assert len(backups)==1 and backups[0].read_bytes()==b'# user\n'
        target = cfgroot/'quickshell/swiftly'
        (target/'local-only').write_bytes(b'keep me')
        (gui/'shell.qml').write_text('// replacement\n')
        helper()
        backups = list(target.parent.glob('swiftly.bak.*'))
        assert len(backups)==1 and (backups[0]/'local-only').read_bytes()==b'keep me'
        assert (backups[0]/'assets/a').read_bytes()==b'asset'
        before = sorted(str(p) for p in root.rglob('*.bak.*'))
        helper()
        assert before == sorted(str(p) for p in root.rglob('*.bak.*'))
    test('complete GUI backup, file modes, identical rerun', backup_preserved)
    def quoting():
        helper('--gestures-only')
        lines=[l for l in hypr.read_text().splitlines() if l.startswith('gesture =')]
        for l in lines:
            cmd=l.split(', exec, ',1)[1]
            words=shlex.split(cmd)
            assert words[:3]==[str(binpath/'qs'),'-p',str(cfgroot/'quickshell/swiftly')]
            assert words[3:7]==['ipc','call','swiftly','swipe']
        lua=home/'hyprland.lua'
        lua.write_text('-- user\n')
        subprocess.run(['python3',str(BUNDLE/'swiftly/support.py'),str(gui),str(lua),'--gestures-only'],env=env,check=True,capture_output=True)
        for l in lua.read_text().splitlines():
            if 'hl.exec_cmd(' in l:
                command=json.loads(l.split('hl.exec_cmd(',1)[1].split(') end',1)[0])
                assert shlex.split(command)[:3]==[str(binpath/'qs'),'-p',str(cfgroot/'quickshell/swiftly')]
    test('spaces round-trip through shell and Lua quoting', quoting)
    valid_hypr=hypr.read_bytes()
    malformed=[None,[],42,{},dict(default,schemaVersion=True),dict(default,stacks=[None]),dict(default,stacks=[{'id':[]}]),dict(default,gestures=[])]
    g=copy.deepcopy(default);g['gestures']['nextDirection']=[];malformed.append(g)
    g=copy.deepcopy(default);g['stacks'].append(copy.deepcopy(g['stacks'][0]));malformed.append(g)
    for number, value in enumerate(malformed):
        def rejection(value=value):
            cfg.write_text(json.dumps(value))
            result=helper('--gestures-only',success=False)
            assert hypr.read_bytes()==valid_hypr
            assert 'Traceback' not in result.stderr, result.stderr
        test(f'malformed input {number}: clean error and no write', rejection)
    cfg.write_text(json.dumps(default))
    for number, text in enumerate(['# BEGIN SWIFTLY GESTURES\n', '# END SWIFTLY GESTURES\n# BEGIN SWIFTLY GESTURES\n', '# BEGIN SWIFTLY GESTURES extra\n# END SWIFTLY GESTURES\n', '# BEGIN SWIFTLY GESTURES\n# END SWIFTLY GESTURES\n'*2]):
        def markers(text=text):
            hypr.write_text(text)
            helper('--gestures-only',success=False)
            assert hypr.read_text()==text
        test(f'malformed markers {number}: no write',markers)
    hypr.write_bytes(valid_hypr)
    def conflicts():
        hypr.write_text('gesture = 4, horizontal, workspace\n')
        helper('--gestures-only',success=False)
        assert hypr.read_text()=='gesture = 4, horizontal, workspace\n'
    test('existing same-finger gesture refused',conflicts)
    def symlink():
        dest=root/'outside.conf';dest.write_text('# outside\n')
        hypr.unlink();hypr.symlink_to(dest)
        helper('--gestures-only',success=False)
        assert dest.read_text()=='# outside\n'
        hypr.unlink();hypr.write_bytes(valid_hypr)
        (gui/'bad-link').symlink_to(dest)
        helper('--check',success=False)
        (gui/'bad-link').unlink()
    test('Hyprland destination and GUI symlink refusal',symlink)
    spec=importlib.util.spec_from_file_location('support',BUNDLE/'swiftly/support.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    def rollback():
        target=root/'rollback';target.mkdir();(target/'old').write_text('preserve')
        original_rename=Path.rename
        def rename(path,dst):
            if path.name.startswith('.swiftly-'): raise OSError('injected final rename failure')
            return original_rename(path,dst)
        try:
            with patch.object(Path,'rename',rename):mod.install_gui(gui,target,BUNDLE/'swiftly/SwiftlyBridge.qml')
        except OSError:pass
        else:raise AssertionError('expected failure')
        assert (target/'old').read_text()=='preserve'
        assert not list(root.glob('.swiftly-*'))
    test('injected GUI final rename failure restores previous tree',rollback)
    def bundled_gui():
        (binpath/'pacman').write_text('#!/bin/bash\n[[ $1 = -T ]]\n')
        (binpath/'pacman').chmod(0o755)
        before=cfg.read_bytes()
        def install():
            result=subprocess.run(['bash',str(BUNDLE/'swiftly/install-all.sh'),str(hypr)],env=env,capture_output=True,text=True)
            assert result.returncode==0,(result.stdout,result.stderr)
        install()
        target=cfgroot/'quickshell/swiftly'
        for name in ['shell.qml','SwiftlyCard.qml','SwiftlySettings.qml','WidgetFace.qml','SwiftlyBridge.qml']:
            assert (target/name).is_file(),name
        assert cfg.read_bytes()==before
        backups=sorted(str(p) for p in target.parent.glob('swiftly.bak.*'))
        install()
        assert backups==sorted(str(p) for p in target.parent.glob('swiftly.bak.*'))
    test('bundled GUI default install preserves config and is idempotent',bundled_gui)

print(f'RESULT: {len(passed)} passed; {len(failed)} failed')
sys.exit(bool(failed))
