"""Bind the original native baseline and retained marker failures without acceptance."""
import argparse
import hashlib
import json
from pathlib import Path

from verify_debug_blueprints import write_json
from _session import process_identity

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parents[1]
INSTANCES = Path('C:/Users/Happy2018new/.pyreact-debug/instances')
BASELINE = '8c6723d6a08f49af9464f1e23bea232c'
FIRST_MARKER = '22852a6c89374b79a7d16f75ca8c94c1'
CONTROL = 'dd24458e830443f583aa49c6fbc01845'
RETRY_MARKER = '517f7c483aa647e784ccdb37bab9bc45'
OWNER = 'snow-r11-position'


def record(path, expected=None):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError('Evidence bytes changed: ' + str(path))
    return {'path': str(path.resolve()), 'sha256': digest}


def load(path):
    return json.loads(path.read_bytes())


def stopped(identifier):
    path = INSTANCES / identifier / 'session.json'
    data = load(path)
    if data['owner'] != OWNER or Path(data['project']).resolve() != ROOT:
        raise ValueError('Evidence session ownership differs')
    for kind in ('game', 'mcdk'):
        if process_identity(data[kind + '_pid']) == data[kind + '_identity']:
            raise ValueError('Owned instance is still running')
    return dict(record(path), owner=data['owner'], session_id=identifier,
                state=data['state'], ready=data['ready'], processes_dead=True,
                error=data.get('error'), noactivation=data['noactivation'])


def capture(data):
    native = data['capture']
    if (not all(native.get(key) for key in ('ok', 'reliable', 'background_only', 'background_safe')) or
            native['owner'] != OWNER or native['frame']['frame_qpc_100ns'] <
            native['frame']['request_qpc_100ns']):
        raise ValueError('Capture contract failed')
    return record(Path(data['path']), data['sha256'])


def pack(output):
    if output.exists():
        raise ValueError('Choose a fresh evidence filename')
    plan_path = SHARED / '.runtime/plant-contract-r11/marked-poppy-plan-v1.json'
    plan = load(plan_path)
    artifact = INSTANCES / BASELINE / 'artifacts/poppy-original-calibration-r11-v1.json'
    baseline = load(artifact)
    if (not all(baseline.get(key) for key in ('completed', 'restored', 'source_assets_stable')) or
            baseline['cleanup_errors'] or baseline['source_errors'] or baseline['production_acceptance']):
        raise ValueError('Original native baseline did not finish cleanly')
    expected = {(tuple(pos), view) for pos in plan['calibration_coordinates'] for view in ('public', 'right')}
    if {(tuple(row['target']), row['view']) for row in baseline['rows']} != expected:
        raise ValueError('Native calibration coordinates differ')
    rows = []
    for row in baseline['rows']:
        rows.append({'target': row['target'], 'view': row['view'],
                     'shown': capture(row['native']['screenshot']),
                     'hidden': capture(row['native']['hidden_screenshot']),
                     'diagnostic_mask': record(Path(row['diagnostic_mask']['path']),
                                               row['diagnostic_mask']['sha256']),
                     'diagnostic_pixels': row['diagnostic_mask']['pixels'],
                     'diagnostic_bounds': row['diagnostic_mask']['bounds'],
                     'clip': row['boxes']['clip'], 'readback': row['native']['readback']})
    if not all(item['clean'] for group in baseline['cleanups'] for item in group['results']):
        raise ValueError('Original fixture restoration differs')
    calibration_path = Path(baseline['calibration']['path'])
    calibration = load(calibration_path)
    if (not all(calibration.get(key) for key in ('completed', 'passed', 'restored')) or
            Path(calibration['session_file']).resolve() !=
            (INSTANCES / BASELINE / 'session.json').resolve()):
        raise ValueError('Original same-session camera calibration differs')
    snapshots = []
    for version in ('v1', 'v2'):
        path = ROOT / ('.runtime/poppy-alpha-marker-r11-' + version + '.json')
        data = load(path)
        if data['candidate_alpha_sha256'] != data['native_alpha_sha256'] or data['before_hex'] is not None:
            raise ValueError('Marker alpha or original override contract differs')
        snapshots.append(dict(record(path), candidate=record(Path(data['candidate']['path']),
                                                             data['candidate']['sha256']),
                              native_alpha_sha256=data['native_alpha_sha256'],
                              candidate_alpha_sha256=data['candidate_alpha_sha256'],
                              restored_override_absent=True))
    if (ROOT / 'resource_pack/textures/blocks/flower_rose.png').exists():
        raise ValueError('Diagnostic texture override is not restored')
    retry_artifacts = INSTANCES / RETRY_MARKER / 'artifacts'
    camera_failure = retry_artifacts / 'snow-camera-alpha-r11-v1-wgc.json'
    control_capture = INSTANCES / CONTROL / 'artifacts/snow-original-control-r11-v1.capture.json'
    retry_capture = retry_artifacts / 'snow-alpha-retry-preflight-r11-v1.capture.json'
    report = {'schema': 1, 'scope': 'Destination-origin adapter and native geometry diagnosis',
              'production_acceptance': False, 'native_mesh_authority_recovered': False,
              'native_offset_formula_recovered': False, 'plan': record(plan_path),
              'baseline': dict(record(artifact), rows=rows, graphics_state=baseline['graphics_state'],
                               restoration=baseline['cleanups'],
                               camera_calibration=record(calibration_path, baseline['calibration']['sha256']),
                               frozen_source=record(Path(baseline['frozen_source']['path']),
                                                    baseline['frozen_source']['sha256'])),
              'viewed_native_pngs': [row['shown'] for row in rows],
              'sessions': [stopped(identifier) for identifier in
                           (BASELINE, FIRST_MARKER, CONTROL, RETRY_MARKER)],
              'alpha_marker_snapshots': snapshots,
              'original_startup_control': dict(record(control_capture),
                                               png=record(Path(load(control_capture)['path']))),
              'marker_retry_camera_failure': dict(record(camera_failure), error=load(camera_failure)['error'],
                                                   mutation_started=False),
              'marker_retry_frozen_content_capture': dict(record(retry_capture),
                                                          png=record(Path(load(retry_capture)['path'])),
                                                          embedded_local_time='2026-10-12T21:30:39+08:00',
                                                          capture_time='2026-10-12T21:35:45+08:00',
                                                          live_render_progress_proven=False),
              'limits': ['GRAPHICS=-1 is unsupported by GetToggleOption, not an identified graphics mode',
                         'No alpha-marker geometry frame was accepted; no opaque marker was installed',
                         'No holdout pixels were acquired or used for fitting',
                         'Native clip boxes alone do not establish mesh pivots or a destination hash',
                         'Production position registry remains empty; original pixel gates remain unchanged'],
              'accepted_scope_unchanged': {'positive_states': 29, 'height_observations': 232,
                                           'negative_lower_half_states': 8,
                                           'seed_name_false_rows_are_observed_negatives': False}}
    write_json(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = pack(args.output)
    print(json.dumps({'evidence': record(args.output), 'native_baseline_rows': len(report['baseline']['rows']),
                      'all_owned_processes_dead': True, 'override_restored': True,
                      'production_acceptance': False}))


if __name__ == '__main__':
    main()
