"""Capture exact public liquid snapshots in an owned world with flow disabled.

This establishes native controls only. It does not infer corner heights, UVs,
hidden faces, or production geometry from a successful capture.
"""
import argparse
import copy
import itertools
import json
from pathlib import Path
import sys
import uuid

from PIL import Image, ImageChops, ImageDraw

import capture_pure_liquid_native_controls as contained
from camera_projection import project_points
from projection.cell import AIR, encode
from projection.debug_liquid_blueprints import VISUAL_CASE, source_document
from verify_missing_neighbor_visuals import hull

ROOT = Path(__file__).resolve().parents[1]
CASE_IDS = tuple(row['id'] for row in VISUAL_CASE['cases'])
FLOW_START = '''saved=sys._neighbor_world_saved
assert saved['pure_liquid_token']==%r
assert not hasattr(sys,'_frozen_liquid_flow_owner'), 'Previous flow owner must be restored'
game=api.GetEngineCompFactory().CreateGame(api.GetLevelId())
sys._frozen_liquid_flow_owner=%r
assert game.ForbidLiquidFlow(True), 'Native flow freeze failed'
saved['shell_verified']=True
_result=json.dumps({'forbidden':True,'baseline':'Fresh owner-bound world; initial flow is allowed',
 'native_return_verified':True,'has_state_getter':False})
'''
FLOW_RESTORE = '''assert getattr(sys,'_frozen_liquid_flow_owner',None)==%r
game=api.GetEngineCompFactory().CreateGame(api.GetLevelId())
assert game.ForbidLiquidFlow(False), 'Native flow restoration failed'
del sys._frozen_liquid_flow_owner
_result=json.dumps({'flow_allowed_requested':True,'native_return_verified':True,
 'has_state_getter':False})
'''


def fixture_plan(identity, cell_origin, platform):
    row = next((item for item in VISUAL_CASE['cases'] if item['id'] == identity), None)
    if row is None:
        raise ValueError('Unknown public liquid case: ' + identity)
    document_origin = tuple(cell_origin[i] - VISUAL_CASE['focus'][i] for i in range(3))
    controls = {}
    for control in contained.CONTROLS:
        document = source_document(identity, isolated=True, control=control)
        controls[control] = {'cells': [
            (tuple(document_origin[i] + pos[i] for i in range(3)), encode(value))
            for pos, value in sorted(document.blocks.items())]}
    positions = [pos for pos, unused in controls['supported_positive']['cells']]
    low = tuple(min(pos[i] for pos in positions) - 1 for i in range(3))
    high = tuple(max(pos[i] for pos in positions) + 1 for i in range(3))
    cavity = set(itertools.product(*(range(low[i], high[i] + 1) for i in range(3))))
    platform = tuple(platform)
    guard = {(platform[0] + x, platform[1] + y, platform[2] + z)
             for x in (-1, 0, 1) for y in range(4) for z in (-1, 0, 1)}
    cavity.update(guard - {platform})
    if platform in cavity:
        raise ValueError('Player platform overlaps the liquid fixture reservation')
    return {'case': identity, 'fixture': VISUAL_CASE['fixture'], 'kind': row['kind'],
            'layer': row['layer'], 'cell_origin': tuple(cell_origin),
            'document_origin': document_origin, 'platform': platform,
            'original_keep': row['keep'], 'isolated_keep': VISUAL_CASE['focus'],
            'shell': [], 'shell_value': AIR, 'cavity': sorted(cavity),
            'reserved': sorted(cavity | {platform}), 'controls': controls,
            'context_changed': False, 'flow_disabled': True}


def native_gate(before, after, plan, requested):
    expected = requested + [(plan['platform'], encode(('minecraft:stone', 0)))]
    sides = {}
    for side in ('server', 'client'):
        sides[side] = {
            'before_matches': contained.matches(before[side], expected, plan['reserved']),
            'after_matches': contained.matches(after[side], expected, plan['reserved']),
            'changes': contained.native_changes(before[side], after[side], plan['reserved'])}
    passed = all(row['before_matches'] and row['after_matches'] and row['changes']['unchanged']
                 for row in sides.values())
    return {'public_snapshot_unchanged': passed, 'sides': sides,
            'flow_disabled': True, 'geometry_accepted': False}


