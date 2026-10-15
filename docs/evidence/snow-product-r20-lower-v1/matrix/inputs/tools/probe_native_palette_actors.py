"""Preserve native foreground/background/actor associations in disposable cells.

Run with run_live_check.py in an owned instance. This collects evidence only;
misnamed actor buckets are recorded without rewriting the native palette.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, MCDKError, return_value

PREPARE = '''import json,sys,math
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR,make_cell,freeze,foreground,background
from modern_projection.projection import block_registry as registry,entity_defaults
from modern_projection.projection.block_traits import is_waterloggable
from modern_projection.projection.visible_actor import compose_actor
assert not hasattr(sys,'_palette_actor_probe'), 'Restore the previous palette actor probe first'
player=api.GetPlayerList()[0]
adapter=WorldAdapter(player)
foot=adapter.factory.CreatePos(player).GetFootPos()
origin=tuple(int(math.floor(foot[i]))+(6,12,6)[i] for i in range(3))
region=tuple((origin[0]+x,origin[1]+y,origin[2]+z)
             for x in range(-2,7) for y in range(-1,4) for z in range(-2,3))
for pos in region:assert adapter.read(pos)==AIR,(pos,adapter.read(pos))
names=sorted(name for name in entity_defaults.source.DEFAULTS
             if is_waterloggable(entity_defaults.material(name)))
cases=[]
for name in names:
 for wet in (False,True):cases.append({'id':name+('_wet' if wet else '_dry'),'cells':[(name,(0,0,0),wet)]})
for wet in (False,True):
 cases.append({'id':'mixed_sign_pot_'+str(wet),'cells':[
  ('minecraft:standing_sign',(0,0,0),True),('minecraft:decorated_pot',(3,0,0),wet)]})
cases.append({'id':'mixed_wet_pot_dry_sign','cells':[
 ('minecraft:decorated_pot',(0,0,0),True),('minecraft:standing_sign',(3,0,0),False)]})
sys._palette_actor_probe={'adapter':adapter,'origin':origin,'region':region,'cases':cases,'active':None}
_result=json.dumps({'game_version':registry.source_version(),'palette_sha256':registry.fingerprint(),
 'origin':origin,'cases':cases,'names':names})
'''

SEED = '''import json,sys
from modern_projection.projection.cell import AIR,make_cell,foreground,background
from modern_projection.projection.visible_actor import compose_actor
from modern_projection.projection import entity_defaults
probe=sys._palette_actor_probe
adapter=probe['adapter']
for pos in probe['region']:
 if adapter.read(pos)!=AIR:assert adapter.write(pos,AIR),(pos,'clear')
origin=probe['origin']
case=probe['cases'][%d]
probe['active']=case
for pos in probe['region']:
 dx,dy,dz=tuple(pos[i]-origin[i] for i in range(3))
 if dy==-1 or dy==3 or dx in (-2,6) or dz in (-2,2):
  assert adapter.write(pos,('minecraft:stone',0)),(pos,'support')
observed=[]
for name,local,wet in case['cells']:
 pos=tuple(origin[i]+local[i] for i in range(3))
 for offset in ((-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1)):
  support=tuple(pos[i]+offset[i] for i in range(3))
  if adapter.read(support)!=('minecraft:stone',0):
   assert adapter.write(support,('minecraft:stone',0)),(support,'adjacent support')
 front=entity_defaults.material(name)
 from modern_projection.projection import block_registry as registry
 properties=registry.states(front)
 if 'facing_direction' in properties:
  candidate=dict(properties,facing_direction=2)
  direction=registry.from_states(name,candidate)
  if direction is not None:front=direction
 value=make_cell(front,('minecraft:water',0) if wet else AIR,
                 compose_actor(None,entity_defaults.nbt(name,pos)))
 write_ok=adapter.write(pos,value)
 actual=adapter.read(pos)
 observed.append({'name':name,'pos':pos,'local':local,'wet':wet,
                  'write_ok':bool(write_ok),
                  'front':foreground(actual),'back':background(actual)})
low=tuple(min(row['pos'][i] for row in observed) for i in range(3))
high=tuple(max(row['pos'][i] for row in observed) for i in range(3))
probe['low'],probe['high']=low,high
_result=json.dumps({'id':case['id'],'low':low,'high':high,'observed':observed})
'''

SERVER_READ = '''import json,sys
from modern_projection.projection.cell import freeze,foreground,background
probe=sys._palette_actor_probe
adapter=probe['adapter']
palette=adapter.palette_block.GetBlockPaletteBetweenPos(adapter.dimension,probe['low'],probe['high'],False)
data=None if palette is None else palette.SerializeBlockPalette()
actors=[]
for name,local,wet in probe['active']['cells']:
 pos=tuple(probe['origin'][i]+local[i] for i in range(3))
 value=adapter.read(pos)
 nbt=adapter.info.GetBlockEntityData(adapter.dimension,pos)
 actors.append({'pos':pos,'front':foreground(value),'back':background(value),'nbt':freeze(nbt)})
_result=json.dumps({'palette':freeze(data),'actors':actors})
'''

CLIENT_READ = '''import json
import mod.client.extraClientApi as api
from modern_projection.projection.cell import freeze
low,high=%r,%r
palette=api.GetEngineCompFactory().CreateBlock(api.GetLevelId()).GetBlockPaletteBetweenPos(low,high,False)
_result=json.dumps({'palette':None if palette is None else freeze(palette.SerializeBlockPalette())})
'''

CLEANUP = '''import json,sys
from modern_projection.projection.cell import AIR
probe=getattr(sys,'_palette_actor_probe',None)
restored=True
residue=[]
if probe is not None:
 for pos in probe['region']:
  if probe['adapter'].read(pos)!=AIR:probe['adapter'].write(pos,AIR)
 for pos in probe['region']:
  if probe['adapter'].read(pos)!=AIR:residue.append(pos)
 restored=not residue
 if restored:del sys._palette_actor_probe
_result=json.dumps({'restored':restored,'residue':residue})
'''


def run(client, code, server=False):
    result = client.call('execute_code', {'code': code, 'is_client': not server,
                                          'direct_return': True})
    if result.get('isError'):
        raise RuntimeError(result)
    value = return_value(result)
    return json.loads(value) if isinstance(value, str) else value


def write_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


def read_palette(client, code, server=False):
    try:
        return run(client, code, server)
    except MCDKError as error:
        # Failed reads remain explicit diagnostics, never negative capabilities.
        response = json.loads(str(error))
        messages = [item.get('text', '') for item in response.get('content', [])]
        if not response.get('isError') or not any('Code execution failed:' in text for text in messages):
            raise
        return {'read_error': response}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case', action='append', help='Native case ID, repeat to select')
    parser.add_argument('--delay', type=float, default=.35)
    parser.add_argument('--resume', type=Path, help='Reuse a restored prefix from the same origin and cases')
    args = parser.parse_args()
    report = {'schema_version': 1, 'method': 'native dual-layer palette and GetBlockEntityData; six adjacent supports; legal horizontal facing; no bucket corrections; v2',
              'completed': False, 'rows': [], 'restored': False}
    with Client(timeout=30) as client:
        try:
            prepared = run(client, PREPARE, True)
            report.update(prepared)
            if args.resume:
                previous = json.loads(args.resume.read_text(encoding='utf8'))
                if (not previous.get('restored') or any(previous.get(key) != prepared[key]
                        for key in ('origin', 'cases', 'names', 'game_version', 'palette_sha256'))):
                    raise ValueError('Resume evidence must have a restored identical origin and coverage')
                for index, row in enumerate(previous['rows']):
                    if row['id'] != report['cases'][index]['id']:
                        raise ValueError('Resume cases are not an ordered prefix')
                    if any(side not in row for side in ('server_immediate', 'server_delayed', 'client_delayed')):
                        break
                    report['rows'].append(row)
            for index, case in enumerate(report['cases']):
                if index < len(report['rows']):
                    continue
                if args.case and case['id'] not in args.case:
                    continue
                row = run(client, SEED % index, True)
                report['rows'].append(row)
                row['server_immediate'] = read_palette(client, SERVER_READ, True)
                time.sleep(args.delay)
                row['server_delayed'] = read_palette(client, SERVER_READ, True)
                row['client_delayed'] = read_palette(client, CLIENT_READ % (tuple(row['low']), tuple(row['high'])))
                write_report(args.output, report)
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            report['cleanup'] = run(client, CLEANUP, True)
            report['restored'] = report['cleanup']['restored']
            write_report(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'cases': len(report['rows']), 'output': str(args.output)}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
