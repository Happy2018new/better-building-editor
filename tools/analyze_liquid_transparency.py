"""Replay geometry-declared submerged and rear-block contributions independently."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil

import numpy as np

from analyze_liquid_workspace import capture_failures, difference_mask, rgb, select_roi

CONTROLS = ('supported_positive', 'supported_negative', 'liquid_only', 'empty')


def pixel_regions(regions, engine_screen, native_screen):
    scale = tuple(native_screen[i] / engine_screen[i] for i in range(2))
    result = {}
    for name, points in regions.items():
        values = [(point['screenX'], point['screenY']) if isinstance(point, dict) else point
                  for point in points]
        xs, ys = ([point[axis] * scale[axis] for point in values] for axis in range(2))
        # Inset rounding keeps every sampled pixel inside the declared logical interior.
        bounds = [math.ceil(min(xs)), math.ceil(min(ys)), math.floor(max(xs)), math.floor(max(ys))]
        if not 0 <= bounds[0] < bounds[2] <= native_screen[0] or not 0 <= bounds[1] < bounds[3] <= native_screen[1]:
            raise ValueError('Declared transparency region is empty or outside the native image')
        result[name] = bounds
    return result


def contribution_row(positive, no_water, liquid_only, empty, regions):
    if any(image.shape != positive.shape for image in (no_water, liquid_only, empty)):
        raise ValueError('Transparency controls must have identical native image dimensions')
    result = {}
    for name in ('submerged_body', 'behind_block'):
        selected = select_roi(positive.shape, regions[name], crosshair=True)
        body = difference_mask(no_water, empty, selected)
        water = difference_mask(liquid_only, empty, selected)
        eligible = body & water
        count = int(eligible.sum())
        body_contribution = difference_mask(positive, liquid_only, eligible)
        water_contribution = difference_mask(positive, no_water, eligible, threshold=3)
        row = {'region': regions[name], 'selected_pixels': int(selected.sum()), 'eligible_pixels': count,
               'body_contribution_pixels': int(body_contribution.sum()),
               'water_contribution_pixels': int(water_contribution.sum()), 'status': 'NOT_TESTED'}
        if count >= 80:
            body_delta = (no_water - empty)[eligible].astype(np.float64)
            residual = (positive - liquid_only)[eligible].astype(np.float64)
            transmission = np.sum(body_delta * residual, axis=1) / np.sum(body_delta ** 2, axis=1)
            valid = (transmission > .02) & (transmission < .95)
            row.update(median_body_transmission=float(np.median(transmission)),
                       transmission_quantiles=[float(value) for value in np.quantile(transmission, (.1, .9))],
                       bounded_transmission_pixels=int(valid.sum()),
                       liquid_only_channel_std=[float(value) for value in liquid_only[eligible].std(axis=0)],
                       status='OBSERVED' if (body_contribution.sum() >= count * .8
                           and water_contribution.sum() >= count * .8 and valid.sum() >= count * .8) else 'FAIL')
        result[name] = row
    statuses = [row['status'] for row in result.values()]
    return {'status': 'FAIL' if 'FAIL' in statuses else 'NOT_TESTED' if 'NOT_TESTED' in statuses else 'OBSERVED',
            'regions': result, 'native_alpha_accepted': False,
            'scope': 'Both bodies contribute beneath water and water changes those bodies; this does not accept UV, final native alpha, or transparent sorting'}


def contrast_row(bright_water, bright_dry, dark_water, dark_dry, regions):
    """Hold water topology fixed while changing each body's opaque artwork."""
    if any(image.shape != bright_water.shape for image in (bright_dry, dark_water, dark_dry)):
        raise ValueError('Contrast controls must have identical native image dimensions')
    result = {}
    for name in ('submerged_body','behind_block'):
        selected = select_roi(bright_water.shape, regions[name], crosshair=True)
        eligible = difference_mask(bright_dry,dark_dry,selected)
        count = int(eligible.sum())
        row = {'region':regions[name], 'eligible_pixels':count, 'status':'NOT_TESTED'}
        if count >= 80:
            dry = (bright_dry-dark_dry)[eligible].astype(np.float64)
            wet = (bright_water-dark_water)[eligible].astype(np.float64)
            coefficient = float(np.sum(dry*wet)/np.sum(dry**2))
            rms = float(np.sqrt(np.mean((wet-coefficient*dry)**2)))
            point_coefficients = np.sum(dry*wet,axis=1)/np.sum(dry**2,axis=1)
            bounded = (point_coefficients>.02) & (point_coefficients<.95)
            row.update(transmission=coefficient, rgb_rmse=rms,
                       bounded_transmission_pixels=int(bounded.sum()),
                       point_transmission_quantiles=[float(value) for value in np.quantile(point_coefficients,(.1,.5,.9))],
                       status='OBSERVED' if .02<coefficient<.95 and rms<=5.
                           and bounded.sum()>=count*.8 else 'FAIL')
        result[name] = row
    statuses = [row['status'] for row in result.values()]
    return {'status':'FAIL' if 'FAIL' in statuses else 'NOT_TESTED' if 'NOT_TESTED' in statuses else 'OBSERVED',
            'regions':result, 'native_alpha_accepted':False,
            'scope':'Transmission conditional on unchanged water geometry, camera and stable opaque contrast artwork'}


