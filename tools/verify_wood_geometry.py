"""Render all six saved plank aux values through the actual mesh boundary.

Client-only temporary geometry; leaves the draft, preferences and world intact.
The screenshot is the visual assertion: SDK success alone cannot detect oak
fallback. Use the instance-bound run_live_check.py runner.
"""
import time
from verify_font_share_polish import game
from verify_complete_projection import install, snapshot
import verify_ui as ui


def main():
    install()
    game('''b=s.bridge
cam=b.factory.CreateCamera(b.level)
api._wood_verification=(cam.IsModCameraLockPitch(),cam.IsModCameraLockYaw(),s.editor.document)
from HelloScript.projection.model import Document
doc=Document((12,1,1),dict(((i,0,0),('minecraft:planks',i//2)) for i in range(12)))
name=b.geometry(doc,name='modern_projection_wood_verification')
origin=tuple(float(v) for v in b.player_origin())
e=b.system.CreateClientEntityByTypeStr(b'modern_projection:anchor',origin,(0.,0.))
api._wood_verification_actor=(e,name,origin)
_result=True''')
    try:
        time.sleep(.3)
        ui.check('six legacy species attach through the production geometry method',game('''e,name,o=api._wood_verification_actor
r=b.factory.CreateActorRender(e)
ok=r.AddActorBlockGeometry(name,(-.5,0.,-.5),(0.,180.,0.))
ok=ok and r.EnableActorBlockGeometryTransparent(name,True)
ok=ok and r.SetActorBlockGeometryTransparency(name,1.)
ok=ok and r.SetEntityExtraUniforms(4,(19487.,0.,0.,0.))
cam=b.factory.CreateCamera(b.level)
cam.LockModCameraPitch(True);cam.LockModCameraYaw(True);cam.DepartCamera()
pos=(o[0]+6.,o[1]+3.,o[2]-14.)
point=(o[0]+6.,o[1]+.5,o[2]+.5)
rot=api.GetRotFromDir(tuple(point[i]-pos[i] for i in range(3)))
cam.SetCameraPos(pos);cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
_result=bool(ok)'''))
        time.sleep(.6)
        snapshot('wood_six_species_verified')
    finally:
        game('''b.system.DestroyClientEntity(api._wood_verification_actor[0])
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos();cam.UnDepartCamera()
cam.LockModCameraPitch(api._wood_verification[0]);cam.LockModCameraYaw(api._wood_verification[1])
assert s.editor.document is api._wood_verification[2]
del api._wood_verification_actor;del api._wood_verification
_result=True''')


if __name__=='__main__':main()
