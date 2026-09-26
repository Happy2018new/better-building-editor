"""Actual pixels: nearest chunk, through-building clipping, edit/undo and pages.

Uses a temporary in-memory draft. Does not write world blocks or the library.
"""
import json
import time
from PIL import Image
import verify_ui as ui
from verify_font_share_polish import game
from verify_whitelist_runtime import settle
from verify_complete_projection import snapshot
from verify_interaction import pointer


def main():
    game('''from modern_projection.projection.model import Document
fields=('editor','name','page','tool','direct_mode','group','inspector','section','solo_layer',
'canvas_x','canvas_z','focused','box_anchor','paste_origin','paste_pinned','camera_yaw','camera_pitch',
'zoom','camera_pan','camera_pivot','camera_depth','camera_depth_pose','camera_pose','focus_view','grid')
api._depth69_saved=dict((k,getattr(s,k)) for k in fields)
blocks={}
for x in range(32):
    for y in range(16):
        blocks[(x,y,7)]=('minecraft:blue_wool',0)
        blocks[(x,y,24)]=('minecraft:red_wool',0)
s._loaded(Document((32,16,32),blocks))
s.direct_mode='browse';s.grid=False;s.focus_view=False;s.emit()
_result=True''')
    try:
        settle()
        def pixels(name, expected):
            time.sleep(.6)
            snapshot('depth69_'+name)
            im=Image.open(ui.OUT/('depth69_'+name+'.jpg')).convert('RGB')
            native=ui.call('native_control',pointer()['id'])['result']
            root=ui.nodes('SafeArea')[0]['children'][0]['layout']
            x,y=native['global'];w,h=native['size']
            sx,sy=im.width/root['width'],im.height/root['height']
            patch=im.crop((int((x+w*.45)*sx),int((y+h*.45)*sy),int((x+w*.55)*sx),int((y+h*.55)*sy)))
            red=sum(r>b*1.5 and r>g*1.5 for r,g,b in patch.getdata())
            blue=sum(b>r*1.5 and b>g*1.1 for r,g,b in patch.getdata())
            count=red if expected=='red' else blue
            ui.check(name+' sees '+expected+' in front',count>patch.width*patch.height*.8)
            return {'red':red,'blue':blue,'area':patch.width*patch.height}

        builds=game('_result=s.tiles.builds')
        results={}
        for name,yaw,depth,color in (('front',0,0,'red'),('back',180,0,'blue'),('inside',0,16,'blue')):
            game('s.reset_camera(False)\ns.camera_view(%r,0,1.3)\ns.camera_depth=%r\ns.emit("camera_depth")\n_result=True'%(yaw,depth))
            results[name]=pixels(name,color)
        ui.check('camera changes reuse geometry',game('_result=s.tiles.builds')==builds)
        game('s.set("page","library")\n_result=True');time.sleep(.4)
        game('s.set("page","workspace")\n_result=True');settle()
        results['reopened']=pixels('reopened','blue')
        game('''s.editor.select_box((0,0,7),(31,15,7))
s.editor.material=('minecraft:red_wool',0)
s.editor.run('fill');s.refresh_preview();s.emit()
_result=True''');settle()
        results['edit']=pixels('edit','red')
        game('s.editor.undo();s.refresh_preview();s.emit()\n_result=True');settle()
        results['undo']=pixels('undo','blue')
        (ui.OUT/'depth69_pixels.json').write_text(json.dumps({'checks':ui.checks,'pixels':results},indent=2),encoding='utf8')
    finally:
        game('''for k,v in api._depth69_saved.items():setattr(s,k,v)
s.camera_revision+=1;s.refresh_preview();s.emit()
_result=True''')
        settle()


if __name__=='__main__':main()
