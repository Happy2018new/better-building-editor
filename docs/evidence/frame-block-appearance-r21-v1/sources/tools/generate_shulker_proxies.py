"""Generate all colour/direction static closed-shell render-only shulker blocks."""
import argparse
import hashlib
import json
import sys
from copy import deepcopy
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.entity_render import SHULKER_COLORS, SHULKER_PROXIES

TEXTURE_MANIFEST = ROOT / 'tools/data/static_shulker_texture_hashes_v1.json'


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


def netease_box_uv(uv, size):
    faces = box_uv(uv, size)
    # MCStudio's installed free-model importer reverses the up endpoints.
    # Its down and side endpoints retain the internal box-UV convention.
    top = faces['up']
    top['uv'] = [origin + extent for origin, extent in zip(top['uv'], top['uv_size'])]
    top['uv_size'] = [-extent for extent in top['uv_size']]
    return faces


def closed_cube(original, name, lid_bottom):
    """Keep only closed-shell exterior faces, with original texel density."""
    cube = deepcopy(original)
    cube['uv'] = netease_box_uv(original['uv'], original['size'])
    if name == 'lid':
        del cube['uv']['down']
    elif name == 'base':
        height = lid_bottom - original['origin'][1]
        cropped = original['size'][1] - height
        if not 0 < height <= original['size'][1]:
            raise ValueError('The versioned closed shulker shell does not overlap as expected')
        cube['size'][1] = height
        del cube['uv']['up']
        for face in ('east', 'west', 'north', 'south'):
            cube['uv'][face]['uv'][1] += cropped
            cube['uv'][face]['uv_size'][1] = height
    return cube


def model(spec, color, facing):
    identifier = SHULKER_PROXIES['minecraft:' + color + '_shulker_box'][facing]
    geometry = spec['geometry']
    lid = next(bone for bone in geometry['bones'] if bone['name'] == 'lid')
    lid_bottom = lid['cubes'][0]['origin'][1]
    bones = []
    for source in geometry['bones']:
        if source['name'] not in spec['visible_closed_bones']:
            continue
        cubes = []
        for original in source['cubes']:
            cube = closed_cube(original, source['name'], lid_bottom)
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
                        'use_ao': True}, 'bones': bones}}


def behavior(identifier, render_layer='alpha'):
    return {'format_version': '1.10.0', 'minecraft:block': {
        'description': {'identifier': identifier, 'register_to_creative_menu': False},
        'components': {'netease:render_layer': {'value': render_layer},
                       'netease:no_crop_face_block': {},
                       'minecraft:block_light_absorption': {'value': 0}}}}


def closed_texture(source):
    """Flatten the complementary lid/base cutouts onto one closed surface."""
    from PIL import Image
    if source.size != (64, 64):
        raise ValueError('Unexpected native shulker texture dimensions')
    result = source.convert('RGBA')
    # At world Y=4..8 the lid's V=24..28 lies over the base's V=44..48.
    # Their alpha cutouts are complementary; preserve both native artworks.
    overlap = Image.alpha_composite(result.crop((0, 44, 64, 48)),
                                    result.crop((0, 24, 64, 28)))
    if overlap.getchannel('A').getextrema() != (255, 255):
        raise ValueError('The versioned lid/base overlap no longer closes the shell')
    result.paste(overlap, (0, 24))
    for rectangle in ((16, 0, 32, 16), (32, 28, 48, 44),
                      (0, 16, 64, 28), (0, 48, 64, 52)):
        if result.crop(rectangle).getchannel('A').getextrema() != (255, 255):
            raise ValueError('A generated closed-shell face has transparent texels')
    output = BytesIO()
    result.save(output, format='PNG', optimize=True)
    return output.getvalue()


