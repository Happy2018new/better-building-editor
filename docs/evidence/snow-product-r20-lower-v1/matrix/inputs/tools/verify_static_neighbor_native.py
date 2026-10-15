"""Capture stored gate and moss states after native adjacency updates.

Use run_live_check.py in the owned disposable NEMC world. Explicit placement
and native neighbor updates are measured; player-input and random growth are
outside this probe's scope.
"""
import argparse
import json
import os
from pathlib import Path
import sys

from context_test_environment import run
from verify_debug_blueprints import BlueprintCheck, Client, write_json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry

STONE = ('minecraft:stone', 0)
WALL = ('minecraft:cobblestone_wall', 0)
AIR = ('minecraft:air', 0)


def material(name, **changes):
    value = ('minecraft:' + name, 0)
    properties = dict(registry.states(value))
    properties.update(changes)
    result = registry.from_states(value[0], properties)
    assert result is not None, (name, properties)
    return result


def plans():
    rows = []
    gate_names = sorted(name for name in registry.DEFAULT_AUX if name.endswith('_fence_gate'))
    gate_names.append('minecraft:fence_gate')
    center = (0, 2, 0)
    for name in gate_names:
        for direction in ('north', 'east', 'south', 'west'):
            for opened in (False, True):
                value = material(name.split(':')[1], **{'minecraft:cardinal_direction': direction,
                                                       'open_bit': opened})
                axis = (1, 0, 0) if direction in ('north', 'south') else (0, 0, 1)
                first = tuple(center[i] + axis[i] for i in range(3))
                second = tuple(center[i] - axis[i] for i in range(3))
                rows.append({'family': 'gate', 'name': name, 'direction': direction, 'open': opened,
                             'setup': [((0, 1, 0), STONE), (center, value)],
                             'actions': [('initial', []), ('one_wall', [(first, WALL)]),
                                         ('both_walls', [(second, WALL)]),
                                         ('erase_first', [(first, AIR)]), ('erase_both', [(second, AIR)]),
                                         ('wrong_axis', [((axis[2], 2, axis[0]), WALL)])]})
    for supplied_tip in (False, True):
        values = [material('pale_hanging_moss', tip=supplied_tip)] * 5
        rows.append({'family': 'hanging_moss', 'supplied_tip': supplied_tip,
                     'setup': [((0, 7, 0), STONE)],
                     'actions': [('extend_' + str(index + 1), [((0, 6 - index, 0), value)])
                                for index, value in enumerate(values)] +
                                [('erase_tip', [((0, 2, 0), AIR)]),
                                 ('erase_middle', [((0, 4, 0), AIR)]),
                                 ('rejoin_middle', [((0, 4, 0), values[0])])]})
    center = (0, 2, 0)
    for face, axis in (('north', (0, 0, -1)), ('east', (1, 0, 0)),
                       ('south', (0, 0, 1)), ('west', (-1, 0, 0))):
        side = tuple(center[i] + axis[i] for i in range(3))
        above = (0, 3, 0)
        side_above = (side[0], 3, side[2])
        lower = material('pale_moss_carpet')
        upper = material('pale_moss_carpet', upper_block_bit=True,
                         **{'pale_moss_carpet_side_' + face: 'short'})
        rows.append({'family': 'moss_carpet', 'face': face,
                     'setup': [((0, 1, 0), STONE), (center, lower)],
                     'actions': [('initial', []), ('side_support', [(side, STONE)]),
                                 ('upper_support', [(side_above, STONE)]),
                                 ('upper_snapshot', [(above, upper)]),
                                 ('erase_upper_support', [(side_above, AIR)]),
                                 ('erase_upper', [(above, AIR)]),
                                 ('erase_side', [(side, AIR)])]})
    return rows