def alpha_row(images, regions):
    """Use transparent/opaque endpoints without removing water or its neighbors."""
    clear, opaque = images['0'], images['1']
    if any(image.shape != clear.shape for image in images.values()):
        raise ValueError('Water alpha controls must have identical native image dimensions')
    result = {}
    for name in ('submerged_body', 'behind_block'):
        selected = select_roi(clear.shape, regions[name], crosshair=True)
        eligible = difference_mask(clear, opaque, selected)
        count = int(eligible.sum())
        row = {'region': regions[name], 'eligible_pixels': count, 'status': 'NOT_TESTED', 'phases': {}}
        if count >= 80:
            for label, alpha in (('0_25', .25), ('0_45', .45), ('0_75', .75)):
                actual = images[label]
                expected = clear.astype(np.float64) * (1. - alpha) + opaque * alpha
                rms = float(np.sqrt(np.mean((actual[eligible] - expected[eligible]) ** 2)))
                body = difference_mask(actual, opaque, eligible)
                water = difference_mask(actual, clear, eligible, threshold=3)
                water_residual = actual[eligible] - clear[eligible] * (1. - alpha)
                row['phases'][label] = {'requested_alpha': alpha, 'endpoint_rgb_rmse': rms,
                    'body_contribution_pixels': int(body.sum()), 'water_contribution_pixels': int(water.sum()),
                    'water_residual_channel_std':[float(value) for value in water_residual.std(axis=0)],
                    'status': 'OBSERVED' if rms <= 3. and body.sum() >= count * .8
                        and water.sum() >= count * .8 else 'FAIL'}
            default_rms = float(np.sqrt(np.mean((images['default'][eligible]
                - images['0_45'][eligible]).astype(np.float64) ** 2)))
            opaque_std = [float(value) for value in opaque[eligible].std(axis=0)]
            row.update(opaque_water_channel_std=opaque_std,
                       water_texture_variation_observed=min(opaque_std) > 2.
                           and all(min(phase['water_residual_channel_std']) > 1.
                                   for phase in row['phases'].values()),
                       default_rgb_rmse=default_rms,
                       status='OBSERVED' if default_rms <= 3.
                           and all(phase['status'] == 'OBSERVED' for phase in row['phases'].values()) else 'FAIL')
        result[name] = row
    statuses = [row['status'] for row in result.values()]
    return {'status': 'FAIL' if 'FAIL' in statuses else 'NOT_TESTED' if 'NOT_TESTED' in statuses else 'OBSERVED',
            'regions': result, 'native_alpha_accepted': False,
            'scope': 'Fixed water geometry transparent/opaque endpoints; intermediate water retains both body and water contributions'}


