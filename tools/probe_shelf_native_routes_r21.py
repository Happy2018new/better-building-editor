"""Capture only south native/empty route-selector images and restore the fixture."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

from PIL import Image

import probe_liquid_pose_channel as native
import probe_native_palette_body_r16 as body
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from prepare_shelf_native_routes_r21 import verify
from probe_shelf_body_matrix_r20 import CELL_PROJECTION, PLACE, STATES
from probe_shelf_native_shape_r17 import READ_WORLD, VIEWS


def pixel_observations(world, empty, projection):
    points = [row['screen'] for row in projection]
    with Image.open(world).convert('RGB') as first, Image.open(empty).convert('RGB') as second:
        if first.size != second.size:
            raise ValueError('The route-selector pair has different image dimensions')
        bounds = [max(0, int(math.floor(min(point['screenX'] for point in points)))-4),
                  max(0, int(math.floor(min(point['screenY'] for point in points)))-4),
                  min(first.width, int(math.ceil(max(point['screenX'] for point in points)))+4),
                  min(first.height, int(math.ceil(max(point['screenY'] for point in points)))+4)]
        if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
            raise ValueError('The native projected cell has no image area')
        markers = {'entity_static_netease': lambda rgb: rgb[0] <= 24 and min(rgb[1:]) >= 220,
                   'terrain_base': lambda rgb: min(rgb[:2]) >= 220 and rgb[2] <= 24}
        result = {'bounds': bounds, 'marker_counts': {}, 'changed_pixels_gt_24': 0,
                  'native_route_qualified': False,
                  'scope': 'Unsegmented cell ROI observations only; background colors cannot establish the shelf route.'}
        pairs = list(zip(first.crop(bounds).getdata(), second.crop(bounds).getdata()))
        changed = [max(abs(a-b) for a, b in zip(left, right)) > 24 for left, right in pairs]
        result['changed_pixels_gt_24'] = sum(changed)
        for name, matches in markers.items():
            result['marker_counts'][name] = {
                'world': sum(matches(left) for left, right in pairs),
                'empty': sum(matches(right) for left, right in pairs),
                'world_changed': sum(delta and matches(left) for (left, right), delta in zip(pairs, changed))}
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh capture directory')
    frozen = verify(args.freeze)
    session = json.loads(args.session.read_bytes())
    if session['owner'] != args.owner or args.owner != frozen['owner']:
        parser.error('Use the exact frozen route-selector owner')
    if Path(session['project']).resolve() != Path(frozen['project']).resolve():
        parser.error('The owner session does not match the frozen v3 clone')
    os.environ.update(MCDEV_SESSION_FILE=str(args.session.resolve()), MCDEV_OWNER=args.owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    args.output.mkdir(parents=True)
    report = {'schema_version': 1, 'direction': 'south', 'completed': False, 'restored': False,
        'source_unchanged': False, 'native_route_qualified': False, 'production_qualified': False,
        'captures': {}, 'cleanup_errors': [], 'resource_samples': [],
        'frozen_manifest_sha256': hashlib.sha256(args.freeze.read_bytes()).hexdigest(),
        'session': {key: session[key] for key in ('id', 'owner', 'game_pid', 'game_identity')},
        'scope': 'Exactly two raw south images, native and empty; no proxy, AO, UI or west expansion.'}
    started = time.monotonic()

    def persist():
        native.write(args.output/'report.json', report)

    def boundary(label):
        sample = commit_at_boundary()
        report['resource_samples'].append(dict(sample, boundary=label))
        persist()
        if sample['commit_available_bytes'] < 6*1024**3:
            raise RuntimeError('The route selector needs 6 GiB available commit')
        if time.monotonic()-started > 150.:
            raise RuntimeError('Stopped admitting capture phases after 150 seconds')

    material = {'name': 'minecraft:oak_shelf', 'aux': 0}
    with native.Client(timeout=40) as client:
        world = saved = environment = workspace_saved = False
        try:
            boundary('before_fixture')
            workspace_saved = True
            report['workspace'] = native.run(client, body.CLOSE_WORKSPACE)
            deadline = time.monotonic()+10.
            while not native.run(client, body.WORLD_VISIBLE):
                if time.monotonic() >= deadline:
                    raise RuntimeError('The workspace obscures the native route fixture')
                time.sleep(.2)
            environment = True
            report['environment'] = native.run(client, native.ENVIRONMENT, True)
            world = True
            report['world'] = native.run(client, body.PREPARE % material['name'], True)
            origin = tuple(report['world']['origin'])
            report['placed'] = native.run(client, PLACE % material, True)
            report['states'] = native.run(client, STATES % (material['name'], 0), True)
            if report['states']['minecraft:cardinal_direction'] != 'south':
                raise RuntimeError('The native shelf is not south-facing')
            report['near_player'] = native.run(client, native.NEAR_PLAYER, True)
            saved = True
            native.run(client, native.SAVE % (origin,))
            report['camera'] = native.run(client, native.CAMERA.replace('offset=(3.,3.,5.)', 'offset='+repr(VIEWS['south'])))
            report['cell_projection'] = native.run(client, CELL_PROJECTION)

            def wait_for(requested):
                deadline = time.monotonic()+15.
                while True:
                    actual = native.run(client, READ_WORLD, True)
                    replica = native.run(client, native.REPLICATION % (origin,))
                    if actual == requested and any(row['name'] == requested['name'] and row['aux'] == requested['aux']
                                                   for row in replica['materials']):
                        return {'world': actual, 'replication': replica}
                    if time.monotonic() >= deadline:
                        raise RuntimeError('The native shelf/air did not replicate')
                    time.sleep(.2)

            for label, requested in (('native', material), ('empty', {'name': 'minecraft:air', 'aux': 0})):
                if label == 'empty':
                    native.run(client, native.CLEAR, True)
                report[label+'_replication'] = wait_for(requested)
                boundary(label)
                if not native.run(client, body.WORLD_VISIBLE):
                    raise RuntimeError('The workspace obscures the capture')
                time.sleep(.4)
                before = native.run(client, native.CAMERA_CHECK)
                capture = native.capture(str(args.session), args.owner, args.output/(label+'.png'), Path(frozen['capture_exe']))
                after = native.run(client, native.CAMERA_CHECK)
                if before != after or (label == 'empty' and before != report['captures']['native']['before']):
                    raise RuntimeError('The native/empty camera changed')
                report['captures'][label] = dict(capture, before=before, after=after)
                persist()
            report['observations'] = pixel_observations(args.output/'native.png', args.output/'empty.png', report['cell_projection'])
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
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'source_unchanged', 'native_route_qualified')}))


if __name__ == '__main__':
    main()
