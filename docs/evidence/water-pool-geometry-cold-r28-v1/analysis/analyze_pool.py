"""Replay a new F-editor report with SDK-declared GUI coordinates only."""
import argparse
import ast
import copy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
HOST = WORK.with_name('water-pool-geometry-cold-v1')
CANDIDATE = ROOT / '.runtime/round-20261022/water-editor-anchor-candidate-v1/candidate_scene_project.py'
CANDIDATE_SHA = '5db34b3a3c0b4d7ffaf90e4e82f1fdd60cc55843743f4eb11b9b5ffbbdf442c2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_sha(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()


def checked_gui(state):
    cache = state.get('gui_cache')
    if not isinstance(cache, dict):
        raise ValueError('Captured native GUI cache is missing')
    gui = cache.get('sdk_integer_gui')
    if (isinstance(gui, bool) or not isinstance(gui, (int, float)) or not 1 <= gui < float('inf')
            or gui != round(gui) or cache.get('cached_gui') != gui):
        raise ValueError('Captured GUI scale is invalid or does not match the actual SDK cache')
    return gui


def activate(source, project):
    assert sha(CANDIDATE) == CANDIDATE_SHA
    sys.path.insert(0, str(project / '.agents/skills/pyreact-debugging/scripts'))
    sys.path.insert(0, str(project / 'tools'))
    base = importlib.import_module('analyze_product_water')
    assert Path(base.__file__).resolve() == project / 'tools/analyze_product_water.py'
    original = next(node for node in ast.parse(Path(base.__file__).read_bytes()).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'scene_project')
    candidate_tree = ast.parse(CANDIDATE.read_bytes())
    candidate_function = next(node for node in candidate_tree.body
                              if isinstance(node, ast.FunctionDef) and node.name == 'scene_project_gui_anchor_v1')
    center = next(node for node in original.body if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == 'center' for target in node.targets))
    divisions = [node for node in ast.walk(center) if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
                 and isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Name)
                 and node.left.func.id == 'min' and isinstance(node.right, ast.Constant) and node.right.value == 4.]
    assert len(divisions) == 1
    divisions[0].right = ast.parse('float(native_gui)', mode='eval').body
    assert [ast.dump(node, include_attributes=False) for node in original.body] == [
        ast.dump(node, include_attributes=False) for node in candidate_function.body[2:]]
    spec = importlib.util.spec_from_file_location('actual_gui_coordinate_candidate_v1', CANDIDATE)
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    states = {}

    def add(state):
        assert isinstance(state, dict)
        gui = checked_gui(state)
        assert gui == 2, 'This capture cohort declares native GUI2'
        states[state_sha(state)] = gui

    for collection in (source['rows'], source.get('extra_rows', {})):
        for row in collection.values():
            assert row['route'] == 'editor'
            add(row['ready'])
    for holdout in source.get('alpha_controls', {}).values():
        add(holdout['baseline'])
        for phase in holdout['phases'].values():
            add(phase['ready'])

    def scene_project_gui_bound(points, shape, state):
        digest = state_sha(state)
        if digest not in states:
            raise ValueError('GUI coordinate adapter received an uncaptured state')
        gui = checked_gui(state)
        assert gui == states[digest]
        return candidate.scene_project_gui_anchor_v1(points, shape, state, gui, base.OrbitCamera)

    base.scene_project = scene_project_gui_bound
    return base, {'version': 'SDK_GUI_captured_state_coordinate_adapter_v2',
                  'candidate_path': str(CANDIDATE), 'candidate_sha256': CANDIDATE_SHA,
                  'bound_state_count': len(states), 'native_gui': 2,
                  'source_coordinate_formula_unchanged': True,
                  'physical_regions_and_pixel_thresholds_unchanged': True,
                  'image_fit_or_roi_search': False, 'original_report_modified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(exist_ok=False)
    binding = json.loads((HOST / 'final-source-binding-v1.json').read_bytes())
    project = Path(binding['project']).resolve()
    path = HOST / 'product-v2-f-editor-v1.json'
    before = sha(path)
    source = json.loads(path.read_bytes())
    assert source['source_contract_sha256'] == binding['source_contract_sha256']
    for relative in ('tools/analyze_product_water.py', 'tools/analyze_water_acceptance_r16.py',
                     'tools/water_capture_contract.py', 'behavior_pack/modern_projection/projection/camera.py',
                     'behavior_pack/modern_projection/projection/liquid_product_deployment.py'):
        assert sha(project / relative) == binding['source_sha256'][relative], relative
    base, activation = activate(source, project)
    product = base.analyze(path)
    acceptance_tool = importlib.import_module('analyze_water_acceptance_r16')
    acceptance = acceptance_tool.replay(path)
    for name, value in (('product-analysis.json', product), ('side-visibility-budget-analysis.json', acceptance)):
        with (output / name).open('x', encoding='ascii') as stream:
            json.dump(value, stream, indent=2)
    assert sha(path) == before
    summary = {'schema': 1, 'source_report': str(path), 'source_report_sha256': before,
               'source_unchanged': True, 'activation': activation,
               'evidence_valid': product['evidence_valid'], 'capture_failures': product['capture_failures'],
               'observed_product_gates': product['observed_product_gates'],
               'geometry_rows': len(product['geometry']),
               'geometry_failed': [key for key, row in product['geometry'].items() if not row['passed']],
               'alpha_failed': [key for key, row in product['alpha_controls'].items() if not row['passed']],
               'transparency_failed': [key for key, row in product['transparency'].items() if not row['passed']],
               'acceptance': {key: value for key, value in acceptance.items()
                              if key not in ('visibility', 'side_uv', 'budgets', 'lifecycle')},
               'acceptance_failed': {field: [key for key, row in acceptance[field].items()
                                            if not (row.get('passed') if isinstance(row, dict) else row)]
                                     for field in ('visibility', 'side_uv', 'budgets', 'lifecycle')},
               'MC_started': False, 'RPC_dispatched': False, 'formal_release_qualification': False}
    with (output / 'summary.json').open('x', encoding='ascii') as stream:
        json.dump(summary, stream, indent=2)
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
