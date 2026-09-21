"""Sample actual native container positions for workspace and shared dialogs.

Uses transient confirmation/rename fixtures; never saves or deletes a building.
"""
import json
import subprocess
import sys
import time
import threading
import mss
from PIL import Image, ImageDraw
import verify_ui as ui
import capture_screen as capture
from verify_materials_paste import game
from verify_large_editor import snapshot
from native_input_mode import key, set_touch


PROBE = '''from HelloScript.pyreact.navigator import NavigatorScreen
from HelloScript.pyreact.debug import _type_name
from HelloScript.pyreact import navigator
import time
api._motion_samples=[]
NavigatorScreen._motion_saved_flush=NavigatorScreen._pyreact_flush
def collect(f, targets):
    name=_type_name(f)
    if name in ('WorkspaceMotion','DialogMotion'):
        targets.append(f)
        return
    for child in f.child_fibers:collect(child, targets)
def sample(targets):
    for f in targets:
        name=_type_name(f)
        outer=f.child_fibers[0]
        moving=outer.child_fibers[1]
        if name=='DialogMotion':moving=moving.child_fibers[0]
        control=f.host.GetBaseUIControl(moving.native_path)
        position=control.GetPosition()
        axis=0 if name=='WorkspaceMotion' else 1
        api._motion_samples.append((time.time(),name,_type_name(f.parent_fiber),position[axis],f.props.get('opened'),
                                   moving.primitive_state.get('motion_alpha',1.),position[1-axis]))
def flush(self):
    result=self._motion_saved_flush()
    if self._root_fiber is not None and len(api._motion_samples)<6000:
        if getattr(self,'_motion_probe_root',None) is not self._root_fiber:
            self._motion_probe_root=self._root_fiber
            self._motion_probe_targets=[]
            collect(self._root_fiber,self._motion_probe_targets)
        sample(self._motion_probe_targets)
    return result
NavigatorScreen._pyreact_flush=flush
_result=True
'''


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    if not game('from HelloScript.pyreact import navigator\n_result=navigator.contains("modern_projection_workspace")'):
        key('p');time.sleep(2.)
    set_touch(False)
    game('s.set("page","workspace")\ns.set("material_browser",None)\ns.set("pending_confirm",None)\ns.set("pending_rename",None)\n_result=True')
    time.sleep(.5)
    original_motion=game('_result=s.reduced_motion')
    records={}
    frames=[]

    def perform(operation, settle=.4):
        if '--visual' not in sys.argv:
            operation()
            return
        frames[:]=[]
        stop=threading.Event()
        left,top,width,height=capture._window_rect(window['hwnd'])
        def record():
            with mss.MSS() as screen:
                while not stop.is_set():
                    raw=screen.grab(dict(left=left,top=top,width=width,height=height))
                    frame=Image.frombytes('RGB',raw.size,raw.bgra,'raw','BGRX')
                    frames.append((time.time(),frame.resize((640,360))))
                    stop.wait(.016)
        thread=threading.Thread(target=record)
        thread.start()
        try:
            operation()
            time.sleep(settle)
        finally:
            stop.set();thread.join()

    def click(node):
        target=node if node['type']=='Button' else ui.nodes('Button',node)[0]
        native=ui.call('native_control',target['id'])['result']
        left,top,width,height=capture._window_rect(window['hwnd'])
        scale=width/ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
        point=tuple(int(origin+(p+size/2)*scale) for origin,p,size in zip((left,top),native['global'],native['size']))
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
        capture.user32.SetCursorPos(*point);time.sleep(.08)
        capture.user32.mouse_event(2,0,0,0,0)
        try:time.sleep(.04)
        finally:capture.user32.mouse_event(4,0,0,0,0)
        time.sleep(.5)
        actual=capture.POINT();capture.user32.GetCursorPos(capture.ctypes.byref(actual))
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground after click'
        assert abs(actual.x-point[0])<3 and abs(actual.y-point[1])<3,'Pointer moved during test'

    def close_action(component=None):
        actions=ui.nodes('Action',ui.nodes(component)[0] if component else None)
        return next(n for n in actions if n['props'].get('label')=='取消') if component in ('Confirmation','RenameDialog') else next(
            n for n in actions if n['props'].get('glyph')=='close' and not n['props'].get('label'))

    def reset():
        game('api._motion_samples=[]\n_result=True')

    def samples(name, component, opening):
        rows=game('_result=api._motion_samples[:]')
        values=[r[3] for r in rows if (r[1]=='WorkspaceMotion' if component=='WorkspaceMotion' else r[2]==component and r[4]==opening)]
        records[name]=rows
        changed=[v for i,v in enumerate(values) if i==0 or abs(v-values[i-1])>.01]
        ui.check(name+' has at least five native intermediate positions',len(changed)>=5 and max(values)-min(values)>(30 if component=='WorkspaceMotion' else 3))
        deltas=[b-a for a,b in zip(changed,changed[1:])]
        # Native flex centering can round the first committed height by <1 px.
        ui.check(name+' moves continuously in the expected direction',all(v<=.5 if opening else v>=-.5 for v in deltas))
        selected=[r for r in rows if (r[1]=='WorkspaceMotion' if component=='WorkspaceMotion' else r[2]==component and r[4]==opening)]
        ui.check(name+' applies intermediate alpha values',len(set(round(r[5],2) for r in selected if .01<r[5]<.99))>=3)
        ui.check(name+' stays on one motion axis',max(r[6] for r in selected)-min(r[6] for r in selected)<.5)
        if component!='WorkspaceMotion':
            scale=game('from HelloScript.projection.widgets import Theme\n_result=Theme.scale')
            ui.check(name+' stays within an 18 design pixel offset',max(values)-min(values)<=18*scale+1.)
        if frames:
            motion=[r for r in rows if (r[1]=='WorkspaceMotion' if component=='WorkspaceMotion' else r[2]==component and r[4]==opening)]
            sheet=Image.new('RGB',(1280,764),'#f1f4f8')
            for i,fraction in enumerate((.08,.35,.65,.92)):
                target=min(values)+(max(values)-min(values))*(1-fraction if opening else fraction)
                stamp=min(motion,key=lambda r:abs(r[3]-target))[0]
                frame=min(frames,key=lambda r:abs(r[0]-stamp))[1]
                x,y=(i%2)*640,(i//2)*382
                sheet.paste(frame,(x,y))
                ImageDraw.Draw(sheet).text((x+8,y+363),'%s  %d%%'%(name,fraction*100),fill='#26374b')
            sheet.save(ui.OUT/(name.replace(' ','_')+'_frames.png'))

    game(PROBE)
    try:
        game('s.set("reduced_motion",False)\n_result=True');time.sleep(.3)
        for preset in ('4:3','16:9'):
            subprocess.run([sys.executable,str(ui.ROOT/'.agents/skills/pyreact-debugging/scripts/resize_window.py'),
                            '--preset',preset],check=True,capture_output=True)
            time.sleep(.6)
            rail=ui.nodes('CategoryRail')[0]
            groups=rail['children'][0]['children'][1]['children']
            bounds=rail['children'][0]['layout']
            top=min(n['layout']['y'] for n in groups)-bounds['y']
            bottom=bounds['y']+bounds['height']-max(n['layout']['y']+n['layout']['height'] for n in groups)
            ui.check(preset+' five categories are vertically centered',len(groups)==5 and abs(top-bottom)<1.5)
        snapshot('workspace_centered_rail')
        reset();perform(lambda:click(close_action()))
        samples('workspace close','WorkspaceMotion',False)
        ui.check('workspace closes after native exit motion',not game('_result=navigator.contains("modern_projection_workspace")'))
        reset();perform(lambda:key('p'),1.5);time.sleep(1.)
        samples('workspace P open','WorkspaceMotion',True)
        ui.check('workspace returns to exact origin',game('_result=[r[3] for r in api._motion_samples if r[1]=="WorkspaceMotion"][-1]')==0.)
        if '--workspace-only' in sys.argv:
            return
        for component,opening in (
            ('Confirmation','s.confirm("Motion check",lambda:None)'),
            ('RenameDialog','s.set("pending_rename",(999,"Motion check"))'),
            ('MaterialBrowser','s.open_materials("material")')):
            reset();perform(lambda:game(opening+'\n_result=True'));time.sleep(.6)
            samples(component+' open',component,True)
            reset();perform(lambda:click(close_action(component)))
            samples(component+' close',component,False)
        # Reverse an in-flight animation twice without remounting the input.
        game('s.open_materials("material")\n_result=True');time.sleep(.5)
        identity=ui.nodes('Input',ui.nodes('BlockInventory')[0])[0]['id']
        reset()
        game('s.set("material_browser",None)\ns.bridge.later(.07,lambda:s.open_materials("material"))\ns.bridge.later(.13,lambda:s.set("material_browser",None))\ns.bridge.later(.18,lambda:s.open_materials("material"))\n_result=True')
        time.sleep(.7)
        ui.check('rapid reversal settles open with the same native input',identity==ui.nodes('Input',ui.nodes('BlockInventory')[0])[0]['id'])
        game('s.set("material_browser",None)\ns.set("reduced_motion",True)\n_result=True');time.sleep(.3)
        reset();game('s.confirm("Reduced motion",lambda:None)\n_result=True');time.sleep(.3)
        values=game('_result=[r[3] for r in api._motion_samples if r[2]=="Confirmation"]')
        ui.check('reduced motion has no intermediate dialog movement',len(set(round(v,2) for v in values))<=2)
        click(close_action('Confirmation'))
        ui.check('reduced motion closes confirmation',not ui.nodes('DialogMotion',ui.nodes('Confirmation')[0])[0]['props']['opened'])
    finally:
        game('''NavigatorScreen._pyreact_flush=NavigatorScreen._motion_saved_flush
del NavigatorScreen._motion_saved_flush
h=api.GetTopScreen()
for name in ('_motion_probe_root','_motion_probe_targets'):
    if hasattr(h,name):delattr(h,name)
s.pending_confirm=None
s.pending_rename=None
s.material_browser=None
s.set('reduced_motion',%r)
_result=True
''' % original_motion)
        output='workspace_motion_checks.json' if '--workspace-only' in sys.argv else 'motion_checks.json'
        (ui.OUT/output).write_text(json.dumps(dict(checks=ui.checks,samples=records),ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
