"""Native clipping pixels and catalogue occlusion; restore the in-memory draft."""
import json
import math
import subprocess
import sys
import time
from PIL import Image
import verify_ui as ui
import capture_screen as capture
from verify_font_share_polish import game
from verify_whitelist_runtime import settle
from verify_biome_controls import native_click, action
from native_input_mode import key, set_touch, state, open_workspace


def controls():
    return game('''from HelloScript.pyreact.debug import _type_name
def find(f,name):
    if _type_name(f)==name:return f
    for child in f.child_fibers:
        found=find(child,name)
        if found:return found
scene=find(api.GetTopScreen()._root_fiber,'Scene').child_fibers[0]
api._clip70_groups=[scene.host.GetBaseUIControl(f.native_path) for f in scene.child_fibers[:4]]
_result=[{'position':c.GetGlobalPosition(),'size':c.GetSize(),'visible':c.GetVisible()} for c in api._clip70_groups]''')


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    original_size=capture._window_rect(window['hwnd'])[2:]
    small='--small' in sys.argv
    resize=str(ui.ROOT/'.agents/skills/pyreact-debugging/scripts/resize_window.py')
    if not game('from HelloScript.pyreact import navigator\n_result=navigator.contains("modern_projection_workspace")'):
        open_workspace();time.sleep(3)
    original_touch=state()['simulated']
    game('''fields=('editor','name','page','tool','direct_mode','group','inspector','section','solo_layer',
'canvas_x','canvas_z','focused','box_anchor','paste_origin','paste_pinned','camera_yaw','camera_pitch',
'zoom','camera_pan','camera_pivot','camera_depth','camera_depth_pose','camera_pose','focus_view','grid','material_browser')
api._clip70_saved=dict((k,getattr(s,k)) for k in fields)
from HelloScript.projection.model import Document
s._loaded(Document((8,8,8),dict(((x,y,z),('minecraft:red_wool',0)) for x in range(8) for y in range(8) for z in range(8))))
s.direct_mode='browse';s.grid=True;s.material_browser=None;s.focus_view=False;s.emit()
_result=True''')
    def shot(name):
        assert capture._activate_window(window['hwnd']), 'Game focus denied'
        time.sleep(.25)
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
        rect=capture._window_rect(window['hwnd'])
        filename=ui.OUT/('clip70_'+('small_' if small else '')+name+'.png')
        capture._capture_region_windows(*rect,filename)
        return Image.open(filename).convert('RGB')
    evidence={}
    try:
        if small:
            subprocess.run([sys.executable,resize,'--size','1280x960'],check=True,capture_output=True)
            time.sleep(1)
        set_touch(False);settle()
        game('s.reset_camera(False)\ns.camera_view(35.,25.,2.5)\n_result=True');time.sleep(.7)
        builds=game('_result=s.tiles.builds')
        for name,pan in (('center',(0.,0.)),('down',(0.,.4)),('up',(0.,-.4)),('left',(-.7,0.)),('right',(.7,0.)),('expanded',(0.,0.))):
            if name=='expanded':
                game('s.set("focus_view",True)\n_result=True');time.sleep(.7)
            game('s.camera_pan=%r\ns.emit("view")\n_result=True'%(pan,));time.sleep(.5)
            groups=controls()
            ui.check(name+' has one clip rectangle for models/grid/blue/spectrum',
                     all(g['position']==groups[1]['position'] and g['size']==groups[1]['size'] for g in groups))
            frame=shot(name+'_after')
            root=ui.nodes('SafeArea')[0]['children'][0]['layout']
            scale=round(frame.width/root['width'])
            x,y=groups[1]['position'];w,h=groups[1]['size']
            box=tuple(int(round(v*scale)) for v in (x,y,x+w,y+h))
            frame.crop((box[0],box[1]-6,box[2],box[1]+12)).resize((box[2]-box[0],72)).save(ui.OUT/('clip70_'+name+'_top.png'))
            frame.crop((box[0],box[3]-12,box[2],box[3]+6)).resize((box[2]-box[0],72)).save(ui.OUT/('clip70_'+name+'_bottom.png'))
            # Read pixels immediately outside the intended model clip. Red is
            # fixture geometry; blue belongs to the outline in these strips.
            outside=[]
            for yy in (box[1]-2,box[1]-1,box[3],box[3]+1):
                row=[frame.getpixel((xx,yy)) for xx in range(box[0]+2,box[2]-2)]
                outside.append(sum((r>g*1.7 and r>b*1.7 and r>70) or (b>r*1.5 and b>g*1.2 and b>150) for r,g,b in row))
            for xx in (box[0]-2,box[0]-1,box[2],box[2]+1):
                column=[frame.getpixel((xx,yy)) for yy in range(box[1]+2,box[3]-2)]
                outside.append(sum((r>g*1.7 and r>b*1.7 and r>70) or (b>r*1.5 and b>g*1.2 and b>150) for r,g,b in column))
            evidence[name]={'groups':groups,'box':box,'outside':outside}
            evidence[name]['lines']=game('''_result=[]
for group in (2,3):
    for f in scene.child_fibers[group].child_fibers:
        c=scene.host.GetBaseUIControl(f.native_path)
        if c.GetVisible():
            im=c.asImage()
            _result.append({'group':group,'position':c.GetGlobalPosition(),'size':c.GetSize(),
                            'angle':im.GetRotateAngle(),'pivot':im.GetRotatePivot(),'rect':im.GetRotateRect()})''')
            ui.check(name+' model and outline stay inside all four sides',not any(outside))
        game('s.set("focus_view",False)\ns.camera_pan=(0.,0.)\ns.emit("view")\n_result=True');time.sleep(.7)
        for touch in (False,True):
            set_touch(touch)
            game('s.set("material_browser","material")\n_result=True');time.sleep(.8)
            groups=controls()
            ui.check(('F11' if touch else 'PC')+' modal suspends native model draw',not groups[1]['visible'])
            native_click(action('彩色方块',ui.nodes('BlockInventory')[0]))
            frame=shot('catalogue_'+('touch' if touch else 'pc'))
            node=ui.call('native_control',ui.nodes('Button',action('彩色方块',ui.nodes('BlockInventory')[0]))[0]['id'])['result']
            root=ui.nodes('SafeArea')[0]['children'][0]['layout'];scale=round(frame.width/root['width'])
            x,y=node['global'];w,h=node['size']
            # The empty right half of the category is flat fill. A viewport
            # scissor leak changed exactly one row to (247,249,252) here.
            rows=[]
            for yy in range(math.ceil((y+5)*scale),math.floor((y+h-5)*scale)):
                rows.append(tuple(frame.getpixel((int((x+w*.85)*scale),yy))))
            ui.check(('F11' if touch else 'PC')+' category has no stray horizontal row',len(set(rows))==1)
            game('s.set("material_browser",None)\n_result=True');settle()
            ui.check(('F11' if touch else 'PC')+' closing modal restores existing models',controls()[1]['visible'])
        ui.check('camera and modal changes do not rebuild geometry',game('_result=s.tiles.builds')==builds)
        evidence['checks']=ui.checks
    finally:
        if small:
            subprocess.run([sys.executable,resize,'--size','%dx%d'%original_size],check=True,capture_output=True)
            time.sleep(.5)
        set_touch(original_touch)
        game('''for k,v in api._clip70_saved.items():setattr(s,k,v)
s.camera_revision+=1;s.refresh_preview();s.emit()
_result=True''')
        if not game('_result=s.material_browser is not None'):settle()
        (ui.OUT/('clip70_'+('small_' if small else '')+'checks.json')).write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
