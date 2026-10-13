"""Replay enlarged native item captures and preserve true-time animation."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from analyze_item_sprite_product import (ROOT, LIMITS, analyze as analyze_base,
    body_measurement, calibration_matches, expected_mask, expanded, temporal_measurement)
from analyze_liquid_workspace import capture_failures, difference_mask, mask_row, rgb
from generate_flat_item_proxies import source_path
from item_sprite_capture_contract import camera_matches, paired_layout_matches, scene_layout, scene_pose
from item_sprite_closeup import POSITIONS, EDITOR_POSE
from projection import block_registry
from projection.cell import actor_data, foreground
from projection.debug_blueprints import build
from projection.debug_item_blueprints import IDENTITY, PAIRS
from projection.nbt_spatial import root_payload, scalar
from projection.visible_actor import entity_nbt

NATIVE_BODY_LIMITS = {'edge_tolerance_pixels': 2, 'minimum_recall': .985,
                      'minimum_precision': .985, 'minimum_extent_pixels': 48}


def native_body_measurement(product, reference):
    """Compare actual unshifted silhouettes; camera validity is checked by the caller."""
    product_count, native_count = int(product.sum()), int(reference.sum())
    tolerance = NATIVE_BODY_LIMITS['edge_tolerance_pixels']
    recall = float((reference & expanded(product, tolerance*2+1)).sum())/max(1,native_count)
    precision = float((product & expanded(reference, tolerance*2+1)).sum())/max(1,product_count)
    scale = min(extent(product)+extent(reference)) >= NATIVE_BODY_LIMITS['minimum_extent_pixels']
    return {'product':mask_row(product),'native':mask_row(reference), 'limits':NATIVE_BODY_LIMITS,
            'recall':recall,'precision':precision,'scale_passed':scale,
            'passed':bool(product_count and native_count and scale
                and recall>=NATIVE_BODY_LIMITS['minimum_recall']
                and precision>=NATIVE_BODY_LIMITS['minimum_precision'])}


def elapsed_sequence(rows):
    times = [row['capture']['frame']['frame_qpc_100ns']/10000000. for row in rows]
    intervals = [second-first for first, second in zip(times, times[1:])]
    valid = bool(intervals) and all(value >= .4 for value in intervals)
    return {'seconds': times[-1]-times[0] if times else 0., 'ordered': valid,
            'frame_intervals_seconds': intervals,
            'passed': valid and times[-1]-times[0] >= 7.}


def extent(mask):
    bounds = mask_row(mask)['bounds']
    return [bounds[2]-bounds[0], bounds[3]-bounds[1]] if bounds else [0, 0]


def save_gif(rows, bounds, path):
    sequence = elapsed_sequence(rows)
    milliseconds = [int(round(value*1000./10.))*10 for value in sequence['frame_intervals_seconds']]
    durations = milliseconds+[milliseconds[-1]]
    frames = []
    for row in rows:
        with Image.open(row['capture']['path']) as source:
            frames.append(source.convert('RGB').crop(bounds))
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=False, disposal=2)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'crop': list(bounds), 'duration_milliseconds': durations,
            'playback': 'Native QPC intervals rounded to GIF 10ms; final frame held for final interval',
            'pixels': 'Fixed crop only; no resizing, synthesis, enhancement or runtime overlay'}


def glint_metrics(images, mask, times):
    selected = np.stack([image[mask] for image in images])
    if not selected.shape[1]:
        return {'body_pixels': 0, 'status': 'NO_OBSERVED_BODY'}
    rgb_range = np.ptp(selected, axis=0).max(axis=1)
    luma = np.tensordot(selected, np.array((.2126, .7152, .0722)), axes=(2, 0))
    luma_range = np.ptp(luma, axis=0)
    yy, xx = np.nonzero(mask)
    width = max(1, int(xx.max()-xx.min()+1))
    highlights = luma-luma.min(axis=0)
    centers = []
    for row in highlights:
        eligible = row > 8.
        centers.append((float(xx[eligible].mean()), float(yy[eligible].mean())) if eligible.any() else None)
    speeds = [float(np.linalg.norm(np.subtract(second, first))/(width*(b-a)))
              for first, second, a, b in zip(centers, centers[1:], times, times[1:])
              if first is not None and second is not None and b>a]
    return {'body_pixels': int(mask.sum()), 'status': 'MEASURED',
            'rgb_range_p50_p90_max': [float(value) for value in np.percentile(rgb_range, (50,90,100))],
            'luma_range_p50_p90_max': [float(value) for value in np.percentile(luma_range, (50,90,100))],
            'motion_fraction_rgb_gt2': float(np.mean(rgb_range > 2)),
            'motion_fraction_rgb_gt8': float(np.mean(rgb_range > 8)),
            'mean_body_luma_p50_p90': [float(value) for value in np.percentile(luma.mean(axis=1), (50,90))],
            'highlight_centroid_body_widths_per_second': speeds,
            'speed_limitations': 'Sparse frame centroid displacement; not continuous phase velocity'}


def native_comparison(source, rows, texture, spec, size, output):
    closeup = source['closeup']
    reference = closeup['native_reference']
    native_rows = {row['label']: row for row in reference.get('captures', ())}
    failures = capture_failures({key: row['capture'] for key,row in native_rows.items()}, source['session'])
    if not reference.get('completed') or not reference.get('restored') or reference.get('cleanup_errors'):
        failures.append('Actual native frame reference did not complete and restore')
    for label,row in native_rows.items():
        if not all(camera_matches(row.get(key), closeup['world_camera']) for key in
                   ('camera_before','camera_after','camera_expected')):
            failures.append({'native_camera_drift': label})
    result = {'capture_failures': failures, 'routes': {}, 'production_qualified': False,
              'native_parity_accepted': False,
              'lighting_limitations': 'Clear noon is fixed; native lighting and custom material lighting are different',
              'source': reference.get('placement')}
    if failures:
        return result
    actual_masks = {}
    for route in ('editor','world','world_missing','native'):
        captures = native_rows if route == 'native' else rows
        sequence = [captures[route+'_'+str(index)] for index in range(20)]
        hidden_label = route+'_items_hidden' if route in ('editor','native') else 'world_items_hidden'
        hidden_row = captures[hidden_label]
        images = [rgb(row['capture']['path']) for row in sequence]
        hidden = rgb(hidden_row['capture']['path'])
        first = rows['editor_0'] if route == 'editor' else rows['world_0']
        calibration = None if route == 'editor' else source['camera_calibration']['data']
        times = [row['capture']['frame']['frame_qpc_100ns']/10000000. for row in sequence]
        measurements, crops = {}, []
        for mode,position in POSITIONS.items():
            expected = expected_mask(position,first,texture,spec['frame_pose'],size,calibration)
            bounds = mask_row(expected)['bounds']
            crop = (max(0,bounds[0]-32),max(0,bounds[1]-32),min(size[0],bounds[2]+32),min(size[1],bounds[3]+32))
            region = np.zeros_like(expected)
            region[crop[1]:crop[3],crop[0]:crop[2]] = True
            observed = difference_mask(images[0],hidden,region,LIMITS['rgb_delta'])
            observation = mask_row(observed)
            actual_masks[(route,mode)] = observed
            moving_mask = observed if mode != 'empty' else expected
            measurements[mode] = {'body': observation, 'extent_pixels': extent(observed),
                'scale_passed': min(extent(observed))>=48 if mode != 'empty' else True,
                'negative_control_passed': bool(observed.sum()<=3) if mode=='empty' else None,
                'temporal': temporal_measurement(images,moving_mask,mode=='enchanted'),
                'glint': glint_metrics(images,moving_mask,times)}
            crops.append(crop)
        gif_crop = (min(row[0] for row in crops), min(row[1] for row in crops),
                    max(row[2] for row in crops), max(row[3] for row in crops))
        result['routes'][route] = {'duration': elapsed_sequence(sequence), 'items': measurements,
                                  'gif': save_gif(sequence,gif_crop,output/(route+'-comparison.gif'))}
    native = result['routes']['native']
    result['reference_valid'] = bool(native['duration']['passed'] and all(
        row['scale_passed'] and row['temporal']['passed'] for row in native['items'].values()))
    result['comparison_status'] = 'SCORED_AGAINST_VISIBLE_NATIVE_ITEMS' if result['reference_valid'] else 'NATIVE_REFERENCE_UNAVAILABLE'
    result['paired_native_body'] = {
        route:{mode:native_body_measurement(actual_masks[(route,mode)],actual_masks[('native',mode)])
               for mode in ('plain','enchanted')}
        for route in ('world','world_missing')}
    return result


def analyze(path, output):
    source = json.loads(path.read_bytes())
    base = analyze_base(path)
    closeup = source.get('closeup', {})
    rows = {row['label']: row for row in closeup.get('captures', ())}
    failures = list(base['capture_failures'])
    failures.extend(capture_failures({key: row['capture'] for key, row in rows.items()}, source['session']))
    fixture = closeup.get('fixture', {})
    if (closeup.get('schema') != 1 or closeup.get('completed') is not True or closeup.get('cleanup_errors')
            or fixture.get('source_fixture') != IDENTITY or fixture.get('source_pair') != {
                key: list(value) if isinstance(value, tuple) else value for key, value in PAIRS[0].items()}
            or fixture.get('positions') != {key: list(value) for key, value in POSITIONS.items()}):
        failures.append('Closeup source association or completion invalid')
    sizes = {(row['capture']['width'], row['capture']['height']) for row in rows.values()}
    if len(sizes) != 1:
        failures.append('Closeup dimensions changed')
    for label, row in rows.items():
        if label.startswith('editor_'):
            if scene_layout(row['state']) != scene_layout(row['state_after']):
                failures.append({'closeup_layout_drift': label})
        elif not all(camera_matches(row.get(key), closeup.get('world_camera'))
                     for key in ('camera_before', 'camera_after', 'camera_expected')):
            failures.append({'closeup_camera_drift': label})
    result = {'schema': 1, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'capture_failures': failures, 'evidence_valid': not failures and base['evidence_valid'],
              'limits': LIMITS, 'routes': {}, 'production_qualified': False,
              'native_glint_accepted': False,
              'scope': 'Enlarged analytic highlight observation, independent of failed declared silhouette geometry',
              'world_limitations': ['Fixed world crosshair may occlude the center sword; no removal or synthesis']}
    if not result['evidence_valid']:
        return result
    size = next(iter(sizes))
    spec = json.loads(source_path().read_bytes())
    item = next(row for row in spec['items'] if row['identifier'] == 'minecraft:diamond_sword' and row['aux'] == 0)
    document = build(IDENTITY)
    with Image.open(ROOT/item['generated_texture']) as texture:
        for route in ('editor', 'world'):
            labels = [route+'_'+str(index) for index in range(20)]
            required = labels+[route+'_items_hidden', route+'_restored',
                               route+'_cutaway' if route == 'editor' else route+'_occupied']
            if not all(label in rows for label in required):
                failures.append({'closeup_required_captures': route})
                continue
            sequence = [rows[label] for label in labels]
            first, hidden = sequence[0], rows[route+'_items_hidden']
            if route == 'editor':
                if any(not paired_layout_matches(first['state'], rows[label]['state'])
                       for label in labels+[route+'_items_hidden']):
                    failures.append('Closeup editor paired layout differs')
                # Cutaway legitimately releases models; restoration allocates
                # new IDs. Those captures retain the same declared camera.
                if any(scene_pose(rows[label]['state']) != scene_pose(first['state'])
                       for label in (route+'_restored', route+'_cutaway')):
                    failures.append('Closeup editor transition camera differs')
                if first['state']['camera_pose'] != list(EDITOR_POSE):
                    failures.append('Closeup editor declared pose differs')
                if any(any(bank['visible']) for bank in hidden['state']['banks']):
                    failures.append('Closeup editor contents were not hidden')
                calibration = None
            else:
                if not calibration_matches(source.get('camera_calibration'), closeup['world_camera'], size, source['session']):
                    failures.append('Closeup independent camera calibration mismatch')
                calibration = source['camera_calibration']['data']
                if any(group['visible'] for group in hidden['state']['groups_data']):
                    failures.append('Closeup world contents were not hidden')
            images = [rgb(row['capture']['path']) for row in sequence]
            hidden_image = rgb(hidden['capture']['path'])
            route_result = {'duration': elapsed_sequence(sequence), 'items': {}}
            crops = []
            for mode, position in POSITIONS.items():
                cell = document.get(PAIRS[0][mode])
                facing = block_registry.states(foreground(cell))['facing_direction']
                rotation = scalar(root_payload(entity_nbt(actor_data(cell))), 'ItemRotation')
                expected = expected_mask(position, first, texture, spec['frame_pose'], size, calibration, facing, rotation)
                observed = difference_mask(images[0], hidden_image, expanded(expected), LIMITS['rgb_delta'])
                body = body_measurement(images[0], hidden_image, expected)
                body['actual_extent_pixels'] = extent(observed)
                body['minimum_extent_passed'] = min(body['actual_extent_pixels']) >= 48 if mode != 'empty' else True
                if mode == 'empty':
                    body = {'unexpected_pixels': int(observed.sum()), 'passed': bool(observed.sum() <= 3),
                            'minimum_extent_passed': True}
                temporal_mask = observed if mode != 'empty' else expected
                temporal = temporal_measurement(images, temporal_mask, mode == 'enchanted')
                restored = body_measurement(rgb(rows[route+'_restored']['capture']['path']), hidden_image, expected)
                item_result = {'body': body, 'temporal_observed_silhouette': temporal,
                               'temporal_declared_silhouette': temporal_measurement(images, expected, mode == 'enchanted'),
                               'restored_body': restored}
                if mode != 'empty' and (route == 'editor' or mode == 'enchanted'):
                    label = route+'_cutaway' if route == 'editor' else route+'_occupied'
                    removed = difference_mask(rgb(rows[label]['capture']['path']), hidden_image,
                                              expanded(expected), LIMITS['rgb_delta'])
                    item_result['removal'] = {'remaining_pixels': int(removed.sum()),
                        'passed': int(removed.sum()) <= 3,
                        'limitation': 'World real occupancy changes block background; pixels are descriptive' if route == 'world' else None}
                bounds = mask_row(expected)['bounds']
                if bounds:
                    crops.append(bounds)
                route_result['items'][mode] = item_result
            crop = (max(0,min(row[0] for row in crops)-40), max(0,min(row[1] for row in crops)-40),
                    min(size[0],max(row[2] for row in crops)+40), min(size[1],max(row[3] for row in crops)+40))
            route_result['gif'] = save_gif(sequence, crop, output/(route+'.gif'))
            route_result['animation_observed'] = (route_result['duration']['passed'] and all(
                row['temporal_observed_silhouette']['passed'] and row['body']['minimum_extent_passed']
                for row in route_result['items'].values()))
            route_result['declared_body_passed'] = all(row['body']['passed'] for row in route_result['items'].values())
            result['routes'][route] = route_result
        if 'native_reference' in closeup:
            result['native_comparison'] = native_comparison(source, rows, texture, spec, size, output)
            failures.extend(result['native_comparison']['capture_failures'])
    result['evidence_valid'] = not failures and base['evidence_valid']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    result = analyze(args.source, args.output)
    (args.output/'analysis.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n', encoding='ascii')
    print(json.dumps({'evidence_valid': result['evidence_valid'], 'routes': {
        route: {key: value[key] for key in ('animation_observed', 'declared_body_passed', 'duration')}
        for route, value in result['routes'].items()}}))
    return 0 if result['evidence_valid'] and result.get('native_comparison',{}).get('reference_valid',True) else 1


if __name__ == '__main__':
    raise SystemExit(main())
