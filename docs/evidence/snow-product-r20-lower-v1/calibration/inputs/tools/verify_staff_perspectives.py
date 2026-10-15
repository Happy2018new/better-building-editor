"""Real SDK movement through 0/1/2/0 perspectives and fixed wire-crystal views.

Use only via run_live_check.py in an isolated ModPC world. All temporary camera,
equipment, flight and selection state is restored; no blocks are changed.
"""
import json
import time
from pathlib import Path
from verify_world_tools import game, equip, snapshot, call
from verify_survey_visuals import camera

OUT = Path(__file__).resolve().parents[1] / '.runtime'


def main():
    old=game('''f=s.bridge.factory;p=s.bridge.player
_result={'view':f.CreatePlayerView(p).GetPerspective(),'rotation':f.CreateRot(p).GetRot(),
 'reduced':s.reduced_motion,'corners':s.bridge.corners,'faces':s.bridge.corner_faces,
 'wire_reduced':s.bridge.survey_effects.reduced_motion}''')
    saved=game('''f=api.GetEngineCompFactory()
_result={'foot':f.CreatePos(player).GetFootPos(),'fly':f.CreateFly(player).IsPlayerFlying(),
 'item':f.CreateItem(player).GetPlayerItem(api.GetMinecraftEnum().ItemPosType.CARRIED,0)}''',True)
    report={}
    try:
        assert equip('modern_projection:terminal')
        x,y,z=saved['foot']
        game('''f=api.GetEngineCompFactory()
f.CreateFly(player).ChangePlayerFlyState(True)
f.CreatePos(player).SetFootPos(%r)
_result=True''' % ((x,y+8.,z),),True)
        game('''s.reduced_motion=False
cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos();cam.UnDepartCamera()
s.bridge.factory.CreateRot(s.bridge.player).SetRot((0.,0.))
_result=True''')
        for index,view in enumerate((0,1,2,0)):
            game('s.bridge.factory.CreatePlayerView(s.bridge.player).SetPerspective(%d)\n_result=True'%view)
            time.sleep(.45)
            sign=1. if index<2 else -1.
            game('''f=api.GetEngineCompFactory()
owner._staff_motion_run=%d
def start(owner=owner,comp=f.CreateActorMotion(player),timer=f.CreateGame(api.GetLevelId()),token=%d):
 def tick(i=0):
  if owner._staff_motion_run!=token:return
  comp.SetPlayerMotion((%r,0.,0.) if i<60 else (0.,0.,0.))
  if i<60:timer.AddTimer(.05,tick,i+1)
 tick()
start()
_result=True''' % (index,index,sign*.13),True)
            time.sleep(.65)
            value=game('_result={"appearance":owner.staff_aura.uniform,"motion":owner.staff_aura.motion_uniform}')
            assert value['motion'][0]*sign>.5,value
            assert value['appearance'][3]==(0. if view==0 else 1.),value
            value['image']=snapshot('staff_motion_view_%d_%d'%(index,view))
            report['view_%d_%d'%(index,view)]=value
            game('''owner._staff_motion_run=-1
api.GetEngineCompFactory().CreateActorMotion(player).SetPlayerMotion((0.,0.,0.))
_result=True''',True)
            time.sleep(.65)
            assert game('_result=owner.staff_aura.motion_uniform[3]')<.1
        assert equip('minecraft:stick')
        foot=game('_result=s.bridge.factory.CreatePos(s.bridge.player).GetFootPos()')
        a=tuple(int(v) for v in foot)
        game('''s.bridge.survey_effects.reduced_motion=True
s.bridge.corners=[%r,None]
s.bridge.corner_faces=[3,None]
s.bridge.draw_bounds()
_result=True''' % ((a[0],a[1]+1,a[2]+2),))
        time.sleep(2.)
        target=(a[0]+.5,a[1]+1.5,a[2]+3.1)
        for name,distance in (('far',3.2),('near',1.1)):
            camera((target[0],target[1],target[2]+distance),target)
            time.sleep(.25)
            report['crystal_'+name]=snapshot('staff_crystal_'+name)
        report['errors']=call('get_latest_error_logs',{'max_count':12,'order':'desc'})
    finally:
        game('''owner._staff_motion_run=-1
f=api.GetEngineCompFactory()
f.CreateActorMotion(player).SetPlayerMotion((0.,0.,0.))
f.CreatePos(player).SetFootPos(%r)
f.CreateFly(player).ChangePlayerFlyState(%r)
saved=%r
if saved:
 for key in ('itemName','newItemName'):
  if isinstance(saved.get(key),unicode):saved[key]=saved[key].encode('utf8')
else:saved={'itemName':'minecraft:air','count':0,'auxValue':0}
f.CreateItem(player).SpawnItemToPlayerCarried(saved,player)
_result=True'''%(tuple(saved['foot']),saved['fly'],saved['item']),True)
        game('''s.reduced_motion=%r
s.bridge.survey_effects.reduced_motion=%r
s.bridge.corners=%r;s.bridge.corner_faces=%r;s.bridge.draw_bounds()
cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos();cam.UnDepartCamera()
s.bridge.factory.CreatePlayerView(s.bridge.player).SetPerspective(%r)
s.bridge.factory.CreateRot(s.bridge.player).SetRot(%r)
_result=True'''%(old['reduced'],old['wire_reduced'],old['corners'],old['faces'],old['view'],tuple(old['rotation'])))
    (OUT/'staff_perspectives.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
