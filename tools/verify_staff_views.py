"""Native front/side/back staff captures and owner-only perspective trail gate.

Run through run_live_check.py after cold loading resources. Uses an isolated
world and restores equipment, view, rotation and the local reduced-motion flag.
"""
import json
import time
from pathlib import Path
from verify_world_tools import game, equip, snapshot
from verify_survey_visuals import camera

OUT = Path(__file__).resolve().parents[1] / '.runtime'


def main():
    old = game('''from modern_projection.pyreact import navigator
if navigator.contains('modern_projection_workspace'):navigator.pop()
f=s.bridge.factory;p=s.bridge.player
_result={'view':f.CreatePlayerView(p).GetPerspective(),
 'rot':f.CreateRot(p).GetRot(),'foot':f.CreatePos(p).GetFootPos(),
 'reduced':s.reduced_motion}''')
    carried = game('_result=api.GetEngineCompFactory().CreateItem(player).GetPlayerItem(api.GetMinecraftEnum().ItemPosType.CARRIED,0)', True)
    report = {}
    try:
        game('''cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos();cam.UnDepartCamera()
s.bridge.factory.CreateRot(s.bridge.player).SetRot((0.,0.))
s.reduced_motion=True
_result=True''')
        x,y,z = old['foot']
        views = (('front',(0.,1.9,3.)), ('right',(-3.,1.9,0.)),
                 ('back',(0.,1.9,-3.)), ('oblique',(-2.5,2.,2.5)))
        assert equip('minecraft:stick')
        game('s.bridge.factory.CreatePlayerView(s.bridge.player).SetPerspective(1)\n_result=True')
        time.sleep(.3)
        for name, offset in views:
            camera(tuple(old['foot'][i] + offset[i] for i in range(3)), (x,y+1.2,z))
            time.sleep(.2)
            report['stick_' + name] = snapshot('stick_reference_' + name)
        assert equip('modern_projection:terminal')
        for view in (0, 1, 2, 0):
            game('s.bridge.factory.CreatePlayerView(s.bridge.player).SetPerspective(%d)\n_result=True' % view)
            time.sleep(.45)
            value = game('_result=owner.staff_aura.uniform')
            assert value[3] == (0. if view == 0 else 1.), (view, value)
        report['perspective_gate'] = True
        game('s.bridge.factory.CreatePlayerView(s.bridge.player).SetPerspective(1)\n_result=True')
        time.sleep(.45)
        for name, offset in views:
            camera(tuple(old['foot'][i] + offset[i] for i in range(3)), (x,y+1.2,z))
            time.sleep(.2)
            report[name] = snapshot('staff_view_' + name)
        # A solo server snapshot should leave no remote client actors.
        report['nearby'] = game('''owner.nearby_staff_auras.update()
_result=list(owner.nearby_staff_auras.auras)''')
    finally:
        game('''s.reduced_motion=%r
cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos();cam.UnDepartCamera()
s.bridge.factory.CreatePlayerView(s.bridge.player).SetPerspective(%r)
s.bridge.factory.CreateRot(s.bridge.player).SetRot(%r)
_result=True''' % (old['reduced'],old['view'],tuple(old['rot'])))
        game('''saved=%r
if saved:
 for key in ('itemName','newItemName'):
  if isinstance(saved.get(key),unicode):saved[key]=saved[key].encode('utf8')
else:saved={'itemName':'minecraft:air','count':0,'auxValue':0}
api.GetEngineCompFactory().CreateItem(player).SpawnItemToPlayerCarried(saved,player)
_result=True''' % carried, True)
    (OUT/'staff_views.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
