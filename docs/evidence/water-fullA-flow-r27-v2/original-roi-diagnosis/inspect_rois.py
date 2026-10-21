"""Overlay the unchanged flow analyzer's physical sample coordinates only."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
HOST = WORK.with_name('water-merged-fullA-v2')
PROJECT = ROOT / '.runtime/projects/water-r27-merged-flow-editor-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(path, names, namespace):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == set(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)


def main():
    report_path = WORK / 'original-roi-overlays-v1.json'
    assert not report_path.exists()
    binding = json.loads((HOST / 'final-source-binding-v1.json').read_bytes())
    paths = {name: PROJECT / name for name in (
        'tools/analyze_product_water.py', 'tools/analyze_product_water_flow.py',
        'behavior_pack/modern_projection/projection/camera.py')}
    for name, path in paths.items():
        assert sha(path) == binding['source_sha256'][name]
    spec = importlib.util.spec_from_file_location('frozen_camera_readonly', paths['behavior_pack/modern_projection/projection/camera.py'])
    camera = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(camera)
    namespace = {'np': np, 'GRID': 96, 'OrbitCamera': camera.OrbitCamera}
    extract(paths['tools/analyze_product_water.py'], {'scene_project'}, namespace)
    extract(paths['tools/analyze_product_water_flow.py'], {'physical_points'}, namespace)
    source_path = HOST / 'product-v2-a-v1.json'
    source_before = sha(source_path)
    source = json.loads(source_path.read_bytes())
    host = json.loads((HOST / 'product-v2-a-v1-host.json').read_bytes())
    flow = {'flow_east': (1, 0), 'flow_south': (0, 1), 'flow_west': (-1, 0), 'flow_north': (0, -1)}
    rows = []
    for key, burst in source['flow_bursts'].items():
        row = burst['row']
        if row['route'] != 'editor':
            continue
        state = row['ready']
        case = row['case']
        if case in flow:
            direction = flow[case]
            position = (3 - direction[0], 3, 3 - direction[1])
            face = 0
            shape = next(shape for shape in state['shapes'] if shape['faces'] & 1 and tuple(shape['position']) == position)
        else:
            position, face = (3, 3, 3), 2
            shape = next(shape for shape in state['shapes'] if shape['faces'] & 4 and tuple(shape['position']) == position)
        points, spacing = namespace['physical_points'](shape, face)
        raw_path = Path(source['captures'][key]['path'])
        raw_sha = sha(raw_path)
        image = Image.open(raw_path).convert('RGB')
        native_size = image.size
        logical = np.asarray(namespace['scene_project'](points, shape, state))
        mapped = logical * (np.asarray(native_size) / np.asarray(state['screen_size']))
        grid = mapped.reshape((96, 96, 2))
        outline = np.concatenate((grid[0], grid[1:, -1], grid[-1, -2::-1], grid[-2:0:-1, 0]))
        draw = ImageDraw.Draw(image)
        boundary = [tuple(float(value) for value in point) for point in outline]
        draw.line(boundary + [boundary[0]], fill=(255, 0, 0), width=3)
        bounds = np.r_[mapped.min(axis=0), mapped.max(axis=0)].tolist()
        draw.rectangle((12, 60, 960, 80), fill=(255, 255, 255))
        draw.text((16, 64), key + ' ORIGINAL ROI (red); source unchanged', fill=(180, 0, 0))
        overlay_path = WORK / (key + '_original_roi_overlay.png')
        image.save(overlay_path)
        origin = tuple(axis // 4 * 4 for axis in shape['position'])
        identities = {group['key'] for group in state['liquid_groups'] if tuple(group['origin']) == origin}
        controls = [control for control in state['liquid_control_requests'] if control['key'] in identities
                    and control['poses'] and any(control['visible'])]
        control = controls[0]
        slot = control['visible'].index(True)
        sdk = [observation for observation in host['native_geometry_observations']
               if observation['label'].startswith('product-v2-a-v1_' + key + '_')]
        rows.append({
            'key': key, 'position': position, 'face': face, 'spacing': spacing,
            'raw_path': str(raw_path), 'raw_sha256': raw_sha,
            'overlay_path': str(overlay_path), 'overlay_sha256': sha(overlay_path),
            'screen_size': state['screen_size'], 'native_size': native_size,
            'camera_pose': state['camera_pose'], 'group_origin': origin,
            'control_key': control['key'], 'visible_slot': slot,
            'doll_global_position': control['doll_positions'][slot],
            'doll_size': control['doll_sizes'][slot], 'pose': control['poses'][slot],
            'original_roi_native_bounds': bounds,
            'sdk_observation_labels': [observation['label'] for observation in sdk],
            'sdk_verdicts': [observation['verdict'] for observation in sdk],
            'raw_unchanged': sha(raw_path) == raw_sha,
        })
    assert sha(source_path) == source_before
    for name, path in paths.items():
        assert sha(path) == binding['source_sha256'][name]
    result = {'schema': 1, 'scope': 'Original coordinates only; no adapter, thresholds, or gates replayed.',
              'source_sha256': source_before, 'source_unchanged': True,
              'frozen_functions': {name: sha(path) for name, path in paths.items()}, 'rows': rows,
              'original_strict_failure_preserved': True, 'ROI_or_threshold_changes': False,
              'MC_started': False, 'formal_A_accepted': False, 'manual_closures_added': 0}
    report_path.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'report': str(report_path), 'sha256': sha(report_path),
                      'rows': [{'key': row['key'], 'bounds': row['original_roi_native_bounds']} for row in rows]}))


if __name__ == '__main__':
    main()
