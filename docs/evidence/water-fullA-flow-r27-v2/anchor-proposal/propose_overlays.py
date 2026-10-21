"""Make a separately versioned anchor proposal overlay; do not replay gates."""
import ast
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
HOST = WORK.with_name('water-merged-fullA-v2')
PREVIOUS = WORK.with_name('water-editor-roi-readonly-v1')
PROJECT = ROOT / '.runtime/projects/water-r27-merged-flow-editor-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = WORK / 'proposal-overlays-v1.json'
    assert not target.exists()
    spec = importlib.util.spec_from_file_location('roi_original_readonly', PREVIOUS / 'inspect_rois.py')
    original_host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original_host)
    spec = importlib.util.spec_from_file_location('anchor_proposal', WORK / 'candidate_scene_project.py')
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    binding = json.loads((HOST / 'final-source-binding-v1.json').read_bytes())
    relative_paths = (
        'tools/analyze_product_water.py', 'tools/analyze_product_water_flow.py',
        'behavior_pack/modern_projection/projection/camera.py',
        'behavior_pack/modern_projection/projection/liquid_product_deployment.py',
        'behavior_pack/modern_projection/projection/liquid_deployment.py',
        'behavior_pack/modern_projection/projection/liquid_viewport.py',
        'behavior_pack/modern_projection/projection/scene.py')
    for relative in relative_paths:
        assert sha(PROJECT / relative) == binding['source_sha256'][relative]
    original_text = (PROJECT / 'tools/analyze_product_water.py').read_text(encoding='utf-8-sig')
    original_function = next(node for node in ast.parse(original_text).body
                             if isinstance(node, ast.FunctionDef) and node.name == 'scene_project')
    original_segment = ast.get_source_segment(original_text, original_function)
    proposal_segment = original_segment.replace('def scene_project(points, shape, state):',
                                               'def scene_project(points, shape, state, native_gui):')
    assert proposal_segment.count('min(size) / 4.') == 1
    proposal_segment = proposal_segment.replace('min(size) / 4.', 'min(size) / float(native_gui)')
    patch = ''.join(difflib.unified_diff(original_segment.splitlines(True), proposal_segment.splitlines(True),
                                       'frozen/analyze_product_water.py:scene_project',
                                       'host-only/gui-anchor-proposal:scene_project'))
    (WORK / 'anchor-formula-changes-v1.patch').write_text(patch, encoding='utf-8')
    spec = importlib.util.spec_from_file_location('anchor_frozen_camera', PROJECT / relative_paths[2])
    camera = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(camera)
    namespace = {'np': np, 'GRID': 96}
    original_host.extract(PROJECT / 'tools/analyze_product_water_flow.py', {'physical_points'}, namespace)
    source_path = HOST / 'product-v2-a-v1.json'
    source_before = sha(source_path)
    source = json.loads(source_path.read_bytes())
    observations = json.loads((HOST / 'product-v2-a-v1-host.json').read_bytes())['native_geometry_observations']
    old_report = json.loads((PREVIOUS / 'original-roi-overlays-v1.json').read_bytes())
    rows = []
    for old in old_report['rows']:
        key = old['key']
        row = source['flow_bursts'][key]['row']
        state = row['ready']
        matched = [observation for observation in observations
                   if observation['label'].startswith('product-v2-a-v1_' + key + '_')]
        assert len(matched) == 3
        gui_values = {observation['state']['gui_cache']['sdk_integer_gui'] for observation in matched}
        cached_values = {observation['state']['gui_cache']['cached_gui'] for observation in matched}
        assert len(gui_values) == 1 and gui_values == cached_values
        native_gui = gui_values.pop()
        shape = next(shape for shape in state['shapes'] if shape['position'] == old['position'])
        points, unused_spacing = namespace['physical_points'](shape, old['face'])
        raw = Path(old['raw_path'])
        assert sha(raw) == old['raw_sha256']
        image = Image.open(raw).convert('RGB')
        projected = np.asarray(candidate.scene_project_gui_anchor_v1(points, shape, state, native_gui, camera.OrbitCamera))
        mapped = projected * (np.asarray(image.size) / np.asarray(state['screen_size']))
        grid = mapped.reshape((96, 96, 2))
        outline = np.concatenate((grid[0], grid[1:, -1], grid[-1, -2::-1], grid[-2:0:-1, 0]))
        boundary = [tuple(float(value) for value in point) for point in outline]
        draw = ImageDraw.Draw(image)
        draw.line(boundary + [boundary[0]], fill=(0, 220, 0), width=3)
        draw.rectangle((12, 60, 1080, 80), fill=(255, 255, 255))
        draw.text((16, 64), key + ' GUI anchor proposal (green); no gate replay', fill=(0, 100, 0))
        path = WORK / (key + '_proposal_roi_overlay.png')
        image.save(path)
        bounds = np.r_[mapped.min(axis=0), mapped.max(axis=0)].tolist()
        rows.append({'key': key, 'recorded_sdk_gui': native_gui,
                     'original_bounds': old['original_roi_native_bounds'], 'proposal_bounds': bounds,
                     'native_vertical_shift': old['original_roi_native_bounds'][1] - bounds[1],
                     'raw_path': str(raw), 'raw_sha256': old['raw_sha256'],
                     'overlay_path': str(path), 'overlay_sha256': sha(path),
                     'raw_unchanged': sha(raw) == old['raw_sha256']})
    assert sha(source_path) == source_before
    for relative in relative_paths:
        assert sha(PROJECT / relative) == binding['source_sha256'][relative]
    result = {'schema': 1, 'scope': 'Formula-only anchor proposal; no image fit or new gate result.',
              'source_sha256': source_before, 'source_unchanged': True,
              'proposal_sha256': sha(WORK / 'candidate_scene_project.py'),
              'frozen_sources': {relative: sha(PROJECT / relative) for relative in relative_paths},
              'rows': rows, 'gate_replay_performed': False, 'threshold_changes': False,
              'MC_started': False, 'original_failed_analysis_revised': False,
              'formal_A_accepted': False, 'manual_closures_added': 0}
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'report': str(target), 'sha256': sha(target), 'proposal_sha256': result['proposal_sha256'],
                      'rows': [{'key': row['key'], 'shift': row['native_vertical_shift'],
                                'bounds': row['proposal_bounds']} for row in rows]}))


if __name__ == '__main__':
    main()
