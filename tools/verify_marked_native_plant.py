"""Observe native poppy texture geometry at independently declared coordinates."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time
import uuid

from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, return_value, write_json
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


def observation_scope(args, plan):
    if getattr(args, 'single_positive_control', False):
        target = [6, 117, 6]
        if (args.partition != 'calibration' or args.stage not in ('original', 'alpha_marker') or
                target not in plan['calibration_coordinates']):
            raise ValueError('Single positive control requires original/alpha calibration at (6,117,6)')
        return [target], {'public': VIEWS['public']}
    coordinates = plan['calibration_coordinates'] if args.partition == 'calibration' else (
        plan['holdout_coordinates'] + [plan['height_repeat']])
    return coordinates, VIEWS


def runtime_control(client, session, receipt):
    receipt.update(verified=False, samples=[], render_progress_verified=False)
    clocks = {}
    for round_number in range(2):
        if round_number:
            time.sleep(.15)
        for is_client in (True, False):
            nonce = uuid.uuid4().hex
            response = client.call('execute_code', {
                'code': ("import json,os,sys,time\n_result=json.dumps({'nonce':%r,"
                         "'pid':os.getpid(),'token':getattr(sys,'_pyreact_mcdk_session',None),"
                         "'clock':time.clock()})" % nonce),
                'is_client': is_client, 'direct_return': True})
            value = return_value(response)
            if isinstance(value, str):
                value = json.loads(value)
            receipt['samples'].append({'round': round_number, 'is_client': is_client,
                                       'expected_nonce': nonce, 'response': value})
            if (not isinstance(value, dict) or value.get('nonce') != nonce or
                    value.get('pid') != session['game_pid'] or value.get('token') != session['token']):
                raise ValueError('Live runtime control returned stale or misrouted identity')
            clock = value.get('clock')
            if type(clock) not in (int, float) or not math.isfinite(clock):
                raise ValueError('Live runtime control returned no finite process clock')
            if is_client in clocks and clock <= clocks[is_client]:
                raise ValueError('Live runtime control clock did not advance')
            clocks[is_client] = clock
    receipt['verified'] = True


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
    coordinates, views = observation_scope(args, plan)
    single_control = getattr(args, 'single_positive_control', False)
    frozen_path = args.output.with_name(args.output.stem + '_source.json')
    frozen_record = freeze(frozen_path)
    frozen = json.loads(frozen_path.read_bytes())
    report = {'schema': 1, 'completed': False, 'restored': False, 'rows': [],
              'scope': 'Native bitmap-marker geometry diagnosis; no new plant rendering acceptance',
              'production_acceptance': False, 'stage': args.stage, 'partition': args.partition,
              'plan': record(args.plan), 'calibration': record(args.camera_calibration),
              'session_file': session['session_file'], 'owner': session['owner'],
              'game_pid': session['game_pid'], 'game_identity': session['game_identity'],
              'planned_coordinates': coordinates, 'views': views, 'frozen_source': frozen_record,
              'single_positive_control': single_control, 'marker_pixels_verified': False,
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
    with Client(timeout=8 if single_control else 30) as client:
        check = SignCheck(client, args.output, 20. if single_control else 90., True)
        try:
            if single_control:
                report['runtime_before_mutation'] = {}
                runtime_control(client, session, report['runtime_before_mutation'])
                write_json(args.output, report)
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
                for view, offset in views.items():
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
                    if single_control:
                        row['runtime_after_capture'] = {}
                        runtime_control(client, session, row['runtime_after_capture'])
                        if not row['diagnostic_mask']['pixels']:
                            raise ValueError('Single positive control has no shown-to-blank pixel change')
                    print(json.dumps({'target': target, 'view': view,
                                      'pixels': row['diagnostic_mask']['pixels']}), flush=True)
                restored = cleanup_fixture(client)
                report['cleanups'].append({'target': target, 'results': restored})
                if not all(row['clean'] for row in restored):
                    raise ValueError('Native marker fixture restoration failed')
                pending = False
            report['completed'] = len(report['rows']) == len(coordinates) * len(views)
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
    parser.add_argument('--single-positive-control', action='store_true',
                        help='Capture only calibration cell (6,117,6), public view, with fresh runtime controls')
    args = parser.parse_args()
    report = run(args)
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'source_assets_stable')}))
    return 0 if all(report[key] for key in ('completed', 'restored', 'source_assets_stable')) else 1


if __name__ == '__main__':
    raise SystemExit(main())
