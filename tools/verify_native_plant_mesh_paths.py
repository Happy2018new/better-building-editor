"""Compare native dry plants with four unmodified engine mesh sources."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid

from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code
from verify_dripstone_direct_seed import GENERATE, ATTACH, VISIBILITY, CLEANUP, PATHS
from verify_native_plant_boxes import replicated
from verify_shulker_orientations import server_run
from verify_sign_visuals import SignCheck
from verify_snow_catalogue_visuals import native_assets, native_boundary, save_mask
from verify_snow_plant_visibility import (NATIVE_SETUP, NATIVE_NEAR_PLAYER, NATIVE_MUTATE,
                                         NATIVE_CLEANUP, native_capture, world_cell_roi,
                                         capture_frame, compare_native)
from verify_fungus_remaining_matrix import freeze, source_errors
from _session import load_session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'behavior_pack/modern_projection'))
from projection.debug_snow_blueprints import VISUAL_CASE


def run(args):
    if args.output.exists():
        raise ValueError('Native plant mesh evidence must have a fresh output path')
    session = load_session(live=True)
    if Path(session['project']).resolve() != ROOT:
        raise ValueError('The session belongs to a different project')
    calibration = json.loads(args.camera_calibration.read_bytes())
    if (not calibration['completed'] or not calibration['passed'] or not calibration['restored'] or
            Path(calibration['session_file']).resolve() != Path(session['session_file']).resolve()):
        raise ValueError('A passed calibration from this owned session is required')
    case = VISUAL_CASE['static_root_screen']
    target = tuple(case['native_target'])
    frozen_path = args.output.with_name(args.output.stem+'_source.json')
    frozen_record = freeze(frozen_path)
    frozen = json.loads(frozen_path.read_bytes())
    extra_paths = (Path(__file__), ROOT/'tools/verify_dripstone_direct_seed.py',
                   ROOT/'tools/verify_native_plant_boxes.py')
    extra_hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in extra_paths}
    report = {'schema': 1, 'completed': False, 'restored': False, 'passed': False, 'rows': [],
              'session_file': session['session_file'], 'owner': session['owner'],
              'game_pid': session['game_pid'], 'game_identity': session['game_identity'],
              'calibration': calibration, 'frozen_source': frozen_record,
              'extra_source_sha256': extra_hashes, 'blueprint_case': case,
              'plants': args.plant, 'native_target': target, 'native_assets': {},
              'scope': 'Dry source-path diagnosis only; no new production or random-offset acceptance',
              'limits': {'native_recall': .75, 'native_precision': .75,
                         'native_edge_tolerance_pixels': 3}}
    installed = saved = native_created = False
    cleanup_errors = []
    with Client(timeout=30) as client:
        check = SignCheck(client, args.output, 90., True)
        try:
            check.run(INSTALL_PROBE)
            installed = True
            check.run(SAVE_VISUAL)
            saved = True
            native_created = True
            report['fixture'] = server_run(client, NATIVE_SETUP % (target,))
            report['near_player'] = server_run(client, NATIVE_NEAR_PLAYER)
            time.sleep(3.)
            for plant in args.plant:
                report['native_assets'][plant] = native_assets(session, plant)
                for view, offset in case['views'].items():
                    native = native_capture(check, plant, 'plant', 0, target, tuple(offset), 2.)
                    row = {'plant': plant, 'view': view, 'native': native, 'paths': {}}
                    width, height = native['screenshot']['size']
                    crop = (width//4, height//4, width*3//4, height*3//4)
                    roi, roi_record = world_cell_roi(check, crop, (width, height), target,
                                                    native['pose'], calibration)
                    row.update(crop=crop, world_roi=roi_record)
                    native_frame = capture_frame(native['screenshot']['path'], crop,
                                                 native['hidden_screenshot']['path'], roi=roi)
                    row['native_mask'] = save_mask(native_frame, args.output, plant+'_'+view+'_native')
                    row['native_roi_boundary'] = native_boundary(native_frame, roi, roi_record,
                                                                 crop, (width, height))
                    server_run(client, NATIVE_MUTATE % (plant, 'plant', 0))
                    replicated(check, target, 'minecraft:'+plant)
                    try:
                        row['generated'] = check.run(GENERATE % ([target], 'plant_path_'+uuid.uuid4().hex, PATHS))
                        server_run(client, NATIVE_MUTATE % (plant, 'blank', 0))
                        replicated(check, target, 'minecraft:air')
                        time.sleep(2.)
                        for path in PATHS:
                            label = plant+'_'+view+'_'+path
                            attachment = check.run(ATTACH % path)
                            time.sleep(.5)
                            shown = check.capture(label+'_shown')
                            try:
                                check.run(VISIBILITY % True)
                                time.sleep(.3)
                                hidden = check.capture(label+'_hidden')
                            finally:
                                check.run(VISIBILITY % False)
                            actual = capture_frame(shown['path'], crop, hidden['path'], roi=roi)
                            comparison = compare_native(native_frame, actual, foliage=False)
                            comparison['native_roi_not_clipped'] = row['native_roi_boundary']['passed']
                            comparison['passed'] = comparison['passed'] and comparison['native_roi_not_clipped']
                            row['paths'][path] = {'attachment': attachment, 'shown': shown,
                                                  'hidden': hidden, 'comparison': comparison,
                                                  'mask': save_mask(actual, args.output, label)}
                    finally:
                        check.run(CLEANUP)
                    report['rows'].append(row)
                    write_json(args.output, report)
                    print(json.dumps({'plant': plant, 'view': view,
                                      'paths': {name: value['comparison'] for name, value in row['paths'].items()}}),
                          flush=True)
            report['completed'] = len(report['rows']) == len(args.plant)*len(case['views'])
            report['passed'] = report['completed'] and all(value['comparison']['passed']
                for row in report['rows'] for value in row['paths'].values())
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            actions = [('mesh', lambda: check.run(CLEANUP))]
            if native_created:
                def clean_native():
                    exists = server_run(client, 'import sys\n_result=hasattr(sys,"_snow_visibility_native")')
                    return server_run(client, NATIVE_CLEANUP) if exists else [{'clean': True}]
                actions.append(('native_fixture', clean_native))
            if saved:
                actions.extend((('projection', lambda: check.run('b.stop_projection()\n_result=True')),
                                ('camera', lambda: check.run(camera_restore_code(False))),
                                ('visual', lambda: check.run('saved=sys._blueprint_visual_saved\ns.origin=saved["origin"]\ns.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\ndel sys._blueprint_visual_saved\n_result=True'))))
            if installed:
                actions.append(('workspace', lambda: check.run(RESTORE)))
            for label, action in actions:
                try:
                    value = action()
                    report[label+'_restored'] = value
                    if label == 'native_fixture' and not all(row['clean'] for row in value):
                        raise ValueError('Native fixture restoration failed')
                except Exception as error:
                    cleanup_errors.append(label+': '+str(error))
            report['cleanup_errors'] = cleanup_errors
            report['restored'] = installed and not cleanup_errors
            report['source_errors'] = source_errors(frozen)
            report['source_assets_stable'] = not report['source_errors'] and all(
                hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
                for path, expected in extra_hashes.items())
            report['passed'] = report['passed'] and report['restored'] and report['source_assets_stable']
            write_json(args.output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--camera-calibration', type=Path, required=True)
    parser.add_argument('--plant', choices=('stone', 'crimson_roots', 'warped_roots', 'nether_sprouts'),
                        action='append', required=True)
    args = parser.parse_args()
    args.plant = tuple(dict.fromkeys(args.plant))
    report = run(args)
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'passed', 'source_assets_stable')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
