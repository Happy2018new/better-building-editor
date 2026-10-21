"""Bind the GUI-anchor proposal to this immutable capture, in the host only."""
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
EXPECTED = {
    'product-v2-a-v1.json': 'b38ae6262e6b98679bd5f15f5a66179c75bbc003b320fe5e39ba9fe609dbd0ba',
    'product-v2-a-v1-host.json': '5692b38296118ff9ee82352c04756617769942363d7242ef4d73d7922b8ca81b',
    'final-source-binding-v1.json': '3d6c304ecd1fecc6b38649f7fb3ab2d792eec1583daf21ac0fd91fd388551796',
}
CANDIDATE_SHA = '5db34b3a3c0b4d7ffaf90e4e82f1fdd60cc55843743f4eb11b9b5ffbbdf442c2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_sha(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()


def function(path, name):
    return next(node for node in ast.parse(path.read_text(encoding='utf-8-sig')).body
                if isinstance(node, ast.FunctionDef) and node.name == name)


def activate():
    for filename, expected in EXPECTED.items():
        assert sha(HOST / filename) == expected, filename
    binding = json.loads((HOST / 'final-source-binding-v1.json').read_bytes())
    project = Path(binding['project']).resolve()
    source = json.loads((HOST / 'product-v2-a-v1.json').read_bytes())
    observations = json.loads((HOST / 'product-v2-a-v1-host.json').read_bytes())['native_geometry_observations']
    required = (
        'tools/analyze_product_water.py', 'tools/analyze_product_water_flow.py',
        'behavior_pack/modern_projection/projection/camera.py',
        'behavior_pack/modern_projection/projection/liquid_product_deployment.py',
        'behavior_pack/modern_projection/projection/liquid_deployment.py',
        'behavior_pack/modern_projection/projection/liquid_viewport.py',
        'behavior_pack/modern_projection/projection/scene.py')
    for relative in required:
        assert sha(project / relative) == binding['source_sha256'][relative], relative
    candidate_path = WORK / 'candidate_scene_project.py'
    assert sha(candidate_path) == CANDIDATE_SHA
    original = function(project / 'tools/analyze_product_water.py', 'scene_project')
    candidate_node = function(candidate_path, 'scene_project_gui_anchor_v1')
    center_assignment = next(node for node in original.body
                             if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'center' for t in node.targets))
    divisions = [node for node in ast.walk(center_assignment)
                 if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
                 and isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Name)
                 and node.left.func.id == 'min' and isinstance(node.right, ast.Constant)
                 and node.right.value == 4.]
    assert len(divisions) == 1
    divisions[0].right = ast.parse('float(native_gui)', mode='eval').body
    assert [ast.dump(node, include_attributes=False) for node in original.body] == [
        ast.dump(node, include_attributes=False) for node in candidate_node.body[2:]]
    ui_offset_node = function(project / required[3], 'ui_offset_for_gui')
    namespace = {'integer_types': (int,)}
    exec(compile(ast.Module(body=[copy.deepcopy(ui_offset_node)], type_ignores=[]),
                 str(project / required[3]), 'exec'), namespace)
    recorded = {}
    rows = []
    for label, burst in source['flow_bursts'].items():
        row = burst['row']
        if row['route'] != 'editor':
            continue
        matched = [observation for observation in observations
                   if observation['label'].startswith('product-v2-a-v1_' + label + '_')]
        assert len(matched) == 3
        for observation in matched:
            verdict = observation['verdict']
            assert verdict['complete'] is True and not verdict['errors']
            assert verdict['geometry_tolerance_logical'] == .02
        gui_values = {observation['state']['gui_cache']['sdk_integer_gui'] for observation in matched}
        cached_values = {observation['state']['gui_cache']['cached_gui'] for observation in matched}
        assert gui_values == cached_values == {2.0}
        for control in row['ready']['liquid_control_requests']:
            if any(control['visible']):
                slot = control['visible'].index(True)
                size = control['doll_sizes'][slot]
                assert namespace['ui_offset_for_gui'](size, 2.0) == (0., min(size) / 2.0)
        digest = state_sha(row['ready'])
        assert digest not in recorded
        recorded[digest] = 2.0
        rows.append({'label': label, 'state_sha256': digest, 'actual_sdk_gui': 2.0,
                     'sdk_observation_labels': [observation['label'] for observation in matched]})
    assert len(rows) == 5 and len(observations) == 15
    sys.path.insert(0, str(project / 'tools'))
    base = importlib.import_module('analyze_product_water')
    assert Path(base.__file__).resolve() == project / 'tools/analyze_product_water.py'
    camera_module = sys.modules[base.OrbitCamera.__module__]
    assert Path(camera_module.__file__).resolve() == project / required[2]
    assert base.scene_project.__name__ == 'scene_project'
    spec = importlib.util.spec_from_file_location('reviewed_editor_anchor_candidate', candidate_path)
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)

    def scene_project_gui_anchor_bound_v1(points, shape, state):
        digest = state_sha(state)
        if digest not in recorded:
            raise ValueError('GUI anchor adapter received an unbound editor capture state')
        return candidate.scene_project_gui_anchor_v1(points, shape, state, recorded[digest], base.OrbitCamera)

    base.scene_project = scene_project_gui_anchor_bound_v1
    for filename, expected in EXPECTED.items():
        assert sha(HOST / filename) == expected
    for relative in required:
        assert sha(project / relative) == binding['source_sha256'][relative]
    return {
        'schema': 1, 'version': 'editor-product-GUI-anchor-host-v1',
        'host_path': str(Path(__file__).resolve()), 'host_sha256': sha(Path(__file__)),
        'candidate_path': str(candidate_path), 'candidate_sha256': CANDIDATE_SHA,
        'bound_reports': EXPECTED, 'editor_states': rows,
        'frozen_sources': {relative: binding['source_sha256'][relative] for relative in required},
        'change': 'Invert existing product ui_offset_for_gui using actual SDK GUI instead of legacy /4.',
        'physical_points_or_thresholds_changed': False, 'world_projection_changed': False,
        'image_fit_performed': False, 'original_failed_report_modified': False,
        'project_or_analyzer_source_bytes_modified': False, 'MC_started': False,
        'formal_A_accepted': False, 'production_admission_performed': False, 'manual_closures_added': 0,
    }
