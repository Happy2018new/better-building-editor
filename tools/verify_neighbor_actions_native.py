"""Capture the public edit-action matrix through owned native neighbor writes.

Run through run_live_check.py after a slot is assigned. This tool never launches
a game. Results preserve the requested writes and actual native readback; local
differences stay diagnostic until reviewed with the declared snapshot scope.
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
from projection.debug_action_blueprints import ACTION_MATRIX
from projection.debug_blueprints import material
from projection.model import Document, Editor

METHOD = 'Public action matrix, legacy native writes, updateNeighbors=True, .12s timer readback'


def plans(families=('rail',)):
    result = []
    for row in ACTION_MATRIX['cases']:
        if row['family'] not in families:
            continue
        focus = row['focus']
        origin = (focus[0], 0, focus[2])

        def resolve(records):
            return [(tuple(pos[i] - origin[i] for i in range(3)), material(name, states))
                    for pos, name, states in records]

        result.append({'id': row['id'], 'family': row['family'], 'focus': (0, focus[1], 0),
                       'setup': resolve(row['supports'] + row['blocks']),
                       'actions': [('initial', [])] + [(identity, resolve(writes))
                                                     for identity, writes in row['actions']]})
    if not result:
        raise ValueError('No declared public action cases selected')
    return result


START = '''import json,sys,math
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry as registry
def begin(plans):
 assert not hasattr(sys,'_neighbor_action_probe'), 'Previous action probe needs cleanup'
 factory=api.GetEngineCompFactory()
 level=api.GetLevelId()
 player=api.GetPlayerList()[0]
 dimension=factory.CreateDimension(player).GetEntityDimensionId()
 foot=factory.CreatePos(player).GetFootPos()
 origin=(int(math.floor(foot[0]))+8,int(math.floor(foot[1]))+12,int(math.floor(foot[2]))+8)
 info=factory.CreateBlockInfo(level)
 states=factory.CreateBlockState(level)
 reserved=[(origin[0]+x,origin[1]+y,origin[2]+z)
           for x in range(-3,4) for y in range(0,6) for z in range(-3,4)]
 for pos in reserved:
  value=info.GetBlockNew(pos,dimension)
  assert value is not None and value['name']=='minecraft:air',(pos,value)
 probe={'origin':origin,'reserved':reserved,'plans':plans,'case':0,'action':0,
        'rows':[],'done':False,'error':None,'info':info,'dimension':dimension,'active':True}
 sys._neighbor_action_probe=probe
 def put(relative,value,updates):
  pos=tuple(origin[i]+relative[i] for i in range(3))
  before=info.GetBlockNew(pos,dimension)
  changed=info.SetBlockNew(pos,{'name':value[0],'aux':value[1]},0,dimension,True,updates)
  return {'pos':relative,'value':value,'before':before,'returned':changed}
 def advance():
  if not probe['active']:return
  if probe['case']==len(plans):
   probe['done']=True
   return
  plan=plans[probe['case']]
  if probe['action']==0:
   for pos in reserved:info.SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,dimension,True,False)
   setup=[put(pos,value,False) for pos,value in plan['setup']]
  else:setup=[]
  identity,writes=plan['actions'][probe['action']]
  probe['pending']={'case':plan['id'],'family':plan['family'],'action':identity,
                    'setup_writes':setup,'writes':[put(pos,value,True) for pos,value in writes]}
  factory.CreateGame(level).AddTimer(.12,observe)
 def observe():
  try:
   observe_cells()
  except Exception as error:
   import traceback
   traceback.print_exc()
   probe['error']=str(error)
   probe['active']=False
 def observe_cells():
  if not probe['active']:return
  cells=[]
  for pos in reserved:
   value=info.GetBlockNew(pos,dimension)
   assert value is not None,('unloaded',pos)
   if value['name']!='minecraft:air':
    cells.append({'pos':tuple(pos[i]-origin[i] for i in range(3)),'value':value,
                  'states':states.GetBlockStates(pos,dimension)})
  probe['pending']['cells']=cells
  probe['rows'].append(probe['pending'])
  probe['action']+=1
  if probe['action']==len(plans[probe['case']]['actions']):
   probe['case']+=1
   probe['action']=0
  advance()
 advance()
 return {'origin':origin,'cases':len(plans),'runtime':api.GetMinecraftVersion(),
          'game_version':registry.SOURCE_VERSION,'palette_sha256':registry.SOURCE_SHA256}
_result=json.dumps(begin(%r))
'''

STATUS = '''import json,sys
probe=sys._neighbor_action_probe
_result=json.dumps(dict((key,probe[key]) for key in ('done','error','case','action','rows')))
'''

RESTORE = '''import json,sys
def restore():
 probe=getattr(sys,'_neighbor_action_probe',None)
 if probe is None:return {'restored':True,'reserved_air':0}
 probe['active']=False
 for pos in probe['reserved']:
  probe['info'].SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,probe['dimension'],True,False)
 for pos in probe['reserved']:
  value=probe['info'].GetBlockNew(pos,probe['dimension'])
  assert value is not None and value['name']=='minecraft:air',(pos,value)
 del sys._neighbor_action_probe
 return {'restored':True,'reserved_air':len(probe['reserved'])}
_result=json.dumps(restore())
'''


def compare_local(report, selected):
    if (report.get('method') != METHOD or not report.get('completed') or not report.get('restored')
            or report.get('game_version') != registry.source_version()
            or report.get('palette_sha256') != registry.fingerprint()):
        raise ValueError('Unrestored, incomplete or mismatching neighbor action evidence')
    rows = report['native']['rows']
    expected = [(plan['id'], action) for plan in selected for action, writes in plan['actions']]
    if [(row['case'], row['action']) for row in rows] != expected:
        raise ValueError('Native action order or declared coverage differs')
    result, offset = [], (15, 4, 15)
    for plan in selected:
        source = {tuple(pos[i] + offset[i] for i in range(3)): tuple(value)
                  for pos, value in plan['setup']}
        editor = Editor(Document((32, 16, 32), source))
        for action, writes in plan['actions']:
            row = rows[len(result)]
            for field, requested in (('setup_writes', plan['setup'] if action == 'initial' else []),
                                      ('writes', writes)):
                actual = [(tuple(write['pos']), tuple(write['value'])) for write in row[field]]
                if actual != [(tuple(pos), tuple(value)) for pos, value in requested]:
                    raise ValueError('Native recorded writes differ from the public source actions')
            for write in row['setup_writes'] + row['writes']:
                before = write['before']
                unchanged = before is not None and (before['name'], before['aux']) == tuple(write['value'])
                if write['returned'] is not True and not unchanged:
                    raise ValueError('Native action write failed')
            for pos, value in writes:
                editor.material = tuple(value)
                editor.paint_at(tuple(pos[i] + offset[i] for i in range(3)), respect_selection=False)
            observed = {tuple(cell['pos'][i] + offset[i] for i in range(3)):
                        (cell['value']['name'], cell['value']['aux']) for cell in row['cells']}
            if len(observed) != len(row['cells']):
                raise ValueError('Duplicate native positions')
            for cell in row['cells']:
                value = (cell['value']['name'], cell['value']['aux'])
                if registry.states(value) != cell['states']:
                    raise ValueError('Native states differ from the current registry')
            local = dict(editor.document.blocks.items())
            differences = [{'pos': pos, 'native': observed.get(pos), 'local': local.get(pos)}
                           for pos in sorted(set(observed) | set(local)) if observed.get(pos) != local.get(pos)]
            result.append({'case': plan['id'], 'action': action, 'matched': not differences,
                           'differences': differences})
    return {'rows': result, 'all_matched': all(row['matched'] for row in result),
            'scope': 'Actual native writes versus local static edits; no visual acceptance or survival deletion contract.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--family', action='append', choices=('rail', 'stairs', 'connections'))
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Existing native evidence must not be overwritten')
    selected = plans(tuple(args.family or ('rail',)))
    report = {'schema': 1, 'method': METHOD, 'completed': False, 'restored': False,
              'session_file': os.environ.get('MCDEV_SESSION_FILE'), 'owner': os.environ.get('MCDEV_OWNER'),
              'source': ACTION_MATRIX['fixture'], 'plans': selected}
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, 180)
            try:
                report['start'] = run(client, START % selected)
                report.update(game_version=report['start']['game_version'],
                              palette_sha256=report['start']['palette_sha256'])
                report['native'] = check.wait('native connection actions', lambda value: value['done'] or value['error'],
                                             lambda: run(client, STATUS))
                if report['native']['error']:
                    raise RuntimeError('Native action callback failed: ' + report['native']['error'])
                report['completed'] = True
            finally:
                report['cleanup'] = run(client, RESTORE)
                report['restored'] = report['cleanup']['restored']
        report['comparison'] = compare_local(report, selected)
    finally:
        write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'rows': len(report['native']['rows']), 'all_matched': report['comparison']['all_matched']}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
