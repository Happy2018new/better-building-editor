"""Observe one full shelf/support render palette, never a detached body overlay."""
import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import time
import uuid

import probe_liquid_pose_channel as native
import probe_native_palette_body_r16 as body
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from prepare_shelf_render_palette_r21 import verify
from probe_shelf_body_matrix_r20 import CELL_PROJECTION, PLACE, STATES
from probe_shelf_native_shape_r17 import VIEWS
from shelf_render_palette_candidate_r21 import SOURCE, PROXY, replace_body_palette

READ_PAIR = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
origin=tuple(saved['origin'])
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
_result=json.dumps([info.GetBlockNew((origin[0],origin[1]-1,origin[2]),saved['dimension']),
                   info.GetBlockNew(origin,saved['dimension'])])
'''
REPLICA_PAIR = '''saved=sys._liquid_pose_client
origin=tuple(saved['origin'])
low=(origin[0],origin[1]-1,origin[2])
palette=factory.CreateBlock(level).GetBlockPaletteBetweenPos(low,origin,False)
assert palette is not None
raw=palette.SerializeBlockPalette()
assert tuple(raw['volume'])==(1,1,2),raw['volume']
cells=[{'name':'minecraft:air','aux':0} for unused in range(2)]
for material,indices in raw.get('common',{}).items():
 for index in indices:
  assert index in (0,1),(material,index)
  cells[index]={'name':material[0],'aux':material[1]}
_result=json.dumps({'cells':cells,'extra':repr(raw.get('extra',{}))})
'''
BUILD = '''import copy
saved=sys._liquid_pose_client
origin=tuple(saved['origin'])
low=(origin[0],origin[1]-1,origin[2])
block=factory.CreateBlock(level)
live=block.GetBlockPaletteBetweenPos(low,origin,False)
assert live is not None
raw=live.SerializeBlockPalette()
before=copy.deepcopy(raw)
assert tuple(raw['volume'])==(1,1,2),raw['volume']
assert raw['common'].get(SOURCE)==[1],raw['common']
assert raw['common'].get(('minecraft:cyan_concrete',0))==[0],raw['common']
from modern_projection.projection.geometry_palette import prepare_palette
from modern_projection.projection.bridge import _native_palette
prepared=prepare_palette(raw)
prepared_before=copy.deepcopy(prepared)
converted=replace_body_palette(prepared)
assert before==raw and prepared_before==prepared
assert converted['common'].get(PROXY)==[1] and SOURCE not in converted['common']
assert converted['common'].get(('minecraft:cyan_concrete',0))==[0]
assert converted.get('extra',{})==prepared.get('extra',{})
assert tuple(converted['volume'])==(1,1,2)
assert not any(1 in rows for name,rows in converted.get('actor',{}).items()
               if name in (SOURCE[0],SOURCE[0].encode('ascii')))
palette=block.GetBlankBlockPalette()
assert palette.DeserializeBlockPalette(_native_palette(converted))
requested=%r
returned=factory.CreateBlockGeometry(level).CombineBlockPaletteToGeometry(palette,requested,0)
assert returned is not None
saved['paths']=[{'path':'full_proxy_support','requested':requested,'returned':returned}]
saved['entity']=api.GetSystem('ModernProjection','ModernProjectionClientSystem').CreateClientEntityByTypeStr(
 'modern_projection:anchor',origin,(0.,0.))
assert saved['entity']
factory.CreateModel(saved['entity']).SetEntityShadowShow(False)
_result=json.dumps({'volume':converted['volume'],'source_common':repr(raw['common']),
 'common':repr(converted['common']),'extra':repr(converted.get('extra',{})),
 'source_actor':repr(raw.get('actor',{})),'actor':repr(converted.get('actor',{})),
 'source_unchanged':before==raw,'prepared_unchanged':prepared_before==prepared,
 'paths':saved['paths'],'support_inside_same_combine':True,
 'independent_body_overlay':False})
