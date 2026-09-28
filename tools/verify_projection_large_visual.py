"""Actual pixels while a solid 524,288-cell projection rebuilds in one actor."""
import time
from PIL import ImageGrab
import verify_projection_occupancy as qa
import verify_projection_shader as visual
from verify_projection_outline import game,server
import capture_screen as capture


def main():
    origin=qa.setup_fixture();installed=False;result={}
    try:
        qa.install_probe(origin);installed=True
        qa.wait_points((x,0,0) for x in range(8))
        server('''from modern_projection.server_system import WorldAdapter
a=WorldAdapter(p);o='''+repr(tuple(origin))+'''
saved=[((o[0]+x,o[1],o[2]),a.read((o[0]+x,o[1],o[2]))) for x in range(32)]
assert all(value==("minecraft:air",0) for pos,value in saved)
api._occupancy_qa_saved+=saved
_result=True''')
        game('''b=s.bridge;b.stop_projection()
from modern_projection.projection.model import Document,Editor
d=Document((64,128,64))
for x in range(4):
    for y in range(8):
        for z in range(4):d.blocks.fill_chunk((x,y,z),("minecraft:quartz_block",0))
s.editor=Editor(d);b.project()
_result=True''')
        qa.wait_count(524288,60)
        game('''b=s.bridge;cam=b.factory.CreateCamera(b.level)
cam.LockModCameraPitch(True);cam.LockModCameraYaw(True);cam.DepartCamera()
o=s.origin
pos=(o[0]+32.,o[1]+64.,o[2]-150.)
target=(o[0]+32.,o[1]+64.,o[2]+32.)
rot=api.GetRotFromDir(tuple(target[i]-pos[i] for i in range(3)))
cam.SetCameraPos(pos);cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
_result=True''')
        time.sleep(.8)
        capture.user32.SetProcessDPIAware()
        window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
        assert window
        ImageGrab.grab(window=window['hwnd']).save(qa.ui.OUT/'projection_large_full.png')
        game('u=s.bridge.projection_occupancy.shader\nv=u.uniforms[4]\nassert u.render.SetEntityExtraUniforms(4,v[:2]+(-1.,v[3]))\n_result=True')
        time.sleep(.25)
        empty=ImageGrab.grab(window=window['hwnd']).resize((850,480)).crop((100,175,750,290))
        game('u=s.bridge.projection_occupancy.shader\nassert u.render.SetEntityExtraUniforms(4,u.uniforms[4])\no=s.bridge.projection_occupancy\nfor x in range(32):o.hint((o.origin[0]+x,o.origin[1],o.origin[2]))\n_result=True')
        time.sleep(.25)
        before=qa.snapshot()
        visual.start_burst(origin,32,4)
        frames,stamps=visual.capture_frames(window,14.)
        after=qa.wait_count(524288,60)
        result=visual.analyze(frames,stamps,'solid524288',empty)
        result['before'],result['after']=before,after
        assert after['actor']==before['actor'] and after['actors']==1
        assert after['metrics']['builds']>before['metrics']['builds']
        print('solid frames',result['frames'],'coverage',result['min_coverage'],'rebuilds',after['metrics']['builds']-before['metrics']['builds'],flush=True)
    finally:
        server('''from modern_projection.server_system import WorldAdapter
if hasattr(api,"_occupancy_qa_burst"):api._occupancy_qa_burst["cancel"]=True
a=WorldAdapter(p)
for pos,value in api._occupancy_qa_saved:assert a.write(pos,value)
_result=True''')
        if installed:
            game('s.bridge.stop_projection()\ncam=s.bridge.factory.CreateCamera(s.bridge.level)\ncam.ResetCameraPos();cam.UnDepartCamera()\ncam.LockModCameraPitch(api._occupancy_qa_camera[0]);cam.LockModCameraYaw(api._occupancy_qa_camera[1])\ns.editor,s.origin,s.projection_missing,s.projection_outline,s.solo_layer,s.bridge.geometry,s.bridge.factory=api._occupancy_qa_saved\ns.refresh_preview();s.emit()\n_result=True')
        qa.dump(qa.ui.OUT/'projection_large_visual_checks.json',result)

if __name__=='__main__':main()
