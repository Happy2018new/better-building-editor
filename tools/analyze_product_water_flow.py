"""Measure visible water motion in physical face coordinates, without phase fits.

The regular product probe supplies the immutable blueprint, same-session
camera and owner-bound burst receipts. Positive animation alone is insufficient:
the moving artwork must travel down the independently declared physical slope.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

from analyze_product_water import analyze, project

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.debug_product_water_blueprints import source_document
from projection.liquid_native_shapes import product_shape_provider

GRID = 96
LIMITS = {'maximum_pair_seconds': .15, 'minimum_frames': 8,
          'minimum_signal_stddev': .3, 'minimum_correlation': .50,
          'minimum_polarity_margin': .05, 'minimum_correct_pair_fraction': .70}
PHYSICAL_FLOW = {'flow_east': (1, 0), 'flow_south': (0, 1),
                 'flow_west': (-1, 0), 'flow_north': (0, -1)}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atlas_motion(path):
    """Measure the installed artwork separately from any provider/UV rotation."""
    with Image.open(path) as image:
        pixels = np.asarray(image.convert('RGB'), dtype=float)
    width = pixels.shape[1]
    frames = pixels.reshape((-1, width, width, 3))
    rows = []
    for index, first in enumerate(frames):
        second = frames[(index + 1) % len(frames)]
        candidates = sorted((float(np.mean((first - np.roll(second, (dy, dx), axis=(0, 1))) ** 2)), dy, dx)
                            for dy in range(-2, 3) for dx in range(-2, 3))
        best, next_best = candidates[:2]
        rows.append({'frame': index, 'motion_xy': (-best[2], -best[1]),
                     'alignment_mse': best[0], 'next_best_mse': next_best[0]})
    return {'sha256': sha(path), 'frame_count': len(frames), 'frame_pixels': width,
            'rows': rows, 'uniform_motion': len({tuple(row['motion_xy']) for row in rows}) == 1}


def physical_points(shape, face):
    """Interpolate actual planar mesh triangles, independently of shader calls."""
    height = np.rint(np.asarray(shape['heights']) * 255) / 255
    nw, ne, se, sw = height
    u, v = np.meshgrid(np.linspace(.08, .92, GRID), np.linspace(.08, .92, GRID))
    if face == 0:
        y = np.where(v <= u, nw + (ne - nw) * u + (se - ne) * v,
                     nw + (se - sw) * u + (sw - nw) * v)
        x, z = u, v
        spacing = .84 / (GRID - 1)
    else:
        endpoints = {1: (nw, ne), 2: (se, sw), 3: (sw, nw), 4: (ne, se)}[face]
        ceiling = min(endpoints)
        if ceiling < .20:
            raise ValueError('Selected flowing side is too shallow for a physical motion measurement')
        y = (.10 + .75 * v) * ceiling
        x, z = {1: (u, np.zeros_like(u)), 2: (1 - u, np.ones_like(u)),
                3: (np.zeros_like(u), 1 - u), 4: (np.ones_like(u), u)}[face]
        spacing = .75 * .84 * ceiling / (GRID - 1)
    origin = shape['position']
    points = np.stack((x + origin[0], y + origin[1], z + origin[2]), axis=-1)
    return points.reshape((-1, 3)).tolist(), spacing


def physical_samples(images, shape, face, row, source):
    points, spacing = physical_points(shape, face)
    with Image.open(images[0]) as image:
        size = image.size
    mapped = np.asarray(project(points, shape, row, source, size))
    if (not np.isfinite(mapped).all() or np.any(mapped < 0)
            or np.any(mapped[:, 0] > size[0] - 1) or np.any(mapped[:, 1] > size[1] - 1)):
        raise ValueError('Physical flowing face is outside the verified native viewport')
    if min(np.ptp(mapped, axis=0)) < 12:
        raise ValueError('Flowing face has insufficient independent native pixels')
    values = []
    for path in images:
        with Image.open(path) as image:
            if image.size != size:
                raise ValueError('Flow burst dimensions changed')
            pixels = np.asarray(image.convert('L'), dtype=float)
        values.append(map_coordinates(pixels, (mapped[:, 1], mapped[:, 0]), order=1,
                                      mode='nearest').reshape((GRID, GRID)))
    return np.asarray(values), spacing


def correlation(first, second):
    first, second = first.flatten(), second.flatten()
    first, second = first - first.mean(), second - second.mean()
    denominator = np.linalg.norm(first) * np.linalg.norm(second)
    return float(first @ second / denominator) if denominator > 1e-9 else 0.


def motion(signal, times, axis, expected_sign, spacing, texels_per_unit):
    # Removing the temporal mean excludes support blocks and static UI/background.
    centered = signal - signal.mean(axis=0)
    energy = float(centered.std())
    pairs = []
    for index, (first, second) in enumerate(zip(centered, centered[1:])):
        delta = (times[index + 1] - times[index]) / 1e7
        if not 0 < delta <= LIMITS['maximum_pair_seconds']:
            continue
        expected_steps = delta * 20 / (texels_per_unit * spacing)
        maximum = min(GRID // 3, max(4, int(expected_steps * 2 + 3)))
        candidates = []
        for shift in range(-maximum, maximum + 1):
            if shift == 0:
                a, b = first, second
            else:
                start = [slice(None), slice(None)]
                end = [slice(None), slice(None)]
                start[axis] = slice(None, -shift) if shift > 0 else slice(-shift, None)
                end[axis] = slice(shift, None) if shift > 0 else slice(None, shift)
                a, b = first[tuple(start)], second[tuple(end)]
            candidates.append((correlation(a, b), shift))
        best = max(candidates)
        forward = max(value for value, shift in candidates if shift * expected_sign > 0)
        backward = max(value for value, shift in candidates if shift * expected_sign < 0)
        pairs.append({'delta_seconds': delta, 'shift_grid_units': best[1], 'correlation': best[0],
                      'forward_correlation': forward, 'backward_correlation': backward,
                      'polarity_margin': forward - backward,
                      'correct': (best[1] * expected_sign > 0
                                  and best[0] >= LIMITS['minimum_correlation']
                                  and forward - backward >= LIMITS['minimum_polarity_margin'])})
    fraction = sum(row['correct'] for row in pairs) / max(1, len(pairs))
    return {'signal_stddev': energy, 'pairs': pairs, 'eligible_pairs': len(pairs),
            'correct_pair_fraction': fraction, 'physical_grid_spacing': spacing,
            'expected_axis': axis, 'expected_sign': expected_sign,
            'passed': (energy >= LIMITS['minimum_signal_stddev']
                       and len(pairs) >= LIMITS['minimum_frames'] - 1
                       and fraction >= LIMITS['minimum_correct_pair_fraction'])}


def burst_frames(capture):
    from capture_native_burst import _validate_native
    if not all(capture.get(key) is True for key in ('ok', 'reliable', 'capture_valid', 'temporal_complete')):
        raise ValueError('Flow burst lacks valid owner-bound temporal evidence')
    replay = dict(capture)
    _validate_native(replay, capture['instance'], capture['window'],
                     json.dumps(capture['native_manifest']).encode('ascii'))
    native = {row['sequence']: row for row in capture['native_manifest']['frames']}
    images, times = [], []
    for row in capture['frames']:
        if row['png'] is None:
            continue
        png = row['png']
        if sha(png['path']) != png['sha256']:
            raise ValueError('Flow burst PNG changed after capture')
        images.append(png['path'])
        times.append(native[row['sequence']]['frame_qpc_100ns'])
    if len(images) < LIMITS['minimum_frames']:
        raise ValueError('Flow direction has insufficient delivered compositor frames')
    return images, times


def analyze_flow(source_path):
    source = json.loads(source_path.read_bytes())
    base = analyze(source_path)
    result = {'schema': 1, 'source_sha256': sha(source_path), 'analyzer_sha256': sha(__file__),
              'limits': LIMITS, 'evidence_valid': base['evidence_valid'], 'rows': {},
              'capture_failures': base['capture_failures'], 'passed': False,
              'native_parity_claimed': False, 'product_style_accepted': False,
              'scope': 'Independent physical face motion in short owner-bound compositor bursts'}
    if not base['evidence_valid'] or source.get('frozen'):
        return result
    result['atlas'] = atlas_motion(ROOT / 'resource_pack/textures/models/modern_projection/liquid/flowing_water_grey.png')
    for label, burst in source.get('flow_bursts', {}).items():
        row = burst['row']
        case = row['case']
        observed = result['rows'][label] = {'case': case, 'route': row['route'], 'passed': False}
        try:
            if burst['before'] != burst['after']:
                raise ValueError('Physical camera changed during flow burst')
            images, times = burst_frames(burst['capture'])
            observed['frames'] = len(times)
            if case in PHYSICAL_FLOW:
                document = source_document(case)
                provider = product_shape_provider(document)
                value = document.get_layer((3, 3, 3), 0)
                vector = provider.flow_vector(document, (3, 3, 3), 0, value)
                expected = PHYSICAL_FLOW[case]
                if vector[0] * expected[0] + vector[1] * expected[1] <= 0:
                    raise ValueError('Blueprint provider flow does not follow the independently declared slope')
                shape = next(shape for shape in row['ready']['shapes']
                             if shape['faces'] & 1 and tuple(shape['position']) == (3, 3, 3))
                signal, spacing = physical_samples(images, shape, 0, row, source)
                observed.update(provider_vector=vector, transmitted_top_uv=shape['flow_uv'],
                                top=motion(signal, times, 1 if expected[0] else 0,
                                           expected[0] or expected[1], spacing, 16))
                observed['passed'] = observed['top']['passed']
            elif case == 'falling':
                shape = next(shape for shape in row['ready']['shapes']
                             if shape['faces'] & 4 and tuple(shape['position']) == (3, 3, 3))
                signal, spacing = physical_samples(images, shape, 2, row, source)
                observed['south_side'] = motion(signal, times, 0, -1, spacing, 15)
                observed['passed'] = observed['south_side']['passed']
            else:
                raise ValueError('Unexpected flow-direction case')
        except (ValueError, KeyError, StopIteration) as error:
            observed['error'] = str(error)
    required = {route + '_' + case + '_wet' for route in source['routes']
                for case in source['cases'] if case in PHYSICAL_FLOW or case == 'falling'}
    result['missing_requested_bursts'] = sorted(required - set(result['rows']))
    result['passed'] = (bool(required) and not result['missing_requested_bursts']
                        and all(result['rows'][label]['passed'] for label in required))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose fresh flow-direction evidence')
    result = analyze_flow(args.source)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'passed': result['passed'], 'rows': {label: row['passed']
                       for label, row in result['rows'].items()}}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
