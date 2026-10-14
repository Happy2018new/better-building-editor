"""Compare isolated book companions with actual native books at matched cameras."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

from audit_native_visual_r15 import ROOT,save
from audit_native_coordinates_r15 import LOAD,PROJECT
from probe_book_native_r16 import BookAudit,CANDIDATE_SETUP,CANDIDATE_RESTORE,document
from verify_debug_blueprints import CLIENT

SERVER='''import json,sys
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
adapter=WorldAdapter(player)
info=factory.CreateBlockInfo(player)
dimension=adapter.dimension
assert dimension==0
'''
PREPARE=SERVER+'''assert not hasattr(sys,'_book_reference_r17')
origin=%r
name=%r
support_name=%r
position=tuple(origin[index]+(3,3,3)[index] for index in range(3))
support=(position[0],position[1]-1,position[2])
items=factory.CreateItem(player)
item_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
empty=next((index for index in range(36) if not items.GetPlayerItem(item_type,index,True)
 or not items.GetPlayerItem(item_type,index,True).get('count')),None)
assert empty is not None
saved={'position':position,'support':support,'slot':empty,'journal':[],'name':name,
 'rotation':factory.CreateRot(player).GetRot()}
sys._book_reference_r17=saved
for pos,block in ((support,{'name':support_name,'aux':0}),
                  (position,{'name':name,'aux':0})):
 previous=info.GetBlockNew(pos,dimension)
 assert previous['name']=='minecraft:air',(pos,previous)
 saved['journal'].append({'pos':pos,'block':previous,'nbt':info.GetBlockEntityData(dimension,pos)})
 assert info.SetBlockNew(pos,block,0,dimension,True,True)
_result=json.dumps({'position':position,'support':support,'slot':empty,
 'native':info.GetBlockEntityData(dimension,position)})
'''
USE=SERVER+'''saved=sys._book_reference_r17
items=factory.CreateItem(player)
item_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
assert not items.GetPlayerItem(item_type,saved['slot'],True)
if saved['name']=='minecraft:lectern':
 assert items.SpawnItemToPlayerInv({'itemName':'minecraft:writable_book','count':1,'auxValue':0},player,saved['slot'])
 used=info.PlayerUseItemToPos(saved['position'],item_type,saved['slot'],1)
 assert items.SetInvItemNum(saved['slot'],0)
else:used=None
_result=json.dumps({'used':used,'block':info.GetBlockNew(saved['position'],dimension),
 'states':factory.CreateBlockState(api.GetLevelId()).GetBlockStates(saved['position'],dimension),
 'native':info.GetBlockEntityData(dimension,saved['position'])})
'''
PLACE_NATIVE=SERVER+'''saved=sys._book_reference_r17
items=factory.CreateItem(player)
item_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
assert not items.GetPlayerItem(item_type,saved['slot'],True)
assert info.SetBlockNew(saved['position'],{'name':'minecraft:air','aux':0},0,dimension,True,True)
assert items.SpawnItemToPlayerInv({'itemName':saved['name'],'count':1,'auxValue':0},player,saved['slot'])
placed=info.PlayerUseItemToPos(saved['support'],item_type,saved['slot'],1)
assert items.SetInvItemNum(saved['slot'],0)
actual=info.GetBlockNew(saved['position'],dimension)
assert actual['name']==saved['name'],(placed,actual)
_result=json.dumps({'placed':placed,'actual':actual,'native':info.GetBlockEntityData(dimension,saved['position'])})
'''
CLEAR=SERVER+'''saved=sys._book_reference_r17
for pos in (saved['position'],saved['support']):
 assert info.SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,dimension,True,True)
_result=True
'''
RESTORE=SERVER+'''saved=getattr(sys,'_book_reference_r17',None)
if saved is None:_result={'restored':True,'owned':False}
else:
 items=factory.CreateItem(player)
 assert items.SetInvItemNum(saved['slot'],0)
 assert factory.CreateRot(player).SetRot(tuple(saved['rotation']))
 rows=[]
 for entry in reversed(saved['journal']):
  info.SetBlockNew(entry['pos'],entry['block'],0,dimension,True,True)
  if entry['nbt'] is not None:info.SetBlockEntityData(dimension,entry['pos'],entry['nbt'])
  actual=info.GetBlockNew(entry['pos'],dimension)
  assert actual==entry['block'],(entry,actual)
  rows.append({'position':entry['pos'],'actual':actual})
 del sys._book_reference_r17
 _result={'restored':True,'rows':rows}
'''


def run(args):
    args.output.mkdir(parents=True,exist_ok=False)
    os.environ['MCDEV_ALLOW_USER_FOREGROUND']='1'
    audit=BookAudit(args)
    report={'schema':1,'engine':'3.10.0.420447','completed':False,'restored':False,
            'captures':{},'rows':{},'cleanup_errors':[],'product_qualified':False}
    sys.path.insert(0,str(ROOT/'behavior_pack/modern_projection'))
    from projection.model import Document
    from projection.cell import make_cell,foreground
    from projection.nbt_spatial import rebase
    from projection.visible_actor import compose_actor
    for case in ('enchanting_table','lectern.book'):
        try:
            audit.execute('candidate_setup',CANDIDATE_SETUP)
            foot=audit.execute('foot',CLIENT+'_result=json.dumps(b.player_position.GetFootPos())')
            origin=tuple(int(foot[index])+args.origin_offset[index] for index in range(3))
            if args.eye_level:
                available=audit.execute('find_eye_level_air',SERVER+'''foot=factory.CreatePos(player).GetFootPos()
found=None
for dx,dz in ((3,0),(-3,0),(0,3),(0,-3),(3,3),(-3,3),(3,-3),(-3,-3)):
 pos=(int(foot[0])+dx,int(foot[1])+1,int(foot[2])+dz)
 support=(pos[0],pos[1]-1,pos[2])
 if all(info.GetBlockNew(p,dimension)['name']=='minecraft:air' for p in (pos,support)):
  found=pos
  break
assert found is not None,'No empty eye-level fixture and support near player'
_result=found
''',False)
                origin=tuple(value-3 for value in available)
            name='minecraft:enchanting_table' if case=='enchanting_table' else 'minecraft:lectern'
            data,source=document(case)
            doc=Document.from_data(data)
            support_name=foreground(doc.get((3,2,3)))[0]
            report['rows'][case]={'origin':origin,
                'prepared':audit.execute('prepare_real_'+case,PREPARE % (origin,name,support_name),False)}
            time.sleep(1.)
            if args.native_placement:
                report['rows'][case]['native_placement']=audit.execute('native_placement',PLACE_NATIVE,False)
                time.sleep(1.)
            report['rows'][case]['used']=audit.execute('authentic_use',USE,False)
            position=tuple(report['rows'][case]['prepared']['position'])
            deadline=time.monotonic()+30.
            while True:
                actual=audit.execute('real_client',CLIENT+
                    '_result=json.dumps(b.factory.CreateBlockInfo(b.level).GetBlock(%r))' % (position,))
                if actual and actual[0]==name:break
                if time.monotonic()>deadline:raise ValueError('Native book reference has not reached client')
                time.sleep(1.)
            report['rows'][case]['client']=actual
            # Real placement can change direction (lectern north is aux 2).
            # Compare the same material, not the blueprint's initial direction.
            placed=report['rows'][case]['used']['block']
            material=(placed['name'],placed['aux'])
            assert tuple(actual)==material,(actual,material)
            real_nbt=report['rows'][case]['used']['native']
            actor=compose_actor(None,rebase(real_nbt,tuple(-value for value in origin)))
            doc.blocks[(3,3,3)]=make_cell(material,nbt=actor)
            report['rows'][case]['source']=source
            report['rows'][case]['document']=doc.to_data()
            if args.player_view:
                audit.execute('attached_camera',CLIENT+'''cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos();cam.UnDepartCamera();cam.LockModCameraPitch(False);cam.LockModCameraYaw(False)
if api.GetTopUI()=='pause_screen':api.PopTopUI()
_result=True
''')
                report['rows'][case]['attached_view']=audit.execute('aim_player',SERVER+'''saved=sys._book_reference_r17
foot=factory.CreatePos(player).GetFootPos()
target=tuple(saved['position'][i]+(.5,1.,.5)[i] for i in range(3))
eye=(foot[0],foot[1]+1.62,foot[2])
rotation=api.GetRotFromDir(tuple(target[i]-eye[i] for i in range(3)))
assert factory.CreateRot(player).SetRot(rotation)
_result={'foot':foot,'target':target,'rotation':rotation}
''',False)
                time.sleep(2.)
                label='native_'+case+'_attached_view'
                report['captures'][label]=audit.frame(label)
            point=tuple(position[index]+(.5,.85,.5)[index] for index in range(3))
            camera=tuple(point[index]+(2.1,1.8,-2.9)[index] for index in range(3))
            camera_code=CLIENT+'''cam=b.factory.CreateCamera(b.level)
target=%r
position=%r
rot=api.GetRotFromDir(tuple(target[index]-position[index] for index in range(3)))
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
if api.GetTopUI()=='pause_screen':api.PopTopUI()
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation()})
''' % (point,camera)
            if args.player_view:
                # Keep the proven player view for BOTH references. A detached
                # camera can show terrain while native book actors are absent.
                camera_code=CLIENT+'''cam=b.factory.CreateCamera(b.level)
if api.GetTopUI()=='pause_screen':api.PopTopUI()
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation()})
'''
            report['rows'][case]['camera']=audit.execute('matched_camera',camera_code)
            time.sleep(1.)
            for sample in range(6 if case=='enchanting_table' else 2):
                label='native_'+case+'_motion%d' % sample
                report['captures'][label]=audit.frame(label)
                report['captures'][label]['native_actor']=audit.execute(label+'_actor',SERVER+'''
_result=info.GetBlockEntityData(dimension,sys._book_reference_r17['position'])
''',False)
                report['captures'][label]['host_time']=time.monotonic()
                time.sleep(.5)
            audit.execute('remove_real',CLEAR,False)
            time.sleep(2.)
            audit.execute('load_candidate',LOAD % ('production',(),json.dumps(doc.to_data())))
            audit.settle()
            code=(PROJECT % False).replace('s.origin=(0,-57,0)','s.origin=%r' % (origin,))
            audit.execute('project_candidate',code);audit.settle(True)
            audit.execute('matched_camera_again',camera_code)
            time.sleep(1.)
            for sample in range(6 if case=='enchanting_table' else 2):
                label='candidate_'+case+'_motion%d' % sample
                report['captures'][label]=audit.frame(label)
                time.sleep(.5)
            report['rows'][case]['candidate_state']=audit.execute('candidate_state',CLIENT+
                '_result=json.dumps({"origin":s.origin,"opacity":s.opacity,"mesh":b.projection_mesh})')
        finally:
            try:
                audit.execute('stop',CLIENT+'b.stop_projection()\n_result=True')
                report['rows'].setdefault(case,{})['world_restoration']=audit.execute('world_restore',RESTORE,False)
                audit.execute('ui_camera_restore',CLIENT+'''if navigator.top is not None:navigator.pop()
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos();cam.UnDepartCamera();cam.LockModCameraPitch(False);cam.LockModCameraYaw(False)
_result=True
''')
                audit.execute('candidate_restore',CANDIDATE_RESTORE)
            except Exception as error:report['cleanup_errors'].append(str(error))
            report['restored']=not report['cleanup_errors']
            save(args.output/'report.json',report)
    report['completed']=True
    save(args.output/'report.json',report)
    print(json.dumps({'captures':len(report['captures']),'completed':report['completed'],
                      'restored':report['restored']}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True);parser.add_argument('--owner',required=True)
    parser.add_argument('--project',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--origin-offset',type=int,nargs=3,default=(6,3,6),
                        help='Fixture origin offset from fixed player foot; local book is (3,3,3).')
    parser.add_argument('--native-placement',action='store_true')
    parser.add_argument('--player-view',action='store_true',
                        help='Additional attached-player camera control; restores player rotation.')
    parser.add_argument('--eye-level',action='store_true',
                        help='Find an empty nearby eye-level fixture for the attached-view control.')
    run(parser.parse_args())


if __name__=='__main__':main()
