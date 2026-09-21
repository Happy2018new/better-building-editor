"""Real filter toggles and both geometry paths, using a restored test-world fixture."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_projection_outline import game, server
from verify_large_editor import snapshot
from native_input_mode import set_touch, state, key


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    original_touch=state()['simulated']
    origin=server('''from HelloScript.HelloServerSystem import WorldAdapter
a=WorldAdapter(p)
offsets=(0,1,2,3,4,17,33)
foot=tuple(int(v) for v in f.CreatePos(p).GetFootPos())
choices=[(foot[0]+dx,foot[1]+dy,foot[2]) for dy in (20,32,40) for dx in (-16,-32,0)]
for origin in choices:
    saved=[((origin[0]+x,origin[1],origin[2]),a.read((origin[0]+x,origin[1],origin[2]))) for x in offsets]
    if all(value==("minecraft:air",0) for pos,value in saved):break
assert all(value==("minecraft:air",0) for pos,value in saved)
api._filter_saved=saved
values=[("minecraft:oak_planks",0),("minecraft:red_wool",0),("minecraft:spruce_log",1),("minecraft:gold_block",0),("minecraft:air",0),("minecraft:oak_planks",0),("minecraft:air",0)]
for (pos,unused),value in zip(saved,values):a.write(pos,value)
_result=origin''')
    game('''api._filter_saved=(s.editor,s.origin,s.page,s.projection_missing,s.apply_air,s.bridge.geometry,s.projection_outline)
api._filter_builds=[]
def wrap_geometry(original,records):
    def build(document,visible=None,name=None):
        points=[p for p in document.blocks if visible is None or visible(p)]
        records.append((document.size,points))
        return original(document,visible,name)
    return build
s.bridge.geometry=wrap_geometry(s.bridge.geometry,api._filter_builds)
s.bridge.stop_projection()
from HelloScript.projection.model import Document,Editor
s.origin='''+repr(tuple(origin))+'''
values=[("minecraft:planks",0),("minecraft:wool",14),("minecraft:log",5),("minecraft:quartz_block",0),("minecraft:quartz_block",0)]
s.editor=Editor(Document((5,1,1),dict(((i,0,0),v) for i,v in enumerate(values))))
s.projection_missing=False
s.projection_outline=True
s.apply_air=True
s.set("page","projection")
s.refresh_preview()
_result=True''')

    def click(label):
        target=next(n for n in ui.nodes('Action') if n['props'].get('label')==label)
        button=ui.nodes('Button',target)[0]
        native=ui.call('native_control',button['id'])['result']
        left,top,width,height=capture._window_rect(window['hwnd'])
        scale=width/ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
        pos=tuple(int(a+(b+d/2)*scale) for a,b,d in zip((left,top),native['global'],native['size']))
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
        capture.user32.SetCursorPos(*pos);time.sleep(.15)
        capture.user32.mouse_event(2,0,0,0,0)
        try:time.sleep(.08)
        finally:capture.user32.mouse_event(4,0,0,0,0)
        time.sleep(.6)
        actual=capture.POINT();capture.user32.GetCursorPos(capture.ctypes.byref(actual))
        assert capture.user32.GetForegroundWindow()==window['hwnd'] and abs(actual.x-pos[0])<3 and abs(actual.y-pos[1])<3,'Game/pointer moved'

    def wait_builds(minimum=1):
        for unused in range(80):
            result=game('_result={"busy":s.busy,"preparing":s.bridge.preparing_entity,"builds":api._filter_builds,"active":s.projection_active,"message":s.editor.message}')
            if not result['busy'] and not result['preparing'] and len(result['builds'])>=minimum:return result
            time.sleep(.12)
        raise AssertionError(result)

    try:
        time.sleep(1.)
        ui.click('写入')
        ui.check('removed world undo has no button or retained action',not any(n['props'].get('label')=='撤销世界写入' for n in ui.nodes('Action')))
        click('应用到世界')
        labels=ui.labels(ui.nodes('Confirmation')[0])
        ui.check('air warning uses short semantic paragraphs',all(v in labels for v in ('将草稿同步到世界？','空气位置的已有方块也会被清除。','此操作无法撤销。')))
        snapshot('stage50_write_confirmation')
        key('esc');time.sleep(.4)
        ui.click('辅助')
        game('s.bridge.project()\n_result=True');result=wait_builds()
        ui.check('unfiltered small projection contains all five draft blocks',len(result['builds'][-1][1])==5)
        for touch in (False,True):
            set_touch(touch);time.sleep(.5)
            if '仅显示缺失方块' not in [n['props'].get('label') for n in ui.nodes('Action')]:ui.click('辅助')
            game('api._filter_builds[:]=[]\n_result=True')
            click('仅显示缺失方块');result=wait_builds()
            ui.check(('F11' if touch else 'PC')+' toggle immediately hides aliases and retains wrong/missing cells',result['builds'][-1][1]==[[3,0,0],[4,0,0]])
            game('api._filter_builds[:]=[]\n_result=True')
            click('仅显示缺失方块');result=wait_builds()
            ui.check(('F11' if touch else 'PC')+' off immediately restores full projection',len(result['builds'][-1][1])==5)
        server('a=WorldAdapter(p)\nfor x in (3,4):a.write((%d+x,%d,%d),("minecraft:quartz_block",0))\n_result=True'%tuple(origin))
        time.sleep(.5)
        game('api._filter_builds[:]=[]\n_result=True')
        click('仅显示缺失方块');result=wait_builds()
        ui.check('all completed means no ghost blocks with range still active',not result['builds'][-1][1] and game('_result=s.bridge.entity is None and s.projection_active and s.bridge.projection_outline.entity is not None'))
        click('仅显示缺失方块');time.sleep(.4)
        server('a=WorldAdapter(p)\na.write((%d+3,%d,%d),("minecraft:gold_block",0))\na.write((%d+4,%d,%d),("minecraft:air",0))\n_result=True'%(tuple(origin)+tuple(origin)))
        game('''s.bridge.stop_projection()
blocks=dict(s.editor.document.blocks.items())
blocks[(17,0,0)]=("minecraft:planks",0)
blocks[(33,0,0)]=("minecraft:quartz_block",0)
s.editor=Editor(Document((64,128,64),blocks))
s.projection_missing=True
api._filter_builds[:]=[]
s.bridge.project()
s.emit()
_result=True''')
        result=wait_builds(3)
        ui.check('64x128x64 chunks retain exactly three missing/wrong blocks',sum(len(v[1]) for v in result['builds'])==3)
        ui.check('large filter retains full document bounds',game('_result=s.bridge.projection_outline.bounds[1]')==[64,128,64])
    finally:
        (ui.OUT/'stage50_filter_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')
        game('s.bridge.stop_projection()\n_result=True')
        server('a=WorldAdapter(p)\nfor pos,value in api._filter_saved:a.write(pos,value)\n_result=True')
        game('s.editor,s.origin,s.page,s.projection_missing,s.apply_air,s.bridge.geometry,s.projection_outline=api._filter_saved\ns.set("pending_confirm",None)\ns.refresh_preview()\ns.emit()\n_result=True')
        set_touch(original_touch)


if __name__=='__main__':main()
