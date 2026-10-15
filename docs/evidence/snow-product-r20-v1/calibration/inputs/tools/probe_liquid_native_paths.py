"""Compare four direct native mesh paths for the public adjacent-water fixture.

Uses the existing owned native path harness, without production context packing,
bank selection or rendering proxies. Requires reliable background native PNGs.
"""
import itertools
import time
import uuid

from PIL import ImageChops

import verify_dripstone_direct_seed as direct
import verify_wet_actor_visuals as wet
from projection.cell import encode
from projection.debug_blueprints import build


CASE = wet.CASES['sign_adjacent_water']
ORIGIN = (0, 89, 0)


def fixture_cells():
    metadata, scene = CASE
    document = build(metadata['fixture'])
    def rows(positions):
        return [(tuple(pos[i] + ORIGIN[i] for i in range(3)), encode(document.get(pos)))
                for pos in positions]
    return rows(scene['cells']), rows(scene['supports'])


CAMERA = '''target,offset=%r,%r
position=tuple(target[i]+offset[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
assert len(direction)>=2,direction
rotation=(direction[0],direction[1]+180.,0.)
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position) and cam.SetCameraRotation(rotation)
_result=json.dumps({'position':position,'rotation':rotation,'target':target})
'''


def execute(check, args, report):
    metadata, scene = CASE
    cells, supports = fixture_cells()
    all_cells = supports + cells
    positions = [pos for pos, value in all_cells]
    keep = tuple(scene['keep'][i] + ORIGIN[i] for i in range(3))
    actor = tuple(scene['actor'][i] + ORIGIN[i] for i in range(3))
    target = tuple((keep[i] + actor[i] + 1.) / 2. for i in range(3))
    report.update(fixture=metadata['fixture'], public_case=scene['id'], origin=ORIGIN,
                  cells=cells, supports=supports,
                  method='Direct native world, returned palette, captured palette and roundtrip; public wet fixture')
    report.pop('native_aabb_reference', None)
    report['public_fixture_source'] = direct.fingerprint(
        direct.ROOT / 'behavior_pack/modern_projection/projection/debug_sign_blueprints.py')
    report['world_setup'] = direct.run(check.client, wet.reserve_code(cells, supports, ORIGIN))
    report['near_player'] = direct.run(check.client, direct.world.NEAR_PLAYER % (cells,))
    direct.world.player_ready(check, report['near_player']['after'])
    report['replication'] = wet.replication(check, all_cells)
    report['generation'] = check.run(direct.GENERATE % (positions, 'liquid_native_' + uuid.uuid4().hex, direct.PATHS))
    pose = check.run(CAMERA % (target, tuple(metadata['camera_offset'])))
    time.sleep(.35)
    shown = direct.capture(check, 'world', pose)
    direct.run(check.client, direct.world.CLEAR_SOURCE % (all_cells,))
    report['cleared'] = wet.replication(check, all_cells, True)
    time.sleep(.35)
    hidden = direct.capture(check, 'world_empty', pose)
    baseline = direct.native.signal(shown['path'], hidden['path'])
    projection = check.run(direct.ROIS % ([keep, actor], target))
    first, second, roi = direct.native.roi_masks(projection, baseline.size, keep, actor, args.calibration)
    mask = ImageChops.lighter(first, second)
    report['world'] = {'shown': shown, 'hidden': hidden, 'roi': roi, 'camera': pose}
    report['paths'], signals = {}, {}
    for key in direct.PATHS:
        item = {'attachment': check.run(direct.ATTACH % key)}
        time.sleep(.35)
        item['shown'] = direct.capture(check, key + '_shown', pose)
        check.run(direct.VISIBILITY % True)
        time.sleep(.35)
        item['hidden'] = direct.capture(check, key + '_hidden', pose)
        signal = direct.native.signal(item['shown']['path'], item['hidden']['path'])
        signals[key] = signal
        item['world_match'] = direct.compare(baseline, signal, mask, args.threshold, args.min_pixels * 2)
        item['components'] = wet.component_checks(baseline, signal, (first, second),
                                                  shown['path'], args.threshold, args.min_pixels)
        signal_path = args.output.with_name(args.output.stem + '_' + key + '_signal.png')
        signal.save(signal_path)
        item['signal'] = direct.fingerprint(signal_path)
        report['paths'][key] = item
        direct.write_json(args.output, report)
    report['pairwise'] = {
        first_path + '_vs_' + second_path: direct.compare(signals[first_path], signals[second_path],
                                                        mask, args.threshold, args.min_pixels * 2)
        for first_path, second_path in itertools.combinations(direct.PATHS, 2)
    }
    report['completed'] = True
    report['all_paths_match_world'] = all(item['world_match']['passed'] and
                                         all(part['passed'] for part in item['components'].values())
                                         for item in report['paths'].values())
    report['pairwise_equal_under_contract'] = all(item['passed'] for item in report['pairwise'].values())


if __name__ == '__main__':
    direct.execute = execute
    raise SystemExit(direct.main())
