"""Read original dry public snapshots through the production native world writer."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from context_test_environment import run
from verify_debug_blueprints import BlueprintCheck, Client, write_json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.debug_blueprints import material
from projection.debug_botanical_blueprints import VISUAL_CASE
from projection.rail_neighbor_data import RUNTIME


def plans():
    result = []
    for row in VISUAL_CASE['cases']:
        source = row['supports'] + row['blocks']
        if row['water'] or any(name in ('water', 'flowing_water', 'lava', 'flowing_lava')
                               for pos, name, states in source):
            continue
        low = tuple(min(pos[i] for pos, name, states in source) for i in range(3))
        records = [(tuple(pos[i] - low[i] for i in range(3)), material(name, states))
                   for pos, name, states in source]
        result.append({'id': row['id'], 'source_origin': low, 'cells': records})
    return result


START = '''import json,sys,math
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR,foreground,background
from modern_projection.projection import block_registry as registry
def begin(plans):
 assert not hasattr(sys,'_botanical_snapshot_probe')
 factory=api.GetEngineCompFactory()
 player=api.GetPlayerList()[0]
 adapter=WorldAdapter(player)
 states=factory.CreateBlockState(adapter.level)
 foot=factory.CreatePos(player).GetFootPos()
 origin=(int(math.floor(foot[0]))+8,int(math.floor(foot[1]))+12,int(math.floor(foot[2]))+8)
 relative=set(tuple(pos[i]+offset[i] for i in range(3))
              for plan in plans for pos,value in plan['cells']
              for offset in ((0,0,0),(-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1)))
 reserved=sorted(tuple(origin[i]+pos[i] for i in range(3)) for pos in relative)
 for pos in reserved:assert adapter.read(pos)==AIR,(pos,adapter.read(pos))
 probe={'adapter':adapter,'reserved':reserved,'origin':origin,'plans':plans,
        'case':0,'rows':[],'active':True,'done':False,'error':None}
 sys._botanical_snapshot_probe=probe
 def clear():
  for pos in reversed(reserved):
   if adapter.read(pos)!=AIR:assert adapter.write(pos,AIR),pos
  for pos in reserved:assert adapter.read(pos)==AIR,(pos,adapter.read(pos))
 def advance():
  if not probe['active']:return
  clear()
  if probe['case']==len(plans):
   probe['done']=True
   return
  plan=plans[probe['case']]
  writes=[]
  for pos,value in plan['cells']:
   absolute=tuple(origin[i]+pos[i] for i in range(3))
   writes.append({'pos':pos,'value':value,'returned':adapter.write(absolute,tuple(value))})
  probe['pending']={'case':plan['id'],'writes':writes,'samples':[]}
  factory.CreateGame(adapter.level).AddTimer(.12,observe)
 def observe():
  try:
   sample()
  except Exception as error:
   import traceback
   traceback.print_exc()
   probe['active']=False
   probe['error']=str(error)
 def sample():
  if not probe['active']:return
  cells=[]
  for pos in reserved:
   value=adapter.read(pos)
   assert value is not None,('unloaded',pos)
   if value!=AIR:
    cells.append({'pos':tuple(pos[i]-origin[i] for i in range(3)),
                  'front':foreground(value),'back':background(value),
                  'states':states.GetBlockStates(pos,adapter.dimension)})
  probe['pending']['samples'].append(cells)
  if len(probe['pending']['samples'])<2:
   factory.CreateGame(adapter.level).AddTimer(.12,observe)
   return
  probe['rows'].append(probe['pending'])
  probe['case']+=1
  advance()
 advance()
 return {'origin':origin,'reserved':len(reserved),'runtime':api.GetMinecraftVersion(),
         'game_version':registry.SOURCE_VERSION,'palette_sha256':registry.SOURCE_SHA256}
_result=json.dumps(begin(%r))
'''
STATUS = '''import json,sys
probe=sys._botanical_snapshot_probe
_result=json.dumps(dict((key,probe[key]) for key in ('done','error','case','rows')))
'''
RESTORE = '''import json,sys
from modern_projection.projection.cell import AIR
def restore():
 probe=getattr(sys,'_botanical_snapshot_probe',None)
 if probe is None:return {'restored':True,'reserved_air':0}
 probe['active']=False
 adapter=probe['adapter']
 for pos in reversed(probe['reserved']):
  if adapter.read(pos)!=AIR:assert adapter.write(pos,AIR),pos
 for pos in probe['reserved']:assert adapter.read(pos)==AIR,(pos,adapter.read(pos))
 del sys._botanical_snapshot_probe
 return {'restored':True,'reserved_air':len(probe['reserved'])}
_result=json.dumps(restore())
'''


def compare(report, selected):
    start = report.get('start', {})
    if (not report.get('completed') or not report.get('restored') or start.get('runtime') != RUNTIME
            or start.get('game_version') != registry.source_version()
            or start.get('palette_sha256') != registry.fingerprint()):
        raise ValueError('Dry native snapshot evidence is incomplete or belongs to another version')
    observed = report['native']['rows']
    if [row['case'] for row in observed] != [row['id'] for row in selected]:
        raise ValueError('Native dry source coverage differs')
    result = []
    for row, plan in zip(observed, selected):
        writes = [(tuple(value['pos']), tuple(value['value'])) for value in row['writes']]
        if writes != plan['cells'] or not all(value['returned'] is True for value in row['writes']):
            raise ValueError('Dry native source writes changed or failed')
        if len(row['samples']) != 2:
            raise ValueError('Dry source needs two independent timer readbacks')
        requested = dict(plan['cells'])
        differences = []
        for number, cells in enumerate(row['samples']):
            actual = {tuple(cell['pos']): tuple(cell['front']) for cell in cells}
            if len(actual) != len(cells):
                raise ValueError('Duplicate native dry cells')
            for pos in sorted(set(requested) | set(actual)):
                if requested.get(pos) != actual.get(pos):
                    differences.append({'sample': number, 'pos': pos,
                                        'requested': requested.get(pos), 'actual': actual.get(pos)})
            for cell in cells:
                if tuple(cell['back']) != ('minecraft:air', 0) or registry.states(tuple(cell['front'])) != cell['states']:
                    differences.append({'sample': number, 'pos': tuple(cell['pos']),
                                        'unexpected_background_or_states': cell})
        result.append({'case': row['case'], 'source_matches_native': not differences,
                       'stable': row['samples'][0] == row['samples'][1], 'differences': differences})
    return {'cases': result, 'all_matched': all(row['source_matches_native'] and row['stable'] for row in result),
            'scope': 'Dry source/state equality only; editor/full/missing image acceptance pending.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Existing dry native evidence must not be overwritten')
    selected = plans()
    session_file, owner = os.environ['MCDEV_SESSION_FILE'], os.environ['MCDEV_OWNER']
    session = json.loads(Path(session_file).read_bytes())
    if session['owner'] != owner or Path(session['project']).resolve() != ROOT:
        raise ValueError('Dry native provenance belongs to another project or owner')
    report = {'schema': 1, 'completed': False, 'restored': False, 'session_file': session_file,
              'owner': owner, 'source': VISUAL_CASE['fixture'], 'plans': selected,
              'provenance': {'session_id': session['id'], 'game_pid': session['game_pid'],
                             'game_identity': session['game_identity'],
                             'game_executable_sha256': hashlib.sha256(Path(session['game_executable']).read_bytes()).hexdigest(),
                             'public_source_sha256': hashlib.sha256((ROOT / 'behavior_pack/modern_projection/projection/debug_botanical_blueprints.py').read_bytes()).hexdigest(),
                             'native_payload_sha256': hashlib.sha256((START % selected).encode('utf8')).hexdigest()},
              'acceptance': {'editor': 'pending', 'full': 'pending', 'missing': 'pending'}}
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, 90)
            try:
                report['start'] = run(client, START % selected)
                report['native'] = check.wait('native dry botanical source snapshots',
                                             lambda value: value['done'] or value['error'],
                                             lambda: run(client, STATUS))
                if report['native']['error']:
                    raise RuntimeError(report['native']['error'])
                report['completed'] = True
            finally:
                report['cleanup'] = run(client, RESTORE)
                report['restored'] = report['cleanup']['restored']
        report['comparison'] = compare(report, selected)
    finally:
        write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'cases': len(report['native']['rows']), 'all_matched': report['comparison']['all_matched']}))


if __name__ == '__main__':
    main()
