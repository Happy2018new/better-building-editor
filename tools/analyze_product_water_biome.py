"""Verify frozen biome controls without accepting camera or geometry drift."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from analyze_product_water import (TRANSPARENCY_REGIONS, analyze, bind_native_editor_gui, contribution, expected_mask,
                                   region_mask, rgb, scene_capture_state)

BIOMES = ('plains', 'swampland', 'mangrove_swamp')


def color_change(first, second, selected):
    result = contribution(first, second, selected, threshold=3)
    if selected.any():
        delta = np.abs(first[selected].astype(float) - second[selected])
        result['mean_absolute_rgb_delta'] = delta.mean(axis=0).tolist()
        result['passed'] = result['passed'] and max(result['mean_absolute_rgb_delta']) >= 3.
    return result


def biome_analysis(path, contact_path=None, native_editor_gui=False):
    source = json.loads(path.read_bytes())
    base = analyze(path, native_editor_gui=True) if native_editor_gui else analyze(path)
    result = {'schema': 1, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'source_contract_sha256': source.get('source_contract_sha256'),
              'evidence_valid': base['evidence_valid'], 'capture_failures': base['capture_failures'],
              'color_limits': {'pixel_rgb_delta': 3, 'minimum_contribution_pixels': 8,
                               'minimum_contribution_fraction': .10, 'minimum_mean_channel_delta': 3},
              'frozen': source.get('frozen'), 'rows': {}, 'passed': False,
              'scope': 'Visible preset changes with unchanged blocks, water geometry and camera'}
    if not result['evidence_valid'] or result['frozen'] is not True:
        return result
    if native_editor_gui:
        result['editor_geometry_oracle'] = bind_native_editor_gui(source)
    sheet = Image.new('RGB', (720, 720), 'white')
    draw = ImageDraw.Draw(sheet)
    for route_index, route in enumerate(source['routes']):
        label = route + '_wet_oak_fence_wet'
        baseline = source['rows'][label]
        size = (source['captures'][label]['width'], source['captures'][label]['height'])
        wet_mask = expected_mask(baseline, source, size)
        regions = {name: region_mask(baseline, source, size, points)
                   for name, points in TRANSPARENCY_REGIONS.items()}
        ys, xs = np.nonzero(wet_mask)
        if not len(xs):
            raise ValueError('Water has no independently projected visible pixels')
        crop = (int(xs.min()) - 20, int(ys.min()) - 20,
                int(xs.max()) + 21, int(ys.max()) + 50)
        row = result['rows'][route] = {'geometry_unchanged': True, 'phases': {},
                                     'pairs': {}, 'passed': False}
        images = {}
        for index, biome in enumerate(BIOMES):
            capture_label = label + '_biome_' + biome
            observed = source['extra_rows'][capture_label]
            ready, original = observed['ready'], baseline['ready']
            unchanged = (ready['source_cells'] == original['source_cells']
                         and ready['shapes'] == original['shapes'])
            if route == 'editor':
                unchanged = unchanged and scene_capture_state(ready) == scene_capture_state(original)
            else:
                unchanged = (unchanged and ready['origin'] == original['origin']
                             and ready['body_parts'] == original['body_parts'])
            row['geometry_unchanged'] = row['geometry_unchanged'] and unchanged
            phase = row['phases'][biome] = {'geometry_unchanged': unchanged,
                'requested_biome_visible': ready['biome'] == biome, 'regions': {},
                'capture_sha256': source['captures'][capture_label]['sha256']}
            images[biome] = rgb(source['captures'][capture_label]['path'])
            for name, selected in regions.items():
                phase['regions'][name] = {'pixels': int(selected.sum()),
                    'mean_rgb': images[biome][selected].mean(axis=0).tolist()}
            with Image.open(source['captures'][capture_label]['path']) as image:
                tile = image.convert('RGB').crop(crop)
                tile.thumbnail((228, 214), Image.Resampling.NEAREST)
                sheet.paste(tile, (index * 240 + (240 - tile.width) // 2,
                                   route_index * 240 + 24))
            draw.text((index * 240 + 4, route_index * 240 + 5), route + ' ' + biome, fill='black')
        for first, second in zip(BIOMES, BIOMES[1:]):
            pair = row['pairs'][first + '_to_' + second] = {}
            for name, selected in regions.items():
                pair[name] = color_change(images[first], images[second], selected)
        initial = rgb(source['captures'][label]['path'])
        restored = images['plains']
        row['plains_restore_rgb_rmse'] = float(np.sqrt(np.mean(
            (initial[wet_mask].astype(float) - restored[wet_mask]) ** 2)))
        row['passed'] = (row['geometry_unchanged'] and row['plains_restore_rgb_rmse'] <= 3.
                         and all(phase['requested_biome_visible'] for phase in row['phases'].values())
                         and all(item['passed'] for pair in row['pairs'].values() for item in pair.values()))
    if contact_path is not None:
        sheet.save(contact_path)
    result['passed'] = bool(result['rows']) and all(row['passed'] for row in result['rows'].values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--contact', type=Path)
    parser.add_argument('--native-editor-gui', action='store_true',
                        help='Use captured SDK integer GUI/cache agreement for editor biome regions')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose fresh analysis evidence')
    result = biome_analysis(args.source, args.contact, native_editor_gui=args.native_editor_gui)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'passed': result['passed'], 'routes': {
        name: row['passed'] for name, row in result['rows'].items()}}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
