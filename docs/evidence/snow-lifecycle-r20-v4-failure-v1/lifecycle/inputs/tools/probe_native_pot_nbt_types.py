"""Compare pot NBT copy/UTF-8/component variants without desktop operations."""
import argparse
import json
from pathlib import Path

import probe_cold_native_actor as cold
import probe_native_pot_isolation as isolation
from verify_debug_blueprints import Client, write_json
from verify_native_entity_appearances import execute
from verify_native_pot_fields import SHERDS


WRITE = '''import copy,json,sys
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
saved=sys._cold_native_actor_saved
factory=api.GetEngineCompFactory()
variant,sherds=%r,%r
component='level' if variant.startswith('level') else 'player'
info=factory.CreateBlockInfo(api.GetLevelId() if component=='level' else saved['player'])
target=tuple(saved['targets']['set_block'])
if variant.startswith('atomic_native'):
 info.SetBlockNew(target,{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
 assert info.SetBlockNew(target,{'name':'minecraft:decorated_pot','aux':0},0,saved['dimension'],True,False)
elif variant.startswith('atomic_palette'):
 from modern_projection.projection.cell import make_cell
 info.SetBlockNew(target,{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
 assert WorldAdapter(saved['player']).write(target,make_cell(('minecraft:decorated_pot',0)))
nbt=info.GetBlockEntityData(saved['dimension'],target)
before=json.dumps(nbt)
if '_fixture_' in variant:
 from modern_projection.projection.debug_blueprints import build
 from modern_projection.projection.debug_pot_blueprints import CASES
 from modern_projection.projection.cell import actor_data
 from modern_projection.projection.visible_actor import entity_nbt
 from modern_projection.projection.nbt_spatial import rebase
 point=CASES[0]['position']
 nbt=rebase(entity_nbt(actor_data(build('test.entities.pottery').get(point))),
  tuple(target[i]-point[i] for i in range(3)))
if variant.endswith('_copy'):nbt=copy.deepcopy(nbt)
nbt['sherds']=[{'__type__':8,'__value__':name} for name in sherds]
if '_shards_only' in variant:nbt={'sherds':nbt['sherds']}
if '_without_item' in variant:nbt.pop('item',None)
if '_without_flags' in variant:
 for key in ('IsIgnoreShuffle','IsOpened','animation'):nbt.pop(key,None)
if variant.endswith('_native'):nbt=WorldAdapter._native_tree(nbt)
types=[]
def describe(value,path):
 if isinstance(value,dict):
  for key,item in value.items():
   types.append({'path':path+'/'+str(key),'key_type':type(key).__name__,'value_type':type(item).__name__})
   describe(item,path+'/'+str(key))
 elif isinstance(value,list):
  for index,item in enumerate(value):describe(item,path+'/'+str(index))
describe(nbt,'')
requested=json.dumps(nbt)
if variant.startswith('existing_production'):
 from modern_projection.projection.cell import make_cell
 from modern_projection.projection.visible_actor import compose_actor
 accepted=WorldAdapter(saved['player']).write(target,make_cell(('minecraft:decorated_pot',0),
  ('minecraft:air',0),compose_actor({},nbt)))
else:accepted=info.SetBlockEntityData(saved['dimension'],target,nbt)
_result=json.dumps({'variant':variant,'component':component,'requested':json.loads(requested),
 'before':json.loads(before),'literal_type':type('text').__name__,'types':types,'accepted':accepted,
 'after':info.GetBlockEntityData(saved['dimension'],target)})
'''

VARIANTS = ('player_raw', 'player_copy', 'player_native',
            'level_raw', 'level_copy', 'level_native')


def run_probe(client, report, output, args):
    check = cold.ColdCheck(client, output, args.timeout)
    state = check.run(cold.COLD_STATE)
    report['initial_client_state'] = state
    assert state['cold'], state
    setup = cold.SETUP.replace('height=min(int(math.floor(foot[1]))+24,300)', 'height='+str(args.fixture_y))
    dx, dz = args.fixture_offset_xz
    setup = setup.replace('base=(int(math.floor(foot[0]))+8,height,int(math.floor(foot[2]))+8)',
                          'base=(int(math.floor(foot[0]))+(%d),height,int(math.floor(foot[2]))+(%d))' % (dx, dz))
    report['setup'] = execute(client, setup)
    target = tuple(report['setup']['targets']['set_block'])
    for variant in args.variant or VARIANTS:
        row = {'variant': variant}
        report['rows'].append(row)
        row['native_placement'] = execute(client, isolation.MUTATE % ('set_block', 'fresh_native'))
        if not variant.startswith('atomic_'):
            row['raw_replication'] = cold.observe(check, cold.READ_CLIENT % (target, None), args.timeout)
        row['write'] = execute(client, WRITE % (variant, SHERDS))
        row['replication'] = cold.observe(check, cold.READ_CLIENT % (target, SHERDS), args.timeout)
        row['server'] = execute(client, isolation.READ_SERVER % 'set_block')
        write_json(output, report)
    report['completed'] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fixture-y', type=int, default=90)
    parser.add_argument('--fixture-offset-xz', type=int, nargs=2, default=(-8, -48))
    parser.add_argument('--timeout', type=float, default=6.)
    parser.add_argument('--variant', action='append')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; preserve evidence and choose a new path')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {'schema': 1, 'completed': False, 'restored': False, 'rows': [],
              'scope': 'Data-only native NBT copy, UTF-8 and component isolation; no visual acceptance'}
    with Client(timeout=30) as client:
        try:
            run_probe(client, report, args.output, args)
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
        finally:
            try:
                report['cleanup'] = execute(client, isolation.RESTORE_WORLD)
                report['restored'] = report['cleanup']['restored']
            except Exception as error:
                report['cleanup_error'] = '%s: %s' % (type(error).__name__, error)
            write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'rows': len(report['rows']), 'report': str(args.output.resolve())}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
