"""Capture native/candidate shelf artwork with matched, restored world state."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

import probe_liquid_pose_channel as native
import probe_native_palette_body_r16 as body
from generate_shelf_resources_r17 import FRONTS, WOODS
from probe_product_water import snapshot_sources
from probe_shelf_native_shape_r17 import READ_WORLD, VIEWS


INITIALIZE = '''saved=sys._liquid_pose_client
saved['paths']=[]
saved['namespace']=%r
saved['entity']=api.GetSystem('ModernProjection','ModernProjectionClientSystem').CreateClientEntityByTypeStr(
 'modern_projection:anchor',tuple(saved['origin']),(0.,0.))
assert saved['entity']
factory.CreateModel(saved['entity']).SetEntityShadowShow(False)
_result=True
'''
PLACE = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
material=%r
changed=info.SetBlockNew(tuple(saved['origin']),material,0,saved['dimension'],True,False)
actual=info.GetBlockNew(tuple(saved['origin']),saved['dimension'])
assert actual==material,(actual,material,changed)
_result=json.dumps({'changed':changed,'placed':actual,
 'nbt':info.GetBlockEntityData(saved['dimension'],tuple(saved['origin']))})
'''
PROXY = '''saved=sys._liquid_pose_client
identifier,material_aux=%r
path_key=identifier+'__aux'+str(material_aux)
block=factory.CreateBlock(level)
palette=block.GetBlockPaletteBetweenPos(tuple(saved['origin']),tuple(saved['origin']),False)
raw=palette.SerializeBlockPalette()
assert tuple(raw['volume'])==(1,1,1)
raw['common']={(identifier,material_aux):[0]}
raw['extra']={}
raw['actor']={}
assert palette.DeserializeBlockPalette(raw)
name=saved['namespace']+'_'+path_key.split(':')[-1]
result=factory.CreateBlockGeometry(level).CombineBlockPaletteToGeometry(palette,name,0)
assert result is not None
saved['paths'].append({'path':path_key,'requested':name,'returned':result})
_result={'identifier':identifier,'path':saved['paths'][-1],'serialized':repr(raw)}
'''
DETACH = '''saved=sys._liquid_pose_client
if saved['attached'] is not None:
 assert factory.CreateActorRender(saved['entity']).DeleteActorBlockGeometry(saved['attached'])
 saved['attached']=None
_result=True
'''
STATES = '''import json
import mod.server.extraServerApi as api
state=api.GetEngineCompFactory().CreateBlockState(api.GetLevelId())
_result=json.dumps(state.GetBlockStatesFromAuxValue(%r,%r))
'''
PLACE_STATES = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
state=api.GetEngineCompFactory().CreateBlockState(api.GetLevelId())
requested=%r
changed=state.SetBlockStates(tuple(saved['origin']),requested,saved['dimension'])
_result=json.dumps({'changed':changed,'requested':requested,
 'actual':state.GetBlockStates(tuple(saved['origin']),saved['dimension'])})
'''


def matrix_cases(matrix):
    if matrix == 'roles':
        return [('oak', aux, 'south', FRONTS) for aux in range(4, 8)]
    if matrix == 'woods':
        return [(wood, 0, 'south', ('unpowered',)) for wood in WOODS]
    return [('oak', aux, direction, ('unpowered',))
            for aux, direction in ((0, 'south'), (8, 'west'), (16, 'north'), (24, 'east'))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--matrix', choices=('roles', 'woods', 'directions'), required=True)
    parser.add_argument('--aux', type=int, help='Restrict role observations to one installed aux state')
    parser.add_argument('--set-states', action='store_true')
    parser.add_argument('--compare-ao', action='store_true', help='Also capture installed _ao controls')
    parser.add_argument('--compare-engine-direction', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh diagnostic directory')
    session = json.loads(args.session.read_bytes())
    if session['owner'] != args.owner:
        parser.error('Use the owner-bound diagnostic instance')
    os.environ.update(MCDEV_SESSION_FILE=str(args.session.resolve()), MCDEV_OWNER=args.owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    project = Path(session['project'])
    sources = snapshot_sources(project)
    report = {'schema_version': 1, 'matrix': args.matrix, 'completed': False,
              'restored': False, 'production_qualified': False, 'cleanup_errors': [],
              'captures': {}, 'cases': [], 'source_sha256': sources,
              'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'session': {key: session[key] for key in ('id', 'owner', 'game_pid', 'game_identity')}}
    args.output.mkdir(parents=True)
    host_snapshot = args.output / 'host_sources'
    host_snapshot.mkdir()
    for module in (Path(__file__), Path(native.__file__), Path(body.__file__)):
        (host_snapshot / module.name).write_bytes(module.read_bytes())

    def persist():
        native.write(args.output / 'report.json', report)

    with native.Client(timeout=40) as client:
        world = saved = environment = workspace_saved = False
        try:
            report['workspace'] = native.run(client, body.CLOSE_WORKSPACE)
            workspace_saved = True
            deadline = time.monotonic() + 10.
            while not native.run(client, body.WORLD_VISIBLE):
                if time.monotonic() >= deadline:
                    raise RuntimeError('Workspace did not close before shelf measurement')
                time.sleep(.2)
            report['environment'] = native.run(client, native.ENVIRONMENT, True)
            environment = True
            report['world'] = native.run(client, body.PREPARE % 'minecraft:oak_shelf', True)
            world = True
            origin = tuple(report['world']['origin'])
            report['near_player'] = native.run(client, native.NEAR_PLAYER, True)
            native.run(client, native.SAVE % (origin,))
            saved = True
            native.run(client, INITIALIZE % ('shelf_matrix_' + uuid.uuid4().hex))

            def wait_for(material):
                deadline = time.monotonic() + 15.
                while True:
                    actual = native.run(client, READ_WORLD, True)
                    replicated = native.run(client, native.REPLICATION % (origin,))
                    if actual == material and any(
                            row['name'] == material['name'] and row['aux'] == material['aux']
                            for row in replicated['materials']):
                        return {'actual': actual, 'replicated': replicated}
                    if time.monotonic() >= deadline:
                        report['replication_failure'] = {'requested': material, 'actual': actual,
                                                         'replicated': replicated}
                        persist()
                        raise RuntimeError('Shelf material did not settle and replicate: ' + repr(material))
                    time.sleep(.2)

            def frame(label, case):
                if not native.run(client, body.WORLD_VISIBLE):
                    raise RuntimeError('Workspace obscures shelf measurement')
                time.sleep(.4)
                before = native.run(client, native.CAMERA_CHECK)
                receipt = native.capture(str(args.session), args.owner,
                                         args.output / (label + '.png'), args.capture_exe)
                after = native.run(client, native.CAMERA_CHECK)
                if before != after:
                    raise RuntimeError('Shelf camera changed during capture')
                report['captures'][label] = dict(receipt, before=before, after=after,
                                                  case=case['label'], camera=case['camera'])
                persist()

            generated = set()
            for wood, aux, direction, fronts in matrix_cases(args.matrix):
                if args.aux is not None and aux != args.aux:
                    continue
                label = wood + '_' + str(aux) + '_' + direction
                material = {'name': 'minecraft:' + wood + '_shelf', 'aux': aux}
                placed = native.run(client, PLACE % material, True)
                states = native.run(client, STATES % (material['name'], aux), True)
                if args.set_states:
                    placed['semantic_write'] = native.run(client, PLACE_STATES % states, True)
                if states['minecraft:cardinal_direction'] != direction:
                    raise RuntimeError('Observed shelf direction disagrees with the diagnostic camera')
                case = {'label': label, 'material': material, 'placed': placed,
                        'states': states, 'replication': wait_for(material), 'candidate_paths': {}}
                case['camera'] = native.run(client, native.CAMERA.replace(
                    'offset=(3.,3.,5.)', 'offset=' + repr(VIEWS[direction])))
                report['cases'].append(case)
                frame(label + '_world', case)
                native.run(client, native.CLEAR, True)
                case['empty_replication'] = wait_for({'name': 'minecraft:air', 'aux': 0})
                frame(label + '_empty', case)
                variants = [(front, suffix) for front in fronts
                            for suffix in (('', '_ao') if args.compare_ao else ('',))]
                if args.compare_engine_direction:
                    variants.extend((front, suffix) for front in fronts
                                    for suffix in ('_directional', '_directional_ao'))
                for front, suffix in variants:
                    directional = suffix.startswith('_directional')
                    identifier = 'modern_projection:preview_shelf_' + wood + '_' + front
                    identifier += suffix if directional else '_' + direction + suffix
                    material_aux = {'south': 0, 'west': 1, 'north': 2, 'east': 3}[direction] if directional else 0
                    path_key = identifier + '__aux' + str(material_aux)
                    if path_key not in generated:
                        case['candidate_paths'][front + suffix] = native.run(client, PROXY % ((identifier, material_aux),))
                        generated.add(path_key)
                    native.run(client, native.ATTACH % (
                        path_key, (-.5, 0., -.5), (0., 0., 0., 0.), []))
                    frame(label + '_' + front + suffix, case)
                    native.run(client, DETACH)
            report['completed'] = True
        except Exception as error:
            report['error'] = type(error).__name__ + ': ' + str(error)
            persist()
            raise
        finally:
            actions = []
            if saved:
                actions.append(('client', native.CLEAN_CLIENT, False))
            if world:
                actions.append(('world', native.CLEAN_WORLD, True))
            if environment:
                actions.append(('environment', native.RESTORE_ENVIRONMENT, True))
            if workspace_saved:
                actions.append(('workspace', body.RESTORE_WORKSPACE, False))
            for label, code, server in actions:
                try:
                    report[label + '_restore'] = native.run(client, code, server)
                except Exception as error:
                    report['cleanup_errors'].append(label + ': ' + str(error))
            report['source_unchanged'] = sources == snapshot_sources(project)
            report['restored'] = not report['cleanup_errors']
            persist()
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'source_unchanged')}))


if __name__ == '__main__':
    main()
