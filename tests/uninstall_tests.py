"""Isolated uninstaller regression tests; qs is mocked here."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

repo=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='swiftly-uninstall-') as directory:
    base=Path(directory)
    for case in ('conf','lua','purge','malformed','outside','symlink','lock','config-only'):
        root=base/case;root.mkdir()
        config=root/'config with spaces';control=config/'swiftly';control.mkdir(parents=True)
        target=config/'quickshell/swiftly'
        if case!='config-only':
            target.mkdir(parents=True);(target/'shell.qml').write_text('// user GUI\n')
        settings=control/'config.json';settings.write_text('{"custom":true}\n')
        (control/'config.json.bak.keep').write_text('old settings')
        (control/'unrelated').write_text('keep')
        for name in ('update.sh','support.py','uninstall.sh'):(control/name).write_text('fixture')
        hypr=root/('hyprland.lua' if case=='lua' else 'hyprland.conf')
        comment='--' if case=='lua' else '#'
        original=f'{comment} user\n{comment} BEGIN SWIFTLY GESTURES\nmanaged fixture\n{comment} END SWIFTLY GESTURES\n{comment} after\n'
        if case=='malformed':original=original.replace(f'{comment} END SWIFTLY GESTURES\n','')
        hypr.write_text(original);hypr.chmod(0o640)
        if case!='config-only':
            (control/'install-state.json').write_text(json.dumps({'schemaVersion':1,'hyprlandConfig':str(hypr)}))
        binpath=root/'bin';binpath.mkdir()
        trace=root/'trace';flag=root/'stopped'
        (binpath/'qs').write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
root=Path(os.environ['TEST_ROOT']);args=sys.argv[1:]
with (root/'trace').open('a') as stream:stream.write(json.dumps(args)+'\\n')
if args[2:]==['list','-j']:
 print(json.dumps([] if (root/'stopped').exists() else [{'pid':12345,'config_path':'/other/shell.qml' if root.name=='outside' else args[1]+'/shell.qml'}]))
elif args[2:]==['kill','--pid','12345']:(root/'stopped').touch()
else:sys.exit(99)
''')
        (binpath/'qs').chmod(0o755)
        env=dict(os.environ,HOME=str(root),XDG_CONFIG_HOME=str(config),PATH=str(binpath)+':/usr/bin:/bin',TEST_ROOT=str(root))
        held=None
        if case=='symlink':
            (control/'update.sh').unlink();(control/'update.sh').symlink_to(control/'unrelated')
        if case=='lock':
            held=(control/'.update.lock').open('w');fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
        args=['--purge'] if case=='purge' else []
        result=subprocess.run(['bash',str(repo/'swiftly/uninstall.sh'),*args],env=env,capture_output=True,text=True,timeout=15)
        if held:held.close()
        if case in ('malformed','outside','symlink','lock'):
            assert result.returncode!=0,(case,result.stdout,result.stderr)
            assert settings.exists() and target.exists() and hypr.read_text()==original
            assert not flag.exists()
            assert not list(root.glob('hyprland.*.bak.*'))
        else:
            assert result.returncode==0,(case,result.stdout,result.stderr)
            assert not target.exists()
            assert settings.exists()==(case!='purge')
            assert (control/'config.json.bak.keep').read_text()=='old settings'
            assert (control/'unrelated').read_text()=='keep'
            if case!='config-only':
                assert hypr.read_text()==f'{comment} user\n{comment} after\n'
                assert hypr.stat().st_mode&0o777==0o640
                assert list(root.glob('hyprland.*.bak.*'))[0].read_text()==original
                assert list(target.parent.glob('swiftly.bak.*'))[0].joinpath('shell.qml').read_text()=='// user GUI\n'
            result=subprocess.run(['bash',str(repo/'swiftly/uninstall.sh')],env=env,capture_output=True,text=True,timeout=15)
            assert result.returncode==0,(result.stdout,result.stderr)
        print('PASS: uninstall',case,flush=True)
print('RESULT: 8 uninstall groups passed')
