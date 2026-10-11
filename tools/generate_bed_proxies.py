"""Generate cell-bounded bed halves from the installed native bed model."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.static_bed import BED_COLORS, BED_PROXIES
from generate_shulker_proxies import behavior, netease_box_uv

SOURCE = ROOT / 'tools/data/bed_static_model_v1.json'


def capture_source(native_root):
    models_path = native_root / 'models/mobs.json'
    entity_path = native_root / 'entity/bed.entity.json'
    geometry = json.loads(models_path.read_text(encoding='utf8'))['geometry.bed']
    entity = json.loads(entity_path.read_text(encoding='utf8'))['minecraft:client_entity']['description']
    if entity['geometry']['default'] != 'geometry.bed':
        raise ValueError('Unexpected native bed geometry binding')
    paths = dict((color, entity['textures'][color]) for color in BED_COLORS)
    return {'schema': 1, 'source': {
        'native_version': 'NEMC 3.9.0.401155 / Minecraft 1.21.120.0',
        'geometry_path': 'models/mobs.json', 'geometry_key': 'geometry.bed',
        'geometry_file_sha256': hashlib.sha256(models_path.read_bytes()).hexdigest(),
        'entity_path': 'entity/bed.entity.json',
        'entity_sha256': hashlib.sha256(entity_path.read_bytes()).hexdigest(),
        'attribution': 'Native Minecraft geometry.bed and bed artwork, Mojang AB.',
        'conversion': 'Clip native model Y at 16 without resampling UVs; rotate -90 X then direction*90 Y around each cell center.',
        'regenerate': 'python tools/generate_bed_proxies.py --native-resource-root <installed vanilla>'},
        'geometry': geometry, 'texture_paths': paths,
        'texture_sha256': dict((color, hashlib.sha256((native_root / (path + '.png')).read_bytes()).hexdigest())
                               for color, path in paths.items())}


def half_cube(original, head):
    cube = deepcopy(original)
    start = original['origin'][1]
    end = start + original['size'][1]
    low, high = (max(start, 16), end) if head else (start, min(end, 16))
    if low >= high:
        return None
    faces = netease_box_uv(original['uv'], original['size'])
    for face in ('east', 'west', 'north', 'south'):
        record = faces[face]
        ratio = record['uv_size'][1] / original['size'][1]
        record['uv'][1] += (end - high) * ratio
        record['uv_size'][1] = (high - low) * ratio
    if low != start:
        del faces['down']
    if high != end:
        del faces['up']
    cube['origin'] = [original['origin'][0] - 16,
                      low - (16 if head else 0), original['origin'][2] + 7]
    cube['size'][1] = high - low
    cube['uv'] = faces
    return cube


def model(spec, color, direction, head):
    identifier = BED_PROXIES[(color, direction, head)]
    cubes = [half_cube(cube, head) for bone in spec['geometry']['bones'] for cube in bone['cubes']]
    return {'format_version': '1.13.0', 'netease:block_geometry': {
        'description': {'identifier': identifier,
                        'textures': ['modern_projection_static_bed_' + color],
                        'textures_descriptions': [{'width': 64, 'length': 64}], 'use_ao': False},
        'bones': [{'name': 'bed_half', 'pivot': [-8, 8, 8],
                   'rotation': [-90, direction * 90, 0],
                   'cubes': [cube for cube in cubes if cube is not None]}]}}


def outputs(spec):
    if spec['schema'] != 1 or set(spec['texture_paths']) != set(BED_COLORS):
        raise ValueError('Incomplete bed source')
    blocks_path = ROOT / 'resource_pack/blocks.json'
    atlas_path = ROOT / 'resource_pack/textures/terrain_texture.json'
    blocks = json.loads(blocks_path.read_text(encoding='utf8'))
    atlas = json.loads(atlas_path.read_text(encoding='utf8'))
    files = {}
    for color in BED_COLORS:
        atlas['texture_data']['modern_projection_static_bed_' + color] = {'textures': spec['texture_paths'][color]}
        for direction in range(4):
            for head in (False, True):
                data = model(spec, color, direction, head)
                identifier = data['netease:block_geometry']['description']['identifier']
                filename = identifier.split(':', 1)[1] + '.json'
                files[ROOT / 'behavior_pack/netease_blocks' / filename] = behavior(identifier)
                files[ROOT / 'resource_pack/models/netease_block' / filename] = data
                blocks[identifier] = {'netease_model': identifier, 'sound': 'wood'}
    files[blocks_path] = blocks
    files[atlas_path] = atlas
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-source', action='store_true')
    parser.add_argument('--native-resource-root', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.capture_source:
        if args.check or args.native_resource_root is None or SOURCE.exists():
            parser.error('Capture a new source once with an installed native resource root')
        SOURCE.write_text(json.dumps(capture_source(args.native_resource_root), indent=2) + '\n', encoding='utf8')
    spec = json.loads(SOURCE.read_text(encoding='utf8'))
    if args.native_resource_root is not None and capture_source(args.native_resource_root) != spec:
        raise ValueError('Installed bed resources differ from the versioned source')
    stale = []
    for path, data in outputs(spec).items():
        content = json.dumps(data, ensure_ascii=True, indent=2) + '\n'
        if args.check:
            if not path.exists() or path.read_text(encoding='utf8') != content:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf8')
    if stale:
        raise SystemExit('Stale bed render assets: ' + ', '.join(stale))
    print('%s 128 cell-bounded bed render blocks and models' % ('Checked' if args.check else 'Generated'))


if __name__ == '__main__':
    main()
