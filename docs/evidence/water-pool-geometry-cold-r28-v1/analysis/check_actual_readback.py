"""Compare exact old failure, frozen candidate, and new actual native geometry."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
HOST = WORK.with_name('water-pool-geometry-cold-v1')
OLD = WORK.with_name('water-geometry-readiness-v1')


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rect_intersection(position, size, other_position, other_size):
    return (max(0., min(position[0] + size[0], other_position[0] + other_size[0]) - max(position[0], other_position[0])) *
            max(0., min(position[1] + size[1], other_position[1] + other_size[1]) - max(position[1], other_position[1])))


def difference(left, right):
    return max(abs(a - b) for a, b in zip(left, right))


def main():
    output = WORK / 'actual-readback-analysis-v1.json'
    assert not output.exists()
    host_path = HOST / 'product-v2-f-editor-v1-host.json'
    host = load(host_path)
    observations = host['native_geometry_observations']
    assert host['completed'] and host['captured'] == 2 and len(observations) == 2
    wet = next(row for row in observations if row['label'].endswith('_wet'))
    dry = next(row for row in observations if row['label'].endswith('_dry'))
    state = wet['state']
    controls = state['native_water_controls']
    assert len(controls) == 8 and dry['state']['native_water_controls'] == []
    assert wet['actual_scene_controls'] == dry['actual_scene_controls']
    canvas = wet['actual_scene_controls']['canvas']['native']
    clip = wet['actual_scene_controls']['clip']['native']
    old_state = load(OLD / 'actual-failure-state-v1.json')
    old_controls = {row['key']: row for row in old_state['native_water_controls']}
    old_ready = {row['key'] for row in old_controls.values() if row['request_ready']}
    old_units = [next(pose for pose in row['poses'] if pose is not None)[0] * min(row['geometry'][1])
                 for row in old_state['liquid_control_requests'] if row['key'] in old_ready]
    assert max(old_units) - min(old_units) < 1e-7
    expected_unit = old_units[0]
    source_controls = load(OLD / 'candidate-controls-v1.json')
    assert difference(canvas['size'], source_controls['source_derived_viewport']) < 1e-7
    spec = importlib.util.spec_from_file_location('reviewed_water_geometry', OLD / 'candidate_geometry.py')
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    requests = {row['key']: row for row in state['liquid_control_requests']}
    rows = []
    for control in controls:
        key = control['key']
        old = old_controls[key]
        old_position, old_size = old['geometry']
        base_position = old_position[0], old_position[1] - min(old_size) / 2.
        expected_geometry = candidate.ui_geometry_for_gui(base_position, old_size, 2.)
        geometry_error = max(difference(expected_geometry[i], control['geometry'][i]) for i in (0, 1))
        assert geometry_error < 1e-7
        banks = [bank for bank in control['banks'] if bank['declared_visible']]
        assert len(banks) == 1
        bank = banks[0]
        assert control['request_ready'] and control['renderer_error'] is None
        assert bank['native_model_id'] == bank['renderer_model_id'] and bank['native_model_id'] >= 0
        assert bank['native_visible'] and bank['surface_visible']
        current_intersection = rect_intersection(bank['global_position'], bank['size'], clip['global'], clip['size'])
        assert current_intersection > 0
        old_global = [canvas['global'][i] + old_position[i] for i in (0, 1)]
        old_intersection = rect_intersection(old_global, old_size, clip['global'], clip['size'])
        request = requests[key]
        pose = request['poses'][bank['slot']]
        effective_unit = pose[0] * min(request['geometry'][1])
        assert abs(effective_unit - expected_unit) < 1e-7
        rows.append({'key': key, 'old_renderer_error': old['renderer_error'],
                     'old_actual_clip_intersection': old_intersection,
                     'new_actual_clip_intersection': current_intersection,
                     'native_model_id': bank['native_model_id'],
                     'geometry_matches_reviewed_candidate_error': geometry_error,
                     'effective_pixel_unit': effective_unit,
                     'declared_geometry': control['geometry'],
                     'actual_active_bank': bank})
    formerly_failed = [row for row in rows if row['old_renderer_error']]
    assert len(formerly_failed) == 2
    assert all(row['old_actual_clip_intersection'] == 0. for row in formerly_failed)
    restore = load(HOST / 'independent-restore-v1.json')
    group = load(HOST / 'group-execution-v1.json')
    exit_report = load(HOST / 'launch/exact-exit.json')
    assert restore['restored'] and restore['source_unchanged']
    assert group['completed'] and all(group['exact_identities_absent'].values())
    assert exit_report['completed']
    pngs = sorted(HOST.glob('*_pool_*.png'))
    assert len(pngs) == 2
    result = {'schema': 1, 'passed': True, 'scope': 'One cold editor pool wet/dry candidate only',
              'host_report_sha256': sha(host_path),
              'product_report_sha256': sha(HOST / 'product-v2-f-editor-v1.json'),
              'source_contract_sha256': host['source_contract_sha256'],
              'actual_canvas': canvas, 'actual_clip': clip,
              'source_derived_viewport_now_checked_against_actual_canvas': True,
              'active_water_groups': len(rows), 'former_failed_groups_now_ready': len(formerly_failed),
              'old_ready_effective_pixel_unit': expected_unit, 'rows': rows,
              'restored': True, 'exact_identities_released': True,
              'actual_exit_codes': {key: value['exit_code_hex'] for key, value in exit_report['processes'].items()},
              'png_sha256': {path.name: sha(path) for path in pngs},
              'images_visually_reviewed': True,
              'formal_release_qualification': False, 'manual_closures_added': 0}
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='ascii')
    print(json.dumps({key: value for key, value in result.items() if key not in ('rows', 'png_sha256')}, indent=2))


if __name__ == '__main__':
    main()
