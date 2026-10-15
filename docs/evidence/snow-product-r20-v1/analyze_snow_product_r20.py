"""Replay snow shape and burial checks from preserved native PNGs."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

from verify_centered_snow_profiles import shape_metrics, world_alpha
from verify_snow_plant_visibility import (capture_frame, compare_controls, count,
                                         editor_cross_above_snow, editor_snow_geometry)
from native_draw_response import backdrop_pixel_coverage
from snow_native_projection_r20 import physical_roi


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def verified_path(record):
    path = Path(record['path'])
    if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
        raise ValueError('Snow evidence bytes changed: ' + str(path))
    return path


def equal_mask(actual, record):
    with Image.open(verified_path(record)) as image:
        expected = image.convert('L')
    if actual.size != expected.size or ImageChops.difference(actual, expected).getbbox() is not None:
        raise ValueError('Snow pixel replay differs from the preserved mask: ' + record['path'])


def analyze(report):
    captures = {}
    for record in walk(report):
        if 'path' in record and 'sha256' in record:
            verified_path(record)
        if 'capture' in record and 'path' in record:
            capture = record['capture']
            if (not capture.get('reliable') or not capture.get('ok')
                    or capture['frame']['frame_qpc_100ns'] < capture['frame']['request_qpc_100ns']):
                raise ValueError('Snow capture lacks its reliable fresh native receipt')
            captures[record['path']] = record['sha256']
    result = {'schema': 1, 'pixels_replayed': False, 'capture_count': len(captures),
              'original_completed': report['completed'], 'original_passed': report['passed'],
              'original_restored': report['restored'], 'rows': [],
              'qualification_changed': False, 'production_accepted': False}
    blanks, frames = {}, {}
    for row in report['rows']:
        plant, kind, height = row['plant'], row['kind'], row['height']
        if row.get('shared_snow_control'):
            continue
        if kind == 'blank':
            blanks[plant] = row['editor']
            continue
        asset = report['assets'][plant]
        model_path, texture_path = Path(asset['model']), Path(asset['texture'])
        if (hashlib.sha256(model_path.read_bytes()).hexdigest() != asset['model_sha256']
                or hashlib.sha256(texture_path.read_bytes()).hexdigest() != asset['texture_sha256']):
            raise ValueError('Snow model or native texture changed')
        model = json.loads(model_path.read_bytes())
        with Image.open(texture_path) as image:
            texture = image.convert('RGBA')
        crop = row['editor_crop']
        editor = capture_frame(row['editor']['path'], crop, blanks[plant]['path'])
        equal_mask(editor['object'], row['editor_mask'])
        checks = {}
        if kind == 'plant':
            expected = editor_cross_above_snow(crop, row['camera_state'], (1, 1, 1), -1, model, texture)
            equal_mask(expected, row['editor_expected_alpha'])
            checks['editor_shape'] = shape_metrics(expected, editor['object'])
            editor['above_snow'] = {h: editor_cross_above_snow(crop, row['camera_state'], (1, 1, 1), h, model, texture)
                                    for h in report['heights'][plant]}
            if shape_metrics(expected, Image.new('L', expected.size))['passed']:
                raise ValueError('Absent-plant negative unexpectedly accepted')
        elif kind == 'snow':
            editor['geometry'] = editor_snow_geometry(crop, row['camera_state'], (1, 1, 1), height)[0]
        else:
            checks['editor_snow'] = compare_controls(frames[('editor', plant, 'plant', 0)],
                frames[('editor', plant, 'snow', height)], editor, height)
        frames[('editor', plant, kind, height)] = editor
        for mode, world in row.get('world', {}).items():
            size = tuple(world['screenshot']['size'])
            crop = (size[0] // 4, size[1] // 4, size[0] * 3 // 4, size[1] * 3 // 4)
            roi_record = world['roi']
            roi, unused = physical_roi(roi_record['native_readback']['native'], size, crop)
            raw = capture_frame(world['screenshot']['path'], crop, world['hidden_screenshot']['path'])
            actual = dict(raw, object=ImageChops.multiply(raw['object'], roi),
                          green=ImageChops.multiply(raw['green'], roi))
            equal_mask(actual['object'], world['mask'])
            checks[mode + '_backdrop'] = backdrop_pixel_coverage(world['hidden_screenshot'], crop, roi)
            outside = count(ImageChops.subtract(raw['object'], roi.filter(ImageFilter.MaxFilter(7))))
            checks[mode + '_inside_cell'] = {'passed': outside <= max(24, count(actual['object']) * .02),
                                             'outside_pixels': outside}
            if kind == 'plant':
                expected = world_alpha(model, texture, world['pose'], size, crop, report['target'], report['calibration'])
                equal_mask(expected, world['expected_alpha'])
                checks[mode + '_shape'] = shape_metrics(expected, actual['object'])
                actual['above_snow'] = {h: world_alpha(model, texture, world['pose'], size, crop,
                    report['target'], report['calibration'], h) for h in report['heights'][plant]}
            elif kind == 'snow':
                actual['geometry'] = actual['object']
            else:
                checks[mode + '_snow'] = compare_controls(frames[(mode, plant, 'plant', 0)],
                    frames[(mode, plant, 'snow', height)], actual, height)
            frames[(mode, plant, kind, height)] = actual
        checks['full_missing_equivalence'] = shape_metrics(frames[('full', plant, kind, height)]['object'],
            frames[('missing', plant, kind, height)]['object'])
        for key, check in checks.items():
            if check['passed'] != row['checks'][key]['passed']:
                raise ValueError('Snow replay changed the recorded outcome: ' + key)
        result['rows'].append({'plant': plant, 'kind': kind, 'height': height,
                               'checks': checks, 'passed': all(check['passed'] for check in checks.values())})
    result['pixels_replayed'] = True
    result['non_background_checks_passed'] = all(check['passed'] for row in result['rows']
        for key, check in row['checks'].items() if not key.endswith('_backdrop'))
    result['background_checks_passed'] = all(check['passed'] for row in result['rows']
        for key, check in row['checks'].items() if key.endswith('_backdrop'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(json.loads(args.report.read_bytes()))
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps({key: result[key] for key in ('pixels_replayed', 'capture_count',
        'original_passed', 'non_background_checks_passed', 'background_checks_passed', 'production_accepted')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
