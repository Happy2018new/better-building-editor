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
    return 0 if result['evidence_valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
