"""Observe owned native shelf bodies, clip boxes and states without draw adapters."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import probe_liquid_pose_channel as native
from generate_shelf_resources_r17 import WOODS
from probe_native_palette_body_r16 import (CLOSE_WORKSPACE, RESTORE_WORKSPACE,
                                           WORLD_VISIBLE)

VIEWS = {'south': (0., 1., 4.), 'east': (4., 1., 0.),
         'north': (0., 1., -4.), 'west': (-4., 1., 0.)}
PREPARE = native.PREPARE + '''
support=(origin[0],origin[1]-1,origin[2])
assert info.SetBlockNew(support,{'name':'minecraft:cyan_concrete','aux':0},0,dimension,True,False)
_result=json.dumps({'origin':origin,'support':support,'dimension':dimension,
 'placed':info.GetBlockNew(origin,dimension),'nbt':info.GetBlockEntityData(dimension,origin)})
'''
OBSERVE = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
origin=tuple(saved['origin']);dimension=saved['dimension']
rows=[]
for wood in %r:
 for aux in range(32):
  material={'name':'minecraft:'+wood+'_shelf','aux':aux}
  assert info.SetBlockNew(origin,material,0,dimension,True,False)
  rows.append({'wood':wood,'requested':material,'placed':info.GetBlockNew(origin,dimension),
    'collision':info.GetBlockCollision(origin,dimension),'clip':info.GetBlockClip(origin,dimension)})
_result=json.dumps(rows)
'''
PLACE = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
material=%r
assert info.SetBlockNew(tuple(saved['origin']),material,0,saved['dimension'],True,False)
_result=json.dumps({'placed':info.GetBlockNew(tuple(saved['origin']),saved['dimension']),
 'nbt':info.GetBlockEntityData(saved['dimension'],tuple(saved['origin']))})
'''
READ_WORLD = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
_result=json.dumps(info.GetBlockNew(tuple(saved['origin']),saved['dimension']))
'''
STATE_MAP = '''import json
import mod.server.extraServerApi as api
state=api.GetEngineCompFactory().CreateBlockState(api.GetLevelId())
rows=[]
for wood in %r:
 for aux in range(32):
  name='minecraft:'+wood+'_shelf'
  actual=state.GetBlockStatesFromAuxValue(name,aux)
  assert actual is not None,(name,aux)
  rows.append({'wood':wood,'name':name,'aux':aux,'states':actual})
_result=json.dumps(rows)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    parser.add_argument('--state-map-only', action='store_true',
                        help='Read the installed engine state mapping without world or camera writes')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh observation directory')
    args.output.mkdir(parents=True)
    session = json.loads(args.session.read_bytes())
    if session['owner'] != args.owner:
        parser.error('Shelf observation needs its own owner')
    os.environ.update(MCDEV_SESSION_FILE=str(args.session.resolve()), MCDEV_OWNER=args.owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    report = {'schema_version': 1, 'engine_version': '3.10.0.420447',
              'completed': False, 'restored': False, 'production_qualified': False,
              'captures': {}, 'cleanup_errors': [],
              'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'session': {key: session[key] for key in ('id', 'owner', 'game_pid', 'game_identity')}}
    def persist():
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    with native.Client(timeout=40) as client:
        if args.state_map_only:
            report['state_mapping'] = native.run(client, STATE_MAP % (WOODS,), True)
            report.update(completed=True, restored=True, read_only=True)
            persist()
            print(json.dumps({'states':len(report['state_mapping']), 'read_only':True}))
            return
        environment = world = saved = workspace_saved = False
        try:
            report['workspace'] = native.run(client, CLOSE_WORKSPACE)
            workspace_saved = True
            deadline = time.monotonic() + 10.
            while not native.run(client, WORLD_VISIBLE):
                if time.monotonic() >= deadline:
                    raise RuntimeError('Workspace obscures the shelf diagnostic')
                time.sleep(.2)
            report['environment'] = native.run(client, native.ENVIRONMENT, True)
            environment = True
            report['world'] = native.run(client, PREPARE % 'minecraft:oak_shelf', True)
            world = True
            origin = tuple(report['world']['origin'])
            report['near_player'] = native.run(client, native.NEAR_PLAYER, True)
            native.run(client, native.SAVE % (origin,))
            saved = True
            report['states'] = native.run(client, OBSERVE % (WOODS,), True)
            persist()
            cases = [(wood, 0, ('south', 'east')) for wood in WOODS]
            cases += [('oak', aux, tuple(VIEWS)) for aux in (1, 2, 3, 4, 8, 16, 24)]
            for wood, aux, views in cases:
                label = wood + '-' + str(aux)
                material = {'name': 'minecraft:' + wood + '_shelf', 'aux': aux}
                placed = native.run(client, PLACE % material, True)
                time.sleep(.4)
                deadline = time.monotonic() + 12.
                while True:
                    settled = native.run(client, READ_WORLD, True)
                    replicated = native.run(client, native.REPLICATION % (origin,))
                    if any(row['name'] == settled['name'] and row['aux'] == settled['aux']
                           for row in replicated['materials']):
                        break
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Shelf state did not replicate: ' + repr(replicated))
                    time.sleep(.2)
                for view in views:
                    if not native.run(client, WORLD_VISIBLE):
                        raise RuntimeError('Workspace reopened during shelf capture')
                    camera = native.run(client, native.CAMERA.replace(
                        'offset=(3.,3.,5.)', 'offset=' + repr(VIEWS[view])))
                    time.sleep(.35)
                    before = native.run(client, native.CAMERA_CHECK)
                    receipt = native.capture(str(args.session), args.owner,
                        args.output / (label + '-' + view + '.png'), args.capture_exe)
                    after = native.run(client, native.CAMERA_CHECK)
                    if before != after:
                        raise RuntimeError('Shelf camera drifted during capture')
                    report['captures'][label + '-' + view] = dict(receipt, camera=camera,
                        before=before, after=after, requested=material,
                        placed=placed, settled=settled,
                        requested_state_retained=settled == material)
                    persist()
            report['completed'] = True
        except Exception as error:
            report['error'] = type(error).__name__ + ': ' + str(error)
            persist()
            raise
        finally:
            for label, code, server in ([('client', native.CLEAN_CLIENT, False)] if saved else []) + (
                    [('world', native.CLEAN_WORLD, True)] if world else []) + (
                    [('environment', native.RESTORE_ENVIRONMENT, True)] if environment else []) + (
                    [('workspace', RESTORE_WORKSPACE, False)] if workspace_saved else []):
                try:
                    report[label + '_restore'] = native.run(client, code, server)
                except Exception as error:
                    report['cleanup_errors'].append(label + ': ' + str(error))
            report['restored'] = not report['cleanup_errors']
            persist()
    print(json.dumps({key: report[key] for key in ('completed', 'restored')}))


if __name__ == '__main__':
    main()
