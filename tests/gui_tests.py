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
for old in [logs/'card.png',logs/'settings.png']: old.unlink(missing_ok=True)
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
    gui=root/'gui';shutil.copytree(repo/'swiftly/gui',gui)
    shutil.copy2(repo/'swiftly/SwiftlyBridge.qml',gui/'SwiftlyBridge.qml')
    cardfile=gui/'SwiftlyCard.qml'
    cardfile.write_text(cardfile.read_text().replace('id: card','id: card\n    readonly property alias testColors: colors',1))
    shell=(gui/'shell.qml').read_text()
    shell=shell.replace('import Quickshell\n','import Quickshell\nimport Quickshell.Io\nimport QtTest\n')
    shell=shell.replace('    Variants {','    Variants {\n        id: testPanels')
    shell=shell.replace('required property var modelData','readonly property alias testCard: widgetCard\n            required property var modelData')
    probe='''
    TestCase {
        id: input
        name: "GuiInput"
        when: false
        parent: testPanels.instances.length ? testPanels.instances[0].testCard : null
    }
    IpcHandler {
        target: "guiTest"
        function state(): string {
            const card = testPanels.instances[0].testCard;
            const faces = [];
            for (let i=0; i<card.widgetRepeater.count; i++) {
                const face=card.widgetRepeater.itemAt(i);
                faces.push({opacity:face.opacity, x:face.x, scale:face.scale});
            }
            return JSON.stringify({index:card.selectedIndex,width:card.width,zone:card.switchArea.x,zoneWidth:card.switchArea.width,railWidth:card.rail.width,masked:testPanels.instances[0].mask.item===card.switchArea,bodyAlpha:card.color.a,contentX:card.contentArea.x,contentY:card.contentArea.y,contentWidth:card.contentArea.width,contentHeight:card.contentArea.height,preset:card.preset,duration:card.duration,faces:faces,hover:runtimeBridge.pointerStackId,settingsVisible:settings.visible,status:settings.status,sourceForeground:card.testColors.theme.foreground,actualForeground:card.testColors.foreground.toString(),titleColor:input.findChild(settings.contentItem,"settingsHeading").color.toString(),presetFill:input.findChild(settings.contentItem,"preset-0").background.color.toString()});
        }
        function wheel(x: real, delta: int): void { input.mouseWheel(testPanels.instances[0].testCard,x,80,0,delta); }
        function move(x: real): void { input.mouseMove(testPanels.instances[0].testCard,x,80); }
        function drag(x: real, dx: real): void { input.mouseDrag(testPanels.instances[0].testCard,x,80,dx,0); }
        function selectPreset(index: int): void {
            const button=input.findChild(settings.contentItem,"preset-"+index);
            input.mouseClick(button);
        }
        function openSettings(): void { const button=input.findChild(testPanels.instances[0].testCard,"cardSettings"); input.mouseClick(button); }
        function durationZero(): void { const slider=input.findChild(settings.contentItem,"animationDuration"); input.mouseClick(slider,slider.leftPadding,slider.height/2); }
        function save(): void { const button=input.findChild(settings.contentItem,"saveAnimation"); input.mouseClick(button); }
        function settingsScreenshot(path: string): void { settings.contentItem.grabToImage(result => result.saveToFile(path)); }
        function closeSettings(): void { settings.close(); }
        function screenshot(path: string): void { testPanels.instances[0].testCard.grabToImage(result => result.saveToFile(path)); }
    }
'''
    (gui/'shell.qml').write_text(shell.rsplit('}',1)[0]+probe+'}\n')
    swayconfig=root/'sway.conf'
    swayconfig.write_text('output * mode 1280x720\nseat * hide_cursor 0\nxwayland disable\nswaybg_command -\n')
    env=dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(config),XDG_RUNTIME_DIR=str(xdg),WLR_BACKENDS='headless',WLR_RENDERER='pixman',WLR_LIBINPUT_NO_DEVICES='1',QT_QPA_PLATFORM='wayland',QT_QUICK_BACKEND='software',QT_QUICK_CONTROLS_STYLE='Basic',XDG_CURRENT_DESKTOP='sway')
    # Sway's dlopened wlroots must resolve against the private library set too.
    swayenv=dict(env,LD_LIBRARY_PATH=str(libs))
    # This test config disables optional Xwayland/background subprocesses.
    swaycmd=[str(loader),'--library-path',str(libs),str(runtime/'usr/bin/sway'),'--unsupported-gpu','-c',str(swayconfig)]
    swaylog=(logs/'sway.log').open('w');qslog=(logs/'quickshell.log').open('w')
    sway=None;qs=None
    def wait(fn,timeout=10):
        end=time.monotonic()+timeout;last=None
        while time.monotonic()<end:
            try:
                if fn():return
            except Exception as e:last=e
            time.sleep(.06)
        raise AssertionError(('timeout',last))
    def call(target,function,*args):
        p=subprocess.run([str(cloud/'bin/qs'),'-p',str(gui),'ipc','call',target,function,*map(str,args)],env=env,capture_output=True,text=True,timeout=15)
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
        qs=subprocess.Popen([str(cloud/'bin/qs'),'-p',str(gui)],env=env,stdout=qslog,stderr=subprocess.STDOUT)
        wait(lambda:state()['width']>0)
        s=state();assert s['preset']=='fade' and s['index']==0
        assert abs(s['zone']-s['width']*.95)<.01 and abs(s['zoneWidth']-s['width']*.05)<.01
        assert abs(s['railWidth']-s['width']*.05)<.01 and s['bodyAlpha']==0 and s['masked']
        assert s['contentX']==0 and s['contentY']==0 and abs(s['contentWidth']-s['width']*.95)<.01
        print('PASS: production panel/card/settings loaded on real headless Wayland; Fade default; strip geometry',flush=True)
        width=s['width']
        for x in [10,width*.5,width*.95-1]:
            call('guiTest','wheel',x,-120);assert state()['index']==0,(x,state())
        call('guiTest','wheel',width*.975,-120);wait(lambda:state()['index']==1)
        time.sleep(.16)
        call('guiTest','wheel',width*.975,120);wait(lambda:state()['index']==0)
        print('PASS: actual Qt wheel events ignored in left 95%, advance/reverse in right 5%',flush=True)
        call('guiTest','drag',width*.5,-80);assert state()['index']==0
        call('guiTest','drag',width*.975,-80);wait(lambda:state()['index']==1)
        print('PASS: actual Qt mouse swipes must start inside right strip',flush=True)
        call('guiTest','move',width*.5)
        before=state()['index'];call('swiftly','swipe','left',4);assert state()['index']==before
        call('guiTest','move',width*.975);wait(lambda:state()['hover']=='daily')
        call('swiftly','swipe','left',4);assert state()['index']==(before+1)%3
        print('PASS: compositor swipe IPC ignores pointer outside strip and accepts inside',flush=True)
        call('guiTest','openSettings');wait(lambda:state()['settingsVisible'])
        assert state()['titleColor']=='#'+default['theme']['foreground'][-6:].lower()
        assert state()['actualForeground']==state()['titleColor']
        call('guiTest','settingsScreenshot',str(logs/'settings.png'));wait(lambda:png_ready(logs/'settings.png'))
        before=cfg.read_bytes()
        call('guiTest','selectPreset',1);call('guiTest','closeSettings')
        wait(lambda:not state()['settingsVisible']);assert cfg.read_bytes()==before
        call('guiTest','openSettings');wait(lambda:state()['settingsVisible'])
        print('PASS: rail menu tap opens Material dialog; Close discards unsaved preset',flush=True)
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
        call('guiTest','screenshot',str(logs/'card.png'));wait(lambda:png_ready(logs/'card.png'))
        print('PASS: legacy config without preset falls back to Fade; real card image captured',flush=True)
        print('RESULT: 9 real GUI groups passed',flush=True)
    finally:
        for p in [qs,sway]:
            if p is not None:
                p.terminate()
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill();p.wait()
        swaylog.close();qslog.close()
