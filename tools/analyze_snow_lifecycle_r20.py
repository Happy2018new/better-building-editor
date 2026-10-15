"""Replay saved native snow workflows while preserving incomplete acquisition state."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from analyze_snow_product_r20 import equal_mask, verified_path, walk
from native_draw_response import changed_pixels, native_clock
from run_snow_scene_lifecycle_r20 import STEPS, snow_control_checks
from verify_centered_snow_profiles import shape_metrics
from verify_snow_plant_visibility import (capture_frame, compare_controls,
    editor_cross_above_snow, editor_snow_geometry)


def response_checks(response, reference, crop, expected_capture=None):
    reference_clock = native_clock(reference)
    reference_clock['crop'] = list(reference_clock['crop'])
    if reference_clock != response['reference_clock']:
        raise ValueError('Snow native response reference clock changed')
    rows = []
    for attempt in response['attempts']:
        picture = attempt['capture']
        clock = native_clock(picture)
        clock['crop'] = list(clock['crop'])
        ticks = attempt['render_frames']
        advanced = clock['sha256'] != reference_clock['sha256']
        if (clock != attempt['clock'] or advanced != attempt['native_clock_advanced']
                or ticks['source'] != 'GameRenderTickEvent' or ticks['after'] < ticks['before'] + 2):
            raise ValueError('Snow native response clock or render ticks changed')
        row = {'native_clock_advanced': advanced, 'render_ticks_advanced': True,
               'changed_pixels_replayed': crop is not None}
        if crop is not None:
            changed = changed_pixels(reference, picture, crop, response.get('channel_threshold', 20))
            if changed != attempt['changed_pixels']:
                raise ValueError('Snow native response changed-pixel count differs')
            row['changed_pixels'] = changed
        rows.append(row)
    if not rows or not rows[-1]['native_clock_advanced']:
        raise ValueError('Snow native response has no advanced final native clock')
    if not response['passed']:
        raise ValueError('Snow native response was not accepted during acquisition')
    if expected_capture is not None and response['attempts'][-1]['capture']['sha256'] != expected_capture['sha256']:
        raise ValueError('Snow native response does not bind the selected screenshot')
    if crop is not None and rows[-1]['changed_pixels'] < response['minimum_changed_pixels']:
        raise ValueError('Snow final native response did not meet its recorded threshold')
    return rows


def analyze(report):
    captures = {}
    for record in walk(report):
        if 'path' in record and 'sha256' in record:
            verified_path(record)
        if 'capture' not in record or 'path' not in record:
            continue
        capture = record['capture']
        if (not capture.get('ok') or not capture.get('reliable')
                or capture.get('owner') != report['owner']
                or capture.get('game_pid') != report['game_pid']
                or capture.get('game_identity') != report['game_identity']
                or capture.get('agent_activation_allowed') is not False
                or capture.get('activation_fallback') is not False
                or capture['frame']['frame_qpc_100ns'] < capture['frame']['request_qpc_100ns']):
            raise ValueError('Snow capture lacks its owner-bound fresh native receipt')
        captures[record['path']] = record['sha256']
    result = {'schema': 1, 'capture_count': len(captures), 'capture_bytes_verified': True,
              'original_completed': report['completed'], 'original_passed': report['passed'],
              'original_restored': report['restored'], 'original_cleanup_errors': report['cleanup_errors'],
              'pixels_replayed': False, 'workflow_accepted': False, 'production_accepted': False,
              'qualification_changed': False, 'responses': {}, 'controls': {}, 'steps': []}
    preflight = report['native_draw_preflight']
    result['responses']['ui_hiding'] = response_checks(preflight['hiding'], preflight['shown'], preflight['crop'], preflight['hidden'])
    result['responses']['ui_showing'] = response_checks(preflight['showing'], preflight['hidden'], preflight['crop'], preflight['restored'])
    residual = changed_pixels(preflight['shown'], preflight['restored'], preflight['crop'])
    if residual != preflight['restoration_changed_pixels'] or residual > 24:
        raise ValueError('Snow native UI header restoration pixels changed')
    blank = report['controls']['blank']['screenshot']
    crop = report.get('editor_crop')
    for kind, row in report['controls'].items():
        if row.get('native_response'):
            result['responses']['control_' + kind] = response_checks(row['native_response'], blank, crop, row['screenshot'])
    for row in report['steps']:
        result['responses'][row['label']] = response_checks(row['native_response'], blank, crop, row['screenshot'])
    if crop is None:
        result['replay_blockers'] = ['Original acquisition did not retain the Scene editor crop']
        return result
    if len(crop) != 4 or crop[2] <= crop[0] or crop[3] <= crop[1]:
        raise ValueError('Snow Scene crop is empty or malformed')
    asset = report['assets']
    model_path, texture_path = Path(asset['model']), Path(asset['texture'])
    if (hashlib.sha256(model_path.read_bytes()).hexdigest() != asset['model_sha256']
            or hashlib.sha256(texture_path.read_bytes()).hexdigest() != asset['texture_sha256']):
        raise ValueError('Snow lifecycle model or native texture bytes changed')
    model = json.loads(model_path.read_bytes())
    with Image.open(texture_path) as image:
        texture = image.convert('RGBA')
    frames = {}
    height = report['height']
    for kind in ('plant', 'snow', 'covered'):
        row = report['controls'][kind]
        camera, focus = row['camera_state'], row['source']['focus']
        frame = capture_frame(row['screenshot']['path'], crop, blank['path'])
        if kind == 'plant':
            expected = editor_cross_above_snow(crop, camera, focus, -1, model, texture)
            equal_mask(expected, row['expected_alpha'])
            check = shape_metrics(expected, frame['object'])
            frame['above_snow'] = {height: editor_cross_above_snow(crop, camera, focus, height, model, texture)}
        elif kind == 'snow':
            frame['geometry'] = editor_snow_geometry(crop, camera, focus, height)[0]
            equal_mask(frame['geometry'], row['expected_alpha'])
            check = snow_control_checks(crop, camera, focus, height, frame['object'])
        else:
            check = compare_controls(frames['plant'], frames['snow'], frame, height)
        if check['passed'] != row['passed'] or check != row['checks']:
            raise ValueError('Snow lifecycle control replay changed: ' + kind)
        frames[kind] = frame
        result['controls'][kind] = check
    if len(report['steps']) > len(STEPS):
        raise ValueError('Snow lifecycle contains unexpected extra steps')
    for index, row in enumerate(report['steps']):
        if (row['label'], row['expected_control']) != STEPS[index][:2]:
            raise ValueError('Snow lifecycle steps are missing or reordered')
        frame = capture_frame(row['screenshot']['path'], crop, blank['path'])
        equal_mask(frame['object'], row['mask'])
        check = shape_metrics(frames[row['expected_control']]['object'], frame['object'])
        if check['passed'] != row['passed'] or check != row['checks']:
            raise ValueError('Snow lifecycle edit replay changed: ' + row['label'])
        result['steps'].append({'label': row['label'], 'checks': check})
    result['pixels_replayed'] = True
    result['workflow_accepted'] = (report['completed'] and report['restored']
        and not report['cleanup_errors'] and len(report['steps']) == len(STEPS)
        and all(row['passed'] for row in result['controls'].values())
        and all(row['checks']['passed'] for row in result['steps']))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(json.loads(args.report.read_bytes()))
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps({key: result[key] for key in ('capture_count', 'capture_bytes_verified',
        'pixels_replayed', 'original_completed', 'original_restored', 'workflow_accepted', 'production_accepted')}))


if __name__ == '__main__':
    main()
