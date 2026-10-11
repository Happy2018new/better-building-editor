"""Bounded native moss AABB evidence; no mesh or pixel acceptance claim."""
import argparse
import hashlib
import json
import math
import os
import time
from pathlib import Path

from verify_debug_blueprints import BlueprintCheck, Client, write_json
from context_test_environment import run
from _session import desktop_lock, load_session


MARKER = '_native_moss_boxes_r6_saved'
FLAGS = ('_native_pot_fields', '_neighbor_world_saved', '_cold_native_actor_saved',
         '_context_environment_saved', '_blueprint_qa_saved', '_blueprint_visual_saved',
         '_neighbor_visual_options_saved', '_native_sign_probe',
         '_pot_editor_diag_hud_saved', '_pot_editor_diag_model_names',
         '_p0_entity_appearance_selected', '_p0_entity_appearances',
         '_p0_entity_appearance_rows', '_p0_entity_appearance_palettes',
         '_p0_entity_appearance_entities', '_p0_visual_daylight',
         '_native_sign_probe_rows', '_sign_editor_diag_hud_saved',
         '_sign_visual_hud_saved', MARKER)

SIDES = dict(('pale_moss_carpet_side_' + side, 'none')
             for side in ('east', 'north', 'south', 'west'))


def matrix():
    flat = dict(SIDES, upper_block_bit=False)
    wall = dict(flat, pale_moss_carpet_side_east='short')
    rows = []
    for x in (4, 5):
        rows.append(dict(case='pale_moss_carpet_flat_pair', pos=(x, 121, 8),
                         value=('minecraft:pale_moss_carpet', 0), states=flat))
    for z in (8, 9):
        rows.append(dict(case='pale_moss_carpet_wall_pair', pos=(12, 121, z),
                         value=('minecraft:pale_moss_carpet', 8), states=wall))
    for y in (125, 124, 123, 122, 121):
        tip = y == 121
        rows.append(dict(case='hanging_moss', pos=(20, y, 8),
                         value=('minecraft:pale_hanging_moss', int(tip)), states={'tip': tip}))
    supports = [((x, 120, 8), ('minecraft:stone', 0)) for x in (4, 5)]
    supports += [((12, 120, z), ('minecraft:stone', 0)) for z in (8, 9)]
    supports += [((13, 121, z), ('minecraft:stone', 0)) for z in (8, 9)]
    supports += [((20, 126, 8), ('minecraft:stone', 0))]
    return rows, supports


SERVER_READ = '''import json,sys
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
info=factory.CreateBlockInfo(level)
state=factory.CreateBlockState(level)
def observe(positions):
 return [{'pos':pos,'value':info.GetBlockNew(pos,dimension),
  'states':state.GetBlockStates(pos,dimension),'clip':info.GetBlockClip(pos,dimension),
  'collision':info.GetBlockCollision(pos,dimension),
  'collision_all':info.GetBlockCollision(pos,dimension,True)} for pos in positions]
'''

SERVER_BOXES = SERVER_READ + '''_result=json.dumps({'runtime':api.GetMinecraftVersion(),
 'dimension':dimension,'rows':observe(%r)})
'''

RESERVE = SERVER_READ + '''from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR
marker=%r
source=%r
supports=%r
cells=supports+source
adapter=WorldAdapter(player)
reserved=set(tuple(pos[i]+offset[i] for i in range(3)) for pos,value in cells
 for offset in ((0,0,0),(-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1)))
assert not hasattr(sys,marker), 'A previous moss fixture needs cleanup'
for pos in sorted(reserved):
 assert adapter.read(pos)==AIR, ('non-air reserve',pos,adapter.read(pos))
 assert info.GetLiquidBlock(pos,dimension) is None, ('liquid reserve',pos)
saved={'player':player,'dimension':dimension,'cells':cells,'reserved':reserved,
 'player_foot':factory.CreatePos(player).GetFootPos()}
setattr(sys,marker,saved)
for pos,value in cells:assert adapter.write(pos,tuple(value)), ('write failed',pos,value)
_result=json.dumps({'runtime':api.GetMinecraftVersion(),'dimension':dimension,
 'reserved':len(reserved),'reserved_positions':sorted(reserved),
 'all_air_before_write':True,'rows':observe([pos for pos,value in cells])})
'''

