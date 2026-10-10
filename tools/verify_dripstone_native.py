"""Read native pointed-dripstone state updates in one owned disposable world."""
import argparse
import json
import os
from pathlib import Path

from context_test_environment import run
from verify_debug_blueprints import BlueprintCheck, Client, write_json

START = '''import json,sys,math
import mod.server.extraServerApi as api
assert not hasattr(sys,'_dripstone_state_qa')
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
level=api.GetLevelId()
dimension=factory.CreateDimension(player).GetEntityDimensionId()
foot=factory.CreatePos(player).GetFootPos()
origin=(int(math.floor(foot[0]))+10,int(math.floor(foot[1]))+32,int(math.floor(foot[2]))+10)
info=factory.CreateBlockInfo(level)
state=factory.CreateBlockState(level)
reserved=[(origin[0]+x,origin[1]+y,origin[2]+z) for x in (-1,0,1) for y in range(-1,9) for z in (-1,0,1)]
for pos in reserved:assert info.GetBlockNew(pos,dimension)['name']=='minecraft:air',(pos,info.GetBlockNew(pos,dimension))
aux={}
for hanging in (False,True):
 aux[hanging]=state.GetBlockAuxValueFromStates('minecraft:pointed_dripstone',
  {'hanging':hanging,'dripstone_thickness':'tip'})
 assert aux[hanging]>=0
plans=[]
for hanging in (False,True):
 plans.append(('reset',hanging,None))
 for height in range(5):plans.append(('extend',hanging,height))
 for height in (4,3,2,1,0):plans.append(('erase',hanging,height))
for order in (0,1):
 plans.extend((('opposed',False,order),('merge',False,None),('erase_pair',False,order)))
saved={'origin':origin,'reserved':reserved,'plans':plans,'index':0,'rows':[],'done':False,
 'aux':aux,'factory':factory,'level':level,'dimension':dimension,'info':info,'state':state}
sys._dripstone_state_qa=saved
def step():
 s=sys._dripstone_state_qa
 if s['index']>=len(s['plans']):
  s['done']=True
  return
 kind,hanging,height=s['plans'][s['index']]
 o=s['origin']
 if kind in ('reset','opposed'):
  for y in range(-1,9):s['info'].SetBlockNew((o[0],o[1]+y,o[2]),{'name':'minecraft:air','aux':0},0,s['dimension'],True,False)
  for y in (-1,2 if kind=='opposed' else 8):
   assert s['info'].SetBlockNew((o[0],o[1]+y,o[2]),{'name':'minecraft:stone','aux':0},0,s['dimension'],True,False)
  if kind=='opposed':
   for y in ((0,1) if not height else (1,0)):
    assert s['info'].SetBlockNew((o[0],o[1]+y,o[2]),{'name':'minecraft:pointed_dripstone','aux':s['aux'][bool(y)]},0,s['dimension'],True,True)
 elif kind=='merge':
  for y in (0,1):assert s['state'].SetBlockStates((o[0],o[1]+y,o[2]),{'hanging':bool(y),'dripstone_thickness':'merge'},s['dimension'])
 else:
  y=height if kind=='erase_pair' else 7-height if hanging else height
  name='minecraft:pointed_dripstone' if kind=='extend' else 'minecraft:air'
  value=s['aux'][hanging] if kind=='extend' else 0
  assert s['info'].SetBlockNew((o[0],o[1]+y,o[2]),{'name':name,'aux':value},0,s['dimension'],True,True)
 s['factory'].CreateGame(s['level']).AddTimer(.15,observe)
def observe():
 s=sys._dripstone_state_qa
 o=s['origin']
 cells=[]
 for y in range(8):
  pos=(o[0],o[1]+y,o[2])
  value=s['info'].GetBlockNew(pos,s['dimension'])
  if value['name']=='minecraft:pointed_dripstone':cells.append({'y':y,'states':s['state'].GetBlockStates(pos,s['dimension'])})
 s['rows'].append({'action':s['plans'][s['index']],'cells':cells})
 s['index']+=1
 step()
step()
_result=json.dumps({'started':True,'cases':len(plans),'origin':origin,'runtime':api.GetMinecraftVersion()})
'''

STATUS = '''import json,sys
s=sys._dripstone_state_qa
_result=json.dumps({'done':s['done'],'index':s['index'],'cases':len(s['plans']),
 'origin':s['origin'],'rows':s['rows']})
'''

RESTORE = '''import json,sys
saved=getattr(sys,'_dripstone_state_qa',None)
if saved is not None:
 for pos in saved['reserved']:saved['info'].SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
 for pos in saved['reserved']:assert saved['info'].GetBlockNew(pos,saved['dimension'])['name']=='minecraft:air',pos
 count=len(saved['reserved'])
 del sys._dripstone_state_qa
else:count=0
_result=json.dumps({'restored':True,'reserved_air':count})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = {'schema': 1, 'completed': False, 'session_file': os.environ.get('MCDEV_SESSION_FILE'),
              'owner': os.environ.get('MCDEV_OWNER'),
              'method': 'Legacy aux resolved from states; neighbor updates enabled; read after .15s native timer',
              'limits': ['State observations only; not pixel acceptance.',
                         'Opposed tips are API placements; no player use-item merge claim.',
                         'No gravity simulation or deletion of unsupported editor segments.']}
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, 30)
            try:
                report['start'] = run(client, START)
                report['native'] = check.wait('dripstone native rows', lambda value: value['done'],
                                             lambda: run(client, STATUS))
                report['completed'] = True
            finally:
                report['cleanup'] = run(client, RESTORE)
                report['restored'] = report['cleanup']['restored']
    finally:
        write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'cases': report['native']['cases']}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
