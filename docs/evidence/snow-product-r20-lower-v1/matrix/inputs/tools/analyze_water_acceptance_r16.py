"""Replay public water side, visibility and game-thread budget acceptance."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

from analyze_product_water import analyze, expected_mask, project, rgb

LIMITS = {'side_correlation': .85, 'side_rgb_rmse': 8.,
          'side_minimum_contrast': 1., 'restored_rgb_rmse': 2.,
          'owner_p95_ms': 5., 'owner_p99_ms': 16.7, 'owner_max_ms': 100.,
          'maximum_groups': 256}


def repetition(first, second):
    first, second = np.asarray(first, dtype=float), np.asarray(second, dtype=float)
    if first.shape != second.shape or first.ndim != 3 or first.shape[2] != 3:
        raise ValueError('Side controls require equally sized RGB samples')
    a, b = first.mean(axis=2).ravel(), second.mean(axis=2).ravel()
    contrast = min(float(a.std()), float(b.std()))
    correlation = float(np.corrcoef(a, b)[0, 1]) if contrast else None
    rmse = float(np.sqrt(np.mean((first - second) ** 2)))
    return {'contrast': contrast, 'correlation': correlation, 'rgb_rmse': rmse,
            'passed': bool(contrast >= LIMITS['side_minimum_contrast'] and
                           correlation >= LIMITS['side_correlation'] and
                           rmse <= LIMITS['side_rgb_rmse'])}


def side_grid(image, shape, face, row, source):
    x, y, z = shape['position']
    heights = [int(value * 255 + .5) / 255. for value in shape['heights']]
    u, v = np.meshgrid(np.linspace(.12, .88, 18), np.linspace(.16, .72, 14))
    points = []
    for horizontal, vertical in zip(u.ravel(), v.ravel()):
        if face == 2:
            point = (x + 1. - horizontal, y + vertical, z + 1.)
        elif face == 4:
            point = (x + 1., y + vertical, z + horizontal)
        else:
            raise ValueError('The declared pool view observes south and east sides')
        if vertical >= min(heights):
            raise ValueError('Side sample exceeds the source waterline')
        points.append(point)
    mapped = np.asarray(project(points, shape, row, source, (image.shape[1], image.shape[0])))
    if (not np.isfinite(mapped).all() or np.any(mapped < .5) or
            np.any(mapped[:, 0] > image.shape[1] - .5) or
            np.any(mapped[:, 1] > image.shape[0] - .5)):
        raise ValueError('Declared physical side samples leave the native viewport')
    return u.shape, mapped


def side_sample(image, shape, face, row, source):
    dimensions, mapped = side_grid(image, shape, face, row, source)
    result = np.stack([map_coordinates(image[:, :, channel].astype(float),
        (mapped[:, 1] - .5, mapped[:, 0] - .5), order=1, mode='nearest')
        for channel in range(3)], axis=1)
    return result.reshape(dimensions + (3,))


def side_checks(source, images):
    results = {}
    for route in source['routes']:
        label = route + '_pool_wet'
        if label not in source['rows']:
            continue
        row = source['rows'][label]
        dry_label = route + '_pool_dry'
        if dry_label not in images:
            raise ValueError('Side continuity needs its paired dry background control')
        opaque_label = label + '_side_opaque'
        if source.get('opaque_side_controls_requested'):
            if opaque_label not in images or opaque_label not in source['extra_rows']:
                raise ValueError('The requested independent opaque side control is missing')
            opaque_row = source['extra_rows'][opaque_label]
            if opaque_row.get('requested_alpha') != 1.:
                raise ValueError('Side control did not request alpha one')
            surface, sample_row = images[opaque_label].astype(float), opaque_row
        else:
            # Legacy controls remove their dry backdrop at the separately accepted alpha.
            surface = (images[label].astype(float) - images[dry_label].astype(float) * .55) / .45
            sample_row = row
        shapes = {tuple(shape['position']): shape for shape in row['ready']['shapes']
                  if shape['texture'] == 'flowing_water_grey' and shape['faces'] & 30}
        native_coordinates = None
        if source.get('native_side_projection_requested') and route != 'editor':
            from water_native_projection import side_coordinates
            try:
                native_coordinates = side_coordinates(source, opaque_label, images)
            except (ValueError, KeyError, TypeError) as error:
                for face in ('south', 'east'):
                    results[label + '_' + face] = {'passed': False, 'error': str(error),
                        'oracle': 'native_api', 'opaque_control': opaque_label}
                continue
        for face, positions in ((2, ((3, 3, 4), (4, 3, 4))),
                                (4, ((4, 3, 3), (4, 3, 4)))):
            try:
                if native_coordinates is None:
                    first, second = (side_sample(surface, shapes[position], face, sample_row, source)
                                     for position in positions)
                else:
                    from water_native_projection import grids, sample
                    plan = grids()
                    keys = ['original_%s_%s' % ('south' if face == 2 else 'east',
                            '_'.join(map(str, position))) for position in positions]
                    first, second = (sample(surface, native_coordinates[key], plan[key]['dimensions']) for key in keys)
            except ValueError as error:
                results[label + '_' + ('south' if face == 2 else 'east')] = {
                    'passed': False, 'error': str(error), 'opaque_control': opaque_label}
                continue
            measured = repetition(first, second)
            measured['background_control'] = dry_label
            measured['surface_opacity'] = 1. if source.get('opaque_side_controls_requested') else .45
            measured['opaque_control'] = opaque_label if source.get('opaque_side_controls_requested') else None
            measured['oracle'] = 'native_api' if native_coordinates is not None else 'analytic'
            measured['negative_mirrored'] = repetition(first, second[:, ::-1])
            measured['negative_constant'] = repetition(first, np.full_like(second, second.mean()))
            measured['negative_wrong_phase'] = repetition(first, np.roll(second, 5, axis=1))
            measured['passed'] = measured['passed'] and all(
                not measured[name]['passed'] for name in
                ('negative_mirrored', 'negative_constant', 'negative_wrong_phase'))
            results[label + '_' + ('south' if face == 2 else 'east')] = measured
    return results


def budget_checks(source):
    samples = source.get('owner_timing_ms', {})
    result = {}
    for method, values in samples.items():
        values = np.asarray(values, dtype=float)
        row = {'samples': len(values), 'p95_ms': None, 'p99_ms': None, 'maximum_ms': None,
               'passed': False}
        if len(values) >= 20 and np.all(np.isfinite(values)) and np.all(values >= 0):
            row.update(p95_ms=float(np.percentile(values, 95)),
                       p99_ms=float(np.percentile(values, 99)), maximum_ms=float(values.max()))
            row['passed'] = (row['p95_ms'] <= LIMITS['owner_p95_ms'] and
                             row['p99_ms'] <= LIMITS['owner_p99_ms'] and
                             row['maximum_ms'] <= LIMITS['owner_max_ms'])
        result[method] = row
    return result


def visibility_pixels(original, dry, hidden, restored, mask):
    water_delta = np.max(np.abs(original.astype(float) - dry), axis=2)
    eligible = mask & (water_delta >= 8)
    count = int(np.count_nonzero(eligible))
    rmse = (float(np.sqrt(np.mean((original[eligible].astype(float) - restored[eligible]) ** 2)))
            if count else None)
    hidden_delta = np.max(np.abs(original.astype(float) - hidden), axis=2)
    return {'restored_rgb_rmse': rmse,
            'visible_water_pixels_removed': int(np.count_nonzero(eligible & (hidden_delta >= 8))),
            'independently_visible_water_pixels': count}


def replay(path):
    source = json.loads(path.read_bytes())
    base = analyze(path)
    result = {'schema': 1, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'limits': LIMITS, 'evidence_valid': base['evidence_valid'],
              'source_unchanged': source.get('source_unchanged'),
              'visibility': {}, 'side_uv': {}, 'budgets': {}, 'lifecycle': {},
              'maximum_observed_groups': 0, 'passed': False,
              'scope': ('Public isolated pool and partial-solid controls; owner-call elapsed time '
                        'excludes IPC and screenshots but can include thread scheduling delays')}
    if not base['evidence_valid']:
        result['capture_failures'] = base['capture_failures']
        return result
    images = {label: rgb(row['path']) for label, row in source['captures'].items()}
    if source.get('visibility_controls_requested'):
        for label, row in source['rows'].items():
            if row['control'] != 'wet' or row['case'] == 'drop_north':
                continue
            hidden_label, restored_label = label + '_section', label + '_section_restored'
            hidden, restored = (source['extra_rows'].get(name) for name in (hidden_label, restored_label))
            measured = {'complete': hidden is not None and restored is not None, 'passed': False}
            if measured['complete']:
                original = images[label]
                mask = expected_mask(row, source, (original.shape[1], original.shape[0]))
                dry_label = label[:-3] + 'dry'
                if dry_label not in images:
                    raise ValueError('Visibility needs a paired control preserving native bodies')
                pixels = visibility_pixels(original, images[dry_label], images[hidden_label],
                                           images[restored_label], mask)
                rmse, changed = pixels['restored_rgb_rmse'], pixels['visible_water_pixels_removed']
                measured.update(hidden_groups=hidden['water_groups'], restored_groups=restored['water_groups'],
                    **pixels)
                measured.update(
                    logical_cells_preserved=all(source['rows'][label]['ready']['source_cells'] == item['ready']['source_cells']
                                                for item in (hidden, restored)))
                measured['passed'] = (hidden['water_groups'] == 0 and restored['water_groups'] > 0 and
                    rmse is not None and rmse <= LIMITS['restored_rgb_rmse'] and changed >= 24
                    and measured['logical_cells_preserved'])
            result['visibility'][label] = measured
    if source.get('frozen'):
        result['side_uv'] = side_checks(source, images)
        if source.get('native_side_projection_requested'):
            result['analytic_side_uv_diagnostic'] = side_checks(
                dict(source, native_side_projection_requested=False), images)
    if source.get('owner_timing_requested'):
        result['budgets'] = budget_checks(source)
    for label, row in source['rows'].items():
        groups = row['ready'].get('liquid_groups', ())
        result['maximum_observed_groups'] = max(result['maximum_observed_groups'], len(groups))
        if row['route'] != 'editor':
            state = row.get('stopped', {})
            result['lifecycle'][label] = bool(state.get('active') is False and
                state.get('liquid') is False and state.get('retired') == 0 and state.get('world_actors') == 0)
    result['model_budget_passed'] = 0 < result['maximum_observed_groups'] <= LIMITS['maximum_groups']
    required = ('visibility', 'side_uv', 'budgets', 'lifecycle')
    result['passed'] = (result['model_budget_passed'] and all(result[key] for key in required) and
        all(row['passed'] for key in required[:-1] for row in result[key].values()) and
        all(result['lifecycle'].values()))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh analysis')
    result = replay(args.source)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps(result))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
