"""Replay an incomplete snow control and attribute unchanged-coordinate pixels."""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


def load_functions(path, names, scope, local_imports=False):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    selected = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                and node.name in names]
    if {node.name for node in selected} != set(names):
        raise ValueError('Pinned replay functions missing: ' + str(path))
    if local_imports:
        # Keep the pinned math while avoiding its game-facing module imports.
        for node in selected:
            node.body = [child for child in node.body
                         if not isinstance(child, (ast.Import, ast.ImportFrom))]
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), scope)


def replay(root, report, failure, output=None):
    inputs = root / 'inputs'
    scope = dict(Image=Image, ImageChops=ImageChops, ImageDraw=ImageDraw,
                 ImageFilter=ImageFilter, math=math)
    load_functions(inputs / 'camera.py', ('clamp', 'OrbitCamera'), scope)
    load_functions(inputs / 'verify_snow_plant_visibility.py',
                   ('maximum', 'count', 'changed', 'green_mask', 'capture_frame', 'convex_hull',
                    'editor_snow_geometry'), scope)
    load_functions(inputs / 'verify_centered_snow_profiles.py', ('shape_metrics',), scope)
    load_functions(inputs / 'run_snow_scene_lifecycle_r20.py', ('snow_control_checks',), scope,
                   local_imports=True)
    count = scope['count']
    crop = report['editor_crop']
    blank = report['controls']['blank']['screenshot']
    plant = report['controls']['plant']
    camera = plant['camera_state']
    focus = plant['source']['focus']
    hull, geometry = scope['editor_snow_geometry'](crop, camera, focus, report['height'])
    halo = hull.filter(ImageFilter.MaxFilter(7))
    with Image.open(blank['path']) as image:
        baseline = image.convert('RGB').crop(crop)
    background_rgb = baseline.getpixel((20, 20))
    background = Image.new('RGB', baseline.size, background_rgb)
    baseline_ink = scope['changed'](baseline, background)
    results = []
    if output:
        output.mkdir(parents=True, exist_ok=True)
        baseline.save(output / 'blank_roi.png')
        with Image.open(plant['screenshot']['path']) as image:
            image.crop(crop).save(output / 'plant_roi.png')
        hull.save(output / 'declared_snow_hull.png')
    for index, attempt in enumerate(failure['attempts'], 1):
        record = attempt['capture']
        frame = scope['capture_frame'](record['path'], crop, blank['path'])
        observed = frame['object']
        checks = scope['snow_control_checks'](crop, camera, focus, report['height'], observed)
        if checks != attempt['validation']:
            raise ValueError('Preceding camera does not reproduce the recorded snow validation')
        outside = ImageChops.subtract(observed, halo)
        current_ink = scope['changed'](frame['image'], background)
        removed_baseline = ImageChops.multiply(baseline_ink, ImageChops.invert(current_ink))
        attributed = ImageChops.multiply(outside, removed_baseline)
        residual = ImageChops.subtract(outside, attributed)
        attributed_values = {}
        for xy, value in zip(((x, y) for y in range(baseline.height)
                             for x in range(baseline.width)), attributed.getdata()):
            if value:
                color = str(baseline.getpixel(xy))
                attributed_values[color] = attributed_values.get(color, 0) + 1
        row = {'attempt': index, 'original_validation': checks,
               'observed_pixels': count(observed), 'outside_hull_halo_pixels': count(outside),
               'removed_baseline_ink_pixels': count(attributed),
               'unattributed_outside_pixels': count(residual),
               'removed_ink_bbox_roi': attributed.getbbox(),
               'removed_baseline_colors': attributed_values,
               'observed_hull_bbox_roi': observed.getbbox(),
               'native_clock_advanced': attempt['native_clock_advanced'],
               'render_frames': attempt['render_frames'],
               'capture_sha256': hashlib.sha256(Path(record['path']).read_bytes()).hexdigest()}
        if output:
            prefix = 'snow_' + str(index)
            frame['image'].save(output / (prefix + '_roi.png'))
            observed.save(output / (prefix + '_difference.png'))
            outside.save(output / (prefix + '_outside_hull.png'))
            attributed.save(output / (prefix + '_removed_baseline_ink.png'))
            overlay = frame['image'].copy()
            overlay.paste((255, 0, 90), mask=attributed)
            overlay.save(output / (prefix + '_attribution.png'))
        results.append(row)
    return {'schema': 1, 'original_completed': report['completed'],
            'original_passed': report['passed'], 'original_restored': report['restored'],
            'original_cleanup_errors': report['cleanup_errors'],
            'lifecycle_steps_completed': len(report['steps']), 'background_rgb': background_rgb,
            'camera_source': 'Original preceding plant control observation; exact recorded snow metrics replay',
            'snow_camera_independently_retained': False,
            'missing_failed_control_observation': True,
            'geometry': geometry, 'attempts': results,
            'images_translated_or_aligned': False, 'thresholds_changed': False,
            'workflow_accepted': False, 'production_accepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    report = json.loads((root / 'lifecycle/report.json').read_bytes())
    failure = json.loads((root / 'lifecycle/report_control_snow_response_error.json').read_bytes())
    mapping = json.loads((root / 'manifest.json').read_bytes())['original_to_package']

    def remap(value):
        if isinstance(value, dict):
            return {key: remap(child) for key, child in value.items()}
        if isinstance(value, list):
            return [remap(child) for child in value]
        return str(root / mapping[value]) if isinstance(value, str) and value in mapping else value

    result = replay(root, remap(report), remap(failure), args.output)
    (args.output / 'diagnosis.json').write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'attempts': [{key: row[key] for key in (
        'attempt', 'outside_hull_halo_pixels', 'removed_baseline_ink_pixels',
        'unattributed_outside_pixels')} for row in result['attempts']],
        'workflow_accepted': False, 'production_accepted': False}))


if __name__ == '__main__':
    main()