CLIENT_BOXES = '''info=b.factory.CreateBlockInfo(b.level)
block=b.factory.CreateBlock(b.level)
positions=%r
rows=[]
for pos in positions:
 palette=block.GetBlockPaletteBetweenPos(pos,pos,False)
 serialized=palette.SerializeBlockPalette() if palette is not None else None
 states=None
 if serialized is not None:
  common=serialized.get('common',{})
  assert len(common)<=1, ('ambiguous native palette',pos,common)
  key=next(iter(common),None)
  states=serialized.get('states',{}).get(key,{}) if key is not None else {}
 rows.append({'pos':pos,'value':info.GetBlock(pos),'states':states,
  'clip':info.GetBlockClip(pos),'collision':info.GetBlockCollision(pos),
  'collision_all':info.GetBlockCollision(pos,True)})
_result=json.dumps({'runtime':api.GetMinecraftVersion(),'rows':rows})
'''

CLEAR = SERVER_READ + '''from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR
marker=%r
saved=getattr(sys,marker,None)
result={'restored':True,'marker_present':saved is not None,'errors':[],'verified_cells':0}
if saved is not None:
 assert saved['player']==player and saved['dimension']==dimension, 'Fixture owner changed'
 adapter=WorldAdapter(saved['player'])
 for pos,value in reversed(saved['cells']):
  try:
   if adapter.read(pos)!=AIR:assert adapter.write(pos,AIR), pos
  except Exception as error:result['errors'].append({'kind':'clear_source','pos':pos,'error':repr(error)})
 for pos in sorted(saved['reserved']):
  try:
   if adapter.read(pos)!=AIR:assert adapter.write(pos,AIR), pos
   assert adapter.read(pos)==AIR and info.GetLiquidBlock(pos,dimension) is None, pos
   result['verified_cells']+=1
  except Exception as error:result['errors'].append({'kind':'clear_verify','pos':pos,'error':repr(error)})
 result['player_foot']=factory.CreatePos(player).GetFootPos()
 result['player_unchanged']=all(abs(result['player_foot'][i]-saved['player_foot'][i])<.01 for i in range(3))
 result['restored']=not result['errors'] and result['player_unchanged']
 if result['restored']:delattr(sys,marker)
_result=json.dumps(result)
'''

CLIENT_STATE = '''_result=json.dumps({'runtime':api.GetMinecraftVersion(),
 'projection_active':s.projection_active,'preparing':bool(b.preparing_entity),
 'projection_actor':b.entity,'projection_actors':len(b.projection_entities),
 'projection_mesh':b.projection_mesh,'busy':s.busy,'edit_job':bool(s.edit_job),
 'io_job':bool(s.io_job),'workspace_open':navigator.contains('modern_projection_workspace'),
 'navigation_transition':navigator.is_transitioning,'player':b.player_position.GetFootPos(),
 'camera':b.factory.CreateCamera(b.level).GetPosition()})
'''


def audit(client, check, flags):
    code = 'import json,sys\n_result=json.dumps(dict((key,hasattr(sys,key)) for key in %r))' % (flags,)
    result = {'server_flags': run(client, code), 'client_flags': check.run(code),
              'server_runtime': run(client, 'import json\nimport mod.server.extraServerApi as api\n_result=json.dumps(api.GetMinecraftVersion())'),
              'client_state': check.run(CLIENT_STATE)}
    state = result['client_state']
    result['clean'] = (not any(result['server_flags'].values()) and
                       not any(result['client_flags'].values()) and
                       not any(state[key] for key in ('projection_active', 'preparing',
                         'projection_actor', 'projection_actors', 'projection_mesh',
                         'busy', 'edit_job', 'io_job', 'workspace_open', 'navigation_transition')))
    return result


def value_pair(value):
    if isinstance(value, dict):
        return value['name'], value['aux']
    assert isinstance(value, (list, tuple)) and len(value) == 2, value
    return tuple(value)


def replicated(snapshot, expected):
    return (len(snapshot['rows']) == len(expected) and
            all(row['value'] is not None and value_pair(row['value']) == expected[tuple(row['pos'])]
                for row in snapshot['rows']))


def box_structure(value):
    if value is None:
        return {'kind': 'none'}
    if isinstance(value, list):
        return {'kind': 'list', 'boxes': [box_structure(item) for item in value]}
    assert isinstance(value, dict), value
    bounds = [value.get(key) for key in ('min', 'max')]
    assert all(isinstance(axes, (tuple, list)) and len(axes) == 3 for axes in bounds), value
    assert all(isinstance(axis, (int, float)) and math.isfinite(axis)
               for axes in bounds for axis in axes), value
    extents = [bounds[1][i] - bounds[0][i] for i in range(3)]
    assert all(extent >= 0 for extent in extents), value
    return {'kind': 'aabb', 'extents': extents, 'zero_extent': any(axis == 0 for axis in extents)}


