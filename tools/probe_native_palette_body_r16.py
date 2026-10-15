"""Compare a native body with live, roundtrip and prepared native palettes.

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
CLOSE_WORKSPACE = '''from modern_projection.pyreact import navigator
assert not navigator.is_transitioning
assert navigator.top is None or navigator.top.key=='modern_projection_workspace'
assert not hasattr(sys,'_palette_body_workspace')
sys._palette_body_workspace=navigator.top is not None
if navigator.top is not None:navigator.pop()
_result={'was_open':sys._palette_body_workspace}
'''
WORLD_VISIBLE = '''from modern_projection.pyreact import navigator
_result=navigator.top is None and not navigator.is_transitioning
'''
RESTORE_WORKSPACE = '''from modern_projection.pyreact import navigator
if hasattr(sys,'_palette_body_workspace'):
 if sys._palette_body_workspace:
  api.GetSystem('ModernProjection','ModernProjectionClientSystem').open_workspace()
 del sys._palette_body_workspace
_result=True
'''
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
for key,position in (('body_only',origin),('support_only',low)):
 palette=block.GetBlockPaletteBetweenPos(position,position,False)
 name=saved['paths'][0]['requested']+'_'+key
 result=geometry.CombineBlockPaletteToGeometry(palette,name,0)
 assert result is not None,(key,result)
 saved['paths'].append({'path':key,'requested':name,'returned':result})
saved['entity']=api.GetSystem('ModernProjection','ModernProjectionClientSystem').CreateClientEntityByTypeStr(
 'modern_projection:anchor',origin,(0.,0.))
assert saved['entity']
factory.CreateModel(saved['entity']).SetEntityShadowShow(False)
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
PROXY = '''saved=sys._liquid_pose_client
block=factory.CreateBlock(level)
palette=block.GetBlockPaletteBetweenPos(tuple(saved['origin']),tuple(saved['origin']),False)
raw=palette.SerializeBlockPalette()
raw['common']={(%r,0):[0]}
raw['extra']={}
raw['actor']={}
assert palette.DeserializeBlockPalette(raw)
name=saved['paths'][0]['requested']+'_proxy'
result=factory.CreateBlockGeometry(level).CombineBlockPaletteToGeometry(palette,name,0)
assert result is not None
saved['paths'].append({'path':'proxy','requested':name,'returned':result})
_result={'raw':repr(raw),'path':saved['paths'][-1]}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    parser.add_argument('--block', default='minecraft:oak_shelf',
                        choices=('minecraft:oak_shelf', 'minecraft:enchanting_table',
                                 'minecraft:lectern', 'minecraft:cyan_concrete'))
    parser.add_argument('--body-offsets',type=float,nargs='+',default=(),
                        help='Diagnostic vertical offsets for a separately generated body; support stays fixed.')
    parser.add_argument('--proxy-block', help='Optional registered internal body candidate; never placed in the real world.')
    parser.add_argument('--shadow-control', action='store_true',
                        help='Capture an explicit shadow on/off negative control after the body matrix.')
    args = parser.parse_args()
    session = json.loads(args.session.read_bytes())
    if session['owner'] != args.owner or args.output.exists():
        parser.error('Use the owned session and a fresh output')
    if args.proxy_block and not args.proxy_block.startswith('modern_projection:preview_'):
        parser.error('Only an internal preview block can be used as a body candidate')
    os.environ.update(MCDEV_SESSION_FILE=str(args.session.resolve()),
                      MCDEV_OWNER=args.owner, MCDEV_ALLOW_USER_FOREGROUND='1')
    project = Path(session['project'])
    sources = snapshot_sources(project)
    report = {'schema': 1, 'completed': False, 'restored': False, 'captures': {},
              'pixel_acceptance_claimed': False, 'source_sha256': sources,
              'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'session': {key: session[key] for key in ('id','owner','game_pid','game_identity')},
              'cleanup_errors': []}
    report['block'] = args.block
    report['entity_shadow_enabled'] = False
    def persist():
        native.write(args.output, report)
    with native.Client(timeout=40) as client:
        world = saved = environment = workspace_saved = False
        try:
            report['workspace'] = native.run(client, CLOSE_WORKSPACE)
            workspace_saved = True
            deadline = time.monotonic()+10.
            while not native.run(client, WORLD_VISIBLE):
                if time.monotonic()>=deadline:
                    raise RuntimeError('Workspace did not close before the world diagnostic')
                time.sleep(.2)
            report['environment'] = native.run(client, native.ENVIRONMENT, True)
            environment = True
            report['world'] = native.run(client, PREPARE % args.block, True)
            world = True
            origin = tuple(report['world']['origin'])
            report['near_player'] = native.run(client, native.NEAR_PLAYER, True)
            deadline = time.monotonic() + 15.
            while True:
                replicated = native.run(client, native.REPLICATION % (origin,))
                if any(row['name'] == args.block for row in replicated['materials']):
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError('Native body did not replicate: ' + repr(replicated))
                time.sleep(.2)
            report['replication'] = replicated
            native.run(client, native.SAVE % (origin,))
            saved = True
            time.sleep(1.)
            report['palette'] = native.run(client, PALETTE % ('shelf_body_' + uuid.uuid4().hex))
            if args.proxy_block:
                report['proxy'] = native.run(client, PROXY % args.proxy_block)
            def frame(label, view):
                if not native.run(client, WORLD_VISIBLE):
                    raise RuntimeError('Workspace obscures the native body capture')
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
            separate = [('body_only', offset, 'separate_'+str(offset)) for offset in args.body_offsets]
            if args.proxy_block:
                separate.append(('proxy', 0., 'proxy'))
            for key, offset, label in separate:
                native.run(client,native.ATTACH % (key,(-.5,offset,-.5),(0.,0.,0.,0.),[]))
                native.run(client,'''saved=sys._liquid_pose_client
render=factory.CreateActorRender(saved['entity'])
path=next(row for row in saved['paths'] if row['path']=='support_only')
assert render.AddActorBlockGeometry(path['returned'],(-.5,-1.,-.5),(0.,180.,0.))
_result={'body_offset':%r,'support_offset':(-.5,-1.,-.5)}
''' % offset)
                for view in VIEWS:
                    frame(label,view)
            if args.shadow_control:
                native.run(client, native.ATTACH % ('prepared',(-.5,-1.,-.5),(0.,0.,0.,0.),[]))
                for view in VIEWS:
                    for enabled, label in ((True, 'shadow_on'), (False, 'shadow_off')):
                        native.run(client, '''saved=sys._liquid_pose_client
factory.CreateModel(saved['entity']).SetEntityShadowShow(%r)
_result=True
''' % enabled)
                        frame(label, view)
                        report['captures'][label+'_'+view]['entity_shadow_enabled'] = enabled
                        persist()
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
                actions.append(('workspace', RESTORE_WORKSPACE, False))
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
