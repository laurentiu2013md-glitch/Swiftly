"""Real Quickshell subprocess and IPC tests, using a minimal shell, not Part 1."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

bundle=Path(sys.argv[1]).resolve()
qs=Path(sys.argv[2]).resolve()
logdir=Path(sys.argv[3]).resolve();logdir.mkdir(parents=True,exist_ok=True)
failed=[];passed=[]
def test(name, fn):
    try:
        fn();passed.append(name);print('PASS:',name,flush=True)
    except Exception as e:
        failed.append(name);print('FAIL:',name,repr(e),flush=True);traceback.print_exc()

shell='''import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
    id: root
    property int settingsCount: 0
    property int observedIndex: bridge.indexFor("daily")
    SwiftlyBridge { id: bridge; onSettingsRequested: root.settingsCount++ }
    IpcHandler {
        target: "probe"
        function identity(): string { return "SELECTED"; }
        function state(): string { return JSON.stringify({theme:bridge.config.theme, stacks:bridge.config.stacks, interaction:bridge.config.interaction, indices:bridge.indices, observed:root.observedIndex, settings:root.settingsCount}); }
        function clear(): void { bridge.indices = ({}); }
        function rawIndex(stackId: string): real { return bridge.indexFor(stackId); }
        function saveAccent(accent: string): void { const theme = Object.assign({},bridge.config.theme); theme.accent=accent; bridge.config.theme=theme; bridge.saveConfig(); }
    }
}
'''
with tempfile.TemporaryDirectory(prefix='swiftly-real-',dir=bundle.parent) as d:
    root=Path(d);home=root/'home';home.mkdir()
    configroot=home/'.config';(configroot/'swiftly').mkdir(parents=True)
    runtime=root/'runtime';runtime.mkdir(mode=0o700)
    path=configroot/'quickshell/swiftly';path.mkdir(parents=True)
    shutil.copy2(bundle/'swiftly/SwiftlyBridge.qml',path/'SwiftlyBridge.qml')
    (path/'shell.qml').write_text(shell.replace('SELECTED','swiftly'))
    base=path.parent
    shutil.copy2(path/'SwiftlyBridge.qml',base/'SwiftlyBridge.qml')
    (base/'shell.qml').write_text(shell.replace('SELECTED','base'))
    default=json.loads((bundle/'swiftly/config.json').read_text())
    cfg=configroot/'swiftly/config.json'
    cfg.write_text(json.dumps(default))
    env=dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(configroot),XDG_RUNTIME_DIR=str(runtime),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',QSG_RHI_BACKEND='software',QT_QUICK_CONTROLS_STYLE='Basic')
    processes=[];logs=[]
    def call(target, function, *args, selected=path, check=True):
        p=subprocess.run([str(qs),'-p',str(selected),'ipc','call',target,function,*map(str,args)],env=env,capture_output=True,text=True,timeout=10)
        if check:assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
        return p.stdout.strip() if check else p
    def wait(fn,timeout=8):
        until=time.monotonic()+timeout;last=None
        while time.monotonic()<until:
            try:
                if fn():return
            except Exception as e:last=e
            time.sleep(.1)
        raise AssertionError(('timed out',last))
    def state():return json.loads(call('probe','state'))
    def write(value,atomic=False):
        if atomic:
            tmp=cfg.with_suffix('.new');tmp.write_text(json.dumps(value));os.replace(tmp,cfg)
        else:cfg.write_text(json.dumps(value))
    try:
        for label, selected in [('swiftly',path),('base',base)]:
            stream=(logdir/f'{label}-server.log').open('w');logs.append(stream)
            p=subprocess.Popen([str(qs),'-p',str(selected)],env=env,stdout=stream,stderr=subprocess.STDOUT);processes.append(p)
            wait(lambda: call('probe','identity',selected=selected,check=False).returncode==0)
        def selection():
            assert call('probe','identity')=='swiftly'
            assert call('probe','identity',selected=base)=='base'
            missing=call('probe','identity',selected=root/'not-running',check=False)
            assert missing.returncode!=0
        test('real CLI -p selects independent nested and base shells',selection)
        def ipc():
            wait(lambda:len(state()['stacks'])==1)
            assert call('swiftly','index','daily')=='0'
            call('swiftly','next','daily');assert call('swiftly','index','daily')=='1'
            assert state()['observed']==1
            call('swiftly','previous','daily');assert call('swiftly','index','daily')=='0'
            call('swiftly','previous','daily');assert call('swiftly','index','daily')=='2'
            call('swiftly','next','daily');assert call('swiftly','index','daily')=='0'
            call('swiftly','settings');assert state()['settings']==1
            call('swiftly','swipe','left',3);assert call('swiftly','index','daily')=='0'
            call('swiftly','swipe','left',4);assert call('swiftly','index','daily')=='1'
            call('swiftly','swipe','right',4);assert call('swiftly','index','daily')=='0'
            bad=call('swiftly','swipe','left','not-int',check=False)
            print('OBSERVED invalid int:',bad.returncode,repr(bad.stdout+bad.stderr),flush=True)
            assert 'Unable to parse argument' in bad.stdout+bad.stderr
            assert call('swiftly','index','daily')=='0'
            bad=call('swiftly','missing',check=False)
            print('OBSERVED unknown function:',bad.returncode,repr(bad.stdout+bad.stderr),flush=True)
            assert 'Function not found' in bad.stdout+bad.stderr
        test('real typed IpcHandler, next/previous wrap, bindings, settings and swipe filters',ipc)
        def reload():
            for atomic,accent in [(False,'#FF123456'),(True,'#FF234567'),(True,'#FF345678'),(False,'#FF456789')]:
                value=copy.deepcopy(default);value['theme']['accent']=accent
                write(value,atomic);wait(lambda:state()['theme']['accent']==accent)
            assert processes[0].poll() is None
        test('FileView/JsonAdapter in-place and repeated atomic replacement live reload',reload)
        def clamp():
            value=copy.deepcopy(default);value['interaction']['wrap']=False
            write(value,True);wait(lambda:state()['interaction']['wrap'] is False)
            call('probe','clear');call('swiftly','previous','daily');assert call('swiftly','index','daily')=='0'
            for _ in range(5):call('swiftly','next','daily')
            assert call('swiftly','index','daily')=='2'
            value['stacks'][0]['widgets']=value['stacks'][0]['widgets'][:1]
            write(value,True);wait(lambda:len(state()['stacks'][0]['widgets'])==1)
            assert call('swiftly','index','daily')=='0' and state()['observed']==0
            value['stacks'][0]['widgets']=[]
            write(value,True);wait(lambda:len(state()['stacks'][0]['widgets'])==0)
            call('swiftly','next','daily');assert call('swiftly','index','daily')=='0'
            assert call('swiftly','index','absent')=='0'
            value=copy.deepcopy(default);value['stacks'][0]['enabled']=False
            write(value,True);wait(lambda:state()['stacks'][0]['enabled'] is False)
            call('probe','clear');call('swiftly','next','daily');assert call('swiftly','index','daily')=='0'
        test('clamp, widget shrink/empty, missing and disabled stacks',clamp)
        def save():
            call('probe','saveAccent','#FFABCDEF')
            wait(lambda:json.loads(cfg.read_text())['theme']['accent']=='#FFABCDEF')
            wait(lambda:json.loads(call('probe','state',selected=base))['theme']['accent']=='#FFABCDEF')
        test('explicit writeAdapter saves and second real shell reloads',save)
        def malformed():
            before=state()['theme'];cfg.write_text('{not json')
            time.sleep(.4)
            assert state()['theme']==before
            write(default,True);wait(lambda:state()['theme']['accent']==default['theme']['accent'])
            assert processes[0].poll() is None
        test('invalid JSON preserves last adapter data and valid atomic edit recovers',malformed)
        def proto():
            value=copy.deepcopy(default);value['stacks'][0]['id']='__proto__';value['gestures']['targetStack']='__proto__'
            write(value,True);wait(lambda:state()['stacks'][0]['id']=='__proto__')
            call('probe','clear');call('swiftly','next','__proto__')
            assert call('swiftly','index','__proto__')=='1',state()
        test('valid __proto__ stack ID advances',proto)
        def fractional():
            value=copy.deepcopy(default);value['stacks'][0]['initialIndex']=1.8
            write(value,True);wait(lambda:state()['stacks'][0]['initialIndex']==1.8)
            call('probe','clear')
            assert float(call('probe','rawIndex','daily'))==1.0
        test('fractional external initialIndex normalized to integer',fractional)
    finally:
        for p in processes:
            p.terminate()
        for p in processes:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
        for f in logs:f.close()
print(f'RESULT: {len(passed)} passed; {len(failed)} failed')
sys.exit(bool(failed))
