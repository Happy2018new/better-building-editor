"""Aux controls, retained palette, depth outlines; preserve the current draft."""
import base64
import json
import sys
import time
import verify_ui as ui
import capture_screen as capture
from verify_font_share_polish import game
from verify_foreground_finish import snap, native_click
from native_input_mode import set_touch, state


def reload_code():
    game('''from HelloScript.pyreact import navigator
if navigator.contains('modern_projection_workspace'):navigator.pop()
_result=True''')
    time.sleep(.4)
    for name in ('scene_lines','materials','bridge','session','panels','material_browser','scene','ui'):
        data=base64.b64encode((ui.ROOT/('behavior_pack/HelloScript/projection/'+name+'.py')).read_bytes()).decode('ascii')
        game('''import base64,importlib
module=importlib.import_module('HelloScript.projection.%s')
names=dict(getattr(module,'DISPLAY_NAMES',{}))
exec(compile(base64.b64decode(%r),%r,'exec'),module.__dict__)
if names:module.DISPLAY_NAMES.update(names)
_result=True'''%(name,data,name+'.py'))
    game('''from HelloScript.projection.session import Session
from HelloScript.projection.ui import Workspace
from HelloScript.projection.bridge import ClientBridge
from HelloScript import HelloClientSystem
s.__class__=Session
s.bridge.__class__=ClientBridge
HelloClientSystem.Workspace=Workspace
HelloClientSystem.Session=Session
navigator.push(Workspace(session=s),key='modern_projection_workspace')
_result=True''')
    time.sleep(3.)


def click_action(label, root, window):
    action=next(n for n in ui.nodes('Action',root) if n['props'].get('label')==label)
    native_click(ui.nodes('Button',action)[0], window)


def verify_palette(window):
    game('s.set("material_browser",None)\n_result=True');time.sleep(.5)
    game('''from HelloScript.pyreact import *
from HelloScript.projection.panels import MaterialPicker
from HelloScript.projection.widgets import surface
@Component
def PaletteCheck():
    return SafeArea(style=Style(width='100%',height='100%'),children=Panel(
        style=Style(width='100%',height='100%',alignItems=AlignItems.center,justifyContent=JustifyContent.center),
        children=surface(width=250,padding=16,children=MaterialPicker(session=s))))
navigator.push(PaletteCheck(),key='palette_check')
_result=True''')
    time.sleep(.8)
    screen=ui.nodes('SafeArea')[0]['children'][0]['layout']
    left,top,width,height=capture._window_rect(window['hwnd'])
    scale=width/screen['width']
    root=ui.nodes('MaterialPicker')[0]
    cells=ui.nodes('PaletteCell',root)
    positions=[]
    for cell in cells[:4]:
        control=ui.call('native_control',ui.nodes('Button',cell)[0]['id'])['result']
        positions.append((int(left+(control['global'][0]+control['size'][0]/2.)*scale),
                          int(top+(control['global'][1]+control['size'][1]/2.)*scale)))
    assert all(left<=x<left+width and top<=y<top+height for x,y in positions),(positions,(left,top,width,height),screen,control)
    game('''api._aux_picks=[]
def record_picks(session,events):
    return session.subscribe(lambda:events.append(session.editor.material),('materials',))
api._aux_stop_picks=record_picks(s,api._aux_picks)
s.editor.material=('minecraft:air',0)
_result=True''')
    try:
        for i in range(12):
            assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground; stopped native palette clicks'
            capture.user32.SetCursorPos(*positions[i%4]);time.sleep(.04)
            capture.user32.mouse_event(2,0,0,0,0)
            time.sleep(.04)
            capture.user32.mouse_event(4,0,0,0,0)
            time.sleep(.045)
        time.sleep(.5)
        expected=[cells[i%4]['props']['value'] for i in range(12)]
        ui.check('12 rapid real palette clicks keep exact order and aux',game('_result=api._aux_picks')==expected)
        for cell in cells:
            badge=ui.nodes('AuxBadge',cell)[0]
            ui.check('palette tile carries its own aux badge',badge['props']['value']==cell['props']['value'][1])
        snap('stage56_palette')
    finally:
        capture.user32.mouse_event(4,0,0,0,0)
        game('api._aux_stop_picks()\n_result=True')


