"""Record transient missing tiles during native orbit, preserving the draft."""
import argparse
import base64
import json
import math
import time
from pathlib import Path
from PIL import Image, ImageGrab, ImageDraw
import verify_ui as ui
import capture_screen as capture
from verify_font_share_polish import game
from verify_interaction import pointer
from native_input_mode import set_touch, state, key, open_workspace
from verify_whitelist_runtime import settle


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',default='baseline')
    parser.add_argument('--depth',type=float,default=0)
    parser.add_argument('--yaw',type=float,default=0)
    parser.add_argument('--pitch',type=float,default=0)
    parser.add_argument('--zoom',type=float,default=1.3)
    parser.add_argument('--amplitude',type=float,default=30)
    parser.add_argument('--fixture',type=Path,help='Serialized document; defaults to a generated maximum ellipsoid')
    parser.add_argument('--touch',action='store_true')
    args=parser.parse_args()
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd']),'Game focus unavailable'
    if not game('from HelloScript.pyreact import navigator\n_result=navigator.contains("modern_projection_workspace")'):
        open_workspace()
        time.sleep(3)
    original=state()['simulated']
    if args.fixture:
        payload=json.loads(args.fixture.read_text(encoding='utf8'))
    else:
        import sys
        sys.path.insert(0,str(ui.ROOT/'behavior_pack/HelloScript'))
        from projection.model import Document
        outer=lambda x,y,z:((x+.5-32)/32)**2+((y+.5-64)/64)**2+((z+.5-32)/32)**2<=1
        blocks={(x,y,z):('minecraft:sandstone',0)
                for x in range(64) for y in range(128) for z in range(64)
                if outer(x,y,z) and any(not outer(x+dx,y+dy,z+dz)
                   for dx,dy,dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)))}
        payload=Document((64,128,64),blocks).to_data()
    encoded=base64.b64encode(json.dumps(payload).encode()).decode()
    game('''import json,base64
from HelloScript.projection.model import Document
fields=('editor','name','page','tool','direct_mode','group','inspector','section','solo_layer',
'canvas_x','canvas_z','focused','box_anchor','paste_origin','paste_pinned','camera_yaw','camera_pitch',
'zoom','camera_pan','camera_pivot','camera_depth','camera_depth_pose','camera_pose','focus_view','grid')
api._orbit69_saved=dict((k,getattr(s,k)) for k in fields)
s._loaded(Document.from_data(json.loads(base64.b64decode('''+repr(encoded)+'''))))
s.direct_mode='browse';s.inspector='params';s.grid=False;s.focus_view=False;s.emit()
_result=True''')
    patched=False
    try:
        settle()
        set_touch(args.touch)
        game('s.reset_camera(False)\ns.camera_view(%r,%r,%r)\ns.camera_depth=%r\ns.emit("camera_depth")\n_result=True'%(args.yaw,args.pitch,args.zoom,args.depth))
        time.sleep(2)
        node=ui.call('native_control',pointer()['id'])['result']
        root=ui.nodes('SafeArea')[0]['children'][0]['layout']
        left,top,width,height=capture._window_rect(window['hwnd'])
        scale=width/root['width']
        box=tuple(int(v) for v in (left+node['global'][0]*scale,top+node['global'][1]*scale,
                  left+(node['global'][0]+node['size'][0])*scale,top+(node['global'][1]+node['size'][1])*scale))
        x,y=(box[0]+box[2])//2,(box[1]+box[3])//2
        design=game('from HelloScript.projection.widgets import Theme\n_result=Theme.scale')
        game('''from HelloScript.projection import native_layers
from HelloScript.pyreact import host
import time
api._orbit69_apply=native_layers.apply_layers
api._orbit69_tick=host.notify_game_render_tick
api._orbit69_record={'layers':[],'frames':[],'active':False}
def layer_probe(original,record):
    def apply(updates):
        if record['active']:record['layers'].append(len(updates))
        original(updates)
    return apply
def frame_probe(original,record,session,clock):
    def frame():
        start=clock()
        try:return original()
        finally:
            if record['active']:record['frames'].append((session.camera_pose[0],(clock()-start)*1000.,session.camera_dragging))
    return frame
native_layers.apply_layers=layer_probe(native_layers.apply_layers,api._orbit69_record)
host.notify_game_render_tick=frame_probe(host.notify_game_render_tick,api._orbit69_record,s,time.clock)
api._orbit69_record['active']=True
_result=s.tiles.builds''')
        patched=True
        builds=game('_result=s.tiles.builds')
        frames=[];times=[]
        capture.user32.SetCursorPos(x,y);time.sleep(.1);capture.user32.mouse_event(2,0,0,0,0)
        start=time.perf_counter()
        try:
            while time.perf_counter()-start<5:
                elapsed=time.perf_counter()-start
                assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
                dx=args.amplitude/.42*design*scale*math.sin(elapsed*math.pi*2/2.5)
                capture.user32.SetCursorPos(x+int(dx),y)
                frames.append(ImageGrab.grab(bbox=box))
                times.append(elapsed)
                time.sleep(.025)
        finally:capture.user32.mouse_event(4,0,0,0,0)
        for unused in range(20):
            frames.append(ImageGrab.grab(bbox=box));times.append(time.perf_counter()-start);time.sleep(.05)
        result=game('api._orbit69_record["active"]=False\n_result=api._orbit69_record')
        result['new_builds']=game('_result=s.tiles.builds')-builds
        result['times']=times
        areas=[]
        for frame in frames:
            areas.append(sum(r>g and g>b+12 and r>70 and b<205 for r,g,b in frame.convert('RGB').getdata()))
        result['areas']=areas
        assert result['new_builds']==0,result
        held=[row[0] for row in result['frames'] if row[2]]
        assert len(held)>40,'Drag not sustained'
        for index in range(3):
            window=held[index*len(held)//3:(index+1)*len(held)//3]
            assert max(window)-min(window)>args.amplitude*.5,'Held orbit stopped in interval %d'%index
        output=ui.OUT/('orbit69_'+args.label)
        frames[0].save(str(output)+'.gif',save_all=True,append_images=frames[1:],duration=65,loop=0)
        chosen=sorted(set([i*(len(frames)-1)//11 for i in range(12)]+sorted(range(len(areas)),key=areas.__getitem__)[:4]))
        thumbs=[]
        for i in chosen:
            im=frames[i].copy();im.thumbnail((300,210));tile=Image.new('RGB',(300,235),'white');tile.paste(im,(0,20))
            ImageDraw.Draw(tile).text((3,3),'%.2fs pixels=%d'%(times[i],areas[i]),fill='black');thumbs.append(tile)
        sheet=Image.new('RGB',(300*4,235*((len(thumbs)+3)//4)),'white')
        for i,im in enumerate(thumbs):sheet.paste(im,((i%4)*300,(i//4)*235))
        sheet.save(str(output)+'.png')
        output.with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf8')
        print(json.dumps({'label':args.label,'captured_frames':len(frames),'min_area':min(areas),'max_area':max(areas),
                          'layer_batches':len(result['layers']),'layer_writes':sum(result['layers']),'builds':result['new_builds']}),flush=True)
    finally:
        capture.user32.mouse_event(4,0,0,0,0)
        if patched:
            game('''native_layers.apply_layers=api._orbit69_apply
host.notify_game_render_tick=api._orbit69_tick
api.GetTopScreen().UpdateScreen(True)
_result=True''')
        set_touch(original)
        game('''for k,v in api._orbit69_saved.items():setattr(s,k,v)
s.camera_revision+=1;s.refresh_preview();s.emit()
_result=True''')
        settle()


if __name__=='__main__':main()
