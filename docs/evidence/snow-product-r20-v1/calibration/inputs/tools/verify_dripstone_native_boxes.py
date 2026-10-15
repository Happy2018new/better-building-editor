"""Observe native dripstone boxes independently of screenshot alignment."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import verify_neighbor_world_visuals as world
from context_test_environment import run
from verify_debug_blueprints import BlueprintCheck, Client, write_json
from verify_neighbor_native_png import restore_owned_window
from release_owned_game_focus import main as release_focus


SAMPLES = (('world_original', (6, -37, 6)),
           ('world_shifted', (7, -37, 8)),
           ('packed_original_lower', (45, 13, 9)),
           ('packed_original_upper', (45, 16, 9)),
           ('packed_source_shift', (25, 13, 25)))


PRESERVABLE_TERRAIN = tuple('minecraft:' + name for name in (
    'air', 'stone', 'deepslate', 'tuff', 'granite', 'diorite', 'andesite',
    'calcite', 'dripstone_block', 'bedrock', 'basalt', 'smooth_basalt',
    'coal_ore', 'iron_ore', 'copper_ore', 'gold_ore', 'redstone_ore',
    'emerald_ore', 'lapis_ore', 'diamond_ore', 'deepslate_coal_ore',
    'deepslate_iron_ore', 'deepslate_copper_ore', 'deepslate_gold_ore',
    'deepslate_redstone_ore', 'deepslate_emerald_ore', 'deepslate_lapis_ore',
    'deepslate_diamond_ore'))


PRESERVE_NATIVE = '''import copy,json,math,sys
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
terrain_info=factory.CreateBlockInfo(level)
terrain_state=factory.CreateBlockState(level)
terrain_block=factory.CreateBlock(level)
def native_snapshot(pos,dimension):
 palette=terrain_block.GetBlockPaletteBetweenPos(dimension,pos,pos,False)
 assert palette is not None, ('missing palette',pos)
 raw=copy.deepcopy(palette.SerializeBlockPalette())
 assert tuple(raw.get('volume',()))==(1,1,1), ('invalid volume',pos,raw)
 for field in ('common','extra','states','extraStates','actor'):
  assert isinstance(raw.get(field),dict), ('missing native layer',pos,field,raw)
 return {'pos':pos,'front':terrain_info.GetBlockNew(pos,dimension),
  'liquid':terrain_info.GetLiquidBlock(pos,dimension),
  'states':terrain_state.GetBlockStates(pos,dimension),
  'entity_nbt':terrain_info.GetBlockEntityData(dimension,pos),'palette':raw}
def tagged(value):
 if isinstance(value,dict):
  return {'type':'dict','items':[[tagged(k),tagged(v)] for k,v in sorted(value.items(),key=lambda item:repr(item[0]))]}
 if isinstance(value,(tuple,list)):
  return {'type':'tuple' if isinstance(value,tuple) else 'list','items':[tagged(v) for v in value]}
 if isinstance(value,bytes):return {'type':'bytes','value':value.decode('utf8')}
 if value is None or isinstance(value,(bool,int,float,str)):
  return {'type':type(value).__name__,'value':value}
 try:
  if isinstance(value,(unicode,long)):return {'type':type(value).__name__,'value':value}
 except NameError:pass
 raise TypeError('Unsupported native snapshot type: '+repr(type(value)))
def palette_layers(row):
 return dict((field,row['palette'][field])
             for field in ('volume','common','extra','states','extraStates','actor'))
def equal_snapshot(before,after):
 return (all(before[field]==after[field] for field in ('pos','front','liquid','states','entity_nbt'))
         and palette_layers(before)==palette_layers(after))
'''


RESERVE_PRESERVED = PRESERVE_NATIVE + '''player=api.GetPlayerList()[0]
adapter=WorldAdapter(player)
source=%r
supports=%r
near_source=%r
allowed=%r
cells=supports+source
offsets=((0,0,0),(-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1))
lo=tuple(min(pos[i] for pos,value in near_source) for i in range(3))
platform=(lo[0]-4,lo[1]-1,lo[2]-4)
reserved=set(tuple(pos[i]+offset[i] for i in range(3))
             for pos,value in cells+[(platform,('minecraft:stone',0))] for offset in offsets)
# The unchanged outer ring excludes fluids, falling blocks and connected actors.
guard=set(tuple(pos[i]+offset[i] for i in range(3))
          for pos in reserved for offset in offsets)-reserved
assert not hasattr(sys,'_neighbor_world_saved')
snapshots=[]
for pos in sorted(reserved|guard):
 row=native_snapshot(pos,adapter.dimension)
 front=row['front']
 assert isinstance(front,dict) and front.get('name') in allowed, ('unsupported terrain',pos,row)
 assert row['liquid'] is None, ('liquid terrain',pos,row)
 assert row['entity_nbt'] is None and not row['palette']['actor'], ('actor terrain',pos,row)
 assert isinstance(row['states'],dict) or (front['name']=='minecraft:air' and row['states'] is None), ('missing states',pos,row)
 common=row['palette']['common']
 assert len(common)==1, ('ambiguous common layer',pos,row)
 key=next(iter(common))
 assert key[0] in (front['name'],front['name'].encode('utf8')) and common[key]==[0], ('inconsistent common layer',pos,row)
 assert row['palette']['states'].get(key,{})==(row['states'] or {}), ('inconsistent native states',pos,row)
 assert all(key[0] in ('minecraft:air',b'minecraft:air') for key in row['palette']['extra']), ('extra layer',pos,row)
 assert all(key[0] in ('minecraft:air',b'minecraft:air') and not value
            for key,value in row['palette']['extraStates'].items()), ('extra states',pos,row)
 restored=terrain_block.GetBlankBlockPalette()
 assert restored is not None and restored.DeserializeBlockPalette(copy.deepcopy(row['palette'])), ('invalid restore palette',pos)
 assert restored.SerializeBlockPalette()==row['palette'], ('lossy restore palette',pos)
 tagged(row)
 snapshots.append(row)
foot=factory.CreatePos(player).GetFootPos()
assert isinstance(foot,(tuple,list)) and len(foot)==3 and all(not math.isnan(axis) and not math.isinf(axis) for axis in foot), foot
for row in snapshots:
 assert equal_snapshot(row,native_snapshot(row['pos'],adapter.dimension)), ('terrain changed before fixture',row['pos'])
saved={'player':player,'dimension':adapter.dimension,'cells':cells,'reserved':reserved,
 'guard':guard,'snapshots':snapshots,'platform':platform,'player_foot':foot,'preserve_terrain':True}
sys._neighbor_world_saved=saved
for pos in sorted(reserved):
 if adapter.read(pos)!=AIR:assert adapter.write(pos,AIR), ('clear terrain',pos)
for pos,value in cells+[(platform,('minecraft:stone',0))]:
 assert adapter.write(pos,tuple(value)), (pos,value)
actual=[(pos,adapter.read(pos)) for pos,value in cells]
for (pos,value),(actual_pos,observed) in zip(cells,actual):
 assert observed is not None and observed[0]==value[0], (pos,value,observed)
_result=json.dumps({'cells':len(cells),'reserved':len(reserved),'guard':len(guard),
 'verified':True,'actual':actual,'platform':platform,'preserve_terrain':True,
 'snapshots':tagged(snapshots),'all_preflight_reads_before_write':True})
'''


NEAR_PRESERVED_PLAYER = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._neighbor_world_saved
assert saved['preserve_terrain']
platform=saved['platform']
point=(platform[0]+.5,platform[1]+1.,platform[2]+.5)
assert api.GetEngineCompFactory().CreatePos(saved['player']).SetFootPos(point)
_result=json.dumps({'before':saved['player_foot'],'after':point,'platform':platform})
'''


REPLICATION_PRESERVED = '''cells=%r
info=b.factory.CreateBlockInfo(b.level)
actual=[]
for pos,value in cells:
 observed=info.GetBlock(tuple(pos))
 actual.append((pos,tuple(observed)) if observed else (pos,None))
_result=json.dumps({'matches':actual==cells,'cells':actual,
 'method':'individual fixed fixture cells; surrounding saved terrain retained'})
'''


CLEAR_PRESERVED = PRESERVE_NATIVE + '''saved=getattr(sys,'_neighbor_world_saved',None)
result={'restored':True,'player_foot':None,'preserve_terrain':True,'errors':[],'verified_cells':0}
if saved is not None:
 assert saved.get('preserve_terrain'), 'Refuse to clear an unrelated fixture'
 result['player_foot']=saved['player_foot']
 try:
  assert factory.CreatePos(saved['player']).SetFootPos(tuple(saved['player_foot']))
 except Exception as error:result['errors'].append({'kind':'player_restore','error':repr(error)})
 for row in reversed(saved['snapshots']):
  pos=row['pos']
  try:
   if equal_snapshot(row,native_snapshot(pos,saved['dimension'])):continue
   palette=terrain_block.GetBlankBlockPalette()
   assert palette is not None and palette.DeserializeBlockPalette(copy.deepcopy(row['palette']))
   assert terrain_block.SetBlockByBlockPalette(palette,saved['dimension'],pos,0,0)
  except Exception as error:result['errors'].append({'kind':'cell_restore','pos':pos,'error':repr(error)})
 for row in saved['snapshots']:
  try:
   observed=native_snapshot(row['pos'],saved['dimension'])
   assert equal_snapshot(row,observed), ('restore mismatch',tagged(row),tagged(observed))
   result['verified_cells']+=1
  except Exception as error:result['errors'].append({'kind':'restore_verify','pos':row['pos'],'error':repr(error)})
 result['restored']=not result['errors']
 result['snapshot_retained_for_retry']=not result['restored']
 if result['restored']:del sys._neighbor_world_saved
_result=json.dumps(result)
'''


def holdout_samples():
    coordinates = (-33, -32, -31, -17, -16, -15, -1, 0, 1, 15, 16, 17, 31, 32, 33)
    positions = sorted(set([(value, 6) for value in coordinates] +
                           [(6, value) for value in coordinates] +
                           list(zip(coordinates, reversed(coordinates))) + [(6, 6)]))
    return tuple(('holdout_%d_%d_y%d' % (x, z, y), (x, y, z))
                 for x, z in positions for y in (-47, -31))


def matrix(source_samples=SAMPLES):
    cells, supports, samples = {}, {}, []
    for identity, root in source_samples:
        positions = (root, (root[0], root[1] + 1, root[2]))
        for pos, aux in zip(positions, (4, 12)):
            cells[pos] = ('minecraft:pointed_dripstone', aux)
            samples.append({'case': identity, 'pos': pos, 'expected_aux': aux})
        for y in (root[1] - 1, root[1] + 2):
            supports[(root[0], y, root[2])] = ('minecraft:stone', 0)
    assert not set(cells).intersection(supports)
    return sorted(cells.items()), sorted(supports.items()), samples


def verify_scene_boxes(server, client, expected):
    server_rows = dict((tuple(row['pos']), row) for row in server['rows'])
    client_rows = dict((tuple(row['pos']), row) for row in client['rows'])
    assert len(server_rows) == len(server['rows']), 'Duplicate server positions'
    assert len(client_rows) == len(client['rows']), 'Duplicate client positions'
    assert set(server_rows) == set(client_rows) == set(expected)
    for pos, value in expected.items():
        first, second = server_rows[pos], client_rows[pos]
        assert isinstance(first['value'], dict), first
        assert (first['value'].get('name'), first['value'].get('aux')) == value, first
        assert isinstance(second['value'], (tuple, list)) and len(second['value']) == 2, second
        assert tuple(second['value']) == value, second
        for row in (first, second):
            for kind in ('clip', 'collision'):
                box = row[kind]
                assert isinstance(box, dict), (pos, kind, box)
                for bound in ('min', 'max'):
                    axes = box.get(bound)
                    assert isinstance(axes, (tuple, list)) and len(axes) == 3, (pos, kind, box)
                    assert all(isinstance(axis, (int, float)) and math.isfinite(axis) for axis in axes), (pos, kind, box)
                assert all(box['min'][axis] < box['max'][axis] for axis in range(3)), (pos, kind, box)
        assert first['clip'] == first['collision'] == second['clip'] == second['collision'], (first, second)
        if value[0] == 'minecraft:stone':
            assert tuple(first['clip']['min']) == pos, first
            assert tuple(first['clip']['max']) == tuple(axis + 1 for axis in pos), first
    return {'all_values_equal': True, 'all_boxes_valid': True,
            'all_box_methods_equal': True, 'stone_unit_boxes': True,
            'cells': len(expected)}


SERVER_BOXES = '''import json
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
dimension=factory.CreateDimension(api.GetPlayerList()[0]).GetEntityDimensionId()
info=factory.CreateBlockInfo(level)
state=factory.CreateBlockState(level)
positions=%r
rows=[{'pos':pos,'value':info.GetBlockNew(pos,dimension),
 'states':state.GetBlockStates(pos,dimension),
 'clip':info.GetBlockClip(pos,dimension),'collision':info.GetBlockCollision(pos,dimension)}
 for pos in positions]
_result=json.dumps({'runtime':api.GetMinecraftVersion(),'dimension':dimension,'rows':rows})
'''

CLIENT_BOXES = '''import json
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
info=factory.CreateBlockInfo(level)
positions=%r
rows=[{'pos':pos,'value':info.GetBlock(pos),'clip':info.GetBlockClip(pos),
 'collision':info.GetBlockCollision(pos)} for pos in positions]
low=tuple(min(pos[i] for pos in positions) for i in range(3))
high=tuple(max(pos[i] for pos in positions) for i in range(3))
palette=factory.CreateBlock(level).GetBlockPaletteBetweenPos(low,high,False)
assert palette is not None
serialized=palette.SerializeBlockPalette()
header=dict((key,value) for key,value in serialized.items()
 if key not in ('common','extra','actor','states','extraStates'))
_result=json.dumps({'runtime':api.GetMinecraftVersion(),'rows':rows,'native_palette_header':header})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--holdout', action='store_true',
                        help='Independent signed-coordinate, axis and chunk-boundary matrix')
    parser.add_argument('--preserve-terrain', action='store_true',
                        help='Snapshot and verify restoration of ordinary solid terrain at the fixed coordinates')
    parser.add_argument('--background-only', action='store_true', default=True,
                        help='Use only SDK observation without activating or releasing game focus')
    args = parser.parse_args()
    from _session import load_session
    report = {'schema': 1, 'completed': False, 'restored': False,
              'background_only': args.background_only,
              'preserve_terrain': args.preserve_terrain,
              'session_file': os.environ.get('MCDEV_SESSION_FILE'),
              'owner': os.environ.get('MCDEV_OWNER'),
              'method': 'Documented native GetBlockClip/GetBlockCollision at independent coordinates',
              'limits': 'Diagnostic raw boxes only; no fitted image offsets or production rule.'}
    source_path = Path(__file__).resolve()
    report['probe_source_sha256'] = hashlib.sha256(source_path.read_bytes()).hexdigest()
    reference = source_path.parent / 'data/native_dripstone_boxes_r5.json'
    if reference.is_file():
        report['native_aabb_reference'] = {'path': str(reference),
                                         'sha256': hashlib.sha256(reference.read_bytes()).hexdigest()}
    cells, supports, samples = matrix(holdout_samples() if args.holdout else SAMPLES)
    report.update(samples=samples, cells=cells, supports=supports)
    report['sampling_plan'] = ('signed-axis/chunk-boundary holdout; fixed before new native observations'
                               if args.holdout else 'original world/source/packed controls')
    try:
        report['owned_window_activation'] = restore_owned_window(load_session(live=True), args.background_only)
        with Client(timeout=90 if args.preserve_terrain else 30) as client:
            check = BlueprintCheck(client, args.output, 90)
            try:
                near_cells = ([((0, -47, 0), ('minecraft:air', 0))] if args.holdout else cells)
                reserve = (RESERVE_PRESERVED % (cells, supports, near_cells, PRESERVABLE_TERRAIN)
                           if args.preserve_terrain else world.RESERVE % (cells, supports))
                report['world_setup'] = run(client, reserve)
                near = NEAR_PRESERVED_PLAYER if args.preserve_terrain else world.NEAR_PLAYER % (near_cells,)
                report['near_player'] = run(client, near)
                report['near_player']['client'] = world.player_ready(check, report['near_player']['after'])
                report['replication'] = (check.wait('client fixture cell replication',
                    lambda value: value['matches'],
                    lambda: check.run(REPLICATION_PRESERVED % (cells + supports,)))
                    if args.preserve_terrain else world.replication(check, cells + supports, False))
                positions = [pos for pos, value in cells + supports]
                report['server'] = run(client, SERVER_BOXES % (positions,))
                report['client'] = check.run(CLIENT_BOXES % (positions,))
                report['seed'] = run(client, 'import mod.server.extraServerApi as api\n'
                    '_result=api.GetEngineCompFactory().CreateGame(api.GetLevelId()).GetSeed()')
                expected = dict(cells + supports)
                report['scene_verification'] = verify_scene_boxes(report['server'], report['client'], expected)
                report['all_box_methods_equal'] = report['scene_verification']['all_box_methods_equal']
                report['completed'] = True
            finally:
                report['cleanup'] = (run(client, CLEAR_PRESERVED) if args.preserve_terrain
                                     else world.clear_world(client))
                if report['cleanup']['player_foot'] is not None:
                    world.player_ready(check, report['cleanup']['player_foot'])
                report['restored'] = report['cleanup']['restored']
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        try:
            report['owned_focus_release'] = ({'background_only': True, 'focus_unchanged': True}
                                            if args.background_only else release_focus())
        except Exception as error:
            report['owned_focus_release'] = {'error': '%s: %s' % (type(error).__name__, error)}
        write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'samples': len(samples), 'cells': report['scene_verification']['cells'],
                      'all_box_methods_equal': report['all_box_methods_equal'],
                      'report': str(args.output.resolve())}))
    return 0 if (report['completed'] and report['restored'] and
                 'error' not in report['owned_focus_release']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