def generate_textures(spec, native_resources, check):
    expected = spec['texture_sha256']
    if check or native_resources is None:
        if not TEXTURE_MANIFEST.exists():
            raise ValueError('Regenerate shulker textures with --native-resource-root')
        manifest = json.loads(TEXTURE_MANIFEST.read_text(encoding='utf8'))
        if manifest['schema'] != 1 or manifest['native_source_sha256'] != expected:
            raise ValueError('Native shulker texture sources changed; regenerate with --native-resource-root')
        names = {'preview_shulker_' + color + '_closed.png' for color in SHULKER_COLORS}
        if set(manifest['closed_texture_sha256']) != names:
            raise ValueError('Incomplete generated closed-shulker texture manifest')
        for name, digest in manifest['closed_texture_sha256'].items():
            path = ROOT / 'resource_pack/textures/blocks' / name
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('Stale closed-shulker texture: ' + name)
        return
    from PIL import Image
    manifest = {'schema': 1, 'native_source_sha256': expected, 'closed_texture_sha256': {}}
    for color in SHULKER_COLORS:
        path = native_resources / (spec['texture_paths'][color] + '.png')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected[color]:
            raise ValueError('Native shulker texture differs from the versioned source: ' + str(path))
        with Image.open(path) as source:
            content = closed_texture(source)
        filename = 'preview_shulker_' + color + '_closed.png'
        output = ROOT / 'resource_pack/textures/blocks' / filename
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)
        manifest['closed_texture_sha256'][filename] = hashlib.sha256(content).hexdigest()
    TEXTURE_MANIFEST.write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n', encoding='utf8')


def outputs(spec):
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    if (spec.get('game_version') != manifest['game_version'] or
            spec.get('palette_sha256') != manifest['source_sha256'].lower()):
        raise ValueError('Native shulker sources do not match the current block registry')
    if spec['schema'] != 2 or set(spec['texture_paths']) != set(SHULKER_COLORS):
        raise ValueError('Unsupported or incomplete shulker model source')
    files = {ROOT / 'behavior_pack/modern_projection/projection/static_shulker_data.py':
             '"""Generated by tools/generate_shulker_proxies.py; do not edit."""\n'
             'SCHEMA_VERSION = 1\n'
             'SOURCE_VERSION = ' + repr(spec['game_version']) + '\n'
             'PALETTE_SHA256 = ' + repr(spec['palette_sha256']) + '\n'}
    blocks_path = ROOT / 'resource_pack/blocks.json'
    blocks = json.loads(blocks_path.read_text(encoding='utf8'))
    atlas_path = ROOT / 'resource_pack/textures/terrain_texture.json'
    atlas = json.loads(atlas_path.read_text(encoding='utf8')) if atlas_path.exists() else {
        'resource_pack_name': 'modern_projection', 'texture_name': 'atlas.terrain', 'texture_data': {}}
    for color in SHULKER_COLORS:
        texture = 'modern_projection_shulker_' + color
        atlas['texture_data'][texture] = {'textures': 'textures/blocks/preview_shulker_' + color + '_closed'}
        for facing, identifier in enumerate(SHULKER_PROXIES['minecraft:' + color + '_shulker_box']):
            filename = identifier.split(':', 1)[1] + '.json'
            files[ROOT / 'behavior_pack/netease_blocks' / filename] = behavior(identifier, 'opaque')
            files[ROOT / 'resource_pack/models/netease_block' / filename] = model(spec, color, facing)
            blocks[identifier] = {'netease_model': identifier, 'sound': 'stone'}
    files[blocks_path] = blocks
    files[atlas_path] = atlas
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--source', type=Path, default=ROOT / 'tools/data/shulker_static_model_v1.json')
    parser.add_argument('--native-resource-root', type=Path)
    args = parser.parse_args()
    spec = json.loads(args.source.read_text(encoding='utf8'))
    files = outputs(spec)
    generate_textures(spec, args.native_resource_root, args.check)
    stale = []
    for path, data in files.items():
        text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=True, indent=2) + '\n'
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
