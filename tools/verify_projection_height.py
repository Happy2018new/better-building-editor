"""Player stays on ground while detached camera and projection are elevated."""
import time
import numpy as np
from PIL import Image
import verify_projection_occupancy as qa
from verify_projection_outline import game,server


def main():
    origin=qa.setup_fixture()
    installed=False
    results=[]
    player=server('_result=f.CreatePos(p).GetFootPos()')
    try:
        qa.install_probe(origin);installed=True
        qa.wait_points((x,0,0) for x in range(8))
        for height in (0,20,127):
            for missing in (True,False):
                point=(origin[0],origin[1]+height,origin[2])
                game('s.bridge.stop_projection()\ns.origin='+repr(point)+'\ns.projection_missing='+repr(missing)+'\ns.bridge.project()\n_result=True')
                time.sleep(.6)
                tag='height_%d_%s'%(height,missing)
                shown=qa.capture_fixture(point,tag)
                state=game('''b=s.bridge
ar=b.factory.CreateActorRender(b.entity)
_result={"entity":b.entity,"mesh":b.projection_mesh,"player":b.player_position.GetFootPos(),"camera":b.factory.CreateCamera(b.level).GetPosition()}
assert ar.SetNotRenderAtAll(True)''')
                empty=qa.capture_fixture(point,tag+'_empty')
                game('assert s.bridge.factory.CreateActorRender(s.bridge.entity).SetNotRenderAtAll(False)\n_result=True')
                first=np.asarray(Image.open(shown).convert('RGB')).astype(int)
                second=np.asarray(Image.open(empty).convert('RGB')).astype(int)
                h,w=first.shape[:2]
                delta=np.max(np.abs(first-second),axis=2)[h//4:h*2//3,w//4:w*3//4]
                pixels=int((delta>12).sum())
                assert pixels>1500,(tag,pixels)
                assert list(state['player'])==list(player),(tag,state,player)
                assert not game('_result=bool(s.bridge.projection_entities)')
                results.append(dict(height=height,missing=missing,pixels=pixels,state=state,image=shown))
                print(tag,pixels,'projection pixels; player unchanged',flush=True)
    finally:
        if installed:
            game('s.bridge.stop_projection()\ncam=s.bridge.factory.CreateCamera(s.bridge.level)\ncam.ResetCameraPos();cam.UnDepartCamera()\ncam.LockModCameraPitch(api._occupancy_qa_camera[0]);cam.LockModCameraYaw(api._occupancy_qa_camera[1])\ns.editor,s.origin,s.projection_missing,s.projection_outline,s.solo_layer,s.bridge.geometry,s.bridge.factory=api._occupancy_qa_saved\ns.refresh_preview();s.emit()\n_result=True')
        qa.dump(qa.ui.OUT/'projection_height_checks.json',results)

if __name__=='__main__':main()
