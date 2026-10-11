"""Generate native-textured closed chest cells, including double halves."""
import argparse
from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.entity_render import CHEST_PROXIES, COPPER_CHEST_STAGES, CHEST_DIRECTIONS
from generate_shulker_proxies import behavior, box_uv

PACKED_TEXTURE_MANIFEST = ROOT / 'tools/data/static_chest_texture_hashes_v1.json'


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
        # The front UV traverses reflected model X in the opposite direction.
        offset = end - high if face == 'south' else low - start
        record['uv'][0] += offset * ratio
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
    texture = 'modern_projection_static_chest_' + stage + ('_double_' + part if part != 'single' else '')
    cubes, unused_patches = packed_geometry(spec, part)
    return {'format_version': '1.13.0', 'netease:block_geometry': {
        'description': {'identifier': identifier, 'textures': [texture],
                        'textures_descriptions': [{'width': 64, 'length': 64}],
                        'use_ao': False},
        'bones': [{'name': 'closed_chest', 'pivot': [-8, 8, 8],
                   'rotation': spec['rotations'][direction],
                   'cubes': [cube for cube in cubes if cube is not None]}]}}


def packed_geometry(spec, part):
    geometry = spec['single' if part == 'single' else 'double']
    cubes = [clipped_cube(original, part) for original in geometry['cubes']]
    cubes = [cube for cube in cubes if cube is not None]
    if part == 'single':
        return cubes, []
    patches, x, y, row_height = [], 1, 1, 0
    # NEMC custom block textures are capped at 64x64. Repack each small face
    # rectangle without resampling the native 128x64 double-chest artwork.
    for cube in cubes:
        for face in sorted(cube['uv']):
            record = cube['uv'][face]
            source = tuple(int(round(value)) for value in record['uv'])
            extent = tuple(int(round(value)) for value in record['uv_size'])
            width, height = (abs(value) for value in extent)
            if x + width + 1 > 64:
                x, y, row_height = 1, y + row_height + 2, 0
            if y + height + 1 > 64:
                raise ValueError('Packed chest face rectangles exceed 64x64')
            rectangle = (min(source[0], source[0] + extent[0]),
                         min(source[1], source[1] + extent[1]),
                         max(source[0], source[0] + extent[0]),
                         max(source[1], source[1] + extent[1]))
            patches.append((rectangle, (x, y)))
            record['uv'] = [x + (width if extent[0] < 0 else 0),
                            y + (height if extent[1] < 0 else 0)]
            record['uv_size'] = list(extent)
            x, row_height = x + width + 2, max(row_height, height)
    return cubes, patches


def packed_texture(source, patches):
    from PIL import Image
    result = Image.new('RGBA', (64, 64))
    for rectangle, (x, y) in patches:
        region = source.crop(rectangle).convert('RGBA')
        width, height = region.size
        result.paste(region, (x, y))
        result.paste(region.crop((0, 0, width, 1)), (x, y - 1))
        result.paste(region.crop((0, height - 1, width, height)), (x, y + height))
        result.paste(region.crop((0, 0, 1, height)), (x - 1, y))
        result.paste(region.crop((width - 1, 0, width, height)), (x + width, y))
        for dx, dy in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
            corner = region.crop((dx, dy, dx + 1, dy + 1))
            result.paste(corner, (x - 1 if dx == 0 else x + width,
                                  y - 1 if dy == 0 else y + height))
    output = BytesIO()
    result.save(output, format='PNG', optimize=True)
    return output.getvalue()


def generate_textures(spec, native_resources, check):
    if check:
        if not PACKED_TEXTURE_MANIFEST.exists():
            raise ValueError('Missing generated chest texture manifest')
        manifest = json.loads(PACKED_TEXTURE_MANIFEST.read_text(encoding='utf8'))
        if manifest['schema'] != 1 or manifest['native_source_sha256'] != spec['double_texture_sha256']:
            raise ValueError('Packed chest texture sources have changed; regenerate with native resources')
        for name, digest in manifest['packed_texture_sha256'].items():
            if hashlib.sha256((ROOT / 'resource_pack/textures/blocks' / name).read_bytes()).hexdigest() != digest:
                raise ValueError('Stale packed chest texture: ' + name)
        return
    if native_resources is None:
        raise ValueError('Pass --native-resource-root pointing to the installed vanilla resource pack')
    from PIL import Image
    manifest = {'schema': 1, 'native_source_sha256': spec['double_texture_sha256'], 'packed_texture_sha256': {}}
    for stage, expected in sorted(spec['double_texture_sha256'].items()):
        extra = spec['extra_texture_paths'].get(stage)
        path = extra['double'] if extra else spec['texture_paths'][stage] + '_double'
        source_path = native_resources / (path + '.png')
        if hashlib.sha256(source_path.read_bytes()).hexdigest() != expected:
            raise ValueError('Native chest texture differs from the versioned source: ' + path)
        with Image.open(source_path) as source:
            if source.size != (128, 64):
                raise ValueError('Unexpected native double-chest texture dimensions')
            for part in ('main', 'sub'):
                unused_cubes, patches = packed_geometry(spec, part)
                content = packed_texture(source, patches)
                filename = 'preview_chest_' + stage + '_double_' + part + '.png'
                output = ROOT / 'resource_pack/textures/blocks' / filename
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(content)
                manifest['packed_texture_sha256'][filename] = hashlib.sha256(content).hexdigest()
    PACKED_TEXTURE_MANIFEST.write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n', encoding='utf8')


def outputs(spec):
    if spec['schema'] != 2 or set(spec['texture_paths']) != set(COPPER_CHEST_STAGES):
        raise ValueError('Unsupported or incomplete copper chest model source')
    blocks_path = ROOT / 'resource_pack/blocks.json'
    atlas_path = ROOT / 'resource_pack/textures/terrain_texture.json'
    blocks = json.loads(blocks_path.read_text(encoding='utf8'))
    atlas = json.loads(atlas_path.read_text(encoding='utf8'))
    atlas['texture_data'] = dict((name, data) for name, data in atlas['texture_data'].items()
                                 if not name.startswith('modern_projection_copper_chest_') and
                                 not name.startswith('modern_projection_static_chest_'))
    files = {}
    for stage in COPPER_CHEST_STAGES + tuple(sorted(spec['extra_texture_paths'])):
        extra = spec['extra_texture_paths'].get(stage)
        for suffix in (('',) if stage == 'ender' else ('', '_double_main', '_double_sub')):
            texture = 'modern_projection_static_chest_' + stage + suffix
            path = ('textures/blocks/preview_chest_' + stage + suffix if suffix else
                    extra['single'] if extra is not None else spec['texture_paths'][stage])
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
    parser.add_argument('--native-resource-root', type=Path)
    args = parser.parse_args()
    spec = json.loads(args.source.read_text(encoding='utf8'))
    generate_textures(spec, args.native_resource_root, args.check)
    stale = []
    for path, data in outputs(spec).items():
        text = json.dumps(data, ensure_ascii=True, indent=2) + '\n'
        if args.check:
            current = path.read_text(encoding='utf8') if path.exists() else None
            matches = (json.loads(current) == data if current is not None and path in
                       (ROOT / 'resource_pack/blocks.json', ROOT / 'resource_pack/textures/terrain_texture.json')
                       else current == text)
            if not matches:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf8')
    if stale:
        raise SystemExit('Stale copper chest render assets: ' + ', '.join(stale))
    print('%s 76 chest render-only blocks and models' % ('Checked' if args.check else 'Generated'))


if __name__ == '__main__':
    main()