'''


def build_code(namespace):
    return ('SOURCE='+repr(SOURCE)+'\nPROXY='+repr(PROXY)+'\n'+
            inspect.getsource(replace_body_palette)+'\n'+BUILD % namespace)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh acquisition directory')
    frozen = verify(args.freeze)
    session = json.loads(args.session.read_bytes())
    if session['owner'] != args.owner or args.owner != frozen['owner']:
        parser.error('Use the exact frozen render-palette owner')
    if Path(session['project']).resolve() != Path(frozen['project']).resolve():
        parser.error('The session does not match the frozen candidate clone')
    os.environ.update(MCDEV_SESSION_FILE=str(args.session.resolve()), MCDEV_OWNER=args.owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1', OPENBLAS_NUM_THREADS='1')
    args.output.mkdir(parents=True)
    report = {'schema_version': 1, 'direction': 'south', 'completed': False, 'restored': False,
        'source_unchanged': False, 'production_qualified': False, 'captures': {},
        'cleanup_errors': [], 'resource_samples': [],
        'frozen_manifest_sha256': hashlib.sha256(args.freeze.read_bytes()).hexdigest(),
        'session': {key: session[key] for key in ('id', 'owner', 'game_pid', 'game_identity')},
        'scope': 'Exactly native shelf/support, full proxy/support and full proxy/support COLOR images. '
                 'South oak unpowered only; no standalone body, packed-context runtime or other directions.'}
    started = time.monotonic()

    def persist():
        native.write(args.output/'report.json', report)

    def boundary(label):
        sample = commit_at_boundary()
        report['resource_samples'].append(dict(sample, boundary=label))
        persist()
        if sample['commit_available_bytes'] < 6*1024**3:
            raise RuntimeError('The render-palette diagnostic requires 6 GiB available commit')
        if time.monotonic()-started > 150.:
            raise RuntimeError('Stopped admitting capture phases after 150 seconds')

    material = {'name': SOURCE[0], 'aux': SOURCE[1]}
    support = {'name': 'minecraft:cyan_concrete', 'aux': 0}
    air = {'name': 'minecraft:air', 'aux': 0}
    with native.Client(timeout=40) as client:
        world = saved = environment = workspace_saved = False
        try:
            boundary('before_fixture')
            workspace_saved = True
            report['workspace'] = native.run(client, body.CLOSE_WORKSPACE)
            deadline = time.monotonic()+10.
            while not native.run(client, body.WORLD_VISIBLE):
                if time.monotonic() >= deadline:
                    raise RuntimeError('The workspace obscures the fixture')
                time.sleep(.2)
            environment = True
            report['environment'] = native.run(client, native.ENVIRONMENT, True)
            world = True
            report['world'] = native.run(client, body.PREPARE % material['name'], True)
            origin = tuple(report['world']['origin'])
            report['placed'] = native.run(client, PLACE % material, True)
            report['states'] = native.run(client, STATES % SOURCE, True)
            if report['states']['minecraft:cardinal_direction'] != 'south':
                raise RuntimeError('The native shelf is not south-facing')
            report['near_player'] = native.run(client, native.NEAR_PLAYER, True)
            saved = True
            native.run(client, native.SAVE % (origin,))
            report['camera'] = native.run(client, native.CAMERA.replace(
                'offset=(3.,3.,5.)', 'offset='+repr(VIEWS['south'])))
            report['cell_projection'] = native.run(client, CELL_PROJECTION)

            def wait_pair(requested):
                deadline = time.monotonic()+15.
                while True:
                    actual = native.run(client, READ_PAIR, True)
                    replica = native.run(client, REPLICA_PAIR)
                    if actual == requested and replica['cells'] == requested:
                        return {'world': actual, 'replication': replica}
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Both shelf/support cells must replicate before proceeding')
                    time.sleep(.2)

            def capture(label):
                boundary(label)
                if not native.run(client, body.WORLD_VISIBLE):
                    raise RuntimeError('The workspace obscures the capture')
                time.sleep(.4)
                before = native.run(client, native.CAMERA_CHECK)
                result = native.capture(str(args.session), args.owner, args.output/(label+'.png'),
                                        Path(frozen['capture_exe']))
                after = native.run(client, native.CAMERA_CHECK)
                if before != after or (report['captures'] and before != report['captures']['native']['before']):
                    raise RuntimeError('The comparison camera changed')
                report['captures'][label] = dict(result, before=before, after=after)
                persist()

            report['native_replication'] = wait_pair([support, material])
            capture('native')
            report['palette'] = native.run(client, build_code('shelf_context_r21_'+uuid.uuid4().hex))
            report['cleared'] = native.run(client, body.CLEAR, True)
            report['empty_replication'] = wait_pair([air, air])
            report['attached'] = native.run(client, native.ATTACH % (
                'full_proxy_support', (-.5, -1., -.5), (0., 0., 0., 0.), []))
            capture('proxy_support')
            report['color_mode'] = native.run(client, '''saved=sys._liquid_pose_client
assert factory.CreateActorRender(saved['entity']).SetEntityExtraUniforms(4,(19491.,6.,0.,0.))
_result=True
''')
            capture('proxy_support_color')
            report['completed'] = True
        except Exception as error:
            report['error'] = type(error).__name__+': '+str(error)
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
                    report[label+'_restore'] = native.run(client, code, server)
                except Exception as error:
                    report['cleanup_errors'].append(label+': '+str(error))
            try:
                verify(args.freeze)
                report['source_unchanged'] = True
            except (OSError, ValueError, RuntimeError) as error:
                report['cleanup_errors'].append('freeze: '+str(error))
            report['restored'] = not report['cleanup_errors']
            report['elapsed_seconds'] = time.monotonic()-started
            persist()
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'source_unchanged')}))


if __name__ == '__main__':
    main()
