"""Capture bounded native shape evidence without invoking state transforms.

Requires an explicitly assigned, owner-bound MCDK session. No desktop input,
camera, player, settings, resources, drafts or building-library changes occur.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from projection import block_registry as registry
from mcdk import Client, return_value
from _session import load_session

MARKER = '_native_state_shapes_r11_saved'
DEFAULT_NAMES = ('minecraft:oak_stairs', 'minecraft:wooden_door', 'minecraft:trapdoor')


def rays():
    result = []
    for axis in (0, 2):
        transverse = 2 if axis == 0 else 0
        for height in (.25, .75):
            for cross in (.25, .75):
                for sign in (-1, 1):
                    start = [.5, height, .5]
                    start[axis] = 1.25 if sign == -1 else -.25
                    start[transverse] = cross
                    direction = [0, 0, 0]
                    direction[axis] = sign
                    result.append({'start': start, 'direction': direction, 'distance': 2})
    return result


def matrix(names, origin):
    rows, supports = [], {}
    index = 0
    for name in names:
        values = [(name, aux) for aux in registry.aux_values(name)]
        if not values:
            raise ValueError('Native name has no palette records: %s' % name)
        for value in values:
            states = registry.states(value)
            if states.get('upper_block_bit') is True:
                continue
            pos = (origin[0] + index % 8 * 4, origin[1], origin[2] + index // 8 * 4)
            rows.append({'pos': pos, 'value': value, 'states': states, 'control': False})
            supports[(pos[0], pos[1] - 1, pos[2])] = ('minecraft:stone', 0)
            if 'door_hinge_bit' in states:
                upper_states = dict(states, upper_block_bit=True)
                upper = registry.from_states(name, upper_states)
                if upper is None:
                    raise ValueError('Door has no matching upper state: %r' % (value,))
                rows.append({'pos': (pos[0], pos[1] + 1, pos[2]), 'value': upper,
                             'states': upper_states, 'control': False})
            index += 1
    for name in ('minecraft:stone', 'minecraft:air'):
        pos = (origin[0] + index % 8 * 4, origin[1], origin[2] + index // 8 * 4)
        value = (name, 0)
        rows.append({'pos': pos, 'value': value, 'states': registry.states(value) or {}, 'control': True})
        index += 1
    return rows, sorted(supports.items())


def reserve_positions(rows, supports):
    cells = supports + [(tuple(row['pos']), tuple(row['value'])) for row in rows]
    return sorted({tuple(pos[i] + offset[i] for i in range(3)) for pos, value in cells
                   for offset in ((0, 0, 0), (-1, 0, 0), (1, 0, 0), (0, -1, 0),
                                  (0, 1, 0), (0, 0, -1), (0, 0, 1))})


def door_pair_palettes(rows):
    positions = {tuple(row['pos']): row for row in rows}
    result = []
    for row in rows:
        states = row['states']
        if 'door_hinge_bit' not in states or states['upper_block_bit']:
            continue
        pos = tuple(row['pos'])
        upper = positions.get((pos[0], pos[1] + 1, pos[2]))
        if (upper is None or upper['value'][0] != row['value'][0] or
                not states_exact(upper['states'], dict(states, upper_block_bit=True))):
            raise ValueError('Native door fixture needs an exact matching upper half')
        common, records = {}, {}
        for index, part in enumerate((row, upper)):
            value = tuple(part['value'])
            common[value] = [index]
            records[value] = part['states']
        result.append((pos, {'volume': (1, 1, 2), 'common': common, 'states': records,
                             'extra': {}, 'extraStates': {}, 'actor': {},
                             'void': False, 'eliminateAir': False}))
    return result


WRITE_CELLS = '''reused=[]
for pos,value in cells:
 expected=adapter._native_tree(registry.states(value) or {})
 actual=state.GetBlockStates(pos,dimension) or {}
 exact=(
  sorted((key,type(item).__name__,item) for key,item in actual.items())==
  sorted((key,type(item).__name__,item) for key,item in expected.items()))
 if adapter.read(pos)==value and exact:
  reused.append(pos)
 else:
  assert adapter.write(pos,value), ('write failed',pos,value)
'''


SERVER_BASE = '''import json,sys
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
players=api.GetPlayerList()
assert len(players)==1, 'Use an owned single-player fixture'
player=players[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
info=factory.CreateBlockInfo(level)
state=factory.CreateBlockState(level)
'''

PREFLIGHT = SERVER_BASE + '''import math
assert not hasattr(sys,%r), 'Previous native transform fixture needs cleanup'
foot=factory.CreatePos(player).GetFootPos()
origin=tuple(int(math.floor(foot[i]))+(4,12,4)[i] for i in range(3))
_result=json.dumps({'runtime':api.GetMinecraftVersion(),'foot':foot,'origin':origin,
 'dimension':dimension})
'''

RESERVE = SERVER_BASE + '''from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR
from modern_projection.projection import block_registry as registry
marker=%r
rows=%r
supports=%r
paired_palettes=%r
adapter=WorldAdapter(player)
cells=supports+[(tuple(row['pos']),tuple(row['value'])) for row in rows]
reserved=set(tuple(pos[i]+offset[i] for i in range(3)) for pos,value in cells
 for offset in ((0,0,0),(-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1)))
assert not hasattr(sys,marker), 'Previous native transform fixture needs cleanup'
for pos in sorted(reserved):
 assert adapter.read(pos)==AIR, ('non-air reserve',pos,adapter.read(pos))
 assert info.GetLiquidBlock(pos,dimension) is None, ('liquid reserve',pos)
saved={'player':player,'dimension':dimension,'cells':cells,'reserved':reserved,
 'foot':factory.CreatePos(player).GetFootPos()}
setattr(sys,marker,saved)
for pos,value in supports:
 assert adapter.write(pos,value), ('support write failed',pos,value)
for pos,data in paired_palettes:
 palette=adapter.palette_block.GetBlankBlockPalette()
 assert palette is not None and palette.DeserializeBlockPalette(adapter._native_tree(data)), ('invalid door pair',pos)
 assert adapter.palette_block.SetBlockByBlockPalette(palette,dimension,pos,0,0), ('door pair write failed',pos)
''' + WRITE_CELLS + '''
_result=json.dumps({'all_air_before_write':True,'reserved':sorted(reserved),
 'planned_cells':len(cells),'single_cell_writes':len(supports)+len(cells)-len(reused),
 'pair_palette_writes':len(paired_palettes),'reused_exact_cells':reused,
 'runtime':api.GetMinecraftVersion()})
'''

OBSERVE = '''rows=%r
rays=%r
observed=[]
for source in rows:
 pos=tuple(source['pos'])
 hits=[]
 for ray in rays:
  start=tuple(pos[i]+ray['start'][i] for i in range(3))
  direction=tuple(ray['direction'])
  found=cast(start,direction,ray['distance'])
  hits.append(found)
 observed.append({'pos':pos,'value':value_at(pos),'states':states_at(pos),
  'clip':clip_at(pos),'collision':collision_at(pos),'rays':hits})
_result=json.dumps({'runtime':api.GetMinecraftVersion(),'rows':observed})
'''

SERVER_OBSERVE = SERVER_BASE + '''def cast(start,direction,distance):
 return api.getEntitiesOrBlockFromRay(dimension,start,direction,distance,False,
  api.GetMinecraftEnum().RayFilterType.OnlyBlocks)
def value_at(pos):return info.GetBlockNew(pos,dimension)
def states_at(pos):return state.GetBlockStates(pos,dimension)
def clip_at(pos):return info.GetBlockClip(pos,dimension)
def collision_at(pos):return info.GetBlockCollision(pos,dimension)
''' + OBSERVE

CLIENT_OBSERVE = '''import json
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
info=factory.CreateBlockInfo(level)
block=factory.CreateBlock(level)
def cast(start,direction,distance):
 return api.getEntitiesOrBlockFromRay(start,direction,distance,False,
  api.GetMinecraftEnum().RayFilterType.OnlyBlocks)
def value_at(pos):return info.GetBlock(pos)
def states_at(pos):
 palette=block.GetBlockPaletteBetweenPos(pos,pos,False)
 assert palette is not None, ('native palette unavailable',pos)
 data=palette.SerializeBlockPalette()
 common=data.get('common',{})
 assert len(common)<=1, ('ambiguous native palette',pos)
 key=next(iter(common),None)
 return data.get('states',{}).get(key,{}) if key is not None else {}
def clip_at(pos):return info.GetBlockClip(pos)
def collision_at(pos):return info.GetBlockCollision(pos)
''' + OBSERVE

CLEAR = SERVER_BASE + '''from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR
marker=%r
saved=getattr(sys,marker,None)
result={'restored':True,'marker_present':saved is not None,'errors':[]}
if saved is not None:
 assert saved['player']==player and saved['dimension']==dimension, 'Fixture owner changed'
 adapter=WorldAdapter(player)
 for pos,value in reversed(saved['cells']):
  if adapter.read(pos)!=AIR:
   if not adapter.write(pos,AIR):result['errors'].append(['clear',pos])
 for pos in sorted(saved['reserved']):
  if adapter.read(pos)!=AIR:adapter.write(pos,AIR)
  if adapter.read(pos)!=AIR or info.GetLiquidBlock(pos,dimension) is not None:
   result['errors'].append(['residue',pos])
 foot=factory.CreatePos(player).GetFootPos()
 result['player_unchanged']=all(abs(foot[i]-saved['foot'][i])<.01 for i in range(3))
 result['restored']=not result['errors'] and result['player_unchanged']
 if result['restored']:delattr(sys,marker)
_result=json.dumps(result)
'''


def execute(client, code, server):
    response = client.call('execute_code', {'code': code, 'is_client': not server,
                                           'direct_return': True})
    if response.get('isError'):
        raise RuntimeError(response)
    value = return_value(response)
    return json.loads(value) if isinstance(value, str) else value


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


def pair(value):
    if isinstance(value, dict):
        return value.get('name'), value.get('aux')
    return tuple(value) if isinstance(value, (tuple, list)) else None


def states_exact(first, second):
    if first is None:
        first = {}
    if second is None:
        second = {}
    return (isinstance(first, dict) and isinstance(second, dict) and
            sorted((key, type(value).__name__, value) for key, value in first.items()) ==
            sorted((key, type(value).__name__, value) for key, value in second.items()))


def replicated(snapshot, requested):
    observed = {tuple(row['pos']): row for row in snapshot['rows']}
    return (len(observed) == len(snapshot['rows']) == len(requested) and
            all(tuple(row['pos']) in observed and
                pair(observed[tuple(row['pos'])]['value']) == tuple(row['value']) and
                states_exact(observed[tuple(row['pos'])]['states'], row['states'])
                for row in requested))


def capture(output, session, owner, names):
    if output.exists():
        raise ValueError('Native evidence requires a fresh output path')
    os.environ.update(MCDEV_SESSION_FILE=str(session.resolve()), MCDEV_OWNER=owner)
    binding = load_session(live=True)
    if Path(binding['project']).resolve() != ROOT:
        raise ValueError('Session belongs to a different project')
    report = {'schema': 1, 'completed': False, 'restored': False,
              'background_only': True, 'desktop_input': False,
              'player_camera_environment_changes': False,
              'game_version': registry.source_version(), 'palette_sha256': registry.fingerprint(),
              'probe_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'instance': {key: binding[key] for key in ('id', 'owner', 'project', 'game_pid',
                          'game_identity', 'mcp_url', 'game_executable')},
              'names': names, 'rays': rays(),
              'limits': 'Raw native clip/collision/rays only; degenerate bounds are not occupancy proof.'}
    write(output, report)
    pending = False
    with Client(timeout=30) as client:
        try:
            report['preflight'] = execute(client, PREFLIGHT % MARKER, True)
            requested, supports = matrix(names, tuple(report['preflight']['origin']))
            if len(requested) > 130:
                raise ValueError('Capture is limited to 128 native records plus two controls')
            report.update(requested=requested, supports=supports,
                          reserved=reserve_positions(requested, supports))
            write(output, report)
            pending = True
            paired_palettes = door_pair_palettes(requested)
            report['setup'] = execute(client, RESERVE % (MARKER, requested, supports, paired_palettes), True)
            write(output, report)
            server_code = SERVER_OBSERVE % (requested, report['rays'])
            client_code = CLIENT_OBSERVE % (requested, report['rays'])
            report['server_first'] = execute(client, server_code, True)
            deadline = time.monotonic() + 20.
            while True:
                report['client_first'] = execute(client, client_code, False)
                if replicated(report['client_first'], requested):
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError('Native client states did not replicate exactly')
                time.sleep(.2)
            time.sleep(1.)
            report['server_later'] = execute(client, server_code, True)
            report['client_later'] = execute(client, client_code, False)
            snapshots = [report[key] for key in ('server_first', 'client_first',
                                                 'server_later', 'client_later')]
            if not all(replicated(snapshot, requested) for snapshot in snapshots):
                raise RuntimeError('Native states changed across time or side')
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
        finally:
            try:
                report['cleanup'] = (execute(client, CLEAR % MARKER, True) if pending else
                                     {'restored': True, 'marker_present': False, 'mutation_attempted': False})
                report['restored'] = report['cleanup']['restored']
                if report['restored'] and pending:
                    positions = report['reserved']
                    code = ('import json\nimport mod.client.extraClientApi as api\n'
                            'info=api.GetEngineCompFactory().CreateBlockInfo(api.GetLevelId())\n'
                            '_result=json.dumps([{\'pos\':pos,\'value\':info.GetBlock(tuple(pos))}'
                            ' for pos in %r])' % positions)
                    deadline = time.monotonic() + 20.
                    while True:
                        report['client_air_after_cleanup'] = execute(client, code, False)
                        if all(pair(row['value']) == ('minecraft:air', 0)
                               for row in report['client_air_after_cleanup']):
                            break
                        if time.monotonic() >= deadline:
                            raise RuntimeError('Native client cleanup did not replicate')
                        time.sleep(.2)
            except Exception as error:
                report['cleanup_error'] = '%s: %s' % (type(error).__name__, error)
                report['restored'] = False
            write(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--name', action='append', help='Native name; repeat to select bounded families')
    args = parser.parse_args()
    names = tuple(args.name or DEFAULT_NAMES)
    if len(names) > 4 or len(set(names)) != len(names):
        parser.error('Use one to four distinct native names per capture')
    report = capture(args.output, args.session, args.owner, names)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'error': report.get('error'), 'output': str(args.output.resolve())}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
