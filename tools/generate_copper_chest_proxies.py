"""Generate native-textured closed chest cells, including double halves."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.entity_render import CHEST_PROXIES, COPPER_CHEST_STAGES, CHEST_DIRECTIONS
from generate_shulker_proxies import behavior, box_uv


def clipped_cube(original, part):
    cube = deepcopy(original)
    cube.pop('name', None)
    faces = box_uv(original['uv'], original['size'])
    if part == 'single':
        cube['uv'] = faces
        return cube
    start = original['origin'][0]
    end = start + original['size'][0]
    low, high = (start, min(end, 0)) if part == 'main' else (max(start, 0), end)
    if low >= high:
        return None
    # Clip the original face rectangles along X rather than stretching their UVs.
    for face in ('north', 'south', 'up', 'down'):
        record = faces[face]
        extent = record['uv_size'][0]
        ratio = extent / original['size'][0]
        record['uv'][0] += (low - start) * ratio
        record['uv_size'][0] = (high - low) * ratio
    if low != start:
        del faces['east']
    if high != end:
        del faces['west']
    cube['origin'][0] = low - (16 if part == 'sub' else 0)
    cube['size'][0] = high - low
    cube['uv'] = faces
    return cube


def model(spec, stage, direction, part):
    name = {'normal': 'chest', 'trapped': 'trapped_chest', 'ender': 'ender_chest'}.get(stage,
            ('' if stage == 'default' else stage + '_') + 'copper_chest')
    identifier = CHEST_PROXIES['minecraft:' + name][(direction, part)]
    geometry = spec['single' if part == 'single' else 'double']
    texture = 'modern_projection_static_chest_' + stage + ('_double' if part != 'single' else '')
    cubes = [clipped_cube(original, part) for original in geometry['cubes']]
    return {'format_version': '1.13.0', 'netease:block_geometry': {
        'description': {'identifier': identifier, 'textures': [texture],
                        'textures_descriptions': [{'width': geometry['texturewidth'],
                                                   'length': geometry['textureheight']}],
                        'use_ao': False},
        'bones': [{'name': 'closed_chest', 'pivot': [-8, 8, 8],
                   'rotation': spec['rotations'][direction],
                   'cubes': [cube for cube in cubes if cube is not None]}]}}


def outputs(spec):
    if spec['schema'] != 1 or set(spec['texture_paths']) != set(COPPER_CHEST_STAGES):
        raise ValueError('Unsupported or incomplete copper chest model source')
    blocks_path = ROOT / 'resource_pack/blocks.json'
    atlas_path = ROOT / 'resource_pack/textures/terrain_texture.json'
    blocks = json.loads(blocks_path.read_text(encoding='utf8'))
    atlas = json.loads(atlas_path.read_text(encoding='utf8'))
    atlas['texture_data'] = dict((name, data) for name, data in atlas['texture_data'].items()
                                 if not name.startswith('modern_projection_copper_chest_'))
    files = {}
    for stage in COPPER_CHEST_STAGES + tuple(sorted(spec['extra_texture_paths'])):
        extra = spec['extra_texture_paths'].get(stage)
        for suffix in (('',) if stage == 'ender' else ('', '_double')):
            texture = 'modern_projection_static_chest_' + stage + suffix
            path = extra['single' if not suffix else 'double'] if extra is not None else spec['texture_paths'][stage] + suffix
            atlas['texture_data'][texture] = {'textures': path}
        for direction in CHEST_DIRECTIONS:
            for part in (('single',) if stage == 'ender' else ('single', 'main', 'sub')):
                data = model(spec, stage, direction, part)
                identifier = data['netease:block_geometry']['description']['identifier']
                filename = identifier.split(':', 1)[1] + '.json'
                files[ROOT / 'behavior_pack/netease_blocks' / filename] = behavior(identifier)
                files[ROOT / 'resource_pack/models/netease_block' / filename] = data
                blocks[identifier] = {'netease_model': identifier, 'sound': 'copper_chest'}
    files[blocks_path] = blocks
    files[atlas_path] = atlas
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--source', type=Path, default=ROOT / 'tools/data/copper_chest_static_model_v1.json')
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
        raise SystemExit('Stale copper chest render assets: ' + ', '.join(stale))
    print('%s 76 chest render-only blocks and models' % ('Checked' if args.check else 'Generated'))


if __name__ == '__main__':
    main()
