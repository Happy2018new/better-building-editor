"""Replay the finite palette/direct experiment without accepting liquid rendering."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

import analyze_liquid_sides as sides
from analyze_liquid_workspace import capture_failures, difference_mask, mask_row, rgb
import capture_frozen_liquid_controls as frozen
import capture_pure_liquid_native_controls as native


LIMITS = {'rgb_delta': 12, 'minimum_signal_pixels': 80, 'inset_pixels': 3,
          'crosshair_half_extent': 20, 'hud_top_fraction': .12,
          'hud_bottom_fraction': .90}
SOURCES = {'h_vnw': 'water_depth_0_foreground',
           'l_vnw': 'water_depth_3_foreground'}
ROUTES = ('native_palette', 'native_direct', 'full')


def reference(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def visibility_masks(source, projection):
    """Geometry and fixed UI exclusions alone choose pixels, never the image."""
    geometry = sides.builtin_geometry(source)
    support_geometry = {'surfaces': [dict(position=position, heights=[255] * 4, faces=63)
                        for position, value in geometry['source_cells']
                        if value[0] == 'minecraft:stone']}
    support = sides.projected_mask(support_geometry, projection, full_height=True)
    # The entire unit cube tests publication independently of a proposed native
    # water height. It does not judge the height or silhouette itself.
    water = sides.projected_mask(geometry, projection, full_height=True) & ~support
    masks = {}
    for name, mask in (('support', support), ('water_envelope', water)):
        inset = LIMITS['inset_pixels']
        mask = np.asarray(Image.fromarray(mask).filter(ImageFilter.MinFilter(inset * 2 + 1))).copy()
        height, width = mask.shape
        extent = LIMITS['crosshair_half_extent']
        mask[height // 2 - extent:height // 2 + extent,
             width // 2 - extent:width // 2 + extent] = False
        mask[:int(height * LIMITS['hud_top_fraction'])] = False
        mask[int(height * LIMITS['hud_bottom_fraction']):] = False
        masks[name] = mask
    return masks


def measure(image, empty, masks):
    if image.shape != empty.shape or any(mask.shape != image.shape[:2] for mask in masks.values()):
        raise ValueError('Native image and source geometry viewport differ')
    result = {}
    for name, selected in masks.items():
        signal = difference_mask(image, empty, selected, LIMITS['rgb_delta'])
        result[name] = dict(mask_row(signal), eligible_pixels=int(selected.sum()),
                            observed=int(signal.sum()) >= LIMITS['minimum_signal_pixels'])
    return result


def camera_matches(actual, expected):
    return (all(actual[key] == expected[key] for key in ('position', 'screen', 'fov'))
            and all(abs((a - b + 180.) % 360. - 180.) <= 1.e-6
                    for a, b in zip(actual['rotation'], expected['rotation'])))


def _native_gate(state, declaration):
    projection = declaration['projection']
    expected = frozen.native_reference([
        (tuple(projection['origin'][i] + pos[i] for i in range(3)), value)
        for pos, value in declaration['source_cells']])
    positions = [tuple(row['pos']) for row in state['before']['server']['cells']]
    return all(native.matches(state[point][side], expected, positions)
               for point in ('before', 'after') for side in ('server', 'client'))


def analyze(path):
    path = Path(path).resolve(strict=True)
    source = json.loads(path.read_bytes())
    if source.get('scope') != 'H/L NW palette versus direct SetBlockNew native visibility diagnostic':
        raise ValueError('Only the finite exact native-write comparison is supported')
    geometry_path = sides.read_reference(source['preflight']['geometry_plan'])
    plan = json.loads(geometry_path.read_bytes())
    if plan['kind'] != 'liquid_native_write_compare6':
        raise ValueError('The capture must bind the corresponding pre-capture geometry plan')
    visibility = plan.get('native_write_visibility', {})
    if (visibility.get('limits') != LIMITS or
            visibility.get('analyzer', {}).get('sha256') != reference(__file__)['sha256']):
        raise ValueError('Visibility source and fixed limits must be bound before capture')
    sides.read_reference(visibility['analyzer'])
    declarations = {row['id']: row for row in plan['declarations']}
    if set(declarations) != {route + '_' + label for route in ROUTES for label in SOURCES}:
        raise ValueError('The unchanged complete H/L six-route matrix is required')
    for name, row in plan['source_bindings'].items():
        if sides.fingerprint(sides.ROOT / name)['sha256'] != row['sha256']:
            raise ValueError('Analyzer or built-in source changed: ' + name)
        sides.read_reference(row)
    for row in declarations.values():
        if row['source_cells'] != sides.builtin_geometry(row['source_id'])['source_cells']:
            raise ValueError('Capture source differs from the built-in positive case')
    binding = source['session_binding']
    if binding != plan['session_binding']:
        raise ValueError('Captured source and pre-capture plan session differ')
    captures = source['captures']
    failures = capture_failures(captures, binding)
    required = set(declarations) | {'native_empty_vnw'}
    missing = sorted(required - set(captures))
    if failures:
        raise ValueError('Unreliable or changed native captures: ' + repr(failures))
    output = {'schema': 1, 'source': reference(path), 'geometry_plan': reference(geometry_path),
              'analyzer': reference(__file__), 'limits': LIMITS, 'missing_captures': missing,
              'completed': source.get('completed', False), 'restored': source.get('restored', False),
              'cleanup_errors': source.get('cleanup_errors', []), 'cases': {},
              'native_visibility_observed': False, 'side_uv_qualified': False,
              'transparency_qualified': False, 'animation_qualified': False,
              'production_qualified': False,
              'scope': 'Source-derived native write visibility only; no native shape, UV, tint, alpha or animation acceptance'}
    if 'native_empty_vnw' not in captures:
        output['status'] = 'NOT_TESTED'
        return output
    if captures['native_empty_vnw']['frame']['frame_qpc_100ns'] <= source['preflight']['created_qpc_100ns']:
        raise ValueError('Empty capture precedes the pre-capture geometry declaration')
    empty = rgb(captures['native_empty_vnw']['path'])
    empty_state = source['states']['native_empty_vnw']
    positions = [tuple(row['pos']) for row in empty_state['before']['server']['cells']]
    if not all(native.matches(empty_state[point][side], [], positions)
               for point in ('before', 'after') for side in ('server', 'client')):
        raise ValueError('Declared empty native baseline contains blocks')
    for label, identity in SOURCES.items():
        row = output['cases'][label] = {}
        projection = declarations['native_palette_' + label]['projection']
        masks = visibility_masks(identity, projection)
        for route in ROUTES:
            name = route + '_' + label
            declaration = declarations[name]
            if declaration['projection'] != projection:
                raise ValueError('Native/full comparison camera or source origin differs')
            if name not in captures:
                row[route] = {'status': 'NOT_TESTED'}
                continue
            state = source['states'][name]
            cameras = [state[point]['camera'] for point in ('before', 'after')]
            cameras += [empty_state[point]['camera'] for point in ('before', 'after')]
            if any(not camera_matches(camera, projection) for camera in cameras):
                raise ValueError('Actual camera changed during native comparison: ' + name)
            capture = captures[name]
            if capture['frame']['frame_qpc_100ns'] <= source['preflight']['created_qpc_100ns']:
                raise ValueError('Capture precedes the pre-capture geometry declaration')
            measured = measure(rgb(capture['path']), empty, masks)
            gate = _native_gate(state, declaration) if route.startswith('native') else bool(
                state['before']['source_cells'] == declaration['source_cells']
                and state['after']['source_cells'] == declaration['source_cells'])
            visible = gate and all(value['observed'] for value in measured.values())
            row[route] = {'status': 'OBSERVED' if visible else 'FAIL',
                          'readback_or_source_gate': gate, 'pixels': measured}
    observations = [output['cases'][label][route]['status']
                    for label in SOURCES for route in ROUTES]
    output['native_visibility_observed'] = bool(not missing and output['completed'] and output['restored']
        and not output['cleanup_errors'] and all(status == 'OBSERVED' for status in observations))
    output['status'] = ('FAIL' if 'FAIL' in observations else
                        'NOT_TESTED' if missing else 'OBSERVED' if output['native_visibility_observed'] else 'FAIL')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Preserve existing native observations; use a fresh output')
    result = analyze(args.input)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'status': result['status'], 'native_visibility_observed': result['native_visibility_observed']}))
    return 0 if result['native_visibility_observed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
