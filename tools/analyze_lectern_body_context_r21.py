"""Review source-bound native and packed-context body controls without alignment."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROUTES = ('world', 'empty', 'live', 'roundtrip', 'prepared', 'context')
VIEWS = ('south', 'north', 'east', 'west')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def silhouette(reference, candidate, empty):
    first = np.max(abs(reference.astype(int)-empty.astype(int)), axis=2) > 12
    second = np.max(abs(candidate.astype(int)-empty.astype(int)), axis=2) > 12
    union, common = first | second, first & second
    if min(int(first.sum()), int(second.sum())) < 100:
        raise ValueError('Insufficient native or candidate body pixels')
    bounds = {}
    for name, mask in (('native', first), ('candidate', second)):
        y, x = np.nonzero(mask)
        bounds[name] = [int(x.min()), int(y.min()), int(x.max())+1, int(y.max())+1]
    return {'native_pixels': int(first.sum()), 'candidate_pixels': int(second.sum()),
            'native_only_pixels': int((first & ~second).sum()),
            'candidate_only_pixels': int((second & ~first).sum()),
            'unshifted_iou': float(common.sum()/union.sum()), 'bounds': bounds}


def top_outline(image, empty):
    pixels = image.astype(float)
    r, g, b = np.moveaxis(pixels, -1, 0)
    changed = np.max(abs(pixels-empty.astype(float)), axis=2) > 12
    brown = changed & (r > g*1.02) & (g > b*1.12)
    result = {}
    for column in (100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300):
        rows = np.flatnonzero(brown[:200, column])
        result[str(column)] = int(rows[0]) if rows.size else None
    return result


def analyze(report_path, output):
    report = json.loads(report_path.read_bytes())
    for key in ('completed', 'restored', 'source_unchanged'):
        if report.get(key) is not True:
            raise ValueError('Control did not complete and restore unchanged sources: '+key)
    if report.get('cleanup_errors') or report['palette']['roundtrip_equal'] is not True:
        raise ValueError('Cleanup or native serialization requires separate investigation')
    requested = report['requested_material']
    if requested['name'] not in ('minecraft:lectern', 'minecraft:cyan_concrete'):
        raise ValueError('Expected an empty lectern or cyan-concrete control')
    if set(report['captures']) != {route+'_'+view for route in ROUTES for view in VIEWS}:
        raise ValueError('Expected the complete six-path, four-view control')
    fragment = 'resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment'
    if not report['source_sha256'].get(fragment):
        raise ValueError('The runtime report must bind the shared clipping fragment')
    output.mkdir(parents=True, exist_ok=False)
    records, tiles, image_size = {}, [], None
    for view in VIEWS:
        camera, arrays, captures = None, {}, {}
        for route in ROUTES:
            label = route+'_'+view
            receipt = report['captures'][label]
            if (receipt.get('ok') is not True or receipt.get('reliable') is not True or
                    receipt.get('agent_activation_allowed') is not False or
                    receipt.get('activation_fallback') is not False):
                raise ValueError('Unreliable or unprotected capture: '+label)
            for state in (receipt['before'], receipt['after']):
                if camera is None:
                    camera = state
                if state != camera:
                    raise ValueError('Native and candidate cameras differ: '+label)
            source = Path(receipt['path'])
            if not source.is_file():
                source = report_path.parent/source.name
            if sha(source) != receipt['sha256']:
                raise ValueError('Capture bytes changed: '+label)
            target = camera['target_screen']
            if target.get('isInScreen') is not True:
                raise ValueError('Body is outside the viewport: '+label)
            with Image.open(source) as picture:
                if image_size is None:
                    image_size = picture.size
                if picture.size != image_size:
                    raise ValueError('Capture dimensions changed: '+label)
                x, y = target['screenX'], target['screenY']
                bounds = (round(x-200), round(y-180), round(x+200), round(y+240))
                if min(bounds) < 0 or bounds[2] > picture.width or bounds[3] > picture.height:
                    raise ValueError('Unscaled review crop leaves viewport: '+label)
                crop = picture.convert('RGB').crop(bounds)
            crop_path = output/(label+'.png')
            crop.save(crop_path)
            arrays[route] = np.asarray(crop)
            captures[route] = {'source_sha256': receipt['sha256'],
                               'crop': bounds, 'crop_sha256': sha(crop_path)}
            tiles.append((label, crop))
        scores = {route: silhouette(arrays['world'], arrays[route], arrays['empty'])
                  for route in ROUTES if route not in ('world', 'empty')}
        records[view] = {'camera': camera, 'captures': captures, 'scores': scores,
                         'top_brown_outline_crop_y': {route: top_outline(array, arrays['empty'])
                             for route, array in arrays.items() if route != 'empty'}}
    width, height = tiles[0][1].size
    sheet = Image.new('RGB', (width*len(ROUTES), (height+24)*len(VIEWS)), '#252525')
    draw = ImageDraw.Draw(sheet)
    for index, (label, crop) in enumerate(tiles):
        x, y = index % len(ROUTES)*width, index // len(ROUTES)*(height+24)
        draw.text((x+4, y+5), label, fill='white')
        sheet.paste(crop, (x, y+24))
    sheet.save(output/'review.png')
    result = {'schema': 1, 'production_qualified': False, 'requested_material': requested,
              'source_report_sha256': sha(report_path), 'tool_sha256': sha(Path(__file__)),
              'source_sha256': report['source_sha256'], 'views': records,
              'review_sha256': sha(output/'review.png'),
              'limits': ['No image alignment, rescaling or recoloring is applied.',
                         'Silhouette scores use a fixed 12-level empty-frame difference.',
                         'Lighting and antialiasing can affect diagnostic silhouette counts.',
                         'Moving clouds and distant scenery can contaminate whole-crop difference masks.',
                         'Fixed-column brown outlines are observations, not a semantic wood mask or acceptance test.',
                         'Empty bodies do not establish book pose or all-direction qualification.']}
    (output/'analysis.json').write_text(json.dumps(result, indent=2)+'\n', encoding='ascii')
    print(json.dumps({view: value['scores'] for view, value in records.items()}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    analyze(arguments.report, arguments.output)
