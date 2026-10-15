"""Record restored dry/wet same-material pot NBT rewrites and inventory."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess

import probe_cold_native_actor as cold
import probe_native_pot_isolation as isolation
from verify_debug_blueprints import Client, write_json
from verify_native_entity_appearances import execute
from verify_native_pot_fields import SHERDS
from generate_native_entity_writes import METHOD

ROOT = Path(__file__).resolve().parents[1]

WRITE = '''import json,sys
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import make_cell,encode,actor_data
from modern_projection.projection.visible_actor import compose_actor,entity_nbt
from modern_projection.projection.nbt_spatial import rebase
from modern_projection.projection.debug_blueprints import build,tag
from modern_projection.projection.debug_pot_blueprints import CASES
from modern_projection.projection import block_registry as registry
saved=sys._cold_native_actor_saved
factory=api.GetEngineCompFactory()
info=factory.CreateBlockInfo(saved['player'])
target=tuple(saved['targets']['set_block'])
wet,sherds,count,item,aux=%r,%r,%r,%r,%r
point=CASES[0]['position']
nbt=entity_nbt(actor_data(build('test.entities.pottery').get(point)))
nbt['sherds']=[tag(name,8) for name in sherds]
nbt['item']['Count']=tag(count,1)
nbt['item']['Name']=tag(item,8)
value=make_cell(('minecraft:decorated_pot',aux),('minecraft:water',0) if wet else ('minecraft:air',0),
 compose_actor({},nbt))
before=encode(value)
adapter=WorldAdapter(saved['player'])
calls=[]
class WriteTrace(object):
 def __init__(self,component,records):
  self.component,self.records=component,records
 def SetBlockNew(self,pos,data,*args):
  result=self.component.SetBlockNew(pos,data,*args)
  self.records.append({'method':'SetBlockNew','position':pos,'block':data,'arguments':args,'returned':result,
   'observed_front':info.GetBlockNew(pos,saved['dimension']),
   'observed_back':info.GetLiquidBlock(pos,saved['dimension'])})
  return result
 def SetLiquidBlock(self,pos,data,*args):
  result=self.component.SetLiquidBlock(pos,data,*args)
  self.records.append({'method':'SetLiquidBlock','position':pos,'block':data,'arguments':args,'returned':result})
  return result
 def SetBlockEntityData(self,*args):
  return self.component.SetBlockEntityData(*args)
adapter.info=WriteTrace(adapter.info,calls)
adapter.layer_info_component=WriteTrace(info,calls)
returned=adapter.write(target,value,tuple(target[i]-point[i] for i in range(3)))
expected_nbt=adapter._native_tree(rebase(nbt,tuple(target[i]-point[i] for i in range(3))))
actual_nbt=info.GetBlockEntityData(saved['dimension'],target)
surroundings=[]
for dx,dy,dz in ((-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1)):
 pos=(target[0]+dx,target[1]+dy,target[2]+dz)
 surroundings.append({'position':pos,'block':info.GetBlockNew(pos,saved['dimension']),
  'liquid':info.GetLiquidBlock(pos,saved['dimension'])})
_result=json.dumps({'returned':returned,'logical_unchanged':before==encode(value),'requested':before,
 'air_staging':calls,'foreground':info.GetBlockNew(target,saved['dimension']),
 'liquid':info.GetLiquidBlock(target,saved['dimension']),
 'nbt':actual_nbt,'requested_world_nbt':expected_nbt,
 'nbt_match':actual_nbt==expected_nbt,'surroundings':surroundings,
 'game_version':registry.source_version(),'palette_sha256':registry.fingerprint()})
'''

ENCLOSE = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._cold_native_actor_saved
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
target=tuple(saved['targets']['set_block'])
rows=[]
for dx,dy,dz in ((-1,0,0),(1,0,0),(0,1,0),(0,0,-1),(0,0,1)):
 pos=(target[0]+dx,target[1]+dy,target[2]+dz)
 assert pos in saved['reserved'],pos
 assert info.SetBlockNew(pos,{'name':'minecraft:glass','aux':0},0,saved['dimension'],True,False)
 rows.append(pos)
_result=json.dumps(rows)
'''

READ_CLIENT = '''target,expected,wet,aux=%r,%r,%r,%r
palette=factory.CreateBlock(level).GetBlockPaletteBetweenPos(target,target,False)
source=palette.SerializeBlockPalette() if palette is not None else {}
entries=[{'name':name,'index':index,'fields':fields} for name,rows in source.get('actor',{}).items()
 for index,fields in rows.items()]
fields=entries[0]['fields'] if len(entries)==1 else None
sherds=[fields.get('decoratedPotShredNames'+str(index)) for index in range(4)] if fields else []
common=[{'material':key,'positions':value} for key,value in source.get('common',{}).items()]
extra=[{'material':key,'positions':value} for key,value in source.get('extra',{}).items()]
layers=(len(common)==1 and tuple(common[0]['material'])==('minecraft:decorated_pot',aux) and
 common[0]['positions']==[0] and
 ((len(extra)==1 and tuple(extra[0]['material'])==('minecraft:water',0) and extra[0]['positions']==[0]) if wet else not extra))
_result=json.dumps({'ready':sherds==list(expected) and layers,'layers_match':layers,
 'pot_sherds':sherds,'actors':entries,'common':common,'extra':extra})
'''

RESTORE = isolation.RESTORE_WORLD.replace(
    "  info.SetBlockNew(tuple(pos),{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)",
    "  info.SetBlockNew(tuple(pos),{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)\n"
    "  info.SetBlockNew(tuple(pos),{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)")


def run_probe(client, report, output, args):
    check = cold.ColdCheck(client, output, args.timeout)
    state = check.run(cold.COLD_STATE)
    report['initial_client_state'] = state
    assert state['cold'], state
    server_path = ROOT / 'behavior_pack/modern_projection/server_system.py'
    if args.baseline_ref:
        source = subprocess.run(['git', 'show', args.baseline_ref+':behavior_pack/modern_projection/server_system.py'],
                                cwd=ROOT, check=True, capture_output=True).stdout
        report['baseline_ref'] = args.baseline_ref
    else:
        source = server_path.read_bytes()
    report['server_source_sha256'] = hashlib.sha256(source).hexdigest()
    report['capability_sources'] = {}
    for name in ('native_entity_write_data', 'native_entity_write'):
        path = ROOT / ('behavior_pack/modern_projection/projection/'+name+'.py')
        content = path.read_bytes()
        report['capability_sources'][name] = hashlib.sha256(content).hexdigest()
        encoded_module = base64.b64encode(content).decode('ascii')
        execute(client, 'import base64\nimport modern_projection.projection.%s as module\n'
                'eval(compile(base64.b64decode(%r),%r,"exec"),module.__dict__)\n_result=True' %
                (name, encoded_module, str(path)))
    encoded = base64.b64encode(source).decode('ascii')
    execute(client, 'import base64\nimport modern_projection.server_system as module\n'
            'eval(compile(base64.b64decode(%r),%r,"exec"),module.__dict__)\n_result=True' %
            (encoded, str(server_path)))
    setup = cold.SETUP.replace('height=min(int(math.floor(foot[1]))+24,300)', 'height='+str(args.fixture_y))
    dx, dz = args.fixture_offset_xz
    setup = setup.replace('base=(int(math.floor(foot[0]))+8,height,int(math.floor(foot[2]))+8)',
                          'base=(int(math.floor(foot[0]))+(%d),height,int(math.floor(foot[2]))+(%d))' % (dx, dz))
    report['setup'] = execute(client, setup)
    target = tuple(report['setup']['targets']['set_block'])
    report['containment'] = execute(client, ENCLOSE)
    transitions = [(aux, initial, final) for aux in args.pot_auxes
                   for initial, final in ((False,False),(False,True),(True,False),(True,True))]
    report['pot_auxes'] = args.pot_auxes
    for aux, initial_wet, final_wet in transitions:
        case = {'id': 'direction_'+str(aux)+'_'+('wet' if initial_wet else 'dry')+'_to_'+
                      ('wet' if final_wet else 'dry'), 'aux': aux, 'writes': []}
        report['cases'].append(case)
        for index, (wet, sherds, count, item) in enumerate((
                (initial_wet, SHERDS, 11, 'minecraft:diamond'),
                (final_wet, tuple(reversed(SHERDS)), 23, 'minecraft:emerald'),
                (final_wet, tuple(reversed(SHERDS)), 23, 'minecraft:emerald'))):
            row = execute(client, WRITE % (wet, sherds, count, item, aux))
            row.update(stage=index, wet=wet, expected_sherds=list(sherds), expected_count=count, expected_item=item)
            row['replication'] = cold.observe(check, READ_CLIENT % (target, sherds, wet, aux), args.timeout)
            back = row['liquid']
            row['layer_match'] = (row['foreground'] == {'name': 'minecraft:decorated_pot', 'aux': aux} and
                                  ((back and back.get('name') == 'minecraft:water') if wet else
                                   (not back or back.get('name') == 'minecraft:air')))
            inventory = row['nbt']['item']
            row['inventory_match'] = (inventory['Count']['__value__'] == count and
                                      inventory['Name']['__value__'] == item)
            row['surroundings_match'] = all(
                point['block'].get('name') == ('minecraft:stone' if point['position'][1] < target[1] else
                                                'minecraft:glass') and
                (not point['liquid'] or point['liquid'].get('name') == 'minecraft:air')
                for point in row['surroundings'])
            row['passed'] = (row['returned'] and row['logical_unchanged'] and row['layer_match'] and
                             row['inventory_match'] and row['nbt_match'] and row['surroundings_match'] and
                             row['replication']['matched'])
            case['writes'].append(row)
            report['game_version'], report['palette_sha256'] = row['game_version'], row['palette_sha256']
            write_json(output, report)
    report['completed'] = True
    report['passed'] = all(row['passed'] for case in report['cases'] for row in case['writes'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fixture-y', type=int, default=90)
    parser.add_argument('--fixture-offset-xz', type=int, nargs=2, default=(-8, -48))
    parser.add_argument('--timeout', type=float, default=6.)
    parser.add_argument('--baseline-ref', help='Load an immutable earlier server source for negative evidence')
    parser.add_argument('--pot-auxes', type=int, nargs='+', default=[0,1,2,3])
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; preserve evidence and choose a new path')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {'schema_version': 1, 'method': METHOD, 'completed': False, 'passed': False,
              'restored': False, 'cases': [],
              'scope': 'Native repeated pot NBT writes, inventory and layers; data-only, no pixel acceptance'}
    with Client(timeout=30) as client:
        try:
            run_probe(client, report, args.output, args)
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
        finally:
            try:
                report['cleanup'] = execute(client, RESTORE)
                report['restored'] = report['cleanup']['restored']
            except Exception as error:
                report['cleanup_error'] = '%s: %s' % (type(error).__name__, error)
            write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'passed': report['passed'], 'restored': report['restored'],
                      'cases': len(report['cases']), 'report': str(args.output.resolve())}))
    return 0 if report['completed'] and report['passed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
