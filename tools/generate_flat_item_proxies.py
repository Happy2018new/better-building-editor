"""Resolve versioned vanilla item resources and extrude their alpha silhouettes."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source_path(root=ROOT):
    manifest = json.loads((root / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    version = manifest['game_version'].removeprefix('NEMC ')
    if not version or version == manifest['game_version']:
        raise ValueError('Expected a versioned NEMC block registry manifest')
    path = root / 'tools/data' / ('flat_item_sources_nemc_' + version + '.json')
    if not path.is_file():
        raise ValueError('Missing versioned flat item resources and frame pose: ' + str(path))
    return path


def validate_source(spec, manifest):
    if (spec.get('schema') != 1 or spec.get('game_version') != manifest['game_version'] or
            spec.get('palette_sha256') != manifest['source_sha256'].lower()):
        raise ValueError('Flat item sources do not match the current block registry')
    if spec['observation']['game_executable_version'] != manifest['game_version'].removeprefix('NEMC '):
        raise ValueError('Flat item observations belong to a different executable version')
    pose = spec['frame_pose']
    if (type(pose['accepted']) is not bool or not 0 < pose['size_pixels'] <= 16 or
            not 0 < pose['thickness_pixels'] <= 16 or not 0 <= pose['front_z_pixels'] < 16):
        raise ValueError('Unsupported flat item frame pose')
    seen = set()
    for item in spec['items']:
        key = (item['identifier'], item['aux'])
        if (key in seen or not isinstance(item['identifier'], str) or ':' not in item['identifier'] or
                type(item['aux']) is not int or not 0 <= item['aux'] <= 65535 or
                type(item['accepted']) is not bool):
            raise ValueError('Invalid or duplicate versioned flat item definition')
        seen.add(key)
        if item['accepted'] and (not pose['accepted'] or not item.get('acceptance_evidence')):
            raise ValueError('Accepted items require accepted pose and native acceptance evidence')
        if item['resolved']['texture_path'] != item['texture_path']:
            raise ValueError('Flat item definition and atlas texture path differ')
        for digest_value in (spec['item_texture_sha256'], item['texture_sha256']):
            if len(digest_value) != 64 or set(digest_value) - set('0123456789abcdef'):
                raise ValueError('Flat item source is missing a SHA-256 fingerprint')


def profile_table(spec):
    return {(item['identifier'], item['aux']): {
        'accepted': item['accepted'], 'acceptance_evidence': item.get('acceptance_evidence'),
        'proxies': {(face, rotation): identifier(item, face, rotation)
                    for face in range(6) for rotation in range(8)}} for item in spec['items']}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def texture_paths(record):
    value = record['textures']
    values = value if isinstance(value, list) else [value]
    return [entry['path'] if isinstance(entry, dict) else entry for entry in values]


def resolve_item(item, atlas, definition=None):
    """Use an item definition's icon, or an observed engine texture path."""
    key, index = None, None
    if definition is not None:
        body = definition['minecraft:item']
        if body['description']['identifier'] != item['identifier']:
            raise ValueError('Item definition identifier changed')
        icon = body['components']['minecraft:icon']
        if isinstance(icon, str):
            key, index = icon, 0
        else:
            key = icon.get('texture') or icon['textures']['default']
            index = icon.get('index', 0)
        path = texture_paths(atlas['texture_data'][key])[index]
        if path != item['texture_path']:
            raise ValueError('Engine observation and item definition disagree')
    else:
        matches = [(name, offset) for name, record in atlas['texture_data'].items()
                   for offset, path in enumerate(texture_paths(record)) if path == item['texture_path']]
        if len(matches) != 1:
            raise ValueError('Observed item texture must resolve to one atlas entry')
        key, index = matches[0]
    return {'texture_key': key, 'texture_index': index, 'texture_path': item['texture_path']}


def silhouette_cubes(image, pose):
    """Two bitmap faces plus exposed texel edges; no faces inside the silhouette."""
    width, height = image.size
    alpha = image.convert('RGBA').getchannel('A')
    if set(alpha.getdata()) - {0, 255}:
        raise ValueError('Intermediate alpha requires an independently accepted material profile')
    occupied = {(x, y) for y in range(height) for x in range(width) if alpha.getpixel((x, y))}
    if not occupied:
        raise ValueError('The source item bitmap is empty')
    scale, depth, z = pose['size_pixels'] / width, pose['thickness_pixels'], pose['front_z_pixels']
    left, bottom = -8 - width * scale / 2., 8 - height * scale / 2.
    cubes = [{'origin': [left, bottom, z], 'size': [width * scale, height * scale, depth],
              'uv': {'north': {'uv': [0, 0], 'uv_size': [width, height]},
                     'south': {'uv': [width, 0], 'uv_size': [-width, height]}}}]
    for x, y in sorted(occupied):
        faces = {}
        for face, neighbor in (('west', (x - 1, y)), ('east', (x + 1, y)),
                               ('up', (x, y - 1)), ('down', (x, y + 1))):
            if neighbor not in occupied:
                faces[face] = {'uv': [x, y], 'uv_size': [1, 1]}
        if faces:
            cubes.append({'origin': [left + x * scale, bottom + (height - y - 1) * scale, z],
                          'size': [scale, scale, depth], 'uv': faces})
    return cubes


