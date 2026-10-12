"""Measure a bounded range of dumped states by native block placement.

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
METHOD = ('8 isolated native legacy-state support/scaffold cells; tile drops disabled; '
          '.35s delayed readback; dual-layer air reset; flow forbidden')
SEGMENT_METHOD = METHOD + '; bounded-range-v2'
MAX_SEGMENT_STATES = 256

START = '''import json,sys,math
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry as registry
marker=%r
assert not hasattr(sys,marker), 'Previous support catalogue requires cleanup'
range_start,range_count=%r,%r
assert (registry.SOURCE_VERSION,registry.SOURCE_SHA256)==(%r,%r), 'Registry mismatch'
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
player=api.GetPlayerList()[0]
dim=factory.CreateDimension(player).GetEntityDimensionId()
foot=factory.CreatePos(player).GetFootPos()
origin=(int(math.floor(foot[0]))+4,int(math.floor(foot[1]))+18,int(math.floor(foot[2]))+4)
info=factory.CreateBlockInfo(level)
block=factory.CreateBlock(level)
air_palette=block.GetBlankBlockPalette()
assert air_palette is not None
assert air_palette.DeserializeBlockPalette({
 'volume':(1,1,1),'common':{('minecraft:air',0):[0]},'states':{},
 'extra':{('minecraft:air',0):[0]},'extraStates':{},'actor':{},
 'void':False,'eliminateAir':False})
game=factory.CreateGame(level)
slots=[(origin[0]+(i%%4)*3,origin[1],origin[2]+(i//4)*3) for i in range(8)]
reserved=set((pos[0]+x,pos[1]+y,pos[2]+z) for pos in slots
 for x in (-1,0,1) for y in (-1,0,1,2,3) for z in (-1,0,1))
for pos in reserved:
 value=info.GetBlockNew(pos,dim)
 assert value is not None and value['name']=='minecraft:air',('non-air reserve',pos,value)
 liquid=info.GetLiquidBlock(pos,dim)
 assert liquid is None or liquid.get('name') in ('minecraft:air',None),('wet reserve',pos,liquid)
source=[(name,aux) for name in sorted(registry.BLOCKS) for aux in registry.aux_values(name)]
assert 0<=range_start<len(source) and 0<range_count<=256, 'Invalid bounded range'
range_stop=min(range_start+range_count,len(source))
s={'reserved':reserved,'slots':slots,'source':source,'index':range_start,'rows':[],
 'range':[range_start,range_stop],'active':True,
 'done':False,'info':info,'block':block,'air_palette':air_palette,'dimension':dim,'game':game,
 'tile_drops':game.GetGameRulesInfoServer()['option_info']['tile_drops']}
setattr(sys,marker,s)
assert game.SetGameRulesInfoServer({'option_info':{'tile_drops':False}})
assert game.GetGameRulesInfoServer()['option_info']['tile_drops'] is False
assert game.ForbidLiquidFlow(True)
def write(pos,value,updates=False):
 before=info.GetBlockNew(pos,dim)
 changed=info.SetBlockNew(pos,{'name':value[0],'aux':value[1]},0,dim,True,updates)
 return {'before':before,'returned':changed}
def advance():
 if not s['active']:return
 if s['index']>=range_stop:s['done']=True;return
 for pos in reserved:block.SetBlockByBlockPalette(air_palette,dim,pos,0,0)
 for pos in reserved:
  value=info.GetBlockNew(pos,dim)
  liquid=info.GetLiquidBlock(pos,dim)
  assert value is not None and value['name']=='minecraft:air',('uncleared reserve',pos,value)
  assert liquid is None or liquid.get('name') in ('minecraft:air',None),('uncleared liquid',pos,liquid)
 pending=[]
 for slot,value in zip(slots,source[s['index']:min(s['index']+len(slots),range_stop)]):
  floor=(slot[0],slot[1]-1,slot[2])
  scaffold=(slot[0],slot[1]+1,slot[2])
  writes=[write(floor,('minecraft:stone',0)),write(slot,value),write(scaffold,('minecraft:scaffolding',0),True)]
  pending.append({'requested':value,'slot':slot,'writes':writes})
 s['pending']=pending
 # Retain the owning segment even if execute_code reuses its global scope.
 game.AddTimer(.35,lambda current=s:observe(current))
def observe(current):
 if current is not s or not current['active']:return
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
 'range':s['range'],
 'tile_drops':False,'original_tile_drops':s['tile_drops'],'flow_forbidden':True,
 'game_version':registry.SOURCE_VERSION,'palette_sha256':registry.SOURCE_SHA256})
'''

STATUS = '''import json,sys
s=getattr(sys,%r)
_result=json.dumps({'done':s['done'],'index':s['index'],'states':len(s['source']),
 'range':s['range'],'rows':s['rows'],
 'next_state':s['source'][s['index']] if s['index']<len(s['source']) else None})
'''
RESULT = '''import json,sys
s=getattr(sys,%r)
assert s['done']
_result=json.dumps({'done':True,'index':s['index'],'states':len(s['source']),
 'range':s['range'],'rows':s['rows']})
'''
RESTORE = '''import json,sys
marker=%r
s=getattr(sys,marker,None)
count=0
rules_restored=True
flow_restored=True
remaining=[]
if s is not None:
 s['active']=False
 s['index']=len(s['source'])
 try:
  for pos in s['reserved']:
   s['block'].SetBlockByBlockPalette(s['air_palette'],s['dimension'],pos,0,0)
  for pos in s['reserved']:
   value=s['info'].GetBlockNew(pos,s['dimension'])
   liquid=s['info'].GetLiquidBlock(pos,s['dimension'])
   if (value is None or value['name']!='minecraft:air' or
       liquid is not None and liquid.get('name') not in ('minecraft:air',None)):
    remaining.append({'pos':pos,'value':value,'liquid':liquid})
  count=len(s['reserved'])-len(remaining)
 finally:
  rules_restored=bool(s['game'].SetGameRulesInfoServer({'option_info':{'tile_drops':s['tile_drops']}}))
  rules_restored=rules_restored and s['game'].GetGameRulesInfoServer()['option_info']['tile_drops']==s['tile_drops']
  flow_restored=bool(s['game'].ForbidLiquidFlow(False))
 if not remaining and rules_restored and flow_restored:delattr(sys,marker)
_result=json.dumps({'restored':not remaining and rules_restored and flow_restored,
 'rules_restored':rules_restored,'flow_restored':flow_restored,'remaining':remaining,'reserved_air':count})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--start-index', type=int, default=0)
    parser.add_argument('--count', type=int, default=MAX_SEGMENT_STATES,
                        help='Maximum states in one owned session range (1-256)')
    args = parser.parse_args()
    state_count = sum(len(registry.aux_values(name)) for name in registry.BLOCKS)
    if not 0 <= args.start_index < state_count or not 0 < args.count <= MAX_SEGMENT_STATES:
        parser.error('Expected an existing start index and count in 1-256')
    report = {'schema': 1, 'method': SEGMENT_METHOD, 'completed': False, 'restored': False,
              'session_file': os.environ.get('MCDEV_SESSION_FILE'), 'owner': os.environ.get('MCDEV_OWNER'),
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'limits': ['SDK placement, not item use.', 'Support readback must equal the requested state.',
                         'Flow restoration assumes an owned fresh-session allowed-flow baseline; SDK has no getter.',
                         'No rendering acceptance or editor falling simulation.']}
    try:
        with Client(timeout=60) as client:
            check = BlueprintCheck(client, args.output, 180)
            def progress():
                value = run(client, STATUS % MARKER)
                report['native'] = value
                report['progress'] = {key: value[key] for key in ('done', 'index', 'states', 'range', 'next_state')}
                write_json(args.output, report)
                return value
            try:
                report['start'] = run(client, START % (
                    MARKER, args.start_index, args.count, registry.SOURCE_VERSION, registry.SOURCE_SHA256))
                report.update(game_version=report['start']['game_version'],
                              palette_sha256=report['start']['palette_sha256'])
                check.wait('complete scaffold support segment', lambda value: value['done'], progress)
                report['native'] = run(client, RESULT % MARKER)
                report['completed'] = True
            except Exception as error:
                report['error'] = '%s: %s' % (type(error).__name__, error)
            finally:
                try:
                    report['cleanup'] = run(client, RESTORE % MARKER)
                    report['restored'] = report['cleanup']['restored']
                except Exception as error:
                    report['cleanup_error'] = '%s: %s' % (type(error).__name__, error)
    finally:
        write_json(args.output, report)
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'progress', 'error', 'cleanup_error') if key in report}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
