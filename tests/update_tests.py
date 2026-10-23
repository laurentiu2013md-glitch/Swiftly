"""Updater failure/scope tests. curl/qs are mocks; GUI tests cover real reloads."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

repo=Path(sys.argv[1]).resolve()
if os.geteuid()==0: raise SystemExit('Run as a normal user.')
with tempfile.TemporaryDirectory(prefix='swiftly-update-tests-') as d:
    root=Path(d);home=root/'user home';home.mkdir()
    cfgroot=home/'.config';target=cfgroot/'quickshell/swiftly';target.mkdir(parents=True)
    (target/'shell.qml').write_text('// fixture\n')
    control=cfgroot/'swiftly';control.mkdir()
    config=control/'config.json';config.write_text('{"keep": "custom"}\n')
    hypr=home/'hyprland.lua';hypr.write_text('-- user\n')
    state=control/'install-state.json'
    trace=root/'trace';mode=root/'mode';flag=root/'flag'
    mock=root/'bin';mock.mkdir()
    qs='''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
root=Path(os.environ['TEST_ROOT']);args=sys.argv[1:]
with (root/'trace').open('a') as f:f.write(json.dumps(args)+'\\n')
mode=(root/'mode').read_text();flag=root/'flag'
if args[2:]==['ipc','call','swiftly','status']:
 if mode=='busy' and not (root/'busy').exists():
  (root/'busy').touch();print('Not ready to accept queries yet.')
 elif mode in ('legacy','outside','stopped') and not flag.exists():print('Function not found.')
 else:print(json.dumps({'generation':'new' if flag.exists() else 'old','ready':True}))
elif args[2:]==['ipc','call','swiftly','reload']:
 flag.touch();print('reloading')
elif args[2:]==['list','-j']:
 if mode=='stopped' or flag.exists():print('No running instances for selected config')
 else:print(json.dumps([{'pid':12345,'config_path':'/other/shell.qml' if mode=='outside' else args[1]+'/shell.qml'}]))
elif args[2:]==['kill','--pid','12345']:flag.touch()
elif args[2:]==['-n','-d']:flag.touch()
else:sys.exit(99)
'''
    curl='''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
root=Path(os.environ['TEST_ROOT']);mode=(root/'mode').read_text()
with (root/'trace').open('a') as f:f.write(json.dumps(['curl',*sys.argv[1:]])+'\\n')
if mode=='http-failure':sys.exit(22)
output=Path(sys.argv[sys.argv.index('--output')+1])
output.write_text('#!/bin/bash\\nexit '+('3' if mode=='install-failure' else '0')+'\\n')
'''
    for name,text in [('qs',qs),('curl',curl)]:
        (mock/name).write_text(text);(mock/name).chmod(0o755)
    env=dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(cfgroot),PATH=str(mock)+':/usr/bin:/bin',TEST_ROOT=str(root))
    def run(case,*args,success=True):
        trace.write_text('');mode.write_text(case);flag.unlink(missing_ok=True)
        before=config.read_bytes()
        result=subprocess.run(['bash',str(repo/'swiftly/update.sh'),*map(str,args)],env=env,capture_output=True,text=True,timeout=25)
        assert (result.returncode==0)==success,(result.returncode,result.stdout,result.stderr)
        assert 'Traceback' not in result.stderr,result.stderr
        assert config.read_bytes()==before
        entries=[json.loads(line) for line in trace.read_text().splitlines()]
        for entry in entries:
            if entry[0]!='curl': assert entry[:2]==['-p',str(target)]
        return entries
    entries=run('normal','--reload-only')
    assert any(e[2:]==['ipc','call','swiftly','reload'] for e in entries)
    assert not any('kill' in e or e[0]=='curl' for e in entries)
    print('PASS: scoped reload-only readiness and config preservation')
    entries=run('busy','--reload-only')
    assert not any('kill' in e or e[2:]==['-n','-d'] for e in entries)
    print('PASS: transient busy IPC is retried without stopping the app')
    for case in ['http-failure','install-failure']:
        entries=run(case,hypr,success=False)
        assert entries and all(e[0]=='curl' for e in entries)
    print('PASS: HTTP/installer failures leave running app and config untouched')
    entries=run('outside','--reload-only',success=False)
    assert not any('kill' in e for e in entries)
    print('PASS: unrelated instance metadata is refused before any kill')
    entries=run('legacy','--reload-only')
    assert any(e[2:]==['kill','--pid','12345'] for e in entries)
    assert any(e[2:]==['-n','-d'] for e in entries)
    print('PASS: legacy app restart selects only its verified PID and path')
    entries=run('stopped','--reload-only')
    assert not any('kill' in e for e in entries)
    assert any(e[2:]==['-n','-d'] for e in entries)
    print('PASS: inactive app starts without killing any process')
    state.write_text('[]');run('normal',success=False)
    state.write_text(json.dumps({'schemaVersion':1,'hyprlandConfig':str(hypr),'guiDirectory':42}))
    run('normal',success=False)
    print('PASS: malformed saved state fails cleanly before download/reload')
    state.write_text(json.dumps({'schemaVersion':1,'hyprlandConfig':str(hypr),'guiDirectory':None}))
    entries=run('normal')
    assert entries[0][0]=='curl' and any(e[2:]==['ipc','call','swiftly','reload'] for e in entries)
    print('PASS: recorded install supports update without repeated arguments')
    with (control/'.update.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert run('normal','--reload-only',success=False)==[]
    print('PASS: concurrent update lock refuses a second updater')
print('RESULT: 9 updater mock groups passed')
