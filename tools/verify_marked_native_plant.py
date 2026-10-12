"""Observe native poppy texture geometry at independently declared coordinates."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code
from verify_fungus_remaining_matrix import freeze, source_errors
from verify_native_plant_boxes import SERVER_BOXES, cleanup_fixture
from verify_shulker_orientations import server_run
from verify_sign_visuals import SignCheck
from verify_snow_plant_visibility import (NATIVE_SETUP, NATIVE_NEAR_PLAYER, NATIVE_MUTATE,
                                         native_capture, capture_frame, count)
from _session import load_session
from prepare_marked_native_plant import validate_marker

ROOT = Path(__file__).resolve().parents[1]
VIEWS = {'public': (-2., .15, -2.5), 'right': (2., .15, -2.5)}
GRAPHICS_STATE = '''game=b.factory.CreateGame(b.level)
view=b.factory.CreatePlayerView(b.level)
options=api.GetMinecraftEnum().OptionId
_result=json.dumps({'runtime':api.GetMinecraftVersion(),
 'options':dict((name,view.GetToggleOption(getattr(options,name)))
                for name in ('GRAPHICS','FANCY_SKIES','SMOOTH_LIGHTING','RENDER_CLOUDS'))})'''


def record(path):
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def run(args):
    session = load_session(live=True)
    if Path(session['project']).resolve() != ROOT or args.output.exists():
        raise ValueError('Choose fresh evidence in the owned project')
    helper = os.environ.get('MCDEV_NATIVE_CAPTURE_HELPER')
    if helper is None or Path(helper).resolve() != ROOT / 'tools/capture_native_window.py':
        raise ValueError('Owner-bound native WGC helper is required')
    calibration = json.loads(args.camera_calibration.read_bytes())
    if (not all(calibration.get(key) for key in ('completed', 'passed', 'restored')) or
            Path(calibration['session_file']).resolve() != Path(session['session_file']).resolve()):
        raise ValueError('Passed same-session camera calibration is required')
    plan = json.loads(args.plan.read_bytes())
    coordinates = plan['calibration_coordinates'] if args.partition == 'calibration' else (
        plan['holdout_coordinates'] + [plan['height_repeat']])
    frozen_path = args.output.with_name(args.output.stem + '_source.json')
    frozen_record = freeze(frozen_path)
    frozen = json.loads(frozen_path.read_bytes())
    report = {'schema': 1, 'completed': False, 'restored': False, 'rows': [],
              'scope': 'Native bitmap-marker geometry diagnosis; no new plant rendering acceptance',
              'production_acceptance': False, 'stage': args.stage, 'partition': args.partition,
              'plan': record(args.plan), 'calibration': record(args.camera_calibration),
              'session_file': session['session_file'], 'owner': session['owner'],
              'game_pid': session['game_pid'], 'game_identity': session['game_identity'],
              'planned_coordinates': coordinates, 'views': VIEWS, 'frozen_source': frozen_record,
              'probe': record(Path(__file__)), 'cleanup_errors': [], 'cleanups': []}
    override = ROOT / 'resource_pack/textures/blocks/flower_rose.png'
    report['marker_override'] = record(override) if override.is_file() else None
    if (args.stage == 'original') != (report['marker_override'] is None):
        raise ValueError('Declared marker stage differs from the pack bitmap override')
    if args.stage != 'original':
        if args.marker_snapshot is None:
            raise ValueError('A prepared marker snapshot is required for marker observations')
        validate_marker(args.marker_snapshot, args.plan, args.stage)
        report['marker_snapshot'] = record(args.marker_snapshot)
    write_json(args.output, report)
    installed = saved = pending = False
    with Client(timeout=30) as client:
        check = SignCheck(client, args.output, 90., True)
        try:
            if server_run(client, 'import sys\n_result=hasattr(sys,"_snow_visibility_native")'):
                raise ValueError('Previous native snow fixture needs cleanup')
            check.run(INSTALL_PROBE)
            installed = True
            check.run(SAVE_VISUAL)
            saved = True
            report['graphics_state'] = check.run(GRAPHICS_STATE)
            for number, target in enumerate(coordinates):
                target = tuple(target)
                report['active_target'] = target
                write_json(args.output, report)
                pending = True
                fixture = server_run(client, NATIVE_SETUP % (target,))
                near = server_run(client, NATIVE_NEAR_PLAYER)
                time.sleep(2.)
                for view, offset in VIEWS.items():
                    server_run(client, NATIVE_MUTATE % ('poppy', 'plant', 0))
                    boxes = server_run(client, SERVER_BOXES)
                    native = native_capture(check, 'poppy', 'plant', 0, target, offset, 2.)
                    width, height = native['screenshot']['size']
                    crop = (width // 4, height // 4, width * 3 // 4, height * 3 // 4)
                    frame = capture_frame(native['screenshot']['path'], crop,
                                          native['hidden_screenshot']['path'])
                    mask = args.output.with_name(args.output.stem + '_cell%d_%s_mask.png' % (number, view))
                    if mask.exists():
                        raise ValueError('Native marker mask output must be fresh')
                    frame['object'].save(mask)
                    row = {'target': target, 'view': view, 'fixture': fixture, 'near_player': near,
                           'native': native, 'boxes': boxes, 'crop': crop,
                           'diagnostic_mask': dict(record(mask), pixels=count(frame['object']),
                                                   bounds=frame['object'].getbbox())}
                    row['graphics_state'] = check.run(GRAPHICS_STATE)
                    if row['graphics_state'] != report['graphics_state']:
                        raise ValueError('Native graphics state changed during marker observation')
                    report['rows'].append(row)
                    write_json(args.output, report)
                    print(json.dumps({'target': target, 'view': view,
                                      'pixels': row['diagnostic_mask']['pixels']}), flush=True)
                restored = cleanup_fixture(client)
                report['cleanups'].append({'target': target, 'results': restored})
                if not all(row['clean'] for row in restored):
                    raise ValueError('Native marker fixture restoration failed')
                pending = False
            report['completed'] = len(report['rows']) == len(coordinates) * len(VIEWS)
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            actions = []
            if pending:
                actions.append(('native', lambda: cleanup_fixture(client)))
            if saved:
                actions.extend((('projection', lambda: check.run('b.stop_projection()\n_result=True')),
                                ('camera', lambda: check.run(camera_restore_code(False))),
                                ('visual', lambda: check.run('saved=sys._blueprint_visual_saved\ns.origin=saved["origin"]\ns.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\ndel sys._blueprint_visual_saved\n_result=True'))))
            if installed:
                actions.append(('workspace', lambda: check.run(RESTORE)))
            for label, action in actions:
                try:
                    restored = action()
                    report[label + '_restored'] = restored
                    if label == 'native' and not all(row['clean'] for row in restored):
                        raise ValueError('Native marker fixture not restored')
                except Exception as error:
                    report['cleanup_errors'].append(label + ': ' + str(error))
            report['restored'] = installed and not report['cleanup_errors']
            report['source_errors'] = source_errors(frozen)
            if record(Path(__file__)) != report['probe']:
                report['source_errors'].append('Native marker probe changed during observation')
            if args.stage != 'original':
                try:
                    validate_marker(args.marker_snapshot, args.plan, args.stage)
                except (OSError, ValueError, KeyError) as error:
                    report['source_errors'].append('Marker validation: ' + str(error))
            report['source_assets_stable'] = not report['source_errors']
            write_json(args.output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--camera-calibration', type=Path, required=True)
    parser.add_argument('--marker-snapshot', type=Path)
    parser.add_argument('--stage', choices=('original', 'alpha_marker', 'opaque_marker'), required=True)
    parser.add_argument('--partition', choices=('calibration', 'holdout'), default='calibration')
    args = parser.parse_args()
    report = run(args)
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'source_assets_stable')}))
    return 0 if all(report[key] for key in ('completed', 'restored', 'source_assets_stable')) else 1


if __name__ == '__main__':
    raise SystemExit(main())
