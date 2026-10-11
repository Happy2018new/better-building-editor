"""Isolate glass, state, liquid, palette and NBT changes on native pots.

Run in a fresh owned disposable instance through run_live_check.py. The order
comes from the preserved r5 checkpoint. Every phase keeps native body pixels
separate from sherd replication; neither is inferred from API return values.
"""
import argparse
import json
import os
import time
from pathlib import Path

import probe_cold_native_actor as cold
from verify_debug_blueprints import Client, write_json
from verify_native_entity_appearances import execute
from verify_native_pot_fields import SHERDS


MUTATE = '''import json,sys
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import actor_data,foreground,make_cell
from modern_projection.projection.debug_blueprints import build
from modern_projection.projection.debug_pot_blueprints import CASES
saved=sys._cold_native_actor_saved
factory=api.GetEngineCompFactory()
info=factory.CreateBlockInfo(saved['player'])
key,operation=%r,%r
target=tuple(saved['targets'][key])
dimension=saved['dimension']
returned=None
if operation in ('glass_add','glass_remove'):
 glass=(target[0],target[1],target[2]+1)
 assert glass in saved['reserved'],glass
 name='minecraft:glass' if operation=='glass_add' else 'minecraft:air'
 returned=info.SetBlockNew(glass,{'name':name,'aux':0},0,dimension,True,False)
 assert info.GetBlockNew(glass,dimension).get('name')==name
elif operation=='fresh_native':
 info.SetBlockNew(target,{'name':'minecraft:air','aux':0},0,dimension,True,False)
 assert info.GetBlockNew(target,dimension).get('name')=='minecraft:air'
 returned=info.SetBlockNew(target,{'name':'minecraft:decorated_pot','aux':0},0,dimension,True,False)
elif operation=='state_only':
 returned=factory.CreateBlockState(api.GetLevelId()).SetBlockStates(target,{'direction':0},dimension)
elif operation=='liquid_air_only':
 returned=info.SetLiquidBlock(target,{'name':'minecraft:air','aux':0},dimension)
elif operation in ('palette_no_extra','palette_extra_air','production_fixture'):
 info.SetBlockNew(target,{'name':'minecraft:air','aux':0},0,dimension,True,False)
 assert info.GetBlockNew(target,dimension).get('name')=='minecraft:air'
 adapter=WorldAdapter(saved['player'])
 if operation=='production_fixture':
  point=CASES[0]['position']
  value=build('test.entities.pottery').get(point)
  origin=tuple(target[i]-point[i] for i in range(3))
  returned=adapter.write(target,value,origin)
 else:
  front=('minecraft:decorated_pot',0)
  common_key,common_states=adapter._palette_layer(front)
  extra_key,extra_states=adapter._palette_layer(('minecraft:air',0))
  data={'volume':(1,1,1),'common':{common_key:[0]},'states':{common_key:common_states},
   'extra':{},'extraStates':{},'actor':{},'void':False,'eliminateAir':False}
  if operation=='palette_extra_air':
   data['extra']={extra_key:[0]}
   if extra_states is not None:data['extraStates']={extra_key:extra_states}
  palette=adapter.palette_block.GetBlankBlockPalette()
  assert palette is not None and palette.DeserializeBlockPalette(data)
  returned=adapter.palette_block.SetBlockByBlockPalette(palette,dimension,target,0,0)
else:
 raise AssertionError('Unsupported isolation operation: '+operation)
saved.setdefault('isolation_mutations',[]).append({'key':key,'operation':operation,'returned':returned})
_result=json.dumps({'operation':operation,'returned':returned,'target':target,
 'foreground':info.GetBlockNew(target,dimension),
 'states':factory.CreateBlockState(api.GetLevelId()).GetBlockStates(target,dimension),
 'liquid':info.GetLiquidBlock(target,dimension),'nbt':info.GetBlockEntityData(dimension,target),
 'native_writes':saved['native_writes'],'isolation_mutations':saved['isolation_mutations']})
'''

READ_SERVER = cold.READ_SERVER.replace(
    "'nbt':info.GetBlockEntityData(saved['dimension'],target)",
    "'nbt':info.GetBlockEntityData(saved['dimension'],target),"
    "'palette_actor':factory.CreateBlock(api.GetLevelId()).GetBlockPaletteBetweenPos("
    "saved['dimension'],target,target,False).SerializeBlockPalette().get('actor',{})")

# The cold fixture verifies every reserved cell is initially empty. Clear the
# whole reservation so an interrupted glass phase cannot leave its glass behind.
RESTORE_WORLD = cold.RESTORE_WORLD.replace(
    "list(saved['targets'].values())+saved['supports']+[saved['platform']]",
    "saved['reserved']")

PHASES = (
    ('item', 'glass_add', 'glass_added'),
    ('item', 'glass_remove', 'glass_removed_without_pot_rewrite'),
    ('set_block', 'fresh_native', 'before_state_only'),
    ('set_block', 'state_only', 'after_state_only'),
    ('set_block', 'fresh_native', 'before_liquid_air_only'),
    ('set_block', 'liquid_air_only', 'after_liquid_air_only'),
    ('set_block', 'palette_no_extra', 'palette_no_extra'),
    ('set_block', 'palette_extra_air', 'palette_extra_air'),
)


