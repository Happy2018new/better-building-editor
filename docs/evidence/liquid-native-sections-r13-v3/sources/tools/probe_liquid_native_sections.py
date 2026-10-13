"""Finite near/far native terrain publication controls, without UI or projection."""
import argparse
import json
import os
from pathlib import Path
import time

import numpy as np

import analyze_liquid_native_write as visibility
import analyze_liquid_sides as oracle
from analyze_liquid_workspace import capture_failures, difference_mask, rgb
import capture_pure_liquid_native_controls as native
import capture_frozen_liquid_controls as frozen
import probe_liquid_original_sides as sides
import probe_liquid_pose_channel as base
import probe_liquid_workspace as workspace
import verify_debug_blueprints as blueprints
import verify_debug_visuals as visuals
from _session import load_session

HEIGHTS = (2, 24)
SOURCE = 'water_depth_0_foreground'
LIMITS = {'rgb_delta': 12, 'support_pixels': 1000, 'support_coverage': .5,
          'neutral_max_channel_spread': 30, 'water_blue_pixels': 80,
          'blue_over_green': 8, 'blue_over_red': 12}
PREPARE = '''import json,math,sys
import mod.server.extraServerApi as api
assert not hasattr(sys,'_liquid_pose_world')
factory=api.GetEngineCompFactory();player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
foot=factory.CreatePos(player).GetFootPos()
assert dimension==0 and foot and all(not math.isnan(v) and not math.isinf(v) for v in foot)
info=factory.CreateBlockInfo(player)
origins=[(int(math.floor(foot[0]))+6,int(math.floor(foot[1]))+lift,int(math.floor(foot[2]))+6) for lift in (2,24)]
region=sorted(set((o[0]+x,o[1]+y,o[2]+z) for o in origins for x in range(-2,4) for y in range(-2,4) for z in range(-2,4)))
assert all(-64<=pos[1]<320 for pos in region)
for pos in region:
 front=info.GetBlockNew(pos,dimension);back=info.GetLiquidBlock(pos,dimension)
 assert front and front.get('name')=='minecraft:air',(pos,front)
 assert back is None or back.get('name')=='minecraft:air',(pos,back)
sys._liquid_pose_world={'origins':origins,'region':region,'player':player,'dimension':dimension,'foot_before':foot,'workspace_cells':[]}
_result=json.dumps({'origins':origins,'region':region,'player':player,'dimension':dimension,'foot':foot,'reserved_air_cells':len(region),'position_write_attempted':False})
'''


