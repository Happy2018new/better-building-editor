"""Generate versioned centered snapshot plants from the installed vanilla atlas."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image

from generate_static_plant_proxies import (ROOT, TEMPLATE, centered_cross_model,
                                           digest, source_path)
from generate_shulker_proxies import behavior

sys.path.insert(0, str(ROOT/'behavior_pack/modern_projection'))
from projection.debug_snow_blueprints import NAMES

MANIFEST = ROOT/'tools/data/block_registry_manifest.json'
PROFILE = source_path(json.loads(MANIFEST.read_bytes())).with_name(
    source_path(json.loads(MANIFEST.read_bytes())).name.replace('static_plant_sources_', 'centered_plant_profiles_'))
TABLE = ROOT/'behavior_pack/modern_projection/projection/centered_plant_data.py'
PROFILE_SCHEMA_VERSION = 2
EXISTING = frozenset(('short_grass', 'fern'))
# The atlas's carried variants are the native static combination of the
# separate stem/eyes or bush/firefly sprites. Snapshots never advance the world.
CARRIED = frozenset(('open_eyeblossom', 'firefly_bush'))
STYLE = {'schema': 1, 'name': 'fixed_centered_snapshot', 'xz_translation': [0, 0],
         'cross_height': 1, 'native_random_offset': False,
         'world_lifecycle': False, 'cell_span': [.1, .9]}


def retained_mesh(name):
    path = ROOT/'resource_pack/models/netease_block'/('preview_'+name+'.json')
    text = path.read_text(encoding='utf8')
    model = json.loads(text)['netease:block_geometry']
    heights = {cube['size'][1]/16. for bone in model['bones'] for cube in bone['cubes']}
    if heights != {.8} or model['description']['identifier'] != 'modern_projection:preview_'+name:
        raise ValueError('Retained centered grass mesh contract changed: '+name)
    return {'path': path.relative_to(ROOT).as_posix(), 'height': .8,
            'sha256_utf8_lf': hashlib.sha256(text.encode('utf8')).hexdigest()}


def snapshot(native):
    registry = json.loads(MANIFEST.read_bytes())
    blocks = json.loads((native/'blocks.json').read_bytes())
    atlas = json.loads((native/'textures/terrain_texture.json').read_bytes())
    plants = {}
    for name in sorted(NAMES):
        definition = blocks[name]
        key = definition['carried_textures'] if name in CARRIED else definition['textures']
        if isinstance(key, dict):
            key = key['up']
        textures = atlas['texture_data'][key]['textures']
        variants = textures if isinstance(textures, list) else [textures]
        if len(variants) != 1 or not isinstance(variants[0], str):
            raise ValueError('Expected one native centered snapshot texture: '+name)
        relative = next((variants[0]+extension for extension in ('.tga', '.png')
                         if (native/(variants[0]+extension)).is_file()), None)
        if relative is None:
            raise ValueError('Native snapshot texture missing: '+name)
        with Image.open(native/relative) as image:
            size = list(image.size)
            alpha = image.convert('RGBA').getchannel('A').getbbox()
        if size != [16, 16] or alpha is None:
            raise ValueError('Expected static 16x16 native snapshot texture: '+name)
        plants[name] = {'definition': definition, 'texture_key': key,
                        'atlas_record': atlas['texture_data'][key], 'texture_path': relative,
                        'texture_sha256': digest(native/relative), 'texture_size': size,
                        'alpha_bounds': list(alpha), 'static_carried_combination': name in CARRIED,
                        'mesh': retained_mesh(name) if name in EXISTING else {'height': 1., 'generated': True}}
    return {'schema': PROFILE_SCHEMA_VERSION, 'game_version': registry['game_version'],
            'palette_sha256': registry['source_sha256'].lower(), 'style': STYLE,
            'source_sha256': {'blocks': digest(native/'blocks.json'),
                              'terrain': digest(native/'textures/terrain_texture.json'),
                              'template': hashlib.sha256(TEMPLATE.read_text(encoding='utf8').encode('utf8')).hexdigest()},
            'plants': plants}


def validate_profile(profile, native=None):
    registry = json.loads(MANIFEST.read_bytes())
    if (profile.get('schema') != PROFILE_SCHEMA_VERSION or profile.get('game_version') != registry['game_version'] or
            profile.get('palette_sha256') != registry['source_sha256'].lower() or profile.get('style') != STYLE):
        raise ValueError('Centered plant profile version or style differs')
    if set(profile['plants']) != set(NAMES):
        raise ValueError('Centered plant profile does not cover this snow catalogue')
    if profile['source_sha256']['template'] != hashlib.sha256(TEMPLATE.read_text(encoding='utf8').encode('utf8')).hexdigest():
        raise ValueError('Centered plant cross template changed')
    for name, plant in profile['plants'].items():
        bounds = plant['alpha_bounds']
        if (plant['texture_size'] != [16, 16] or len(bounds) != 4 or
                not 0 <= bounds[0] < bounds[2] <= 16 or not 0 <= bounds[1] < bounds[3] <= 16):
            raise ValueError('Centered plant alpha extent invalid: '+name)
        textures = plant['atlas_record']['textures']
        values = textures if isinstance(textures, list) else [textures]
        if values != [plant['texture_path'].rsplit('.', 1)[0]]:
            raise ValueError('Centered plant atlas mapping differs: '+name)
        if plant['static_carried_combination'] != (name in CARRIED):
            raise ValueError('Centered plant static snapshot choice differs: '+name)
        expected_mesh = retained_mesh(name) if name in EXISTING else {'height': 1., 'generated': True}
        if plant.get('mesh') != expected_mesh:
            raise ValueError('Centered plant mesh source changed: '+name)
        fingerprint = plant['texture_sha256']
        if len(fingerprint) != 64 or any(char not in '0123456789abcdef' for char in fingerprint):
            raise ValueError('Centered plant source fingerprint invalid: '+name)
        if native is not None:
            if digest(native/plant['texture_path']) != fingerprint:
                raise ValueError('Installed centered plant texture changed: '+name)
            with Image.open(native/plant['texture_path']) as image:
                alpha = image.convert('RGBA').getchannel('A').getbbox()
                if list(image.size) != plant['texture_size'] or list(alpha or ()) != bounds:
                    raise ValueError('Installed centered plant alpha changed: '+name)
    if native is not None:
        for key, relative in (('blocks', 'blocks.json'), ('terrain', 'textures/terrain_texture.json')):
            if digest(native/relative) != profile['source_sha256'][key]:
                raise ValueError('Installed centered plant atlas changed: '+key)


def outputs(profile):
    validate_profile(profile)
    source = {'template': json.loads(TEMPLATE.read_bytes())}
    blocks_path, atlas_path = ROOT/'resource_pack/blocks.json', ROOT/'resource_pack/textures/terrain_texture.json'
    blocks, atlas = (json.loads(path.read_bytes()) for path in (blocks_path, atlas_path))
    result, proxies, heights = {}, {}, {}
    for name, plant in sorted(profile['plants'].items()):
        material = ('minecraft:'+name, 0)
        heights[material] = plant['mesh']['height']*(1.-plant['alpha_bounds'][1]/16.)
        if name in EXISTING:
            continue
        identifier, key = 'modern_projection:centered_'+name, 'modern_projection_centered_'+name
        definition = behavior(identifier, 'alpha')
        definition['minecraft:block']['components'].update({
            'netease:water_source': {'value': True}, 'netease:water_flow_source': {'value': True}})
        result[ROOT/'behavior_pack/netease_blocks'/('centered_'+name+'.json')] = definition
        result[ROOT/'resource_pack/models/netease_block'/('centered_'+name+'.json')] = centered_cross_model(source, identifier, key)
        appearance = {'netease_model': identifier, 'sound': plant['definition'].get('sound', 'grass')}
        if name == 'bush':
            appearance['use_colormap'] = 'textures/colormap/grass'
        blocks[identifier] = appearance
        atlas['texture_data'][key] = {'textures': plant['texture_path'].rsplit('.', 1)[0]}
        proxies[material] = identifier
    lines = ['# Generated by tools/generate_centered_plant_profiles.py; do not edit.',
             'from __future__ import unicode_literals', 'SCHEMA_VERSION = '+repr(PROFILE_SCHEMA_VERSION),
             'STYLE_VERSION = 1', 'STYLE = '+repr(STYLE['name']),
             'SOURCE_VERSION = '+repr(profile['game_version']),
             'PALETTE_SHA256 = '+repr(profile['palette_sha256']),
             'PROFILE_SHA256 = '+repr(digest(PROFILE)), 'CENTERED_PLANT_PROXIES = {']
    lines.extend('    %r: %r,' % (key, value) for key, value in sorted(proxies.items()))
    lines.extend(('}', 'CENTERED_PLANT_MAX_Y = {'))
    lines.extend('    %r: %r,' % (key, value) for key, value in sorted(heights.items()))
    lines.extend(('}', ''))
    result[TABLE] = '\n'.join(lines)
    result[blocks_path], result[atlas_path] = blocks, atlas
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-resource-root', type=Path)
    parser.add_argument('--refresh-source', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.refresh_source:
        if args.native_resource_root is None or args.check:
            parser.error('Source refresh needs installed native resources and write mode')
        PROFILE.write_text(json.dumps(snapshot(args.native_resource_root), ensure_ascii=True, indent=2)+'\n', encoding='ascii')
    profile = json.loads(PROFILE.read_bytes())
    validate_profile(profile, args.native_resource_root)
    stale = []
    for path, value in outputs(profile).items():
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=True, indent=2)+'\n'
        if args.check:
            current = path.read_text(encoding='utf8') if path.is_file() else None
            matches = json.loads(current) == value if isinstance(value, dict) and current is not None else current == text
            if not matches:
                stale.append(path.relative_to(ROOT).as_posix())
        else:
            path.write_text(text, encoding='ascii')
    if stale:
        raise SystemExit('Stale centered plant profiles: '+', '.join(stale))
    print('%s %d centered plant source profiles; %d new proxies' %
          ('Checked' if args.check else 'Generated', len(profile['plants']), len(profile['plants'])-len(EXISTING)))


if __name__ == '__main__':
    main()
