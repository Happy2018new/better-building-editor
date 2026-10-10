"""Generate all colour/direction static closed-shell render-only shulker blocks."""
import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.entity_render import SHULKER_COLORS, SHULKER_PROXIES


def box_uv(uv, size):
    u, v = uv
    width, height, depth = size
    regions = {
        'east': ((0, depth), (depth, height)),
        'west': ((depth + width, depth), (depth, height)),
        'up': ((depth + width, depth), (-width, -depth)),
        'down': ((depth + 2 * width, 0), (-width, depth)),
        'south': ((2 * depth + width, depth), (width, height)),
        'north': ((depth, depth), (width, height)),
    }
    return dict((face, {'uv': [u + origin[0], v + origin[1]], 'uv_size': list(extent)})
                for face, (origin, extent) in regions.items())


def model(spec, color, facing):
    identifier = SHULKER_PROXIES['minecraft:' + color + '_shulker_box'][facing]
    geometry = spec['geometry']
    bones = []
    for source in geometry['bones']:
        if source['name'] not in spec['visible_closed_bones']:
            continue
        cubes = []
        for original in source['cubes']:
            cube = deepcopy(original)
            cube['uv'] = box_uv(original['uv'], original['size'])
            cube['origin'][0] -= 8
            cube['origin'][2] += 8
            cubes.append(cube)
        bones.append({'name': source['name'], 'pivot': [-8, 8, 8],
                      'rotation': spec['poses'][facing]['rotation'], 'cubes': cubes})
    texture = 'modern_projection_shulker_' + color
    return {'format_version': '1.13.0', 'netease:block_geometry': {
        'description': {'identifier': identifier, 'textures': [texture],
                        'textures_descriptions': [{'width': geometry['texturewidth'],
                                                   'length': geometry['textureheight']}],
                        'item_texture': color + '_shulker_box' if color != 'undyed' else 'undyed_shulker_box_top',
                        'use_ao': False}, 'bones': bones}}


def behavior(identifier):
    return {'format_version': '1.10.0', 'minecraft:block': {
        'description': {'identifier': identifier, 'register_to_creative_menu': False},
        'components': {'netease:render_layer': {'value': 'alpha'},
                       'netease:no_crop_face_block': {},
                       'minecraft:block_light_absorption': {'value': 0}}}}


def outputs(spec):
    if spec['schema'] != 1 or set(spec['texture_paths']) != set(SHULKER_COLORS):
        raise ValueError('Unsupported or incomplete shulker model source')
    files = {}
    blocks_path = ROOT / 'resource_pack/blocks.json'
    blocks = json.loads(blocks_path.read_text(encoding='utf8'))
    atlas_path = ROOT / 'resource_pack/textures/terrain_texture.json'
    atlas = json.loads(atlas_path.read_text(encoding='utf8')) if atlas_path.exists() else {
        'resource_pack_name': 'modern_projection', 'texture_name': 'atlas.terrain', 'texture_data': {}}
    for color in SHULKER_COLORS:
        texture = 'modern_projection_shulker_' + color
        atlas['texture_data'][texture] = {'textures': spec['texture_paths'][color]}
        for facing, identifier in enumerate(SHULKER_PROXIES['minecraft:' + color + '_shulker_box']):
            filename = identifier.split(':', 1)[1] + '.json'
            files[ROOT / 'behavior_pack/netease_blocks' / filename] = behavior(identifier)
            files[ROOT / 'resource_pack/models/netease_block' / filename] = model(spec, color, facing)
            blocks[identifier] = {'netease_model': identifier, 'sound': 'stone'}
    files[blocks_path] = blocks
    files[atlas_path] = atlas
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--source', type=Path, default=ROOT / 'tools/data/shulker_static_model_v1.json')
    args = parser.parse_args()
    spec = json.loads(args.source.read_text(encoding='utf8'))
    stale = []
    for path, data in outputs(spec).items():
        text = json.dumps(data, ensure_ascii=True, indent=2) + '\n'
        if args.check:
            if not path.exists() or path.read_text(encoding='utf8') != text:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf8')
    if stale:
        raise SystemExit('Stale shulker render assets: ' + ', '.join(stale))
    print('%s 102 shulker render-only blocks and models' % ('Checked' if args.check else 'Generated'))


if __name__ == '__main__':
    main()