START = '''import json,sys,math
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry as registry
assert not hasattr(sys,'_static_neighbor_probe')
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
level=api.GetLevelId()
dimension=factory.CreateDimension(player).GetEntityDimensionId()
foot=factory.CreatePos(player).GetFootPos()
origin=(int(math.floor(foot[0]))+8,int(math.floor(foot[1]))+12,int(math.floor(foot[2]))+8)
info=factory.CreateBlockInfo(level)
state=factory.CreateBlockState(level)
reserved=[(origin[0]+x,origin[1]+y,origin[2]+z) for x in range(-2,3) for y in range(0,9) for z in range(-2,3)]
for pos in reserved:
 value=info.GetBlockNew(pos,dimension)
 assert value is not None and value['name']=='minecraft:air',(pos,value)
s={'origin':origin,'reserved':reserved,'plans':%r,'case':0,'action':-1,'rows':[],
 'done':False,'info':info,'state':state,'dimension':dimension,'factory':factory,'level':level}
sys._static_neighbor_probe=s
def put(relative,value,updates=True):
 pos=tuple(s['origin'][i]+relative[i] for i in range(3))
 before=s['info'].GetBlockNew(pos,s['dimension'])
 result=s['info'].SetBlockNew(pos,{'name':value[0],'aux':value[1]},0,s['dimension'],True,updates)
 return {'pos':relative,'value':value,'before':before,'returned':result}
def advance():
 if s['case']>=len(s['plans']):
  s['done']=True
  return
 plan=s['plans'][s['case']]
 if s['action']==-1:
  for pos in s['reserved']:
   s['info'].SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,s['dimension'],True,False)
  for relative,value in plan['setup']:put(relative,value,False)
  s['action']=0
 action,writes=plan['actions'][s['action']]
 s['pending']={'case':s['case'],'metadata':dict((k,v) for k,v in plan.items() if k not in ('setup','actions')),
  'action':action,'writes':[put(relative,value) for relative,value in writes]}
 s['factory'].CreateGame(s['level']).AddTimer(.12,observe)
def observe():
 cells=[]
 for pos in s['reserved']:
  value=s['info'].GetBlockNew(pos,s['dimension'])
  if value is not None and value['name']!='minecraft:air':
   cells.append({'pos':tuple(pos[i]-s['origin'][i] for i in range(3)),'value':value,
    'states':s['state'].GetBlockStates(pos,s['dimension'])})
 s['pending']['cells']=cells
 s['rows'].append(s['pending'])
 s['action']+=1
 if s['action']>=len(s['plans'][s['case']]['actions']):s['case']+=1;s['action']=-1
 advance()
advance()
_result=json.dumps({'origin':origin,'cases':len(s['plans']),'runtime':api.GetMinecraftVersion(),
 'game_version':registry.SOURCE_VERSION,'palette_sha256':registry.SOURCE_SHA256})
'''

STATUS = '''import json,sys
s=sys._static_neighbor_probe
_result=json.dumps({'done':s['done'],'cases':len(s['plans']),'case':s['case'],'rows':s['rows']})
'''

RESTORE = '''import json,sys
s=getattr(sys,'_static_neighbor_probe',None)
count=0
if s is not None:
 for pos in s['reserved']:
  s['info'].SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,s['dimension'],True,False)
 for pos in s['reserved']:assert s['info'].GetBlockNew(pos,s['dimension'])['name']=='minecraft:air',pos
 count=len(s['reserved'])
 del sys._static_neighbor_probe
_result=json.dumps({'restored':True,'reserved_air':count})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = {'schema': 1, 'completed': False, 'restored': False,
              'session_file': os.environ.get('MCDEV_SESSION_FILE'), 'owner': os.environ.get('MCDEV_OWNER'),
              'method': 'Explicit legacy-state placement, updateNeighbors=True, native .12s timer readback',
              'limits': ['Not player mouse input or item placement.',
                         'No random growth, gravity, or unsupported-fragment deletion in the editor.']}
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, 150)
            try:
                report['start'] = run(client, START % plans())
                report.update(game_version=report['start']['game_version'],
                              palette_sha256=report['start']['palette_sha256'])
                report['native'] = check.wait('static native adjacency rows', lambda value: value['done'],
                                             lambda: run(client, STATUS))
                report['completed'] = True
            finally:
                report['cleanup'] = run(client, RESTORE)
                report['restored'] = report['cleanup']['restored']
    finally:
        write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'cases': report['native']['cases'], 'rows': len(report['native']['rows'])}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
