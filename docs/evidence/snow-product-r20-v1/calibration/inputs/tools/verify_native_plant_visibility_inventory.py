"""Inventory native dry visibility for every public snow plant without proxies."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

from verify_debug_blueprints import INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code
from verify_shulker_orientations import server_run
from verify_sign_visuals import SignCheck
from verify_snow_catalogue_visuals import (SnowClient, native_assets, frame_for,
                                         native_boundary, save_mask)
from verify_snow_plant_visibility import (NATIVE_SETUP, NATIVE_NEAR_PLAYER,
                                         NATIVE_CLEANUP, native_capture,
                                         world_cell_roi, cross_assets, count)
from _session import load_session
from projection.debug_snow_blueprints import NAMES, VISUAL_CASE


READ_NATIVE = '''import json,sys
from modern_projection.server_system import WorldAdapter
saved=sys._snow_visibility_native
adapter=WorldAdapter(saved['player'])
target=saved['target']
palette=adapter.palette_block.GetBlockPaletteBetweenPos(saved['dimension'],target,target,False)
data=palette.SerializeBlockPalette() if palette is not None else {}
state=adapter.factory.CreateBlockState(adapter.level)
_result=json.dumps({'front':adapter.info.GetBlockNew(target,saved['dimension']),
 'states':state.GetBlockStates(target,saved['dimension']),
 'palette':dict((key,[[value[0],value[1],indices] for value,indices in data.get(key,{}).items()])
  for key in ('common','extra'))})
'''


class InventoryCheck(SignCheck):
    def capture(self, label, tree=None):
        before = server_run(self.client, READ_NATIVE)
        shot = SignCheck.capture(self, label, tree)
        shot['native_snapshot_before'] = before
        shot['native_snapshot_after'] = server_run(self.client, READ_NATIVE)
        return shot


def source_changes(snapshot):
    changed = []
    for relative, expected in snapshot['hashes_sha256'].items():
        path = Path(snapshot['project']) / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            changed.append(relative)
    return changed


def summarize(report):
    measured = [row['plant'] for row in report['rows']]
    report['completed'] = set(measured) == set(NAMES) and len(measured) == len(NAMES)
    report['observable_requested_plants'] = [row['plant'] for row in report['rows']
                                             if row['observable_requested_plant']]
    report['conditions'] = [{'plant': row['plant'], 'conditions': row['conditions']}
                            for row in report['rows'] if row['conditions']]
    report['inventory_ready'] = (report['completed'] and report['restored']
                                 and report.get('source_assets_stable', False)
                                 and not report.get('frozen_source_changes'))
    report['public_controls_eligible'] = False
    report['new_production_plant_acceptance'] = False


def run(args):
    session = load_session(live=True)
    calibration_raw = args.camera_calibration.read_bytes()
    calibration = json.loads(calibration_raw)
    assert calibration['completed'] and calibration['passed'] and calibration['restored']
    assert Path(calibration['session_file']).resolve() == Path(session['session_file']).resolve()
    snapshot_raw = args.frozen_source.read_bytes()
    snapshot = json.loads(snapshot_raw)
    assert not source_changes(snapshot), 'Frozen runtime/resource source changed before inventory'
    report = {'schema_version': 1, 'completed': False, 'restored': False,
              'inventory_ready': False, 'rows': [], 'plants': list(NAMES),
              'scope': 'Native dry control inventory at one fixed calibrated world position; no editor or projection comparisons',
              'session_file': session['session_file'], 'owner': session['owner'],
              'calibration': {'path': str(args.camera_calibration.resolve()),
                              'sha256': hashlib.sha256(calibration_raw).hexdigest()},
              'frozen_source': {'path': str(args.frozen_source.resolve()),
                                'sha256': hashlib.sha256(snapshot_raw).hexdigest(),
                                'files': len(snapshot['hashes_sha256'])},
              'native_assets': {}, 'fixture_lift_y': args.fixture_lift_y,
              'world_camera_offset': VISUAL_CASE['camera']['world_offset'],
              'limits': {'minimum_observable_pixels': 80, 'native_pixel_change': 20,
                         'native_roi_boundary_contact_pixels': 0},
              'public_controls_eligible': False, 'new_production_plant_acceptance': False}
    installed = saved = native_created = False
    with SnowClient(timeout=30) as client:
        check = InventoryCheck(client, args.output, args.timeout, True)
        try:
            markers = check.run('_result=json.dumps(dict((key,hasattr(sys,key)) for key in '
                                '("_blueprint_qa_saved","_blueprint_visual_saved","_snow_visibility_native")))')
            assert not any(markers.values()), 'Previous fixture needs cleanup: '+repr(markers)
            installed = True
            check.run(INSTALL_PROBE)
            saved = True
            check.run(SAVE_VISUAL)
            report['original_workspace_open'] = check.run('_result=sys._blueprint_qa_saved["workspace"]')
            report['original_visual'] = check.run('_result=json.dumps(sys._blueprint_visual_saved)')
            target = tuple(check.run('_result=json.dumps(tuple(b.player_origin()[i]+(6,8+%r,6)[i] for i in range(3)))' % args.fixture_lift_y))
            report['native_target'] = target
            native_created = True
            report['native_fixture'] = server_run(client, NATIVE_SETUP % (target,))
            report['player_fixture'] = server_run(client, NATIVE_NEAR_PLAYER)
            point = report['player_fixture']['after']
            check.wait('native inventory player replication',
                       lambda foot: all(abs(foot[i]-point[i]) < .1 for i in range(3)),
                       lambda: check.run('_result=json.dumps(b.factory.CreatePos(api.GetLocalPlayerId()).GetFootPos())'))
            time.sleep(3.)
            for plant in NAMES:
                report['native_assets'][plant] = native_assets(session, plant)
                proxy = cross_assets(session, plant)
                foot_before = check.run('_result=json.dumps(b.factory.CreatePos(api.GetLocalPlayerId()).GetFootPos())')
                native = native_capture(check, plant, 'plant', 0, target,
                                        tuple(VISUAL_CASE['camera']['world_offset']), settle_seconds=2.)
                foot_after = check.run('_result=json.dumps(b.factory.CreatePos(api.GetLocalPlayerId()).GetFootPos())')
                assert all(abs(foot_before[i]-foot_after[i]) < .1 for i in range(3)), 'Native inventory player moved during a capture pair'
                size = native['screenshot']['size']
                width, height = size
                crop = (width//4, height//4, width*3//4, height*3//4)
                roi, record = world_cell_roi(check, crop, size, target, native['pose'], calibration)
                frame = frame_for(native['screenshot'], native['hidden_screenshot'], crop, roi)
                boundary = native_boundary(frame, roi, record, crop, size)
                mask = save_mask(frame, args.output, plant+'_dry_native')
                expected_name = 'minecraft:'+plant
                shown = native['screenshot']
                hidden = native['hidden_screenshot']
                requested_stable = all(shown[key]['front']['name'] == expected_name
                                       for key in ('native_snapshot_before', 'native_snapshot_after'))
                hidden_air = all(hidden[key]['front']['name'] == 'minecraft:air'
                                 for key in ('native_snapshot_before', 'native_snapshot_after'))
                conditions = []
                if not requested_stable:
                    conditions.append('Requested plant identity changed around native PNG')
                if not hidden_air:
                    conditions.append('Cleared native reference was not air around PNG')
                if count(frame['object']) < report['limits']['minimum_observable_pixels']:
                    conditions.append('Native dry plant contribution below observable-control minimum')
                if not boundary['passed']:
                    conditions.append('Native dry contribution contacts fixed calibrated ROI boundary')
                row = {'plant': plant, 'kind': 'plant', 'height': 0, 'native': native,
                       'crop': crop, 'world_roi': record, 'native_mask': mask,
                       'native_roi_boundary': boundary, 'native_identity_stable': requested_stable,
                       'cleared_identity_stable': hidden_air,
                       'observable_requested_plant': requested_stable and hidden_air and
                                                     mask['pixels'] >= report['limits']['minimum_observable_pixels'],
                       'existing_cross_proxy': proxy[2] if proxy is not None else None,
                       'conditions': conditions}
                report['rows'].append(row)
                write_json(args.output, report)
                print(json.dumps({'plant': plant, 'native_pixels': mask['pixels'],
                                  'observable_requested_plant': row['observable_requested_plant'],
                                  'existing_cross_proxy': proxy is not None, 'conditions': conditions}), flush=True)
            report['source_assets_stable'] = all(native_assets(session, plant) == value
                                                 for plant, value in report['native_assets'].items())
        finally:
            prior = sys.exc_info()[0]
            if prior is not None:
                report['error'] = '%s: %s' % (prior.__name__, sys.exc_info()[1])
            errors = []
            actions = []
            if native_created:
                def cleanup_native():
                    exists = server_run(client, 'import sys\n_result=hasattr(sys,"_snow_visibility_native")')
                    return server_run(client, NATIVE_CLEANUP) if exists else [{'resource': 'fixture_not_created', 'clean': True}]
                actions.append(('native_fixture', cleanup_native))
            if saved:
                def restore_visual():
                    exists = check.run('_result=hasattr(sys,"_blueprint_visual_saved")')
                    if exists:
                        check.run(camera_restore_code(False))
                        check.run('saved=sys._blueprint_visual_saved\ns.origin=saved["origin"]\ns.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\ndel sys._blueprint_visual_saved\n_result=True')
                actions.extend((('projection', lambda: check.run('b.stop_projection()\n_result=True')),
                                ('visual', restore_visual)))
            if installed:
                def restore_workspace():
                    exists = check.run('_result=hasattr(sys,"_blueprint_qa_saved")')
                    return check.run(RESTORE) if exists else None
                actions.append(('workspace', restore_workspace))
            for name, action in actions:
                try:
                    value = action()
                    if name == 'native_fixture':
                        report['native_cleanup'] = value
                        assert value and all(row['clean'] for row in value)
                except Exception as error:
                    errors.append(name+': '+str(error))
            if saved and installed and not errors and 'original_visual' in report:
                try:
                    original_open = report['original_workspace_open']
                    navigation = check.navigation()
                    if original_open and not navigation['open']:
                        check.run('owner.open_workspace()\n_result=True')
                    elif not original_open and navigation['open']:
                        check.run('navigator.pop()\n_result=True')
                    report['restored_navigation'] = check.wait('restore inventory navigation',
                        lambda value: value['open'] == original_open and not value['transition'], check.navigation)
                    current = check.run('''cam=b.factory.CreateCamera(b.level)
_result=json.dumps({'origin':s.origin,'opacity':s.opacity,'missing':s.projection_missing,
 'outline':s.projection_outline,'camera_rot':cam.GetCameraRotation(),
 'pitch_lock':cam.IsModCameraLockPitch(),'yaw_lock':cam.IsModCameraLockYaw()})''')
                    report['restored_visual'] = current
                    original = report['original_visual']
                    assert all(current[key] == original[key] for key in ('origin', 'opacity', 'missing', 'outline', 'pitch_lock', 'yaw_lock'))
                    assert all(abs(current['camera_rot'][i]-original['camera_rot'][i]) < .01 for i in range(3))
                except Exception as error:
                    errors.append('restoration_readback: '+str(error))
            report['cleanup_errors'] = errors
            report['binding_read_failures'] = client.binding_read_failures
            report['restored'] = not errors
            report['frozen_source_changes'] = source_changes(snapshot)
            summarize(report)
            write_json(args.output, report)
            if errors and prior is None:
                raise RuntimeError('Native plant inventory cleanup failed: '+repr(errors))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--camera-calibration', type=Path, required=True)
    parser.add_argument('--frozen-source', type=Path, required=True)
    parser.add_argument('--fixture-lift-y', type=int, default=16)
    parser.add_argument('--timeout', type=float, default=60.)
    args = parser.parse_args()
    report = run(args)
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'inventory_ready',
                                                  'observable_requested_plants', 'conditions',
                                                  'public_controls_eligible')}))
    return 0 if report['inventory_ready'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
