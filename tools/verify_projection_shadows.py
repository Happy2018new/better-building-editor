"""Native shadow A/B on a temporary platform in an independent test world."""
import time
import verify_ui as ui
from verify_font_share_polish import game
from verify_projection_outline import server
from verify_complete_projection import snapshot
from verify_projection_visibility import difference


def main():
    server('api._shadow_cells=[]\napi._shadow_player=(f.CreatePos(p).GetFootPos(),f.CreateFly(p).IsPlayerFlying())\n_result=True')
    base = game('''from HelloScript.pyreact import navigator
b=s.bridge
cam=b.factory.CreateCamera(b.level)
api._shadow_saved=(s.editor,s.origin,s.opacity,s.projection_outline,s.reduced_motion,s.projection_active,
 cam.IsModCameraLockPitch(),cam.IsModCameraLockYaw(),s.solo_layer,s.projection_missing)
p=b.player_origin()
_result=(p[0],200,p[2])''')
    try:
        server('''base='''+repr(tuple(base))+'''
info=f.CreateBlockInfo(api.GetLevelId())
cells=[(base[0]+x,base[1],base[2]+z) for x in range(-5,9) for z in range(-5,9)]
assert all(info.GetBlockNew(pos,0)['name']=='minecraft:air' for pos in cells)
api._shadow_cells=cells
for pos in cells: info.SetBlockNew(pos,{'name':'minecraft:stone','aux':0},0,0,True,False)
assert all(info.GetBlockNew(pos,0)['name']=='minecraft:stone' for pos in cells)
f.CreateFly(p).ChangePlayerFlyState(True)
f.CreatePos(p).SetFootPos((base[0]-3.,base[1]+2.5,base[2]-3.))
_result=True''')
        game('''from HelloScript.pyreact import navigator
from HelloScript.projection.model import Document,Editor
navigator.pop()
b.stop_projection()
s.editor=Editor(Document((4,4,4),{(2,0,2):('minecraft:quartz_block',0),(2,1,2):('minecraft:quartz_block',0)}))
base='''+repr(tuple(base))+'''
s.origin=(base[0],base[1]+1,base[2])
s.opacity=.5;s.projection_outline=True;s.reduced_motion=True;s.solo_layer=False;s.projection_missing=False
b.project()
cam.LockModCameraPitch(True);cam.LockModCameraYaw(True);cam.DepartCamera()
pos=(base[0]-3.,base[1]+4.,base[2]-3.)
target=(base[0],base[1]+1.,base[2])
rot=api.GetRotFromDir(tuple(target[i]-pos[i] for i in range(3)))
cam.SetCameraPos(pos);cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
_result=True''')
        time.sleep(1.)
        snapshot('projection_shadow_disabled')
        # Display the native actor shadow close to the floor so that its
        # absence cannot simply be due to distance from terrain.
        game('''api._shadow_follow=b.follow_projection
b.follow_projection=lambda:None
origin=s.origin
anchor=(origin[0]+.1,origin[1]+.15,origin[2]+.1)
e=b.projection_outline.entity
b.factory.CreatePos(e).SetPosForClientEntity(anchor)
centre=tuple(origin[i]+s.editor.document.size[i]*.5 for i in range(3))
b.factory.CreateActorRender(e).SetEntityExtraUniforms(2,tuple(centre[i]-anchor[i] for i in range(3))+(1.,))
b.factory.CreateModel(e).SetEntityShadowShow(True)
_result=True''')
        time.sleep(.3)
        snapshot('projection_shadow_enabled')
        game('b.factory.CreateModel(e).SetEntityShadowShow(False)\n_result=True')
        time.sleep(.3)
        snapshot('projection_shadow_fixed')
        pixels=difference('projection_shadow_enabled','projection_shadow_fixed')
        assert pixels>150,'native shadow was not visibly exercised'
        print({'nativeShadowDifferentPixels':pixels},flush=True)
    finally:
        game('''if hasattr(api,'_shadow_follow'): b.follow_projection=api._shadow_follow
b.stop_projection()
v=api._shadow_saved
s.editor,s.origin,s.opacity,s.projection_outline,s.reduced_motion=v[:5]
s.solo_layer,s.projection_missing=v[8:10]
cam.ResetCameraPos();cam.UnDepartCamera();cam.LockModCameraPitch(v[6]);cam.LockModCameraYaw(v[7])
if v[5]:b.project()
from HelloScript.projection.ui import Workspace
navigator.push(Workspace(session=s),key='modern_projection_workspace')
_result=True''')
        server('''info=f.CreateBlockInfo(api.GetLevelId())
for pos in getattr(api,'_shadow_cells',[]): info.SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,0,True,False)
assert all(info.GetBlockNew(pos,0)['name']=='minecraft:air' for pos in getattr(api,'_shadow_cells',[]))
f.CreatePos(p).SetFootPos(api._shadow_player[0]);f.CreateFly(p).ChangePlayerFlyState(api._shadow_player[1])
_result=True''')


if __name__ == '__main__':
    main()