def masks(check, direct, plan, pose, size, calibration):
    documents = {key: source_document(plan['case'], isolated=True, control=key)
                 for key in ('liquid_only', 'supported_negative')}
    projected = {}
    for key, document in documents.items():
        positions = [tuple(plan['document_origin'][i] + pos[i] for i in range(3))
                     for pos in document.blocks]
        points = check.run(direct.ROIS % (positions, pose['target']))
        scale = (size[0] / points['screen'][0], size[1] / points['screen'][1])
        mask = Image.new('L', size)
        drawer = ImageDraw.Draw(mask)
        for entry in points['cells']:
            pixels = project_points(entry['world_points'], pose['stable']['position'], pose['target'],
                                    points['screen'], calibration['vertical_fov'])
            polygon = hull((point['screenX'] * scale[0], point['screenY'] * scale[1]) for point in pixels)
            drawer.polygon(polygon, fill=255)
        projected[key] = mask
    from PIL import ImageFilter
    support = projected['supported_negative'].filter(ImageFilter.MaxFilter(7))
    liquid = ImageChops.subtract(projected['liquid_only'], support)
    return liquid, projected['supported_negative']


class FrozenHarness(contained.NativeHarness):
    def freeze(self):
        return self.server(contained.server_code(FLOW_START % (self.token, self.token)))

    def delete_marker(self):
        self.report['flow_restore'] = self.server(contained.server_code(FLOW_RESTORE % self.token))
        self.checkpoint()
        return super().delete_marker()