def snapshot(check, report, output, args, key, label, expected=None):
    row = report['controls'][key]
    target = tuple(row['target'])
    stage = cold.capture_stage(check, target, args.offset, label, True)
    row['stages'][label] = stage
    stage['server'] = execute(check.client, READ_SERVER % key)
    stage['client'] = cold.observe(check, cold.READ_CLIENT % (target, expected), args.replication_timeout)
    mask = output.with_name(output.stem+'_'+label+'_body.png')
    stage['body'] = cold.analyze_body(stage, row['empty'], target, mask, args.vertical_fov)
    report['events'].append(label)
    write_json(output, report)
    return stage


def run_probe(check, report, output, args):
    state = check.run(cold.COLD_STATE)
    report['initial_client_state'] = state
    assert state['cold'], state
    report['environment'] = execute(check.client, cold.ENVIRONMENT)
    report['camera_saved'] = check.run(cold.SAVE_CAMERA)
    setup = cold.SETUP.replace('height=min(int(math.floor(foot[1]))+24,300)', 'height='+str(args.fixture_y))
    dx, dz = getattr(args, 'fixture_offset_xz', (8, 8))
    setup = setup.replace('base=(int(math.floor(foot[0]))+8,height,int(math.floor(foot[2]))+8)',
                          'base=(int(math.floor(foot[0]))+(%d),height,int(math.floor(foot[2]))+(%d))' % (dx, dz))
    report['setup'] = execute(check.client, setup)
    report['events'].append('world_reserved')
    time.sleep(args.weather_settle)
    for key in ('item', 'set_block'):
        target = tuple(report['setup']['targets'][key])
        row = {'target': target, 'stages': {}}
        report['controls'][key] = row
        row['empty'] = cold.capture_stage(check, target, args.offset, key+'_empty', True)
    for key, method in (('item', 'PlayerUseItemToPos'), ('set_block', 'SetBlockNew')):
        row = report['controls'][key]
        row['placement'] = execute(check.client, cold.PLACE % (key, method))
        stage = snapshot(check, report, output, args, key, key+'_untouched_native')
        assert row['placement']['returned'] and stage['body']['positive_control_passed'], stage
    for key, operation, label in PHASES:
        report['mutations'].append(execute(check.client, MUTATE % (key, operation)))
        snapshot(check, report, output, args, key, label)
    report['fixture_nbt'] = execute(check.client, cold.WRITE_NBT % ('set_block', SHERDS))
    snapshot(check, report, output, args, 'set_block', 'palette_then_fixture_nbt', SHERDS)
    report['mutations'].append(execute(check.client, MUTATE % ('set_block', 'production_fixture')))
    snapshot(check, report, output, args, 'set_block', 'production_world_adapter_fixture', SHERDS)
    report['completed'] = True
    report['native_positive_controls_passed'] = all(
        row['stages'][key+'_untouched_native']['body']['positive_control_passed']
        for key, row in report['controls'].items())
    report['glass_remove_restored_body'] = report['controls']['item']['stages'][
        'glass_removed_without_pot_rewrite']['body']['positive_control_passed']
    report['passed'] = report['native_positive_controls_passed'] and report['glass_remove_restored_body']


def cleanup(check, report):
    original = cold.RESTORE_WORLD
    cold.RESTORE_WORLD = RESTORE_WORLD
    try:
        cold.cleanup(check, report)
    finally:
        cold.RESTORE_WORLD = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fixture-y', type=int, default=90)
    parser.add_argument('--fixture-offset-xz', type=int, nargs=2, default=(8, 8))
    parser.add_argument('--timeout', type=float, default=30.)
    parser.add_argument('--replication-timeout', type=float, default=6.)
    parser.add_argument('--weather-settle', type=float, default=10.)
    parser.add_argument('--offset', type=float, nargs=3, default=(0.,.4,4.))
    parser.add_argument('--vertical-fov', type=float, default=66.5)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; preserve evidence and choose a new path')
    if not -60 <= args.fixture_y <= 300:
        parser.error('Fixture y must leave room for the support and upper reservation')
    if min(args.timeout, args.replication_timeout) <= 0 or args.weather_settle < 0:
        parser.error('Timeouts must be positive and settle duration nonnegative')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {'schema': 1, 'completed': False, 'passed': False, 'restored': False,
              'controls': {}, 'mutations': [], 'events': [],
              'session_file': os.environ.get('MCDEV_SESSION_FILE'), 'fixture_y': args.fixture_y,
              'fixture_offset_xz': args.fixture_offset_xz,
              'scope': 'Ordered native pot isolation; no projection or editor opening; sherd replication separate',
              'causal_claim': None}
    with Client(timeout=30) as client:
        check = cold.ColdCheck(client, args.output, args.timeout)
        try:
            run_probe(check, report, args.output, args)
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
        finally:
            cleanup(check, report)
            write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'passed': report['passed'],
                      'restored': report['restored'], 'report': str(args.output.resolve())}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