def main():
    if '--reload' in sys.argv:reload_code()
    if '--reload-only' in sys.argv:return
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd']), 'FOCUS_DENIED; no input sent'
    original_mode=state()['simulated']
    game('''import json
api._aux_document=json.dumps(s.editor.document.to_data(),sort_keys=True,ensure_ascii=True)
api._aux_saved=(s.page,s.direct_mode,s.inspector,s.material_browser,list(s.palette),s.bridge.save_preferences,
    s.editor.material,s.editor.secondary,s.editor.source,s.editor.filter_material,
    s.editor.selection,s.editor.start,s.editor.end,s.editor.selection_revision,s.box_anchor,
    s.camera_yaw,s.camera_pitch,s.zoom,s.camera_pan,s.camera_pivot,s.camera_depth,s.grid)
s.bridge.save_preferences=lambda data:None
s.page='workspace';s.direct_mode='place';s.inspector='params';s.emit()
_result=True''')
    try:
        if '--palette-only' in sys.argv:
            if '--touch-palette' in sys.argv:set_touch(True)
            verify_palette(window)
            return
        for touch in (False,True):
            set_touch(touch)
            game("s.open_materials('material')\n_result=True")
            time.sleep(1.4)
            root=ui.nodes('BlockInventory')[0]
            search=ui.nodes('Input',root)[0]
            ui.call('set_input',search['id'],'羊毛')
            time.sleep(.3)
            root=ui.nodes('BlockInventory')[0]
            cell=next(n for n in ui.nodes('InventoryCell',root) if n['props']['item'] and
                      n['props']['item']['value']==['minecraft:wool',0])
            native_click(ui.nodes('Button',cell)[0],window)
            root=ui.nodes('AuxEditor')[0]
            plus=next(n for n in ui.nodes('Action',root) if n['props'].get('glyph')=='plus')
            native_click(ui.nodes('Button',plus)[0],window)
            ui.check(('touch' if touch else 'pc')+' native aux increment',
                     ui.nodes('AuxEditor')[0]['props']['value']==['minecraft:wool',1])
            root=ui.nodes('AuxEditor')[0]
            aux=ui.nodes('Input',root)[0]
            ui.call('set_input',aux['id'],'15');time.sleep(.2)
            root=ui.nodes('BlockInventory')[0]
            ui.check('catalogue preview uses aux 15',any(n['props'].get('value')==['minecraft:wool',15]
                                                      for n in ui.nodes('MaterialIcon',root)))
            ui.check('variant name matches the black wool preview', '黑色羊毛' in ui.labels(root))
            snap('stage56_aux_'+('touch' if touch else 'pc'))
            click_action('添加并使用',root,window)
            ui.check('aux variant selected and retained in palette',game('_result=s.editor.material==("minecraft:wool",15) and ("minecraft:wool",15) in s.palette'))
            time.sleep(.5)
        game('s.open_materials("material")\n_result=True');time.sleep(.5)
        aux=ui.nodes('Input',ui.nodes('AuxEditor')[0])[0]
        ui.call('set_input',aux['id'],'**');time.sleep(.2)
        root=ui.nodes('BlockInventory')[0]
        add=next(n for n in ui.nodes('Action',root) if n['props'].get('label')=='添加并使用')
        ui.check('filtered aux disables adding without corrupting selection',not add['props']['enabled'])
        click_action('归零',root,window)
        ui.check('stepper recovers invalid input without keyboard',ui.nodes('AuxEditor')[0]['props']['value']==['minecraft:wool',0])
        verify_palette(window)
    finally:
        game('''from HelloScript.pyreact import navigator
if navigator.contains('palette_check'):navigator.pop()
_result=True''')
        game('''(s.page,s.direct_mode,s.inspector,s.material_browser,palette,s.bridge.save_preferences,
    s.editor.material,s.editor.secondary,s.editor.source,s.editor.filter_material,
    s.editor.selection,s.editor.start,s.editor.end,s.editor.selection_revision,s.box_anchor,
    s.camera_yaw,s.camera_pitch,s.zoom,s.camera_pan,s.camera_pivot,s.camera_depth,s.grid)=api._aux_saved
s.palette=palette
s.camera_pose=(s.camera_yaw,s.camera_pitch,s.zoom);s.camera_revision+=1
s.emit()
assert json.dumps(s.editor.document.to_data(),sort_keys=True,ensure_ascii=True)==api._aux_document
_result=True''')
        set_touch(original_mode)
        report=('stage56_palette_touch_checks.json' if '--touch-palette' in sys.argv else
                'stage56_palette_checks.json' if '--palette-only' in sys.argv else 'stage56_aux_checks.json')
        (ui.OUT/report).write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
