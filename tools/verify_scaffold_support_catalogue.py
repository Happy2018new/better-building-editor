"""Measure scaffold support for every dumped state by native block placement.

Each isolated cell has a floor, the requested supporting state and a scaffold.
Results include the actual support and scaffold readback; changed supports are
not silently classified as the requested snapshot. This is not pixel evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from context_test_environment import run
from verify_debug_blueprints import BlueprintCheck, Client, write_json
from verify_scaffolding_native import registry

MARKER = '_scaffold_support_catalogue_r8'
METHOD = '8 isolated native legacy-state support/scaffold cells; .35s delayed readback'

START = '''import json,sys,math
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry as registry
marker=%r
assert not hasattr(sys,marker), 'Previous support catalogue requires cleanup'
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
player=api.GetPlayerList()[0]
dim=factory.CreateDimension(player).GetEntityDimensionId()
foot=factory.CreatePos(player).GetFootPos()
origin=(int(math.floor(foot[0]))+4,int(math.floor(foot[1]))+18,int(math.floor(foot[2]))+4)
info=factory.CreateBlockInfo(level)
slots=[(origin[0]+(i%%4)*3,origin[1],origin[2]+(i//4)*3) for i in range(8)]
reserved=set((pos[0]+x,pos[1]+y,pos[2]+z) for pos in slots
 for x in (-1,0,1) for y in (-1,0,1,2,3) for z in (-1,0,1))
for pos in reserved:
 value=info.GetBlockNew(pos,dim)
 assert value is not None and value['name']=='minecraft:air',('non-air reserve',pos,value)
source=[(name,aux) for name in sorted(registry.BLOCKS) for aux in registry.aux_values(name)]
s={'reserved':reserved,'slots':slots,'source':source,'index':0,'rows':[],
 'done':False,'info':info,'dimension':dim,'factory':factory,'level':level}
setattr(sys,marker,s)
def write(pos,value,updates=False):
 before=info.GetBlockNew(pos,dim)
 changed=info.SetBlockNew(pos,{'name':value[0],'aux':value[1]},0,dim,True,updates)
 return {'before':before,'returned':changed}
def advance():
 if s['index']>=len(source):s['done']=True;return
 for pos in reserved:write(pos,('minecraft:air',0))
 pending=[]
 for slot,value in zip(slots,source[s['index']:s['index']+len(slots)]):
  floor=(slot[0],slot[1]-1,slot[2])
  scaffold=(slot[0],slot[1]+1,slot[2])
  writes=[write(floor,('minecraft:stone',0)),write(slot,value),write(scaffold,('minecraft:scaffolding',0),True)]
  pending.append({'requested':value,'slot':slot,'writes':writes})
 s['pending']=pending
 factory.CreateGame(level).AddTimer(.35,observe)
def observe():
 for row in s['pending']:
  slot=row.pop('slot')
  row['support']=info.GetBlockNew(slot,dim)
  row['scaffold']=info.GetBlockNew((slot[0],slot[1]+1,slot[2]),dim)
  if row['scaffold'] is not None and row['scaffold']['name']=='minecraft:scaffolding':
   row['states']=registry.states((row['scaffold']['name'],row['scaffold']['aux']))
  else:row['states']=None
  s['rows'].append(row)
 s['index']+=len(s['pending'])
 advance()
advance()
_result=json.dumps({'origin':origin,'slots':len(slots),'reserved':len(reserved),
 'states':len(source),'runtime':api.GetMinecraftVersion(),
 'game_version':registry.SOURCE_VERSION,'palette_sha256':registry.SOURCE_SHA256})
'''

STATUS = '''import json,sys
s=getattr(sys,%r)
_result=json.dumps({'done':s['done'],'index':s['index'],'states':len(s['source'])})
'''
RESULT = '''import json,sys
s=getattr(sys,%r)
assert s['done']
_result=json.dumps({'done':True,'index':s['index'],'states':len(s['source']),'rows':s['rows']})
'''
RESTORE = '''import json,sys
marker=%r
s=getattr(sys,marker,None)
count=0
if s is not None:
 s['index']=len(s['source'])
 for pos in s['reserved']:
  s['info'].SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,s['dimension'],True,False)
 for pos in s['reserved']:assert s['info'].GetBlockNew(pos,s['dimension'])['name']=='minecraft:air',pos
 count=len(s['reserved'])
 delattr(sys,marker)
_result=json.dumps({'restored':True,'reserved_air':count})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = {'schema': 1, 'method': METHOD, 'completed': False, 'restored': False,
              'session_file': os.environ.get('MCDEV_SESSION_FILE'), 'owner': os.environ.get('MCDEV_OWNER'),
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'limits': ['SDK placement, not item use.', 'Support readback must equal the requested state.',
                         'No rendering acceptance or editor falling simulation.']}
    try:
        with Client(timeout=60) as client:
            check = BlueprintCheck(client, args.output, 1800)
            try:
                report['start'] = run(client, START % MARKER)
                report.update(game_version=report['start']['game_version'],
                              palette_sha256=report['start']['palette_sha256'])
                report['progress'] = check.wait('complete scaffold support catalogue', lambda value: value['done'],
                                               lambda: run(client, STATUS % MARKER))
                report['native'] = run(client, RESULT % MARKER)
                report['completed'] = True
            finally:
                report['cleanup'] = run(client, RESTORE % MARKER)
                report['restored'] = report['cleanup']['restored']
    finally:
        write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'states': report['native']['states'], 'rows': len(report['native']['rows'])}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
