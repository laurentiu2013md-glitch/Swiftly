"""Real Wayland/Quickshell GUI tests with QtTest pointer/key events.

Stages the production GUI and injects a test-only IPC/QtTest probe. No production
handler, MouseArea, animation or settings component is replaced.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

repo=Path(sys.argv[1]).resolve()
cloud=Path(sys.argv[2]).resolve()
logs=Path(sys.argv[3]).resolve();logs.mkdir(parents=True,exist_ok=True)
for old in [logs/'card.png',logs/'card-overlay.png',logs/'settings.png',logs/'desktop.png']: old.unlink(missing_ok=True)
def png_ready(path):
    if not path.exists(): return False
    data=path.read_bytes()
    return data.startswith(b'\x89PNG\r\n\x1a\n') and data.endswith(b'\x00\x00\x00\x00IEND\xaeB`\x82')
runtime=cloud/'runtime-root'
loader=runtime/'usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2'
libs=runtime/'usr/lib/x86_64-linux-gnu'
with tempfile.TemporaryDirectory(prefix='swiftly-gui-') as d:
    root=Path(d);home=root/'home';home.mkdir()
    config=home/'.config';(config/'swiftly').mkdir(parents=True)
    cfg=config/'swiftly/config.json'
    default=json.loads((repo/'swiftly/config.json').read_text())
    cfg.write_text(json.dumps(default))
    xdg=root/'runtime';xdg.mkdir(mode=0o700)
    gui=config/'quickshell/swiftly';gui.parent.mkdir(parents=True);shutil.copytree(repo/'swiftly/gui',gui)
    shutil.copy2(repo/'swiftly/SwiftlyBridge.qml',gui/'SwiftlyBridge.qml')
    facefile=gui/'WidgetFace.qml'
    facefile.write_text(facefile.read_text().replace('id: face','id: face\n    readonly property string testRevision: "before"',1))
    cardfile=gui/'SwiftlyCard.qml'
    cardfile.write_text(cardfile.read_text().replace('id: card','id: card\n    readonly property alias testColors: colors',1))
    shell=(gui/'shell.qml').read_text()
    shell=shell.replace('import Quickshell\n','import Quickshell\nimport Quickshell.Io\nimport QtTest\n')
    shell=shell.replace('required property var modelData','readonly property alias testCard: widgetCard\n            required property var modelData')
    probe='''
    TestCase {
        id: input
        name: "GuiInput"
        when: false
        parent: widgetPanels.instances.length ? widgetPanels.instances[0].testCard : null
    }
    IpcHandler {
        target: "guiTest"
        function state(): string {
            const card = widgetPanels.instances[0].testCard;
            const faces = [];
            for (let i=0; i<card.widgetRepeater.count; i++) {
                const face=card.widgetRepeater.itemAt(i);
                faces.push({revision:face.testRevision,opacity:face.opacity, x:face.x, scale:face.scale});
            }
            return JSON.stringify({index:card.selectedIndex,width:card.width,zone:card.switchArea.x,zoneWidth:card.switchArea.width,masked:widgetPanels.instances[0].mask.item===card.switchArea,bodyAlpha:card.color.a,contentX:card.contentArea.x,contentY:card.contentArea.y,contentWidth:card.contentArea.width,contentHeight:card.contentArea.height,preset:card.preset,duration:card.duration,faces:faces,hover:runtimeBridge.pointerStackId,settingsVisible:settings.visible,generation:runtimeBridge.generation,panelCount:widgetPanels.instances.length,status:settings.status,sourceForeground:card.testColors.theme.foreground,actualForeground:card.testColors.foreground.toString(),titleColor:input.findChild(settings.contentItem,"settingsHeading").color.toString(),presetFill:input.findChild(settings.contentItem,"preset-0").background.color.toString()});
        }
        function setAutoReload(enabled: bool): void { Quickshell.watchFiles = enabled; }
        function wheel(x: real, delta: int): void { input.mouseWheel(widgetPanels.instances[0].testCard,x,80,0,delta); }
        function move(x: real): void { input.mouseMove(widgetPanels.instances[0].testCard,x,80); }
        function drag(x: real, dx: real): void { input.mouseDrag(widgetPanels.instances[0].testCard,x,80,dx,0); }
        function selectPreset(index: int): void {
            const button=input.findChild(settings.contentItem,"preset-"+index);
            input.mouseClick(button);
        }
        function openSettings(): void { runtimeBridge.settingsRequested(); }
        function durationZero(): void { const slider=input.findChild(settings.contentItem,"animationDuration"); input.mouseClick(slider,slider.leftPadding,slider.height/2); }
        function save(): void { const button=input.findChild(settings.contentItem,"saveAnimation"); input.mouseClick(button); }
        function settingsScreenshot(path: string): void { settings.contentItem.grabToImage(result => result.saveToFile(path)); }
        function closeSettings(): void { settings.close(); }
        function screenshot(path: string): void { widgetPanels.instances[0].testCard.grabToImage(result => result.saveToFile(path)); }
    }
'''
    (gui/'shell.qml').write_text(shell.rsplit('}',1)[0]+probe+'}\n')
    swayconfig=root/'sway.conf'
    swayconfig.write_text('output * mode 1280x720\nseat * hide_cursor 0\nxwayland disable\nswaybg_command -\n')
    env=dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(config),XDG_RUNTIME_DIR=str(xdg),WLR_BACKENDS='headless',WLR_RENDERER='pixman',WLR_LIBINPUT_NO_DEVICES='1',QT_QPA_PLATFORM='wayland',QT_QUICK_BACKEND='software',QT_QUICK_CONTROLS_STYLE='Basic',XDG_CURRENT_DESKTOP='sway',PATH=str(cloud/'bin')+':'+os.environ.get('PATH',''))
    # Sway's dlopened wlroots must resolve against the private library set too.
    swayenv=dict(env,LD_LIBRARY_PATH=str(libs))
    # This test config disables optional Xwayland/background subprocesses.
    swaycmd=[str(loader),'--library-path',str(libs),str(runtime/'usr/bin/sway'),'--unsupported-gpu','-c',str(swayconfig)]
    swaylog=(logs/'sway.log').open('w');qslog=(logs/'quickshell.log').open('w')
    sway=None;qs=None;other=None
    othergui=root/'other-shell';othergui.mkdir()
    (othergui/'shell.qml').write_text('import Quickshell\nimport Quickshell.Io\nShellRoot { IpcHandler { target: "other"; function ping(): string { return "alive"; } } }\n')
    otherlog=(logs/'other-shell.log').open('w')
    def wait(fn,timeout=10):
        end=time.monotonic()+timeout;last=None
        while time.monotonic()<end:
            try:
                if fn():return
            except Exception as e:last=e
            time.sleep(.06)
        raise AssertionError(('timeout',last))
    def call(target,function,*args,selected=gui):
        p=subprocess.run([str(cloud/'bin/qs'),'-p',str(selected),'ipc','call',target,function,*map(str,args)],env=env,capture_output=True,text=True,timeout=15)
        assert p.returncode==0,(p.stdout,p.stderr)
        assert not p.stderr,(p.stdout,p.stderr)
        return p.stdout.strip()
    def state():return json.loads(call('guiTest','state'))
    def save_config(value):
        tmp=cfg.with_suffix('.tmp');tmp.write_text(json.dumps(value));os.replace(tmp,cfg)
    try:
        sway=subprocess.Popen(swaycmd,env=swayenv,stdout=swaylog,stderr=subprocess.STDOUT)
        wait(lambda:any(p.is_socket() for p in xdg.glob('wayland-*')))
        env['WAYLAND_DISPLAY']=next(p.name for p in xdg.glob('wayland-*') if not p.name.endswith('.lock'))
        other=subprocess.Popen([str(cloud/'bin/qs'),'-p',str(othergui)],env=env,stdout=otherlog,stderr=subprocess.STDOUT)
        wait(lambda:call('other','ping',selected=othergui)=='alive')
        qs=subprocess.Popen([str(cloud/'bin/qs'),'-p',str(gui)],env=env,stdout=qslog,stderr=subprocess.STDOUT)
        wait(lambda:state()['width']>0)
        s=state();assert s['preset']=='fade' and s['index']==0
        assert abs(s['zone']-s['width']*default['interaction'].get('clickEdgeStart',.95))<.01 and abs(s['zoneWidth']-s['width']*(1-default['interaction'].get('clickEdgeStart',.95)))<.01
        assert s['panelCount']==1
        assert s['bodyAlpha']==0 and s['masked']
        assert s['contentX']==0 and s['contentY']==0 and abs(s['contentWidth']-s['width'])<.01
        print('PASS: production panel/card/settings loaded on real headless Wayland; Fade default; strip geometry',flush=True)
        width=s['width']
        edge_start=default['interaction'].get('clickEdgeStart',.95)
        edge_mid=(1+edge_start)/2
        for x in [10,width*.5,width*edge_start-1]:
            call('guiTest','wheel',x,-120);assert state()['index']==0,(x,state())
        call('guiTest','wheel',width*edge_mid,-120);wait(lambda:state()['index']==1)
        time.sleep(.16)
        call('guiTest','wheel',width*edge_mid,120);wait(lambda:state()['index']==0)
        print('PASS: wheel input stays inside the configured edge strip',flush=True)
        call('guiTest','drag',width*.5,-80);assert state()['index']==0
        call('guiTest','drag',width*edge_mid,-80);wait(lambda:state()['index']==1)
        print('PASS: actual Qt mouse swipes must start inside right strip',flush=True)
        call('guiTest','move',width*.5)
        before=state()['index'];call('swiftly','swipe','left',4);assert state()['index']==before
        call('guiTest','move',width*edge_mid);wait(lambda:state()['hover']=='daily')
        call('swiftly','swipe','left',4);assert state()['index']==(before+1)%3
        print('PASS: compositor swipe IPC ignores pointer outside strip and accepts inside',flush=True)
        call('guiTest','openSettings');wait(lambda:state()['settingsVisible'])
        assert state()['titleColor']=='#'+default['theme']['foreground'][-6:].lower()
        assert state()['actualForeground']==state()['titleColor']
        call('guiTest','settingsScreenshot',str(logs/'settings.png'));wait(lambda:png_ready(logs/'settings.png'))
        grim=runtime/'usr/bin/grim'
        if grim.exists():
            time.sleep(.08)
            subprocess.run([str(loader),'--library-path',str(libs),str(grim),str(logs/'desktop.png')],env=env,check=True,timeout=10)
        before=cfg.read_bytes()
        call('guiTest','selectPreset',1);call('guiTest','closeSettings')
        wait(lambda:not state()['settingsVisible']);assert cfg.read_bytes()==before
        call('guiTest','openSettings');wait(lambda:state()['settingsVisible'])
        print('PASS: settings signal opens Material dialog; Close discards unsaved preset',flush=True)
        for index,preset in enumerate(['fade','slide','zoom','none']):
            call('guiTest','selectPreset',index)
            call('guiTest','save')
            wait(lambda:json.loads(cfg.read_text())['interaction']['animationPreset']==preset)
            wait(lambda:state()['status']=='Saved')
            assert state()['preset']==preset
        print('PASS: real Material preset pill selection and Save button persist all four presets',flush=True)
        call('guiTest','selectPreset',0);call('guiTest','durationZero');call('guiTest','save')
        wait(lambda:json.loads(cfg.read_text())['interaction']['animationMs']==0)
        print('PASS: real Material duration slider writes zero duration on Save',flush=True)
        call('guiTest','closeSettings')
        for preset in ['fade','slide','zoom','none']:
            value=json.loads(cfg.read_text());value['interaction']['animationPreset']=preset;value['interaction']['animationMs']=800
            save_config(value);wait(lambda:state()['preset']==preset)
            time.sleep(.85)
            old=state()['index'];call('swiftly','next','daily')
            sample=state();new=(old+1)%3
            if preset=='none':assert sample['faces'][new]['opacity']==1 and sample['faces'][old]['opacity']==0
            else:
                assert 0<sample['faces'][old]['opacity']<1,sample
                if preset=='slide':assert abs(sample['faces'][old]['x'])>0,sample
                if preset=='zoom':assert sample['faces'][old]['scale']<1,sample
            wait(lambda:state()['faces'][new]['opacity']==1 and state()['faces'][old]['opacity']==0)
        print('PASS: sampled real fade/slide/zoom transitions; None switches immediately; final states settle',flush=True)
        value=json.loads(cfg.read_text());value['interaction'].pop('animationPreset');save_config(value)
        wait(lambda:state()['preset']=='fade')
        wait(lambda:state()['faces'][state()['index']]['opacity']==1)
        call('guiTest','move',width*.5)
        call('guiTest','screenshot',str(logs/'card.png'));wait(lambda:png_ready(logs/'card.png'))
        call('guiTest','move',width*edge_mid)
        call('guiTest','screenshot',str(logs/'card-overlay.png'));wait(lambda:png_ready(logs/'card-overlay.png'))
        assert state()['panelCount']==1 and state()['contentWidth']==width
        print('PASS: full-width widget keeps its invisible switching strip in the same panel',flush=True)
        print('PASS: legacy config without preset falls back to Fade; real card image captured',flush=True)
        call('guiTest','setAutoReload',False)
        old=state()['generation'];before=cfg.read_bytes()
        assert state()['faces'][0]['revision']=='before'
        facefile.write_text(facefile.read_text().replace('testRevision: "before"','testRevision: "after"'))
        result=subprocess.run(['bash',str(repo/'swiftly/update.sh'),'--reload-only'],env=env,capture_output=True,text=True,timeout=25)
        assert result.returncode==0,(result.stdout,result.stderr)
        wait(lambda:state()['generation']!=old)
        assert cfg.read_bytes()==before,('config changed',before,cfg.read_bytes())
        assert qs.poll() is None,('app exited',qs.returncode,result.stdout,result.stderr)
        assert all(face['revision']=='after' for face in state()['faces'])
        assert other.poll() is None and call('other','ping',selected=othergui)=='alive'
        print('PASS: production update script hard-reloads app/widgets in the same real process and preserves JSON',flush=True)
        previous=json.loads(call('swiftly','status'))['generation']
        qs.terminate();qs.wait(timeout=5)
        result=subprocess.run(['bash',str(repo/'swiftly/update.sh'),'--reload-only'],env=env,capture_output=True,text=True,timeout=30)
        assert result.returncode==0,(result.stdout,result.stderr)
        assert json.loads(call('swiftly','status'))['generation']!=previous
        assert cfg.read_bytes()==before and call('other','ping',selected=othergui)=='alive'
        print('PASS: real stopped app is started automatically; unrelated shell remains alive',flush=True)
        if '--network-update' in sys.argv[4:]:
            # Reproduce the reported update failure using a real existing config.
            legacy=json.loads(cfg.read_text())
            legacy['gestures'].pop('fingers')
            replacement=cfg.with_suffix('.new')
            replacement.write_text(json.dumps(legacy, indent=3)+'\n')
            os.replace(replacement,cfg)
            before=cfg.read_bytes()
            mock=root/'package-mocks';mock.mkdir()
            for name,text in {
                'hyprctl':'#!/bin/bash\necho "Hyprland 0.55.0"\n',
                'pacman':'#!/bin/bash\n[[ $1 = -T ]]\n',
                'sudo':'#!/bin/bash\nexit 99\n',
            }.items():
                (mock/name).write_text(text);(mock/name).chmod(0o755)
            updateenv=dict(env,PATH=str(mock)+':'+env['PATH'])
            hypr=root/'hyprland.lua';hypr.write_text('-- test config\n')
            for label,command in [
                ('explicit', ['bash',str(repo/'swiftly/update.sh'),str(hypr)]),
                ('recorded', ['bash',str(config/'swiftly/update.sh')]),
            ]:
                previous=json.loads(call('swiftly','status'))['generation']
                result=subprocess.run(command,env=updateenv,capture_output=True,text=True,timeout=180)
                (logs/('update-'+label+'.log')).write_text(result.stdout+result.stderr)
                assert result.returncode==0,(result.stdout,result.stderr)
                current=json.loads(call('swiftly','status'))
                assert current['ready'] is True and current['generation']!=previous
                assert current['stacks'][0]['widgets']==3
                assert cfg.read_bytes()==before and call('other','ping',selected=othergui)=='alive'
            call('swiftly','settings')
            if grim.exists():
                time.sleep(.2)
                subprocess.run([str(loader),'--library-path',str(libs),str(grim),str(logs/'updated-desktop.png')],env=env,check=True,timeout=10)
            print('PASS: two real network updates install verified files and reload real app/widgets; recorded no-argument update works',flush=True)
        print('RESULT: 12 real GUI groups passed'+(' + 2 end-to-end network update runs' if '--network-update' in sys.argv[4:] else ''),flush=True)
    finally:
        if qs is not None:
            subprocess.run([str(cloud/'bin/qs'),'-p',str(gui),'kill'],env=env,capture_output=True,timeout=10)
        for p in [qs,other,sway]:
            if p is not None:
                p.terminate()
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill();p.wait()
        swaylog.close();qslog.close();otherlog.close()