def native_positive(dry, wet, empty, masks):
    support = masks['support']
    support_changed = difference_mask(dry, empty, support, LIMITS['rgb_delta'])
    neutral = (np.max(dry, axis=2) - np.min(dry, axis=2)) <= LIMITS['neutral_max_channel_spread']
    support_signal = support_changed & neutral
    support_pixels = int(support_signal.sum())
    coverage = support_pixels / max(1, int(support.sum()))
    water = difference_mask(wet, dry, masks['water_envelope'], LIMITS['rgb_delta'])
    blue = (wet[..., 2] > wet[..., 1] + LIMITS['blue_over_green']) & (
        wet[..., 2] > wet[..., 0] + LIMITS['blue_over_red'])
    water_pixels = int((water & blue).sum())
    return {'support_pixels': support_pixels, 'support_eligible_pixels': int(support.sum()),
            'support_coverage': coverage,
            'support_observed': support_pixels >= LIMITS['support_pixels'] and coverage >= LIMITS['support_coverage'],
            'water_blue_pixels': water_pixels, 'water_observed': water_pixels >= LIMITS['water_blue_pixels'],
            'production_qualified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--capture-exe', required=True, type=Path)
    parser.add_argument('--physical', required=True, type=Path)
    parser.add_argument('--viewport-receipt', required=True, type=Path)
    parser.add_argument('--normal-deadline-unix', required=True, type=float)
    parser.add_argument('--cleanup-deadline-unix', required=True, type=float)
    args = parser.parse_args()
    if args.output.exists() or not time.time() < args.normal_deadline_unix < args.cleanup_deadline_unix:
        parser.error('Fresh output and ordered future fixed deadlines required')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    session = load_session(args.session, args.owner, live=True)
    physical = json.loads(args.physical.read_bytes())
    binding = {key: session[key] for key in ('owner', 'session_file', 'game_pid', 'game_identity')}
    viewport = json.loads(args.viewport_receipt.read_bytes())
    if (not viewport.get('ok') or not viewport.get('reliable') or
            any(viewport[key] != binding[key] for key in binding) or
            oracle.fingerprint(viewport['path'])['sha256'] != viewport['sha256']):
        raise ValueError('Current exact-session reliable initial viewport is mandatory')
    if (not physical.get('passed') or not physical.get('actual_world_ready') or
            any(physical['session_binding'][key] != binding[key] for key in binding)):
        raise ValueError('Current exact-session actual-world readiness is mandatory')
    report = {'schema': 1, 'scope': 'Native near/far terrain publication diagnostic only',
              'completed': False, 'restored': False, 'captures': {}, 'states': {}, 'writes': {},
              'session_binding': binding, 'limits': LIMITS, 'source': oracle.fingerprint(__file__),
              'world_ready': oracle.fingerprint(args.physical), 'viewport': oracle.fingerprint(args.viewport_receipt), 'heights': HEIGHTS,
              'cleanup_errors': [], 'production_qualified': False, 'side_uv_qualified': False,
              'transparency_qualified': False, 'animation_qualified': False}
    save = lambda: base.write(args.output, report)
    save()
    with sides.FiniteClient(args.normal_deadline_unix, args.cleanup_deadline_unix) as client:
        check = sides.FiniteCheck(client, args.output, 3.)
        visual_saved = environment_saved = world_saved = observer_saved = False
        journal = report.setdefault('camera_settle_journal', [])
        try:
            if check.navigation()['open'] or check.navigation()['transition']:
                raise ValueError('Native-only diagnostic requires the ordinary workspace closed')
            report['visual_saved'] = check.run(visuals.SAVE_VISUAL); visual_saved = True
            report['render_observer'] = check.run(sides.FRAME_INSTALL); observer_saved = True
            report['environment'] = base.run(client, base.ENVIRONMENT, True); environment_saved = True
            world_saved = True
            report['reservation'] = base.run(client, PREPARE, True)
            base.run(client, workspace.FLOW % True, True)
            declarations = {}
            for height, origin in zip(HEIGHTS, report['reservation']['origins']):
                document_origin = tuple(value - 3 for value in origin)
                target = tuple(origin[i] + (.35 if i == 1 else .5) for i in range(3))
                camera = sides.settle_camera(check, target, (-1., .6, -1.2), journal, save)
                # 66.6 is a prior geometry hypothesis solely for a generous
                # publication envelope. No camera or water shape is accepted.
                projection = dict(camera, vertical_fov=66.6, origin=list(document_origin),
                                  kind='perspective', native_image_screen=[viewport['width'], viewport['height']])
                declarations[str(height)] = dict(source_id=SOURCE, source_cells=oracle.builtin_geometry(SOURCE)['source_cells'],
                    document_origin=document_origin, target=target, projection=projection,
                    observed_positions=sides.native_comparison_positions(oracle.builtin_geometry(SOURCE)['source_cells'],
                        document_origin, report['reservation']['region']))
            report['declarations'] = declarations
            report['preflight_qpc_100ns'] = sides.qpc(); save()
            for height in HEIGHTS:
                label = 'y' + str(height)
                declaration = declarations[str(height)]
                projection = declaration['projection']
                camera = sides.settle_camera(check, declaration['target'], (-1., .6, -1.2), journal, save)
                if not sides.camera_matches(camera, projection):
                    raise ValueError('Actual native camera differs from pre-capture declaration')
                positions = declaration['observed_positions']
                def state():
                    return {'server': base.run(client, native.snapshot_code(positions, True), True),
                            'client': check.run(native.snapshot_code(positions)), 'camera': check.run(sides.CAMERA_STATE)}
                def frame(name, expected):
                    before = state()
                    report['states'][name] = {'before': before}; save()
                    if (not sides.camera_matches(before['camera'], projection) or
                            any(not native.matches(before[side], expected, positions) for side in ('server', 'client'))):
                        raise ValueError('Native source/camera mismatch before ' + name)
                    report['captures'][name] = base.capture(args.session, args.owner,
                        args.output.with_name(args.output.stem + '_' + name + '.png'), args.capture_exe)
                    after = state(); report['states'][name]['after'] = after; save()
                    capture = report['captures'][name]
                    if ([capture['width'], capture['height']] != projection['native_image_screen'] or
                            capture['frame']['frame_qpc_100ns'] <= report['preflight_qpc_100ns'] or
                            not sides.camera_matches(after['camera'], projection) or
                            any(not native.matches(after[side], expected, positions) for side in ('server', 'client'))):
                        raise ValueError('Native source/camera changed across ' + name)
                frame(label + '_empty', [])
                for route, writer in (('direct', sides.DIRECT_WRITE), ('palette', workspace.WRITE)):
                    for control in ('supported_negative', 'supported_positive'):
                        cells = [(tuple(declaration['document_origin'][i] + pos[i] for i in range(3)), value)
                                 for pos, value in oracle.builtin_geometry(SOURCE, control)['source_cells']]
                        name = label + '_' + route + ('_dry' if control == 'supported_negative' else '_wet')
                        count = check.run(sides.CAMERA_STATE)['render_events']
                        report['writes'][name] = {'render_events_at_request': count,
                            'write': base.run(client, writer % native.wire(cells), True)}; save()
                        check.wait('two real render events after ' + name,
                            lambda value: value['render_events'] >= count + 2 and sides.camera_matches(value, projection),
                            lambda: check.run(sides.CAMERA_STATE))
                        frame(name, frozen.native_reference(cells))
                base.run(client, workspace.WRITE % native.wire([]), True)
                frame(label + '_restored', [])
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
        finally:
            client.cleaning = True
            actions = []
            if world_saved:
                actions.extend((('native_clear', lambda: base.run(client, workspace.guarded_cleanup(workspace.WRITE % native.wire([]), '_liquid_pose_world'), True)),
                    ('flow_restore', lambda: base.run(client, workspace.guarded_cleanup(workspace.FLOW % False, '_liquid_pose_world'), True)),
                    ('world_restore', lambda: base.run(client, workspace.QUALIFICATION_CLEAN_WORLD, True))))
            if visual_saved:
                actions.extend((('camera_restore', lambda: check.run(workspace.guarded_cleanup(visuals.camera_restore_code(False), '_blueprint_visual_saved'))),
                    ('visual_restore', lambda: check.run("del sys._blueprint_visual_saved\n_result=True"))))
            if environment_saved:
                actions.append(('environment_restore', lambda: base.run(client, workspace.guarded_cleanup(base.RESTORE_ENVIRONMENT, '_context_environment_saved'), True)))
            if observer_saved:
                actions.append(('render_observer_removed', lambda: check.run(sides.FRAME_REMOVE)))
            for name, action in actions:
                try:
                    report[name] = action()
                except Exception as error:
                    report['cleanup_errors'].append('%s: %s' % (name, error))
                save()
            report['restored'] = not report['cleanup_errors']; save()
    failures = capture_failures(report['captures'], binding)
    report['capture_failures'] = failures
    report['native_positive'] = {}
    for height in HEIGHTS:
        label = 'y' + str(height)
        if label + '_empty' not in report['captures']:
            continue
        masks = visibility.visibility_masks(SOURCE, report['declarations'][str(height)]['projection'])
        empty = rgb(report['captures'][label + '_empty']['path'])
        for route in ('direct', 'palette'):
            names = [label + '_' + route + suffix for suffix in ('_dry', '_wet')]
            if all(name in report['captures'] for name in names):
                report['native_positive'][label + '_' + route] = native_positive(
                    rgb(report['captures'][names[0]]['path']), rgb(report['captures'][names[1]]['path']), empty, masks)
    save()
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'captures': len(report['captures']), 'error': report.get('error'),
                      'native_positive': report['native_positive']}))
    return 0 if report['completed'] and report['restored'] and not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