def verify_snapshots(snapshots, rows, supports):
    expected = {tuple(row['pos']): (tuple(row['value']), row['states']) for row in rows}
    expected.update((tuple(pos), (tuple(value), {})) for pos, value in supports)
    result = {'original_values_exact': True, 'original_states_exact': True,
              'all_boxes_structurally_valid': True, 'observations': []}
    for name, snapshot in snapshots.items():
        observed = {tuple(row['pos']): row for row in snapshot['rows']}
        assert len(snapshot['rows']) == len(observed) and set(observed) == set(expected), name
        for pos, (value, states) in expected.items():
            row = observed[pos]
            assert value_pair(row['value']) == value, (name, pos, value, row)
            assert row['states'] == states, (name, pos, states, row)
            result['observations'].append({'snapshot': name, 'pos': pos,
                'boxes': {kind: box_structure(row[kind])
                          for kind in ('clip', 'collision', 'collision_all')}})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--audit-flag', action='append', default=[])
    args = parser.parse_args()
    os.environ['MCDEV_SESSION_FILE'] = str(args.session.resolve())
    os.environ['MCDEV_OWNER'] = args.owner
    report = {'schema': 1, 'completed': False, 'restored': False, 'background_only': True,
        'preflight_only': args.preflight_only, 'owner': args.owner,
        'session_file': str(args.session.resolve()), 'method': 'Native Clip/Collision observation',
        'limits': 'AABB does not establish mesh topology or pixels; no production proxy accepted.',
        'existing_pixel_threshold': 16, 'existing_min_pixels': 80,
        'desktop_input': False, 'window_activation': False, 'resource_reload': False,
        'player_camera_environment_changes': False,
        'probe_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    rows, supports = matrix()
    source = [(tuple(row['pos']), tuple(row['value'])) for row in rows]
    positions = [pos for pos, value in supports + source]
    report.update(requested=rows, supports=supports)
    try:
        binding = load_session(live=True)
        assert binding is not None and Path(binding['project']).resolve() == args.project.resolve(), 'Project mismatch'
        report['instance'] = {key: binding[key] for key in ('id', 'owner', 'project', 'game_pid',
                             'game_identity', 'mcdk_pid', 'mcdk_identity', 'mcp_url', 'game_executable')}
        with desktop_lock(), Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, 20)
            flags = FLAGS + tuple(args.audit_flag)
            report['preflight'] = audit(client, check, flags)
            assert report['preflight']['clean'], report['preflight']
            assert report['preflight']['server_runtime'] == report['preflight']['client_state']['runtime']
            if args.preflight_only:
                report.update(completed=True, restored=True)
            else:
                try:
                    report['setup'] = run(client, RESERVE % (MARKER, source, supports))
                    report['client_first'] = check.wait('native moss replication',
                        lambda item: replicated(item, dict(supports + source)),
                        lambda: check.run(CLIENT_BOXES % (positions,)))
                    report['server_first'] = run(client, SERVER_BOXES % (positions,))
                    time.sleep(1.0)
                    report['server_later'] = run(client, SERVER_BOXES % (positions,))
                    report['client_later'] = check.run(CLIENT_BOXES % (positions,))
                    snapshots = {key: report[key] for key in ('setup', 'server_first',
                                  'client_first', 'server_later', 'client_later')}
                    report['verification'] = verify_snapshots(snapshots, rows, supports)
                    report['completed'] = True
                except Exception as error:
                    report['error'] = '%s: %s' % (type(error).__name__, error)
                    print(report['error'], flush=True)
                    write_json(args.output, report)
                    raise
                finally:
                    report['cleanup_marker_read'] = run(client,
                        'import sys\n_result=hasattr(sys,%r)' % MARKER)
                    report['cleanup'] = (run(client, CLEAR % (MARKER,))
                        if report['cleanup_marker_read'] else
                        {'restored': True, 'marker_present': False, 'errors': []})
                    report['post_cleanup'] = audit(client, check, flags)
                    report['restored'] = report['cleanup']['restored'] and report['post_cleanup']['clean']
                    if report['restored'] and 'setup' in report:
                        reserved = report['setup']['reserved_positions']
                        final = check.wait('native air replication after cleanup',
                            lambda item: replicated(item, dict((tuple(pos), ('minecraft:air', 0))
                                                              for pos in reserved)),
                            lambda: check.run(CLIENT_BOXES % ([tuple(pos) for pos in reserved],)))
                        report['client_air_after_cleanup'] = final
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
        print(report['error'], flush=True)
    finally:
        write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'error': report.get('error'), 'output': str(args.output.resolve())}), flush=True)
    return 0 if report['completed'] and report['restored'] and 'error' not in report else 1


if __name__ == '__main__':
    raise SystemExit(main())
