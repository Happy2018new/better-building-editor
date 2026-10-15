"""Observe bounded native scaffold support updates in an owned test world.

This SDK-only probe never activates a window. It records physical native
placement and readback, including fragments removed by the engine; it does not
accept geometry, pixels, or editor gravity behavior.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from context_test_environment import run
from verify_debug_blueprints import BlueprintCheck, Client, write_json

AIR = ('minecraft:air', 0)
STONE = ('minecraft:stone', 0)
SCAFFOLD = ('minecraft:scaffolding', 0)
MARKER = '_scaffolding_native_r8'
READBACK_DELAY = 1.2
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry


def support_plans():
    samples = [('stone', {}), ('glass', {}), ('tinted_glass', {}),
               ('oak_leaves', {'persistent_bit': True}), ('ice', {}),
               ('oak_slab', {'minecraft:vertical_half': 'bottom'}),
               ('oak_slab', {'minecraft:vertical_half': 'top'}),
               ('oak_stairs', {'upside_down_bit': False}),
               ('oak_stairs', {'upside_down_bit': True}),
               ('cobblestone_wall', {}), ('oak_fence', {}),
               ('trapdoor', {'open_bit': False, 'upside_down_bit': False}),
               ('trapdoor', {'open_bit': False, 'upside_down_bit': True}),
               ('trapdoor', {'open_bit': True, 'upside_down_bit': True})]
    rows = []
    for index, (name, changes) in enumerate(samples):
        full_name = 'minecraft:' + name
        properties = dict(registry.states((full_name, 0)), **changes)
        value = registry.from_states(full_name, properties)
        assert value is not None, (full_name, properties)
        rows.append({'id': 'scaffold_support_' + str(index), 'family': 'support',
                     'support': value, 'support_states': properties,
                     'setup': [((0, 0, 0), STONE), ((0, 1, 0), value)],
                     'actions': [('place_scaffold', [((0, 2, 0), SCAFFOLD)])]})
    return rows


def plans():
    rows = []
    for face, axis in (('east', (1, 0)), ('west', (-1, 0)),
                       ('south', (0, 1)), ('north', (0, -1))):
        side = lambda distance, y: (axis[0] * distance, y, axis[1] * distance)
        actions = [('column_' + str(y), [((0, y, 0), SCAFFOLD)]) for y in (1, 2, 3)]
        actions += [('span_' + str(distance), [(side(distance, 3), SCAFFOLD)])
                    for distance in range(1, 8)]
        actions += [('far_support', [(side(6, y), STONE) for y in (0, 1, 2)]),
                    ('rejoin_far_end', [(side(distance, 3), SCAFFOLD) for distance in (6, 7, 8)]),
                    ('erase_near_column', [((0, y, 0), AIR) for y in (1, 2, 3)]),
                    ('erase_far_support', [(side(6, 2), AIR)])]
        rows.append({'id': 'scaffold_span_' + face, 'family': 'scaffolding',
                     'setup': [((0, 0, 0), STONE)], 'actions': actions})
    rows.append({'id': 'scaffold_horizontal_then_column', 'family': 'scaffolding',
                 'setup': [((0, 0, 0), STONE), ((0, 1, 0), SCAFFOLD)],
                 'actions': [('extend_' + str(x), [((x, 1, 0), SCAFFOLD)]) for x in range(1, 7)] +
                            [('rise_' + str(y), [((6, y, 0), SCAFFOLD)]) for y in (2, 3, 4)] +
                            [('near_support', [((5, 0, 0), STONE)]),
                             ('remove_bridge', [((3, 1, 0), AIR)]),
                             ('remove_alternate_support', [((5, 0, 0), AIR)])]})
    return rows


START = '''import json,sys,math
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry as registry
marker=%r
assert not hasattr(sys,marker), 'Prior scaffold probe requires cleanup'
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
level=api.GetLevelId()
dimension=factory.CreateDimension(player).GetEntityDimensionId()
foot=factory.CreatePos(player).GetFootPos()
origin=(int(math.floor(foot[0]))+8,int(math.floor(foot[1]))+12,int(math.floor(foot[2]))+8)
info=factory.CreateBlockInfo(level)
state=factory.CreateBlockState(level)
plans=%r
relative=set()
for plan in plans:
 for pos,value in plan['setup']:
  relative.add(pos)
 for action,writes in plan['actions']:
  for pos,value in writes:relative.add(pos)
low=tuple(min(pos[i] for pos in relative)-1 for i in range(3))
high=tuple(max(pos[i] for pos in relative)+1 for i in range(3))
reserved=[(origin[0]+x,origin[1]+y,origin[2]+z)
 for x in range(low[0],high[0]+1) for y in range(low[1],high[1]+1) for z in range(low[2],high[2]+1)]
for pos in reserved:
 value=info.GetBlockNew(pos,dimension)
 assert value is not None and value['name']=='minecraft:air',('non-air reserve',pos,value)
s={'origin':origin,'reserved':reserved,'plans':plans,'case':0,'action':-1,'rows':[],
 'done':False,'info':info,'state':state,'dimension':dimension,'factory':factory,'level':level}
setattr(sys,marker,s)
def put(relative,value,updates=True):
 pos=tuple(origin[i]+relative[i] for i in range(3))
 before=info.GetBlockNew(pos,dimension)
 returned=info.SetBlockNew(pos,{'name':value[0],'aux':value[1]},0,dimension,True,updates)
 return {'pos':relative,'value':value,'before':before,'returned':returned}
def observe():
 cells=[]
 for pos in reserved:
  value=info.GetBlockNew(pos,dimension)
  if value is not None and value['name']!='minecraft:air':
   cells.append({'pos':tuple(pos[i]-origin[i] for i in range(3)),
    'value':value,'states':state.GetBlockStates(pos,dimension)})
 s['pending']['cells']=cells
 s['rows'].append(s['pending'])
 s['action']+=1
 if s['action']>=len(plans[s['case']]['actions']):s['case']+=1;s['action']=-1
 advance()
def advance():
 if s['case']>=len(plans):s['done']=True;return
 plan=plans[s['case']]
 if s['action']==-1:
  for pos in reserved:info.SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,dimension,True,False)
  for relative,value in plan['setup']:put(relative,value,False)
  s['action']=0
 action,writes=plan['actions'][s['action']]
 s['pending']={'case':s['case'],'metadata':dict((k,v) for k,v in plan.items() if k not in ('setup','actions')),
  'action':action,'writes':[put(relative,value) for relative,value in writes]}
 factory.CreateGame(level).AddTimer(%r,observe)
advance()
_result=json.dumps({'origin':origin,'reserved_count':len(reserved),'cases':len(plans),
 'runtime':api.GetMinecraftVersion(),'game_version':registry.SOURCE_VERSION,'palette_sha256':registry.SOURCE_SHA256})
'''

STATUS = '''import json,sys
s=getattr(sys,%r)
_result=json.dumps({'done':s['done'],'cases':len(s['plans']),'case':s['case'],'rows':s['rows']})
'''

RESTORE = '''import json,sys
marker=%r
s=getattr(sys,marker,None)
count=0
if s is not None:
 s['case']=len(s['plans'])
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
    parser.add_argument('--support-only', action='store_true')
    args = parser.parse_args()
    report = {'schema': 1, 'completed': False, 'restored': False,
              'session_file': os.environ.get('MCDEV_SESSION_FILE'), 'owner': os.environ.get('MCDEV_OWNER'),
              'method': 'Native legacy-state writes with neighbor updates; delayed readback',
              'readback_delay': READBACK_DELAY,
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'limits': ['No pixel or geometry acceptance.', 'Native removed fragments are recorded; no editor gravity simulation.']}
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, 100)
            try:
                report['start'] = run(client, START % (MARKER, support_plans() if args.support_only else plans(), READBACK_DELAY))
                report.update(game_version=report['start']['game_version'],
                              palette_sha256=report['start']['palette_sha256'])
                report['native'] = check.wait('native scaffold support rows', lambda value: value['done'],
                                             lambda: run(client, STATUS % MARKER))
                report['completed'] = True
            finally:
                report['cleanup'] = run(client, RESTORE % MARKER)
                report['restored'] = report['cleanup']['restored']
    finally:
        write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'cases': report['native']['cases'], 'rows': len(report['native']['rows'])}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