def execute_controls(harness, options, runtime_args, report):
    direct, wet, check = harness.direct, harness.wet, harness.check
    source = tuple(options.cell_origin)
    offset = tuple(VISUAL_CASE['camera']['world_offset'])
    base = source_document(options.case[0], isolated=True)
    cells = [(tuple(source[i] + pos[i] - VISUAL_CASE['focus'][i] for i in range(3)), encode(value))
             for pos, value in base.blocks.items()]
    platform = wet.camera_side_platform(cells, offset)
    plans = [fixture_plan(identity, source, platform) for identity in options.case]
    # A single air reservation covers all chosen states and neighbor arrangements.
    reservation = copy.deepcopy(plans[0])
    reservation['cavity'] = sorted(set(tuple(pos) for plan in plans for pos in plan['cavity']))
    reservation['reserved'] = sorted(set(tuple(pos) for plan in plans for pos in plan['reserved']))
    report.update(schema=1, method='Public native liquid snapshots with SDK flow disabled; no shell',
                  fixture=VISUAL_CASE['fixture'], context_changed=False,
                  native_geometry_accepted=False, accuracy_accepted=False,
                  public_controls_eligible=False,
                  registry_version=VISUAL_CASE['registry_version'],
                  registry_fingerprint=VISUAL_CASE['registry_fingerprint'],
                  runner_source=direct.fingerprint(Path(__file__)),
                  public_fixture_source=direct.fingerprint(
                      ROOT / 'behavior_pack/modern_projection/projection/debug_liquid_blueprints.py'),
                  reservation=reservation, cases=[],
                  limits='Flow suppression changes simulation, not source neighbors. No native flow-state getter; '
                         'the baseline is a newly created owned world. No inferred corner heights or hidden faces.')
    report.pop('native_aabb_reference', None)
    harness.checkpoint()
    report['world_setup'] = harness.reserve(reservation)
    if not report['world_setup']['reserved']:
        raise RuntimeError('Reservation is not verified foreground/background air')
    harness.checkpoint()
    report['flow_freeze'] = harness.freeze()
    harness.checkpoint()
    report['near_player'] = harness.server(wet.NEAR_PLAYER % (platform,))
    report['near_player']['client'] = direct.world.player_ready(check, report['near_player']['after'])
    target = tuple(source[i] + .5 for i in range(3))
    pose = check.run(contained.CAMERA % (target, offset))
    harness.settle()
    pose['stable'] = check.run(direct.native.CAMERA_STATE)
    report['camera'] = pose
    actual_player = check.run('_result=json.dumps(b.player_position.GetFootPos())')
    report['player_camera_side'] = wet.player_camera_side(actual_player, pose)
    if not report['player_camera_side']['passed']:
        raise RuntimeError('Native player is on the opposite camera side')
    expected_size = None
    for plan in plans:
        plan['cavity'], plan['reserved'] = reservation['cavity'], reservation['reserved']
        row = {'case': plan['case'], 'source': plan, 'controls': {}, 'completed': False}
        report['cases'].append(row)
        harness.checkpoint()
        for control in contained.CONTROLS:
            item = row['controls'][control] = {'completed': False, 'requested': plan['controls'][control]}
            contained.clear_cavity(harness, plan, item)
            item['write'] = harness.write(plan['controls'][control]['cells'])
            if not all(entry['written'] for entry in item['write']['writes']):
                raise RuntimeError('Native control write failed; no retry')
            harness.settle()
            item['native_before_capture'] = harness.snapshot(plan['reserved'])
            harness.checkpoint()
            item['capture'] = harness.frame(plan['case'] + '_' + control, pose)
            item['fixed_viewport'] = contained.fixed_viewport(item['capture'], pose)
            item['png_validation'] = contained.validate_png(item['capture'], harness.session, expected_size)
            expected_size = item['png_validation']['size']
            item['native_after_capture'] = harness.snapshot(plan['reserved'])
            item['native_gate'] = native_gate(item['native_before_capture'], item['native_after_capture'],
                                               plan, plan['controls'][control]['cells'])
            item['completed'] = True
            harness.checkpoint()
            if not item['native_gate']['public_snapshot_unchanged']:
                raise RuntimeError('Native source or surrounding layers changed during capture')
        liquid_mask, support_mask = masks(check, direct, plan, pose, expected_size, runtime_args.calibration)
        paths = {key: item['capture']['path'] for key, item in row['controls'].items()}
        row['pixel_controls'], signals = contained.positive_pixel_controls(
            paths, liquid_mask, support_mask, runtime_args.threshold, runtime_args.min_pixels)
        row['signals'] = {}
        for label, image in signals.items():
            path = runtime_args.output.with_name(runtime_args.output.stem + '_' + plan['case'] + '_' + label + '_signal.png')
            image.save(path)
            row['signals'][label] = direct.fingerprint(path)
        row['native_controls_passed'] = row['pixel_controls']['independent_liquid_signals_passed']
        row['completed'] = True
        harness.checkpoint()
    report['completed'] = True
    report['native_controls_passed'] = all(row['native_controls_passed'] for row in report['cases'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case', choices=CASE_IDS, action='append', required=True)
    parser.add_argument('--cell-origin', type=int, nargs=3, required=True)
    parser.add_argument('--capture-helper', type=Path, required=True)
    parser.add_argument('--camera-calibration', type=Path, required=True)
    parser.add_argument('--fresh-owned-world', action='store_true', required=True,
                        help='Requires an untouched, newly created test world with default flow enabled')
    parser.add_argument('--threshold', type=int, default=16)
    parser.add_argument('--min-pixels', type=int, default=80)
    parser.add_argument('--settle-seconds', type=float, default=.35)
    options = parser.parse_args(argv)
    if (len(set(options.case)) != len(options.case) or options.output.exists() or
            any(options.output.parent.glob(options.output.stem + '_*'))):
        parser.error('Use unique cases and a fresh report/capture prefix')
    if not .35 <= options.settle_seconds < 10 or not 0 <= options.threshold < 255 or options.min_pixels <= 0:
        parser.error('Invalid settle time or pixel gates')
    import verify_dripstone_direct_seed as direct
    originals = (direct.world.CASES, direct.native.VIEWS, direct.native.VISUAL_CASES, direct.world.BlueprintCheck)
    import verify_wet_actor_visuals as wet
    direct.world.CASES, direct.native.VIEWS, direct.native.VISUAL_CASES, direct.world.BlueprintCheck = originals
    saved_execute, saved_clear, saved_argv = direct.execute, direct.world.clear_world, sys.argv
    active, token = {}, uuid.uuid4().hex

    def execute(check, args, report):
        args.settle_seconds = options.settle_seconds
        harness = FrozenHarness(direct, wet, check, args, report, token)
        active.update(harness=harness, report=report)
        execute_controls(harness, options, args, report)

    def clear_world(client):
        if 'reservation' not in active.get('report', {}):
            return {'restored': True, 'player_foot': None, 'no_owned_reservation': True}
        return contained.cleanup_containment(active['harness'], active['report']['reservation'], active['report'])

    try:
        direct.execute, direct.world.clear_world = execute, clear_world
        sys.argv = [str(Path(__file__)), str(options.output), '--capture-helper', str(options.capture_helper),
                    '--camera-calibration', str(options.camera_calibration), '--threshold', str(options.threshold),
                    '--min-pixels', str(options.min_pixels), '--background-only']
        return direct.main()
    finally:
        direct.execute, direct.world.clear_world, sys.argv = saved_execute, saved_clear, saved_argv


if __name__ == '__main__':
    raise SystemExit(main())
