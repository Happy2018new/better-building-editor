"""Compare a public shelf body with live, roundtrip and prepared native palettes.

This owner-bound diagnostic preserves four views and a cyan support positive
control. It does not activate a window or grant production qualification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

import probe_liquid_pose_channel as native
from probe_product_water import snapshot_sources


VIEWS = {'south': (0., 1., 4.), 'north': (0., 1., -4.),
         'east': (4., 1., 0.), 'west': (-4., 1., 0.)}
PREPARE = native.PREPARE + '''
support=(origin[0],origin[1]-1,origin[2])
assert info.SetBlockNew(support,{'name':'minecraft:cyan_concrete','aux':0},0,dimension,True,False)
_result=json.dumps({'origin':origin,'support':support,'dimension':dimension,
 'placed':info.GetBlockNew(origin,dimension),'nbt':info.GetBlockEntityData(dimension,origin)})
'''
PALETTE = '''saved=sys._liquid_pose_client
origin=tuple(saved['origin'])
low=(origin[0],origin[1]-1,origin[2])
block=factory.CreateBlock(level)
live=block.GetBlockPaletteBetweenPos(low,origin,False)
assert live is not None
raw=live.SerializeBlockPalette()
copy=block.GetBlankBlockPalette()
assert copy.DeserializeBlockPalette(raw)
from modern_projection.projection.geometry_palette import prepare_palette
prepared=prepare_palette(raw)
converted=block.GetBlankBlockPalette()
assert converted.DeserializeBlockPalette(prepared)
geometry=factory.CreateBlockGeometry(level)
saved['paths']=[]
for key,palette in (('live',live),('roundtrip',copy),('prepared',converted)):
 name=%r+'_'+key
 result=geometry.CombineBlockPaletteToGeometry(palette,name,0)
 assert result is not None,(key,result)
 saved['paths'].append({'path':key,'requested':name,'returned':result})
saved['entity']=api.GetSystem('ModernProjection','ModernProjectionClientSystem').CreateClientEntityByTypeStr(
 'modern_projection:anchor',origin,(0.,0.))
assert saved['entity']
_result=json.dumps({'volume':raw['volume'],'common':repr(raw['common']),
 'extra':repr(raw.get('extra',{})),'actor':repr(raw.get('actor',{})),
 'roundtrip_equal':copy.SerializeBlockPalette()==raw,
 'prepared_common':repr(prepared['common']),'prepared_actor':repr(prepared.get('actor',{})),
 'paths':saved['paths']})
'''
CLEAR = native.CLEAR + '''
support=(saved['origin'][0],saved['origin'][1]-1,saved['origin'][2])
assert info.SetBlockNew(support,{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
_result=True
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    args = parser.parse_args()
    session = json.loads(args.session.read_bytes())
    if session['owner'] != args.owner or args.output.exists():
        parser.error('Use the owned session and a fresh output')
    os.environ.update(MCDEV_SESSION_FILE=str(args.session.resolve()),
                      MCDEV_OWNER=args.owner, MCDEV_ALLOW_USER_FOREGROUND='1')
    project = Path(session['project'])
    sources = snapshot_sources(project)
    report = {'schema': 1, 'completed': False, 'restored': False, 'captures': {},
              'pixel_acceptance_claimed': False, 'source_sha256': sources,
              'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'session': {key: session[key] for key in ('id','owner','game_pid','game_identity')},
              'cleanup_errors': []}
    def persist():
        native.write(args.output, report)
    with native.Client(timeout=40) as client:
        world = saved = environment = False
        try:
            report['environment'] = native.run(client, native.ENVIRONMENT, True)
            environment = True
            report['world'] = native.run(client, PREPARE % 'minecraft:oak_shelf', True)
            world = True
            origin = tuple(report['world']['origin'])
            report['near_player'] = native.run(client, native.NEAR_PLAYER, True)
            deadline = time.monotonic() + 15.
            while True:
                replicated = native.run(client, native.REPLICATION % (origin,))
                if any(row['name'] == 'minecraft:oak_shelf' for row in replicated['materials']):
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError('Shelf did not replicate: ' + repr(replicated))
                time.sleep(.2)
            report['replication'] = replicated
            native.run(client, native.SAVE % (origin,))
            saved = True
            time.sleep(1.)
            report['palette'] = native.run(client, PALETTE % ('shelf_body_' + uuid.uuid4().hex))
            def frame(label, view):
                code = native.CAMERA.replace('offset=(3.,3.,5.)', 'offset=' + repr(VIEWS[view]))
                camera = native.run(client, code)
                time.sleep(.5)
                before = native.run(client, native.CAMERA_CHECK)
                path = args.output.with_name(args.output.stem+'_'+label+'_'+view+'.png')
                receipt = native.capture(str(args.session), args.owner, path, args.capture_exe)
                after = native.run(client, native.CAMERA_CHECK)
                if before != after:
                    raise RuntimeError('Camera changed during capture')
                report['captures'][label+'_'+view] = dict(receipt, camera=camera, before=before, after=after)
                persist()
            for view in VIEWS:
                frame('world', view)
            native.run(client, CLEAR, True)
            time.sleep(.6)
            for view in VIEWS:
                frame('empty', view)
            for key in ('live','roundtrip','prepared'):
                native.run(client, native.ATTACH % (key,(-.5,-1.,-.5),(0.,0.,0.,0.),[]))
                for view in VIEWS:
                    frame(key, view)
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
            for label, code, server in actions:
                try:
                    report[label+'_restore'] = native.run(client, code, server)
                except Exception as error:
                    report['cleanup_errors'].append(label+': '+str(error))
            report['source_unchanged'] = sources == snapshot_sources(project)
            report['restored'] = not report['cleanup_errors']
            persist()
    print(json.dumps({key:report[key] for key in ('completed','restored','source_unchanged')}))


if __name__ == '__main__':
    main()
