"""Static coordinate controls only; no PNG flow or acceptance analysis."""
import ast
import copy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys

WORK = Path(__file__).resolve().parent
HOST = WORK.with_name('water-merged-fullA-v2')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = WORK / 'controls-v1.json'
    assert not target.exists()
    binding = json.loads((HOST / 'final-source-binding-v1.json').read_bytes())
    project = Path(binding['project']).resolve()
    sys.path.insert(0, str(project / '.agents/skills/pyreact-debugging/scripts'))
    module_receipts = []
    for name in ('_session', '_window'):
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve()
        relative = path.relative_to(project).as_posix()
        assert sha(path) == binding['source_sha256'][relative]
        module_receipts.append({'name': name, 'path': str(path), 'sha256': sha(path)})
    spec = importlib.util.spec_from_file_location('anchor_host_controls', WORK / 'analysis_anchor_host.py')
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    metadata = host.activate()
    base = sys.modules['analyze_product_water']
    original_node = host.function(project / 'tools/analyze_product_water.py', 'scene_project')
    namespace = {'OrbitCamera': base.OrbitCamera}
    exec(compile(ast.Module(body=[copy.deepcopy(original_node)], type_ignores=[]),
                 str(project / 'tools/analyze_product_water.py'), 'exec'), namespace)
    original = namespace['scene_project']
    spec = importlib.util.spec_from_file_location('candidate_controls', WORK / 'candidate_scene_project.py')
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    source = json.loads((HOST / 'product-v2-a-v1.json').read_bytes())
    rows = []
    first = None
    for label, burst in source['flow_bursts'].items():
        row = burst['row']
        if row['route'] != 'editor':
            continue
        state = row['ready']
        shape = state['shapes'][0]
        points = [[float(axis) + .37 for axis in shape['position']]]
        original_result = original(points, shape, state)
        legacy = candidate.scene_project_gui_anchor_v1(points, shape, state, 4.0, base.OrbitCamera)
        assert original_result == legacy
        bound = base.scene_project(points, shape, state)
        direct = candidate.scene_project_gui_anchor_v1(points, shape, state, 2.0, base.OrbitCamera)
        assert bound == direct
        rows.append({'label': label, 'gui4_exact_legacy_compatibility': True,
                     'bound_gui2_exact_direct_coordinate_match': True})
        if first is None:
            first = points, shape, state
    assert len(rows) == 5
    points, shape, state = first
    negative = []
    for label, gui in (('true', True), ('false', False), ('zero', 0), ('below_one', .5),
                       ('fractional', 1.5), ('nan', float('nan')), ('positive_infinity', float('inf')),
                       ('string', '2'), ('missing', None)):
        try:
            candidate.scene_project_gui_anchor_v1(points, shape, state, gui, base.OrbitCamera)
        except ValueError:
            negative.append({'case': label, 'rejected': True})
        else:
            raise AssertionError('Invalid GUI accepted: ' + label)
    changed = copy.deepcopy(state)
    changed['camera_pose'][0] += 1.
    try:
        base.scene_project(points, shape, changed)
    except ValueError:
        negative.append({'case': 'unbound_editor_state', 'rejected': True})
    else:
        raise AssertionError('Unbound state accepted')
    for filename, expected in host.EXPECTED.items():
        assert sha(HOST / filename) == expected
    for relative, expected in metadata['frozen_sources'].items():
        assert sha(project / relative) == expected
    result = {'schema': 1, 'passed': True, 'activation': metadata,
              'private_session_modules': module_receipts,
              'coordinate_controls': rows, 'negative_controls': negative,
              'original_physical_points_limits_motion_bytes_unchanged': True,
              'flow_gate_replayed': False, 'MC_started': False,
              'original_failed_report_modified': False, 'formal_A_accepted': False,
              'manual_closures_added': 0}
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'report': str(target), 'sha256': sha(target),
                      'host_sha256': metadata['host_sha256'],
                      'coordinate_controls': len(rows), 'negative_controls': len(negative),
                      'flow_gate_replayed': False, 'passed': True}))


if __name__ == '__main__':
    main()
