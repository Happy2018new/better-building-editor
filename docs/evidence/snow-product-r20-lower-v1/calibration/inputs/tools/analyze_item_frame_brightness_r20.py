"""Compare fixed editor frame-body patches before and after item overlays."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from analyze_item_sprite_product import expected_mask
from analyze_liquid_workspace import capture_failures, rgb
from item_sprite_capture_contract import paired_layout_matches, snapshot_digest
from projection.item_icon_data import ITEMS

ROOT = Path(__file__).resolve().parents[1]
LIMITS = {'maximum_rgb_change': 3, 'minimum_patch_pixels': 16}


def compare(shown, before, after, mask):
    delta = np.maximum(np.max(abs(shown - before), axis=2), np.max(abs(shown - after), axis=2))
    pixels = int(mask.sum())
    maximum = int(delta[mask].max()) if pixels else None
    return {'patch_pixels': pixels, 'maximum_rgb_change': maximum,
            'changed_patch_pixels': int((delta[mask] > LIMITS['maximum_rgb_change']).sum()),
            'passed': pixels >= LIMITS['minimum_patch_pixels'] and maximum <= LIMITS['maximum_rgb_change']}


def analyze(paths, output):
    output.mkdir(parents=True, exist_ok=False)
    # Use the upper two projected body corners, clear of the editor's bottom tools.
    patch = Image.new('RGBA', (100, 100))
    for x in (18, 80):
        for y in (18, 80):
            ImageDraw.Draw(patch).rectangle((x, y, x + 1, y + 1), fill=(255, 255, 255, 255))
    pose = json.loads((ROOT / 'tools/data/item_icon_catalog_nemc_3.10.0.420447.json').read_bytes())['pose']
    body_pose = dict(pose, size_pixels=16., front_z_pixels=15.)
    rows, crops = [], []
    for path in paths:
        report = json.loads(path.read_bytes())
        if not report['completed'] or not report['source_unchanged'] or report['cleanup_errors']:
            raise ValueError('Editor brightness report did not complete restoration')
        if (report['launch_sources'] != report['sources_after'] or
                snapshot_digest(report['launch_sources']) != report['launch_sources_sha256']):
            raise ValueError('Editor brightness source snapshot changed')
        captures = {row['label']: row for row in report['captures']}
        for case in report['cases']:
            if not case.get('measurement_completed'):
                raise ValueError('Incomplete editor pose')
            prefix = case['id'] + '_editor'
            captures_for_case = {phase: captures[prefix + '_' + phase]
                                 for phase in ('shown', 'hidden_before', 'hidden_after')}
            failures = capture_failures({phase: row['capture'] for phase, row in captures_for_case.items()},
                                        report['session'])
            if failures:
                raise ValueError('Invalid editor brightness captures: ' + str(failures))
            if any(not paired_layout_matches(captures_for_case['shown']['state'],
                                             captures_for_case[phase]['state'])
                   for phase in ('hidden_before', 'hidden_after')):
                raise ValueError('Editor brightness layout changed')
            shown, before, after = (rgb(captures_for_case[phase]['capture']['path'])
                                    for phase in ('shown', 'hidden_before', 'hidden_after'))
            size = (shown.shape[1], shown.shape[0])
            row = dict(captures_for_case['shown'], label='editor_' + case['id'])
            source = case['source']
            facing = source.get('facing', 2)
            resource = ITEMS[tuple(source['item'])]['ui_model'].removeprefix('modern_projection_item_icon_')
            texture = Image.open(ROOT / 'resource_pack/textures/models/modern_projection/item_icons' / (resource + '.png'))
            for mode, position in source['targets'].items():
                mask = expected_mask(position, row, patch, body_pose, size, report['camera_calibration'], facing, 0.)
                projected_y = np.where(mask)[0]
                if not len(projected_y):
                    raise ValueError('Declared frame-body patches are outside the editor viewport')
                mask[np.arange(size[1]) > np.median(projected_y), :] = False
                item = expected_mask(position, row, texture, pose, size, report['camera_calibration'],
                                     facing, source.get('rotation_degrees', 0.))
                if np.any(mask & item):
                    raise ValueError('Declared frame-body patch overlaps the item bitmap')
                result = compare(shown, before, after, mask)
                changed = shown.copy()
                changed[mask] = np.clip(changed[mask] + 12, 0, 255)
                result.update(case=case['id'], mode=mode, facing=facing,
                    baseline_median_rgb=np.median(before[mask], axis=0).tolist(),
                    negative_control_rejected=not compare(changed, before, after, mask)['passed'],
                    original_report=str(path.resolve()),
                    original_report_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                rows.append(result)
                ys, xs = np.where(mask)
                box = (max(0, int(xs.min()) - 10), max(0, int(ys.min()) - 10),
                       min(size[0], int(xs.max()) + 11), min(size[1], int(ys.max()) + 11))
                preview = shown.astype(np.uint8).copy()
                preview[mask] = (255, 0, 255)
                tile = Image.fromarray(preview).crop(box)
                tile.thumbnail((210, 190))
                canvas = Image.new('RGB', (220, 215), 'white')
                canvas.paste(tile, ((220 - tile.width) // 2, 23))
                ImageDraw.Draw(canvas).text((3, 3), case['id'].split('.')[-1] + ' ' + mode, fill='black')
                crops.append(canvas)
            texture.close()
    result = {'schema': 1, 'scope': 'Editor pre-existing empty frame body compared with its item overlay shown',
              'limits': LIMITS, 'rows': rows, 'production_qualified': False,
              'passed': bool(rows) and all(row['passed'] and row['negative_control_rejected'] for row in rows)}
    (output / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    sheet = Image.new('RGB', (220 * 4, 215 * ((len(crops) + 3) // 4)), 'white')
    for index, crop in enumerate(crops):
        sheet.paste(crop, ((index % 4) * 220, (index // 4) * 215))
    sheet.save(output / 'review.png')
    print(json.dumps({'passed': result['passed'], 'cases': len(rows),
        'maximum_rgb_change': max(row['maximum_rgb_change'] for row in rows)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    analyze(args.report, args.output)