def identifier(item, facing, rotation):
    name = item['identifier'].replace(':', '_')
    return 'modern_projection:preview_item_%s_%d_f%d_r%d' % (name, item['aux'], facing, rotation)


def model(item, image, pose, facing, rotation):
    # The native palette importer mirrors X. Local clockwise rotation therefore
    # uses positive Z. The positive-depth plane rotates toward the support face.
    orientation = {0: [-90, 0, 0], 1: [90, 0, 0], 2: [0, 0, 0],
                   3: [0, 180, 0], 4: [0, -90, 0], 5: [0, 90, 0]}[facing]
    texture = 'modern_projection_flat_' + item['identifier'].replace(':', '_') + '_' + str(item['aux'])
    return {'format_version': '1.13.0', 'netease:block_geometry': {
        'description': {'identifier': identifier(item, facing, rotation), 'textures': [texture],
                        'textures_descriptions': [{'width': image.width, 'length': image.height}],
                        'item_texture': item['resolved']['texture_key'], 'use_ao': False},
        'bones': [{'name': 'item', 'pivot': [-8, 8, 8],
                   'rotation': [orientation[0], orientation[1], rotation * 45],
                   'cubes': silhouette_cubes(image, pose)}]}}


def behavior(name):
    return {'format_version': '1.10.0', 'minecraft:block': {
        'description': {'identifier': name, 'register_to_creative_menu': False},
        'components': {'netease:render_layer': {'value': 'alpha'},
                       'netease:no_crop_face_block': {},
                       'minecraft:block_light_absorption': {'value': 0}}}}


def outputs(spec, native_root=None):
    from PIL import Image
    registry = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    validate_source(spec, registry)
    blocks_path = ROOT / 'resource_pack/blocks.json'
    atlas_path = ROOT / 'resource_pack/textures/terrain_texture.json'
    blocks = json.loads(blocks_path.read_text(encoding='utf8'))
    atlas = json.loads(atlas_path.read_text(encoding='utf8'))
    result, profiles = {}, profile_table(spec)
    for original in spec['items']:
        item = dict(original)
        if native_root is not None:
            native_atlas = native_root / 'textures/item_texture.json'
            if digest(native_atlas) != spec['item_texture_sha256']:
                raise ValueError('Installed item_texture changed')
            definition = None
            if item.get('definition_path'):
                path = native_root / item['definition_path']
                if digest(path) != item['definition_sha256']:
                    raise ValueError('Installed item definition changed')
                definition = json.loads(path.read_text(encoding='utf8'))
            resolved = resolve_item(item, json.loads(native_atlas.read_text(encoding='utf8')), definition)
            if resolved != item['resolved']:
                raise ValueError('Versioned item resource resolution changed')
            source = native_root / (item['texture_path'] + '.png')
            if digest(source) != item['texture_sha256']:
                raise ValueError('Installed item bitmap changed')
            texture_data = source.read_bytes()
        else:
            source = ROOT / item['generated_texture']
            if digest(source) != item['texture_sha256']:
                raise ValueError('Generated item bitmap changed; provide --native-resource-root')
            texture_data = source.read_bytes()
        from io import BytesIO
        with Image.open(BytesIO(texture_data)) as image:
            if list(image.size) != item['texture_size']:
                raise ValueError('Item bitmap dimensions changed')
            result[ROOT / item['generated_texture']] = texture_data
            for facing in range(6):
                for rotation in range(8):
                    name = identifier(item, facing, rotation)
                    filename = name.split(':')[1] + '.json'
                    result[ROOT / 'behavior_pack/netease_blocks' / filename] = behavior(name)
                    result[ROOT / 'resource_pack/models/netease_block' / filename] = model(
                        item, image, spec['frame_pose'], facing, rotation)
                    blocks[name] = {'netease_model': name}
        texture = 'modern_projection_flat_' + item['identifier'].replace(':', '_') + '_' + str(item['aux'])
        atlas['texture_data'][texture] = {'textures': item['generated_texture'].removeprefix('resource_pack/').removesuffix('.png')}
    result[blocks_path], result[atlas_path] = blocks, atlas
    result[ROOT / 'behavior_pack/modern_projection/projection/static_frame_item_data.py'] = (
        '"""Generated by tools/generate_flat_item_proxies.py; do not edit."""\n'
        'SCHEMA_VERSION = 1\nSOURCE_VERSION = ' + repr(spec['game_version']) + '\n'
        'PALETTE_SHA256 = ' + repr(spec['palette_sha256']) + '\n'
        'SOURCE_SHA256 = ' + repr(hashlib.sha256(json.dumps(spec, sort_keys=True).encode('utf8')).hexdigest()) + '\n'
        'FRAME_ITEMS = ' + repr(profiles) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-resource-root', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    spec = json.loads(source_path().read_text(encoding='utf8'))
    stale = []
    for path, value in outputs(spec, args.native_resource_root).items():
        content = value if isinstance(value, bytes) else (
            value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=True) + '\n').encode('utf8')
        if args.check:
            matching = path.exists() and (path.read_bytes() == content if isinstance(value, bytes)
                                           else path.read_text(encoding='utf8') == content.decode('utf8'))
            if not matching:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    if stale:
        raise SystemExit('Stale flat item outputs: ' + ', '.join(stale))


if __name__ == '__main__':
    main()