def water_geometry(state, world=False):
    rows = state['liquid_groups']
    if world:
        return sorted((repr(row['group'][0]),row['group'][1],row['group'][3][:3]) for row in rows)
    return sorted((row['key'],row['model'],row['uniforms'][:3]) for row in rows)


def contrast_context(state, world=False):
    if world:
        appearance = sorted((repr(row['group'][0]), row['group'][3][3]) for row in state['liquid_groups'])
        view = None
    else:
        appearance = sorted((row['key'], row['uniforms'][3]) for row in state['liquid_groups'])
        view = (state['camera_pose'], state['camera_pan'], state['screen_size'],
                sorted((row['key'], row['geometry'], row['poses']) for row in state['liquid_control_requests']))
    return water_geometry(state, world), appearance, view


def alpha_context(state, world=False):
    """Only liquid opacity y may vary within a fixed-geometry holdout."""
    if world:
        appearance = sorted((repr(row['group'][0]), row['group'][3][3][::2], row['group'][3][3][3])
                            for row in state['liquid_groups'])
        models = sorted((row['key'], row['id']) for row in state['liquid_groups'])
        body = (state['body_entity'], state['body_parts'], state['body_uniforms'])
        view = None
    else:
        appearance = sorted((row['key'], row['uniforms'][3][::2], row['uniforms'][3][3])
                            for row in state['liquid_groups'])
        models = sorted((row['key'], row['model_ids'], row['front']) for row in state['liquid_groups'])
        body = (state['document_id'], state['model_name'], state['tile_builds'])
        view = (state['camera_pose'], state['camera_pan'], state['screen_size'],
                sorted((row['key'], row['geometry'], row['poses'], row['visible'])
                       for row in state['liquid_control_requests']))
    return water_geometry(state, world), appearance, models, body, view, state['source_cells']


