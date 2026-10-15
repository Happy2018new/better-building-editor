"""Replay the twelve declared deployment alpha controls without promoting side UV."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

from analyze_liquid_workspace import capture_failures, difference_mask, rgb, select_roi
from analyze_liquid_transparency import alpha_context, pixel_regions

PHASES = {'0': 0., '0_45': .45, '1': 1., 'default': -1.}
REGIONS = {'submerged_body', 'behind_block'}
SOURCES = ('analyze_liquid_deployment.py', 'analyze_liquid_workspace.py', 'analyze_liquid_transparency.py')


def phase_state(row, world):
    return row if world else row['capture_state']


def opacity_matches(state, alpha, world):
    groups = state['liquid_groups']
    if not groups or not all((row['group'][3][3][1] if world else row['uniforms'][3][1]) == alpha
                             for row in groups):
        return False
    if world:
        return True
    controls = state['liquid_control_requests']
    return bool(controls) and all(row['visible'] and any(row['visible'])
        and row['uniforms'][row['visible'].index(True)].get('4', [None, None])[1] == alpha
        for row in controls)


def analyze(path):
    source = json.loads(path.read_bytes())
    captures, plan = source['captures'], source['transparency_plan']
    failures = capture_failures(captures, source['session_binding'])
    if not source['completed'] or not source['restored'] or source['cleanup_errors']:
        failures.append('Native probe did not complete and restore')
    expected_labels = {prefix + 'water_alpha_' + name
                       for prefix in ('scene_fence_rear_', 'world_fence_rear_full_', 'world_fence_rear_missing_')
                       for name in PHASES}
    if set(captures) != expected_labels:
        raise ValueError('Deployment alpha qualification needs exactly twelve declared captures')
    results = {}
    for mode, prefix, kind in (('editor', 'scene_fence_rear_', 'scene'),
                               ('full', 'world_fence_rear_full_', 'world'),
                               ('missing', 'world_fence_rear_missing_', 'world')):
        images = {name: rgb(captures[prefix + 'water_alpha_' + name]['path'])
                  for name in PHASES}
        if any(value.shape != images['0'].shape for value in images.values()):
            raise ValueError('Deployment alpha controls must have identical native image dimensions')
        capture = captures[prefix + 'water_alpha_0_45']
        regions = pixel_regions(plan[kind + '_engine_regions'], plan[kind + '_engine_screen'],
                                (capture['width'], capture['height']))
        if set(regions) != REGIONS:
            raise ValueError('Deployment alpha qualification needs both declared submerged regions')
        states = (source['scene']['fence_rear']['water_alpha'] if mode == 'editor' else
                  source['world']['fence_rear'][mode + '_water_alpha'])
        context = alpha_context(states['baseline'], mode != 'editor')
        unchanged = all(alpha_context(phase_state(states[name], mode != 'editor'),
                                      mode != 'editor') == context for name in PHASES)
        opacity = all(opacity_matches(phase_state(states[name], mode != 'editor'), alpha,
                                      mode != 'editor') for name, alpha in PHASES.items())
        rows = {}
        for name, region in regions.items():
            selected = select_roi(images['0'].shape, region, crosshair=True)
            eligible = difference_mask(images['0'], images['1'], selected)
            count = int(eligible.sum())
            expected = .55 * images['0'].astype(float) + .45 * images['1']
            rmse = float(np.sqrt(np.mean((images['0_45'][eligible] - expected[eligible]) ** 2))) if count else None
            default_rmse = float(np.sqrt(np.mean((images['default'][eligible] - images['0_45'][eligible]) ** 2))) if count else None
            body = int(difference_mask(images['0_45'], images['1'], eligible).sum())
            water = int(difference_mask(images['0_45'], images['0'], eligible, threshold=3).sum())
            rows[name] = {'region': region, 'eligible_pixels': count, 'endpoint_rgb_rmse': rmse,
                          'default_rgb_rmse': default_rmse, 'body_contribution_pixels': body,
                          'water_contribution_pixels': water,
                          'passed': bool(count >= 80 and rmse <= 3. and default_rmse <= 3.
                                         and body >= .8 * count and water >= .8 * count)}
        results[mode] = {'regions': rows, 'source_shape_models_body_tint_unchanged': unchanged,
                         'declared_alpha_uniforms_applied': opacity,
                         'passed': unchanged and opacity and all(row['passed'] for row in rows.values())}
    return {'schema': 1, 'source': {'path': str(path.resolve()),
                                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()},
            'analyzer_sources': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                 for name in SOURCES},
            'limits': {'minimum_eligible_pixels': 80, 'maximum_rgb_rmse': 3.,
                       'minimum_contribution_fraction': .8, 'body_rgb_threshold': 12,
                       'water_rgb_threshold': 3},
            'capture_failures': failures, 'routes': results,
            'visible_alpha_qualified': not failures and all(row['passed'] for row in results.values()),
            'side_uv_qualified': False, 'animation_qualified': False, 'production_qualified': False,
            'scope': 'Fixed geometry body/water contributions and existing .45 fallback only'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Keep every qualification report immutable')
    archive = args.output.with_suffix('.sources')
    if archive.exists():
        parser.error('Keep every analyzer source archive immutable')
    result = analyze(args.input)
    archive.mkdir(parents=True)
    for name in SOURCES:
        shutil.copyfile(Path(__file__).with_name(name), archive / name)
    result['analyzer_source_archive'] = str(archive.resolve())
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'visible_alpha_qualified': result['visible_alpha_qualified']}))
    return 0 if result['visible_alpha_qualified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
