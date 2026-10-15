"""Isolate declared side-only pixels and compare their actual native appearance."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from analyze_item_sprite_product import ROOT, expected_mask, expanded, item_polygons, LIMITS
from analyze_item_sprite_sides import extruded_mask
from analyze_visible_items_r16 import body_region, target
from analyze_liquid_workspace import capture_failures, difference_mask, mask_row, rgb
from item_sprite_capture_contract import camera_matches, paired_layout_matches, snapshot_digest
from camera_projection import project_points

SIDE_LIMITS = {'minimum_native_side_pixels': 32, 'edge_tolerance_pixels': 1,
               'minimum_recall': .985, 'minimum_precision': .985}


def eroded(mask, radius):
    return ~expanded(~mask, radius * 2 + 1)


def side_comparison(product, reference):
    native_count, product_count = int(reference.sum()), int(product.sum())
    recall = float((expanded(product, 3) & reference).sum()) / max(1, native_count)
    precision = float((expanded(reference, 3) & product).sum()) / max(1, product_count)
    return {'native_pixels': native_count, 'product_pixels': product_count,
            'recall': recall, 'precision': precision,
            'passed': native_count >= SIDE_LIMITS['minimum_native_side_pixels']
            and product_count >= SIDE_LIMITS['minimum_native_side_pixels']
            and recall >= SIDE_LIMITS['minimum_recall']
            and precision >= SIDE_LIMITS['minimum_precision']}


def appearance(product, native, front, side):
    if not front.any() or not side.any():
        return {'measurable': False}
    weights = np.array((.2126, .7152, .0722))
    product_luma, native_luma = product @ weights, native @ weights
    valid_front = front & (native_luma > 8) & (product_luma > 8)
    valid_side = side & (native_luma > 8) & (product_luma > 8)
    if not valid_front.any() or not valid_side.any():
        return {'measurable': False}
    front_gain = float(np.median(product_luma[valid_front] / native_luma[valid_front]))
    side_gains = product_luma[valid_side] / native_luma[valid_side]
    product_chroma = product[valid_side] / np.maximum(1., product[valid_side].sum(axis=1, keepdims=True))
    native_chroma = native[valid_side] / np.maximum(1., native[valid_side].sum(axis=1, keepdims=True))
    chroma_error = np.max(abs(product_chroma - native_chroma), axis=1)
    rgb_error = np.max(abs(product[valid_side] - native[valid_side] * front_gain), axis=1)
    return {'measurable': True, 'front_samples': int(valid_front.sum()), 'side_samples': int(valid_side.sum()),
            'front_luma_product_over_native': front_gain,
            'side_luma_product_over_native_p10_p50_p90': np.percentile(side_gains, (10, 50, 90)).tolist(),
            'relative_side_over_front_gain_p10_p50_p90': np.percentile(side_gains / front_gain, (10, 50, 90)).tolist(),
            'side_chromaticity_error_p50_p95_max': np.percentile(chroma_error, (50, 95, 100)).tolist(),
            'side_rgb_error_after_front_gain_p50_p95_max': np.percentile(rgb_error, (50, 95, 100)).tolist(),
            'scope': 'Appearance diagnostics; no automatic UV, light, or frame-occlusion qualification'}


def bound_asset(report, relative, assets):
    path = assets / relative
    if hashlib.sha256(path.read_bytes()).hexdigest() != report['launch_sources'].get(relative):
        raise ValueError('Analysis asset does not match the captured source: ' + relative)
    return path


def side_surfaces(position, texture, pose, facing, rotation, row, size, calibration):
    """Rasterize opaque source texel faces with depth, independent of mesh output."""
    rgba = np.asarray(texture.convert('RGBA'))
    occupied = {tuple(map(int, point)) for point in np.argwhere(rgba[:, :, 3] >= 128)}
    front = list(item_polygons(position, texture, pose, rotation, facing))
    back = list(item_polygons(position, texture,
        dict(pose, front_z_pixels=pose['front_z_pixels'] + pose['thickness_pixels']), rotation, facing))
    owners = np.full((size[1], size[0]), -1, dtype=np.int32)
    depth = np.full(owners.shape, np.inf)
    surfaces = []
    camera = row['camera_expected']

    def draw(points, metadata):
        identity = len(surfaces)
        surfaces.append(metadata)
        world = [tuple(point[axis] + row['state']['origin'][axis] for axis in range(3)) for point in points]
        projected = project_points(world, camera['position'], camera['target'], size, calibration['vertical_fov'])
        if min(point['depth'] for point in projected) <= .05:
            raise ValueError('Texel face crosses the camera near plane')
        for indices in ((0, 1, 2), (0, 2, 3)):
            triangle = np.array([(projected[index]['screenX'], projected[index]['screenY']) for index in indices])
            left, top = np.maximum(0, np.floor(triangle.min(axis=0)).astype(int))
            right, bottom = np.minimum(size, np.ceil(triangle.max(axis=0)).astype(int))
            if left >= right or top >= bottom:
                continue
            transform = np.vstack((triangle.T, np.ones(3)))
            if abs(np.linalg.det(transform)) < 1e-9:
                continue
            yy, xx = np.indices((bottom - top, right - left))
            barycentric = np.linalg.solve(transform,
                np.stack((xx + left + .5, yy + top + .5, np.ones_like(xx))).reshape(3, -1))
            inside = np.all(barycentric >= -1e-7, axis=0).reshape(xx.shape)
            inverse_depth = np.array([1. / projected[index]['depth'] for index in indices]) @ barycentric
            candidate = (1. / inverse_depth).reshape(xx.shape)
            nearest = inside & (candidate < depth[top:bottom, left:right] - 1e-9)
            depth[top:bottom, left:right][nearest] = candidate[nearest]
            owners[top:bottom, left:right][nearest] = identity

    for (y, x), first, rear in zip(sorted(occupied), front, back):
        color = rgba[y, x, :3].tolist()
        draw(first, {'kind': 'front', 'texel': [x, y], 'color': color})
        draw(rear, {'kind': 'back', 'texel': [x, y], 'color': color})
        for name, neighbor, a, b in (('left', (y, x - 1), 3, 0), ('right', (y, x + 1), 1, 2),
                                      ('top', (y - 1, x), 0, 1), ('bottom', (y + 1, x), 2, 3)):
            if neighbor in occupied:
                continue
            points = np.array((first[a], first[b], rear[b], rear[a]))
            normal = np.cross(points[1] - points[0], points[2] - points[0])
            normal /= np.linalg.norm(normal)
            draw(points, {'kind': 'side', 'edge': name, 'texel': [x, y], 'color': color,
                          'normal': normal.tolist()})
    return owners, surfaces


def surface_appearance(product, native, visible, owners, surfaces):
    weights = np.array((.2126, .7152, .0722))
    result = []
    for identity, surface in enumerate(surfaces):
        if surface['kind'] != 'side':
            continue
        selected = eroded(owners == identity, 1) & visible
        count = int(selected.sum())
        if count < 4:
            continue
        source = np.array(surface['color'], dtype=float)
        source_luma = source @ weights
        if source_luma <= 8:
            continue
        observed_product, observed_native = product[selected], native[selected]
        product_chroma = observed_product / np.maximum(1., observed_product.sum(axis=1, keepdims=True))
        native_chroma = observed_native / np.maximum(1., observed_native.sum(axis=1, keepdims=True))
        chroma = source / source.sum()
        result.append(dict(surface, pixels=count,
            product_source_luma_gain=float(np.median(observed_product @ weights / source_luma)),
            native_source_luma_gain=float(np.median(observed_native @ weights / source_luma)),
            product_source_chroma_error_p95=float(np.percentile(np.max(abs(product_chroma - chroma), axis=1), 95)),
            native_source_chroma_error_p95=float(np.percentile(np.max(abs(native_chroma - chroma), axis=1), 95)),
            product_native_chroma_error_p95=float(np.percentile(np.max(abs(product_chroma - native_chroma), axis=1), 95))))
    return result


def analyze(source, output, assets=ROOT):
    report = json.loads(source.read_bytes())
    if (not report['completed'] or report['cleanup_errors'] or not report['source_unchanged']
            or report['launch_sources'] != report['sources_after']
            or snapshot_digest(report['launch_sources']) != report['launch_sources_sha256']):
        raise ValueError('Thickness evidence must finish restoration with stable source snapshots')
    failures = capture_failures({row['label']: row['capture'] for row in report['captures']}, report['session'])
    if failures:
        raise ValueError('Invalid thickness capture receipts: ' + str(failures))
    output.mkdir(parents=True, exist_ok=False)
    captures = {row['label']: row for row in report['captures']}
    catalog = json.loads(bound_asset(report, 'tools/data/item_icon_catalog_nemc_3.10.0.420447.json', assets).read_bytes())
    pose = catalog['pose']
    results, panels = [], []
    for case in report['cases']:
        if not case.get('measurement_completed') or not case['native_reference']['restored']:
            raise ValueError('Incomplete thickness case or native restoration')
        native_row = case['native_reference']['prepare']['rows'][0]
        mode = native_row['mode']
        position = case['source']['targets'][mode]
        native_position = native_row['position']
        origin = tuple(native_position[axis] - position[axis] for axis in range(3))
        name, aux = case['source']['item']
        resource = next(row['resource'] for row in catalog['items'] if (row['name'], row['aux']) == (name, aux))
        texture = Image.open(bound_asset(report, 'resource_pack/textures/models/modern_projection/item_icons/' + resource + '.png', assets))
        facing, rotation = case['source']['facing'], case['source']['rotation_degrees']
        routes = {}
        for route in ('editor', 'full', 'missing', 'native'):
            prefix = case['id'] + '_' + route
            raw = captures[prefix + '_shown']
            for phase in ('hidden_before', 'hidden_after'):
                hidden_row = captures[prefix + '_' + phase]
                matches = (paired_layout_matches(raw['state'], hidden_row['state']) if route == 'editor'
                           else camera_matches(raw['camera'], hidden_row['camera']))
                if not matches:
                    raise ValueError('Thickness camera or editor layout changed')
            row = copy.deepcopy(raw)
            row['label'] = ('editor_' if route == 'editor' else route + '_') + case['id']
            row['state']['origin'] = origin
            if route != 'editor':
                row['camera_expected'] = dict(row['camera'], target=target(row['camera']))
            shown = rgb(raw['capture']['path'])
            before, after = (rgb(captures[prefix + '_' + phase]['capture']['path'])
                             for phase in ('hidden_before', 'hidden_after'))
            stable = np.max(abs(before - after), axis=2) <= 3
            size = (shown.shape[1], shown.shape[0])
            front = expected_mask(position, row, texture, pose, size, report['camera_calibration'], facing, rotation)
            extruded = extruded_mask(position, row, texture, pose, size, report['camera_calibration'], facing, rotation)
            side = eroded(extruded, 1) & ~expanded(front, 3)
            observed = difference_mask(shown, (before + after) / 2., body_region(extruded), LIMITS['rgb_delta']) & stable
            routes[route] = {'shown': shown, 'observed': observed, 'side': side,
                             'front': eroded(front, 2), 'raw': raw,
                             'geometry': {'observed': mask_row(observed), 'front_plane': mask_row(front),
                                          'extruded_union': mask_row(extruded), 'side_only_roi': mask_row(side)}}
        native = routes['native']
        result = {'case': case['id'], 'mode': mode, 'rotation': rotation,
                  'angle_degrees': report['view_configuration']['angle_degrees'], 'routes': {},
                  'side_geometry_comparison': {}, 'appearance': {}, 'side_surface_appearance': {}}
        native_camera = copy.deepcopy(native['raw'])
        native_camera['state']['origin'] = origin
        native_camera['camera_expected'] = dict(native_camera['camera'], target=target(native_camera['camera']))
        owners, surfaces = side_surfaces(position, texture, pose, facing, rotation,
                                         native_camera, (native['shown'].shape[1], native['shown'].shape[0]),
                                         report['camera_calibration'])
        for route, data in routes.items():
            result['routes'][route] = data['geometry']
            bounds = mask_row(expanded(data['observed'] | data['side'], 17))['bounds']
            if bounds:
                box = (bounds[0], bounds[1], bounds[2] + 1, bounds[3] + 1)
                for overlay in (False, True):
                    preview = data['shown'].astype(np.uint8).copy()
                    if overlay:
                        preview[data['side']] = (255, 0, 255)
                    tile = Image.fromarray(preview).crop(box)
                    tile.thumbnail((230, 230), Image.Resampling.NEAREST)
                    panel = Image.new('RGB', (240, 260), 'white')
                    panel.paste(tile, ((240 - tile.width) // 2, 25))
                    ImageDraw.Draw(panel).text((3, 3), case['id'].split('.')[-1] + ' ' + route + (' ROI' if overlay else ''), fill='black')
                    panels.append(panel)
            if route not in ('full', 'missing'):
                continue
            if not camera_matches(data['raw']['camera'], native['raw']['camera']):
                raise ValueError('Thickness product and actual native cameras differ')
            declared_side = native['side']
            reference = native['observed'] & declared_side
            product = data['observed'] & declared_side
            comparison = side_comparison(product, reference)
            comparison['negative_controls'] = {
                'blank_rejected': not side_comparison(np.zeros_like(product), reference)['passed'],
                'shifted_rejected': not side_comparison(np.roll(product, 8, axis=1), reference)['passed']}
            result['side_geometry_comparison'][route] = comparison
            front = native['front'] & data['front'] & native['observed'] & data['observed']
            side = reference & product
            result['appearance'][route] = appearance(data['shown'], native['shown'], front, side)
            result['side_surface_appearance'][route] = surface_appearance(data['shown'], native['shown'],
                native['observed'] & data['observed'], owners, surfaces)
        results.append(result)
        texture.close()
    sheet = Image.new('RGB', (240 * 4, 260 * ((len(panels) + 3) // 4)), 'white')
    for index, panel in enumerate(panels):
        sheet.paste(panel, ((index % 4) * 240, (index // 4) * 260))
    sheet.save(output / 'review.png')
    result = {'schema': 1, 'production_qualified': False, 'thickness_appearance_accepted': False,
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'side_limits': SIDE_LIMITS, 'cases': results,
              'limitations': ['Side-only ROI excludes a one-pixel front and silhouette boundary',
                              'Appearance metrics preserve front-relative native lighting differences',
                              'UV continuity and frame-bottom/rim occlusion require the retained actual image review',
                              'Animated glint phases are not synchronized by static snapshots']}
    (output / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'cases': len(results), 'side_geometry_passed': all(
        row['passed'] and all(row['negative_controls'].values())
        for case in results for row in case['side_geometry_comparison'].values()),
        'thickness_appearance_accepted': False, 'production_qualified': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--assets', type=Path, default=ROOT,
                        help='Frozen captured source root; catalog and texture hashes must match.')
    args = parser.parse_args()
    analyze(args.source, args.output, args.assets)
