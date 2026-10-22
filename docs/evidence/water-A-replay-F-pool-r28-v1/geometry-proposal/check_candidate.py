"""Actual-state and independent algebra controls; no native success claim."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random

from candidate_geometry import ui_geometry_for_gui

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
PROJECT = ROOT / '.runtime/projects/water-r27-merged-flow-editor-v1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def close(a, b):
    return max(abs(x - y) for x, y in zip(a, b)) < 1e-7


def anchor(position, size, gui):
    return (position[0] + size[0] / 2., position[1] + size[1] / 2. - min(size) / gui)


def contains(outer, inner):
    (x, y), (w, h) = outer
    (ix, iy), (iw, ih) = inner
    return x <= ix + 1e-7 and y <= iy + 1e-7 and x + w >= ix + iw - 1e-7 and y + h >= iy + ih - 1e-7


def intersection(geometry, viewport):
    (x, y), (w, h) = geometry
    return max(0., min(viewport[0], x + w) - max(0., x)) * max(0., min(viewport[1], y + h) - max(0., y))


def evaluate(position, size, gui, unit, geometry_fn=ui_geometry_for_gui, recalc_pose=True):
    actual = geometry_fn(position, size, gui)
    center = (position[0] + size[0] / 2., position[1] + size[1] / 2.)
    effective_unit = unit / min(actual[1] if recalc_pose else size) * min(actual[1])
    return {'contains_base_rect': contains(actual, (position, size)),
            'native_anchor_preserved': close(anchor(*actual, gui), center),
            'effective_unit_preserved': abs(effective_unit - unit) < 1e-7,
            'minimum_is_width': min(actual[1]) == actual[1][0]}


def main():
    assert not (WORK / 'candidate-controls-v1.json').exists()
    state = json.loads((WORK / 'actual-failure-state-v1.json').read_bytes())
    camera = load('frozen_water_camera', PROJECT / 'behavior_pack/modern_projection/projection/camera.py')
    gui = state['gui_cache']['sdk_integer_gui']
    assert gui == state['gui_cache']['cached_gui'] == 2.
    ready_keys = {entry['key'] for entry in state['native_water_controls'] if entry['request_ready']}
    units = [next(p for p in item['poses'] if p is not None)[0] * min(item['geometry'][1])
             for item in state['liquid_control_requests'] if item['key'] in ready_keys]
    assert max(units) - min(units) < 1e-7
    unit = units[0]
    # Scene.unit() in the exact frozen source: min(native viewport)*zoom*.72/max(scene_size).
    short_edge = unit * max(state['scene_size']) / (state['camera_pose'][2] * .72)
    widths = [item['geometry'][0][0] + item['geometry'][1][0]
              for item in state['liquid_control_requests'] if item['geometry'][0][0] < 0.]
    assert max(widths) - min(widths) < 1e-7 and widths[0] > short_edge
    viewport = (widths[0], short_edge)
    rows = []
    right, up, unused = camera.OrbitCamera(*state['camera_pose']).basis()
    projected_point_count = 0
    for entry in state['native_water_controls']:
        old_position, size = entry['geometry']
        base_position = (old_position[0], old_position[1] - min(size) / gui)
        base_geometry = base_position, size
        new_geometry = ui_geometry_for_gui(base_position, size, gui)
        original_anchor = anchor(old_position, size, gui)
        new_anchor = anchor(*new_geometry, gui)
        old_scale = unit / min(size)
        new_scale = unit / min(new_geometry[1])
        for dx in (-2., 0., 2.):
            for dy in (-2., 0., 2.):
                for dz in (-2., 0., 2.):
                    point = dx, dy, dz
                    before = (original_anchor[0] + old_scale * min(size) * sum(point[i] * right[i] for i in range(3)),
                              original_anchor[1] - old_scale * min(size) * sum(point[i] * up[i] for i in range(3)))
                    after = (new_anchor[0] + new_scale * min(new_geometry[1]) * sum(point[i] * right[i] for i in range(3)),
                             new_anchor[1] - new_scale * min(new_geometry[1]) * sum(point[i] * up[i] for i in range(3)))
                    assert close(before, after)
                    projected_point_count += 1
        checks = evaluate(base_position, size, gui, unit)
        assert all(checks.values()) and contains(base_geometry, ((0., 0.), viewport))
        failed = entry['renderer_error'] is not None
        assert (intersection((old_position, size), viewport) == 0.) == failed
        rows.append({'key': entry['key'], 'renderer_error': entry['renderer_error'],
                     'native_model_ids': [bank['native_model_id'] for bank in entry['banks']],
                     'actual_shifted_geometry': entry['geometry'], 'base_geometry': base_geometry,
                     'proposed_geometry': new_geometry, 'old_scale': old_scale, 'new_scale': new_scale,
                     'effective_unit': unit, 'old_viewport_intersection_pixels': intersection((old_position, size), viewport),
                     'new_viewport_intersection_pixels': intersection(new_geometry, viewport), 'checks': checks})
    rng = random.Random(20261023)
    stress_count = 0
    for native_gui in (1., 2., 3., 4., 8., 16., 256.):
        for unused in range(500):
            size = (10 ** rng.uniform(-2., 6.), 10 ** rng.uniform(-2., 6.))
            position = (-rng.random() * size[0], -rng.random() * size[1])
            checks = evaluate(position, size, native_gui, 10 ** rng.uniform(-3., 3.))
            assert all(checks.values()), (native_gui, position, size, checks)
            stress_count += 1
    rejected = []
    for invalid in (True, False, 0., -1., .5, 1.5, float('nan'), float('inf'), -float('inf'), '2', None):
        try:
            ui_geometry_for_gui((0., 0.), (100., 50.), invalid)
        except ValueError:
            rejected.append(repr(invalid))
        else:
            raise AssertionError('Accepted invalid GUI: ' + repr(invalid))
    base, size, g, unit = (0., 0.), (400., 100.), 2., 50.
    old = lambda p, s, gui: ((p[0], p[1] + min(s) / gui), s)
    unshifted = lambda p, s, gui: (p, ui_geometry_for_gui(p, s, gui)[1])
    mismatch = lambda p, s, gui: ui_geometry_for_gui(p, s, 4.)
    negative = {
        'old_offset_loses_original_rectangle': not evaluate(base, size, g, unit, old)['contains_base_rect'],
        'height_change_without_pose_recalc_changes_pixels': not evaluate(base, size, g, unit, recalc_pose=False)['effective_unit_preserved'],
        'wrong_gui_moves_projection': not evaluate(base, size, g, unit, mismatch)['native_anchor_preserved'],
    }
    # A nonzero original position and GUI4 exercise the max(W,...) branch independently.
    negative['expansion_without_center_compensation_moves_projection'] = not evaluate((-30., -20.), (400., 100.), 4., unit, unshifted)['native_anchor_preserved']
    assert all(negative.values())
    output = {'schema': 1, 'passed': True, 'actual_readback_rows': len(rows), 'rows': rows,
              'actual_sdk_gui': gui, 'source_derived_viewport': viewport,
              'viewport_provenance': 'Derived, not directly read back: exact frozen Scene.unit() and render_bounds(), with actual pose/size/position/zoom/scene-size.',
              'source_sha256': {name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
                  for name in ('behavior_pack/modern_projection/projection/scene.py', 'behavior_pack/modern_projection/projection/camera.py',
                               'behavior_pack/modern_projection/projection/liquid_deployment.py')},
              'candidate_sha256': hashlib.sha256((WORK / 'candidate_geometry.py').read_bytes()).hexdigest(),
              'projected_points': projected_point_count, 'stress_rows': stress_count,
              'invalid_gui_rejections': rejected, 'negative_controls': negative,
              'raw_scale_invariant_claimed': False, 'effective_pixel_unit_invariant': True,
              'native_success_claimed': False, 'shared_source_changed': False}
    (WORK / 'candidate-controls-v1.json').write_text(json.dumps(output, sort_keys=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps({key: value for key, value in output.items() if key not in ('rows', 'source_sha256')}, indent=2))


if __name__ == '__main__':
    main()
