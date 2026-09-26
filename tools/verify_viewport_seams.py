"""Subpixel viewport origin on first mount, later chunks and modal return."""
import json
import sys
import time
from PIL import Image
import verify_ui as ui
import capture_screen as capture
from verify_font_share_polish import game
from verify_whitelist_runtime import settle
from native_input_mode import key, set_touch, state, open_workspace


def alignment():
    return game('''from modern_projection.pyreact.debug import _type_name
def find(f,name):
    if _type_name(f)==name:return f
    for child in f.child_fibers:
        found=find(child,name)
        if found:return found
def tiles(f):
    if _type_name(f)=='PreviewTile':yield f
    for child in f.child_fibers:
        for tile in tiles(child):yield tile
root=find(api.GetTopScreen()._root_fiber,'Scene').child_fibers[0]
clip=root.host.GetBaseUIControl(root.child_fibers[1].native_path)
expected=tuple(-p for p in clip.GetPosition())
actual=[]
for tile in tiles(root):
    for surface in tile.child_fibers[0].child_fibers[1:]:
        actual.append(surface.host.GetBaseUIControl(surface.native_path).GetPosition())
_result={'expected':expected,'actual':actual,'builds':s.tiles.builds}''')


def check_alignment(name):
    result=alignment()
    ui.check(name, bool(result['actual']) and all(abs(a-b)<1e-5 for p in result['actual'] for a,b in zip(p,result['expected'])))
    return result


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    original_touch=state()['simulated']
    if not game('from modern_projection.pyreact import navigator\n_result=navigator.contains("modern_projection_workspace")'):
        open_workspace();time.sleep(3)
    game('''fields=('editor','name','page','tool','direct_mode','group','inspector','section','solo_layer',
'canvas_x','canvas_z','focused','box_anchor','paste_origin','paste_pinned','camera_yaw','camera_pitch',
'zoom','camera_pan','camera_pivot','camera_depth','camera_depth_pose','camera_pose','focus_view','grid','material_browser')
api._seam70_saved=dict((k,getattr(s,k)) for k in fields)
from modern_projection.projection.model import Document
s._loaded(Document((32,8,16),dict(((x,y,z),('minecraft:red_wool',0)) for x in range(32) for y in range(8) for z in range(16))))
s.editor.selection=set();s.direct_mode='browse';s.grid=False;s.material_browser=None;s.emit()
_result=True''')
    evidence={}
    try:
        settle();evidence['initial']=check_alignment('first mounted tile pairs share the canvas origin')
        game('s.reset_camera(False)\ns.camera_view(8.,25.,1.35)\n_result=True');time.sleep(.7)
        assert capture._activate_window(window['hwnd']);time.sleep(.2)
        assert capture.user32.GetForegroundWindow()==window['hwnd']
        path=ui.OUT/'seam70_fixed.png'
        capture._capture_region_windows(*capture._window_rect(window['hwnd']),path)
        im=Image.open(path).convert('RGB')
        top={}
        for y in range(int(im.height*.32),int(im.height*.7)):
            for x in range(int(im.width*.25),int(im.width*.77)):
                r,g,b=im.getpixel((x,y))
                if r>g*1.7 and r>b*1.7 and r>70 and x not in top:top[x]=y
        ui.check('seam fixture is actually rendered',len(top)>150)
        low,high=min(top),max(top)
        middle=range(int(low+(high-low)*.2),int(low+(high-low)*.9))
        jumps=[abs(top[x+1]-top[x]) for x in middle]
        ui.check('shallow roof edge has no extra step at the chunk join',max(jumps)<=1)
        evidence['roof_max_step']=max(jumps)
        builds=game('_result=s.tiles.builds')
        for page in ('library','workspace'):
            game('s.set("page",%r)\n_result=True'%page);time.sleep(.4)
        settle();evidence['return']=check_alignment('returning to scene preserves every tile origin')
        ui.check('page changes reuse geometry',game('_result=s.tiles.builds')==builds)
        game('''s._loaded(Document((64,128,64),{(0,0,0):('minecraft:stone',0)}))
s.material_browser=None;s.emit()
_result=True''');settle()
        initial=len(alignment()['actual'])
        game('''s.editor.material=('minecraft:stone',0)
s.editor.select_box((48,80,48),(48,80,48));s.editor.run('fill')
s.refresh_preview();s.emit()
_result=True''');settle()
        evidence['late']=check_alignment('a new distant chunk receives origin compensation on both buffers')
        ui.check('late-mount regression actually created another renderer',len(evidence['late']['actual'])>initial)
        game('s.editor.undo();s.refresh_preview();s.emit()\n_result=True');settle()
        check_alignment('undo preserves native origins')
        if '--touch' in sys.argv:
            from verify_native_touch import sustained_drag
            set_touch(True)
            sustained_drag('solid')
            sustained_drag('demo_large')
    finally:
        set_touch(original_touch)
        game('''for k,v in api._seam70_saved.items():setattr(s,k,v)
s.camera_revision+=1;s.refresh_preview();s.emit()
_result=True''')
        if not game('_result=s.material_browser is not None'):settle()
        evidence['checks']=ui.checks
        (ui.OUT/'seam70_checks.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