def analyze(path):
    source = json.loads(path.read_bytes())
    captures, plan = source['captures'], source['transparency_plan']
    failures = capture_failures(captures, source['session_binding'])
    if not source['completed'] or not source['restored'] or source['cleanup_errors']:
        failures.append('Probe was incomplete or did not restore all owned state')
    result = {'schema': 1, 'source': {'path': str(path.resolve()),
                                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest()},
              'capture_failures': failures, 'controls': {}, 'contrast_controls': {}, 'water_alpha_controls': {},
              'native_alpha_accepted': False,
              'production_editor_accepted': False, 'production_world_accepted': False,
              'limits': {'minimum_eligible_pixels': 80, 'minimum_contribution_fraction': .8,
                         'body_rgb_threshold': 12, 'water_rgb_threshold': 3,
                         'bounded_transmission_interval': [.02, .95]},
              'declaration': plan}
    for mode, prefix, kind in (('editor', 'scene_fence_rear_', 'scene'),
                               ('native', 'native_fence_rear_', 'world'),
                               ('full', 'world_fence_rear_full_', 'world'),
                               ('missing', 'world_fence_rear_missing_', 'world')):
        labels = [prefix + control for control in CONTROLS]
        if any(label not in captures for label in labels) or kind + '_engine_regions' not in plan:
            result['controls'][mode] = {'status': 'NOT_TESTED', 'reason': 'Four controls or declared geometry are absent'}
            continue
        capture = captures[labels[0]]
        regions = pixel_regions(plan[kind + '_engine_regions'], plan[kind + '_engine_screen'],
                                (capture['width'], capture['height']))
        images = [rgb(captures[label]['path']) for label in labels]
        result['controls'][mode] = contribution_row(*images, regions)
        contrast_labels = [prefix+name for name in
                           ('supported_positive','supported_negative','supported_positive_dark','supported_negative_dark')]
        if all(label in captures for label in contrast_labels):
            contrast = contrast_row(*(rgb(captures[label]['path']) for label in contrast_labels),regions)
            if mode=='editor':
                states=source['scene']['fence_rear']
                unchanged=contrast_context(states['supported_positive']['ready'])==contrast_context(states['supported_positive_dark']['ready'])
            elif mode in ('full','missing'):
                states=source['world']['fence_rear']
                unchanged=contrast_context(states[mode+'_supported_positive']['ready'],True)==contrast_context(states[mode+'_supported_positive_dark']['ready'],True)
            else:
                unchanged=all(row['gates'][side]['unchanged'] and row['gates'][side]['before_matches']
                    and row['gates'][side]['after_matches'] for name,row in source['native']['fence_rear'].items()
                    if isinstance(row,dict) and 'gates' in row for side in ('server','client'))
                contrast['native_geometry_scope']='Exact native state/control snapshots; equality of native tessellation is not directly observed'
            contrast['water_geometry_and_appearance_control']=unchanged
            if not unchanged:
                contrast['status']='FAIL'
            result['contrast_controls'][mode]=contrast
        alpha_labels = {name: prefix+'water_alpha_'+name for name in ('0','0_25','0_45','0_75','1','default')}
        if mode != 'native' and all(label in captures for label in alpha_labels.values()):
            alpha = alpha_row({name:rgb(captures[label]['path']) for name,label in alpha_labels.items()},regions)
            if mode == 'editor':
                states = source['scene']['fence_rear']['water_alpha']
                baseline = alpha_context(states['baseline'])
                unchanged = all(alpha_context(row['capture_state']) == baseline for name,row in states.items()
                                if name != 'baseline')
            else:
                states = source['world']['fence_rear'][mode+'_water_alpha']
                baseline = alpha_context(states['baseline'],True)
                unchanged = all(alpha_context(row,True) == baseline for name,row in states.items() if name != 'baseline')
            alpha['source_shape_models_body_tint_unchanged'] = unchanged
            alpha['camera_control'] = ('Measured native Scene pose/layout unchanged in each phase' if mode == 'editor'
                else 'Initial native camera measured; frozen probe issues no camera changes during world phases')
            if not unchanged:
                alpha['status'] = 'FAIL'
            result['water_alpha_controls'][mode] = alpha
    result['contributions_observed'] = not failures and all(
        row['status'] == 'OBSERVED' for row in result['controls'].values())
    result['contrast_contributions_observed'] = not failures and all(
        result['contrast_controls'].get(mode,{}).get('status') == 'OBSERVED'
        for mode in ('editor','native','full','missing'))
    result['water_alpha_holdout_observed'] = not failures and all(
        result['water_alpha_controls'].get(mode,{}).get('status') == 'OBSERVED'
        for mode in ('editor','full','missing'))
    result['water_texture_variation_observed'] = result['water_alpha_holdout_observed'] and all(
        row.get('water_texture_variation_observed',False)
        for controls in result['water_alpha_controls'].values() for row in controls['regions'].values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require', choices=('contributions','contrast','water-alpha','water-texture'), action='append',
                        help='Choose observation gates explicitly; default preserves the original four-control gate')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh replay report')
    archive = args.output.with_suffix('.analyzer.py')
    if archive.exists():
        parser.error('Choose a fresh analyzer source archive')
    archive.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(__file__,archive)
    report = analyze(args.input)
    report['analyzer_source'] = {'path':str(archive.resolve()),
                                'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    gates = {'contributions':'contributions_observed', 'contrast':'contrast_contributions_observed',
             'water-alpha':'water_alpha_holdout_observed', 'water-texture':'water_texture_variation_observed'}
    report['required_observations'] = args.require or ['contributions']
    report['required_observations_passed'] = all(report[gates[name]] for name in report['required_observations'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'contributions_observed': report['contributions_observed'],
                      'contrast_contributions_observed':report['contrast_contributions_observed'],
                      'water_alpha_holdout_observed':report['water_alpha_holdout_observed'],
                      'water_texture_variation_observed':report['water_texture_variation_observed'],
                      'controls': {name: row['status'] for name, row in report['controls'].items()},
                      'capture_failures': report['capture_failures']}))
    return 0 if report['required_observations_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
