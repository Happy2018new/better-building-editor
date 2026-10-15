"""Compare unchanged world-native and projected block face pixels offline."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_erosion
from scipy.spatial import ConvexHull

from archive_frame_block_evidence_r21 import verify_files, write_json

LUMA = np.array([.2126, .7152, .0722])
EROSION_PIXELS = 2


def face_regions(position, pose, camera, size, fov, silhouette, project):
    scale = pose['scale_blocks']
    offset = pose['center_offset_blocks']
    center = np.array(position, dtype=float) + .5 + [-offset[0], offset[1], offset[2]]
    pitch, yaw = map(math.radians, camera['rotation'][:2])
    direction = np.array([math.sin(yaw)*math.cos(pitch), -math.sin(pitch), -math.cos(yaw)*math.cos(pitch)])
    target = np.array(camera['position']) + direction
    interior = binary_erosion(silhouette, iterations=EROSION_PIXELS)
    regions = {}
    for axis, label in enumerate(('x', 'y', 'z')):
        for sign in (-1, 1):
            normal = np.eye(3)[axis] * sign
            face_center = center + normal * scale / 2.
            if np.dot(np.array(camera['position']) - face_center, normal) <= 0:
                continue
            other = [index for index in range(3) if index != axis]
            corners = [face_center + np.eye(3)[other[0]] * first * scale / 2.
                + np.eye(3)[other[1]] * second * scale / 2.
                for first, second in ((-1, -1), (-1, 1), (1, 1), (1, -1))]
            points = project(corners, camera['position'], target, size, fov)
            polygon = [(point['screenX'], point['screenY']) for point in points]
            region = Image.new('1', size)
            ImageDraw.Draw(region).polygon(polygon, fill=1)
            mask = binary_erosion(np.asarray(region), iterations=EROSION_PIXELS) & interior
            if mask.any():
                regions[label + ('+' if sign > 0 else '-')] = {'mask': mask,
                    'polygon': polygon, 'normal': normal.tolist()}
    return regions


def color_summary(pixels):
    values = pixels.astype(float)
    luma = values @ LUMA
    return {'pixels': len(values), 'mean_rgb': values.mean(axis=0).tolist(),
        'median_rgb': np.median(values, axis=0).tolist(), 'std_rgb': values.std(axis=0).tolist(),
        'mean_luma_encoded': float(luma.mean()), 'std_luma_encoded': float(luma.std())}


def color_pair(native, product):
    first, second = native.astype(float), product.astype(float)
    delta = second - first
    luma_first, luma_second = first @ LUMA, second @ LUMA
    correlation = (float(np.corrcoef(luma_first, luma_second)[0, 1])
                   if min(luma_first.std(), luma_second.std()) > 1e-9 else None)
    return {'mean_signed_rgb': delta.mean(axis=0).tolist(),
        'mean_absolute_rgb': np.abs(delta).mean(axis=0).tolist(),
        'max_absolute_channel': float(np.abs(delta).max()),
        'p95_max_channel_delta': float(np.percentile(np.abs(delta).max(axis=1), 95)),
        'identical_pixel_fraction': float(np.all(delta == 0, axis=1).mean()),
        'mean_luma_ratio': float(luma_second.mean()/luma_first.mean()) if luma_first.mean() else None,
        'texture_luma_correlation': correlation,
        'fitted_alignment_or_color_correction': False}


def bounds(mask):
    y, x = np.nonzero(mask)
    return [int(x.min()), int(y.min()), int(x.max()+1), int(y.max()+1)]


def draw_montage(rows, output, annotated=False):
    font = ImageFont.load_default(size=18)
    panel_width, panel_height = 360, 400
    montage = Image.new('RGB', (panel_width*3, panel_height*len(rows)), 'white')
    draw = ImageDraw.Draw(montage)
    for index, row in enumerate(rows):
        box = np.array(bounds(row['mask'])) + [-12, -12, 12, 12]
        for column, route in enumerate(('native', 'full', 'missing')):
            crop = row['images'][route].crop(tuple(box))
            ratio = min((panel_width-16)/crop.width, (panel_height-48)/crop.height)
            crop = crop.resize((round(crop.width*ratio), round(crop.height*ratio)), Image.Resampling.NEAREST)
            left = column*panel_width+(panel_width-crop.width)//2
            top = index*panel_height+40
            montage.paste(crop, (left, top))
            draw.text((column*panel_width+8, index*panel_height+8),
                      str(row['angle'])+' deg / '+route, fill='black', font=font)
            if annotated:
                colors = ('#ffdf20', '#00eaff', '#ff40e0')
                for color, (label, region) in zip(colors, row['regions'].items()):
                    mask = region['mask']
                    y, x = np.nonzero(mask)
                    hull = np.column_stack((x+.5, y+.5))
                    points = hull[ConvexHull(hull).vertices]
                    points = [(left+(point[0]-box[0])*ratio, top+(point[1]-box[1])*ratio) for point in points]
                    draw.line(points+points[:1], fill=color, width=2)
                    center = np.mean(points, axis=0)
                    draw.text(tuple(center), label, fill=color, font=font, stroke_width=1, stroke_fill='black')
    montage.save(output)


def analyze(bundle, output):
    bundle = bundle.resolve()
    manifest, report = verify_files(bundle)
    output.mkdir(parents=True, exist_ok=False)
    helper = bundle / 'sources/tools/camera_projection.py'
    spec = importlib.util.spec_from_file_location('frozen_frame_camera_projection', helper)
    projection = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(projection)
    captures = {row['label']: row for row in report['captures']}
    pose = json.loads((bundle / 'candidate.json').read_bytes())['pose']
    result = {'schema': 1, 'production_qualified': False, 'appearance_accepted': False,
        'source_bundle_manifest_sha256': hashlib.sha256((bundle/'manifest.json').read_bytes()).hexdigest(),
        'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'camera_helper_sha256': hashlib.sha256(helper.read_bytes()).hexdigest(),
        'scope': 'Three fixed-camera stone face interiors; native world frame versus projection full/missing, no registration or color fitting',
        'roi': {'face_polygon_erosion_pixels': EROSION_PIXELS, 'common_silhouette_erosion_pixels': EROSION_PIXELS,
            'source': 'Predeclared candidate face planes intersected with all three independently differenced visible masks',
            'occlusion': 'Frame-board and solid-support pixels excluded by common observed body silhouette',
            'minimum_large_roi_pixels': 64},
        'lighting': {'source': 'Captured frame block world vertex and opaque fragment shader',
            'formula': 'texel.rgb * TILE_LIGHT_COLOR.xyz * ((1 + Ny*TILE_LIGHT_COLOR.w)*0.275 - Nx*Nx*0.1 + Nz*Nz*0.1 + 0.45)',
            'directional_coefficients_if_tile_w_equals_one': {'top': 1., 'bottom': .45, 'x_side': .625, 'z_side': .825},
            'native': 'Actual engine item-frame rendering; coefficients are not independently read from native shader',
            'environment': 'Setup source asserts clear weather, frozen time 6000; report environment was saved prior state, not a post-setup independent readback',
            'limits': ['Per-face TILE_LIGHT_COLOR values were not logged', 'This fragment has no explicit fog multiplication',
                'Encoded Rec.709 weighted RGB is descriptive, not calibrated radiometry',
                'Different visible texture samples confound comparisons of mean brightness between faces',
                'One clear-noon condition does not accept day/night, biome, occlusion or changed world-light behavior']},
        'cases': [], 'quartz_static_glint_color_accepted': False}
    stone_rows, quartz_rows = [], []
    for case in report['cases']:
        name = case['source']['item'][0]
        if name not in ('minecraft:stone', 'minecraft:quartz_block'):
            continue
        images = {route: Image.open(bundle / captures[case['id']+'_'+route+'_shown']['capture']['path']).convert('RGB')
                  for route in ('native', 'full', 'missing')}
        masks = [np.asarray(Image.open(bundle / ('analysis-v1/'+case['id']+'-'+route+'-mask.png'))).astype(bool)
                 for route in ('native', 'full', 'missing')]
        common = np.logical_and.reduce(masks)
        row = {'angle': case['source']['view_angle_degrees'], 'images': images, 'mask': common}
        if name == 'minecraft:quartz_block':
            quartz_rows.append(row)
            continue
        camera = captures[case['id']+'_native_shown']['camera']
        regions = face_regions(case['native_reference']['prepare']['rows'][0]['position'], pose,
            camera, images['native'].size, report['camera_calibration']['vertical_fov'], common, projection.project_points)
        row['regions'] = regions
        stone_rows.append(row)
        measured = {'id': case['id'], 'angle': row['angle'], 'faces': {}}
        arrays = {route: np.asarray(image) for route, image in images.items()}
        for face, region in regions.items():
            mask = region['mask']
            pixels = {route: image[mask] for route, image in arrays.items()}
            measured['faces'][face] = {'roi_bounds': bounds(mask), 'roi_pixels': int(mask.sum()),
                'large_roi': int(mask.sum()) >= 64, 'world_normal': region['normal'],
                'routes': {route: color_summary(values) for route, values in pixels.items()},
                'native_product': {route: color_pair(pixels['native'], pixels[route]) for route in ('full', 'missing')}}
            Image.fromarray(mask).save(output / (case['id']+'-'+face+'-roi.png'))
        result['cases'].append(measured)
    assert len(stone_rows) == len(quartz_rows) == 3
    draw_montage(stone_rows, output / 'stone-three-view.png')
    draw_montage(stone_rows, output / 'stone-three-view-rois.png', annotated=True)
    draw_montage(quartz_rows, output / 'quartz-three-view.png')
    write_json(output / 'appearance.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = analyze(args.bundle, args.output)
    print(json.dumps({'cases': len(result['cases']), 'faces': [len(row['faces']) for row in result['cases']],
                      'appearance_accepted': result['appearance_accepted']}))
