"""Generate measured static mushroom and fungus proxies from native textures."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'behavior_pack/modern_projection'))
from projection.debug_snow_blueprints import NAMES
from generate_shulker_proxies import behavior

MANIFEST = ROOT/'tools/data/block_registry_manifest.json'


def source_path(manifest):
    version = manifest['game_version'].removeprefix('NEMC ')
    if version == manifest['game_version'] or not version:
        raise ValueError('Expected a versioned NEMC source manifest')
    return ROOT/'tools/data'/('static_plant_sources_nemc_'+version+'.json')


SOURCE = source_path(json.loads(MANIFEST.read_text(encoding='utf8')))
TEMPLATE = ROOT/'resource_pack/models/netease_block/preview_fern.json'
EXISTING = frozenset(('short_grass', 'fern'))
CANDIDATES = frozenset(('brown_mushroom', 'red_mushroom', 'crimson_fungus', 'warped_fungus'))
SPECIAL = {
    'firefly_bush': 'Emissive animated texture requires a separate material and phase contract',
    'open_eyeblossom': 'Emissive texture and day/night lifecycle require separate evidence',
    'closed_eyeblossom': 'Day/night lifecycle requires separate evidence',
}
GEOMETRY_CONTRACT = ('Centered crossed template with unchanged XZ spans .1-.9, rotations and UV; '
                     'new static candidates use height 1 and pivot Y .5. Native texture alpha-height '
                     'anchors support this vertical extent; no native random offset is fitted. '
                     'Whole rendered silhouettes require independent captures.')
GEOMETRY_EVIDENCE = {
    'report': 'snow-poppy-mushroom-native-baseline-r5.json',
    'report_sha256': '212579fad73d4b3679b68325abf4bbafa6dac017003f004b97a2a7c2628d0962',
    'method': 'Native alpha-row and calibrated world-height anchors; no whole-mask fitting',
    'brown_mushroom': {
        'native_png_sha256': '4fff2278eb483287a8107420238b36a18f7158d73ae8fe1de616b129c0b6cfd7',
        'texture_alpha_top_row': 8,
        'texture_height': 16,
        'native_top_screen_y_approx': 550,
        'calibrated_half_block_screen_y_approx': 552,
    },
    'poppy': {
        'native_png_sha256': '825e889cef9bd98e96aa42a8b435dfbec6f7ab27ae3e04c64a6fc65d5df9fa76',
        'texture_alpha_top_row': 5,
        'texture_height': 16,
        'native_visible_height_pixels': 191,
    },
    'fungus_boundary_r7': {
        'report': 'fungus-candidate-boundary-two-view-r7.json',
        'report_sha256': 'cabf1dcdffa514dc81a2614737f87743f40890575bee8541c1f3e11af256d605',
        'accepted_scope': 'Dry plus crimson h4/h5 and warped h3/h4, both full/missing modes and two predefined views only',
        'mesh_authority': 'Centered cross copied from the mushroom construction; independent native pixels validate only the fixed accepted scope',
        'all_eight_snow_heights_accepted': False,
        'crimson_fungus_alpha_bounds': [3, 4, 13, 16],
        'warped_fungus_alpha_bounds': [3, 7, 13, 16],
        'public_world_offset': [-2., .15, -2.5],
        'right_world_offset': [2., .15, -2.5],
    },
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def named_texture(definition, terrain):
    names = definition['textures']
    key = names['up'] if isinstance(names, dict) else names
    variants = terrain['texture_data'][key]['textures']
    variants = variants if isinstance(variants, list) else [variants]
    if len(variants) != 1:
        raise ValueError('Static plant has multiple native texture variants: '+key)
    variant = variants[0]
    if isinstance(variant, dict):
        if set(variant)-{'path'}:
            raise ValueError('Static plant has native texture modifiers: '+key)
        variant = variant['path']
    return key, variant


def capture_source(native):
    paths = {'blocks': 'blocks.json', 'terrain': 'textures/terrain_texture.json'}
    blocks, terrain = (json.loads((native/paths[key]).read_text(encoding='utf8'))
                       for key in ('blocks', 'terrain'))
    manifest = json.loads(MANIFEST.read_text(encoding='utf8'))
    plants = {}
    for name in NAMES:
        if name in EXISTING or name in SPECIAL:
            continue
        key, texture = named_texture(blocks[name], terrain)
        relative = next((texture+extension for extension in ('.tga', '.png')
                         if (native/(texture+extension)).is_file()), None)
        if relative is None:
            raise ValueError('Native plant texture is missing: '+texture)
        with Image.open(native/relative) as image:
            size = image.size
            alpha = image.convert('RGBA').getchannel('A').getbbox()
        if size != (16, 16) or alpha is None:
            raise ValueError('Static crossed plant needs an independently checked 16x16 alpha texture: '+name)
        paths['texture_'+name] = relative
        plants[name] = {'definition': blocks[name], 'texture_key': key,
                        'atlas_record': terrain['texture_data'][key],
                        'texture_path': relative, 'texture_size': size, 'alpha_bounds': alpha}
    template = json.loads(TEMPLATE.read_text(encoding='utf8'))
    return {'schema': 1, 'game_version': manifest['game_version'],
            'palette_sha256': manifest['source_sha256'], 'paths': paths,
            'sha256': {key: digest(native/path) for key, path in paths.items()},
            'plants': plants, 'excluded': SPECIAL, 'template': template,
            'template_path': str(TEMPLATE.relative_to(ROOT)).replace('\\', '/'),
            'template_sha256_utf8_lf': hashlib.sha256(TEMPLATE.read_text(encoding='utf8').encode('utf8')).hexdigest(),
            'geometry_contract': GEOMETRY_CONTRACT,
            'geometry_evidence': GEOMETRY_EVIDENCE,
            'scope': 'Exact native texture identities for static candidates; source hashes do not certify rendered pixels'}


def validate(spec, native=None):
    manifest = json.loads(MANIFEST.read_text(encoding='utf8'))
    if (spec.get('schema') != 1 or spec.get('game_version') != manifest['game_version'] or
            spec.get('palette_sha256', '').lower() != manifest['source_sha256'].lower()):
        raise ValueError('Static plant sources do not match the native registry')
    expected = set(NAMES)-EXISTING-set(SPECIAL)
    if set(spec['plants']) != expected or spec['excluded'] != SPECIAL:
        raise ValueError('Static plant source coverage changed')
    if (spec.get('geometry_contract') != GEOMETRY_CONTRACT or
            spec.get('geometry_evidence') != GEOMETRY_EVIDENCE):
        raise ValueError('Static plant vertical geometry evidence changed')
    if set(spec['paths']) != {'blocks', 'terrain'}|{'texture_'+name for name in expected} or set(spec['sha256']) != set(spec['paths']):
        raise ValueError('Static plant source fingerprints are incomplete')
    if any(len(value) != 64 or any(character not in '0123456789abcdef' for character in value)
           for value in spec['sha256'].values()):
        raise ValueError('Static plant source fingerprint is invalid')
    template = TEMPLATE.read_text(encoding='utf8')
    if (json.loads(template) != spec['template'] or
            hashlib.sha256(template.encode('utf8')).hexdigest() != spec['template_sha256_utf8_lf']):
        raise ValueError('Static crossed geometry template changed')
    for name, plant in spec['plants'].items():
        bounds = plant['alpha_bounds']
        if (plant['texture_size'] != [16, 16] or not bounds or len(bounds) != 4 or
                not 0 <= bounds[0] < bounds[2] <= 16 or
                not 0 <= bounds[1] < bounds[3] <= 16):
            raise ValueError('Static native plant alpha contract changed: '+name)
        key, texture = named_texture(plant['definition'], {'texture_data': {plant['texture_key']: plant['atlas_record']}})
        if key != plant['texture_key'] or plant['texture_path'].rsplit('.', 1)[0] != texture:
            raise ValueError('Static native plant texture mapping changed: '+name)
        if spec['paths']['texture_'+name] != plant['texture_path']:
            raise ValueError('Static native plant source path changed: '+name)
    if native is not None:
        for key, path in spec['paths'].items():
            if digest(native/path) != spec['sha256'][key]:
                raise ValueError('Installed native plant source changed: '+path)
        for name, plant in spec['plants'].items():
            with Image.open(native/plant['texture_path']) as image:
                alpha = image.convert('RGBA').getchannel('A').getbbox()
                if (list(image.size) != plant['texture_size'] or
                        (list(alpha) if alpha is not None else None) != plant['alpha_bounds']):
                    raise ValueError('Installed native plant alpha metadata changed: '+name)


def outputs(spec):
    blocks_path = ROOT/'resource_pack/blocks.json'
    atlas_path = ROOT/'resource_pack/textures/terrain_texture.json'
    blocks = json.loads(blocks_path.read_text(encoding='utf8'))
    atlas = json.loads(atlas_path.read_text(encoding='utf8'))
    for name in spec['plants']:
        blocks.pop('modern_projection:preview_'+name, None)
        atlas['texture_data'].pop('modern_projection_static_'+name, None)
    files = {}
    lines = ['# Generated by tools/generate_static_plant_proxies.py; do not edit.',
             'from __future__ import unicode_literals',
             'SOURCE_VERSION = '+repr(spec['game_version']),
             'PALETTE_SHA256 = '+repr(spec['palette_sha256']),
             'STATIC_PLANT_PROXIES = {']
    for name in sorted(CANDIDATES):
        source = spec['plants'][name]
        identifier = 'modern_projection:preview_'+name
        filename = 'preview_'+name+'.json'
        key = 'modern_projection_static_'+name
        model = deepcopy(spec['template'])
        for bone in model['netease:block_geometry']['bones']:
            bone['pivot'][1] = 8
            for cube in bone['cubes']:
                cube['size'][1] = 16
        description = model['netease:block_geometry']['description']
        description.update(identifier=identifier, textures=[key], item_texture=key)
        definition = behavior(identifier, 'alpha')
        definition['minecraft:block']['components'].update({
            'netease:water_source': {'value': True}, 'netease:water_flow_source': {'value': True}})
        files[ROOT/'behavior_pack/netease_blocks'/filename] = definition
        files[ROOT/'resource_pack/models/netease_block'/filename] = model
        appearance = {'netease_model': identifier, 'sound': source['definition'].get('sound', 'grass')}
        if name == 'bush':
            appearance['use_colormap'] = 'textures/colormap/grass'
        blocks[identifier] = appearance
        atlas['texture_data'][key] = {'textures': source['texture_path'].rsplit('.', 1)[0]}
        lines.append('    (%r, 0): %r,' % ('minecraft:'+name, identifier))
    lines.extend(('}', 'STATIC_PLANT_MAX_Y = {'))
    for name in sorted(CANDIDATES):
        source = spec['plants'][name]
        height = 1. - source['alpha_bounds'][1]/float(source['texture_size'][1])
        lines.append('    (%r, 0): %r,' % ('minecraft:'+name, height))
    lines.extend(('}', ''))
    files[ROOT/'behavior_pack/modern_projection/projection/plant_proxy_data.py'] = '\n'.join(lines)
    # Chest generation owns the trailing atlas entries and compares stable text.
    chest_entries = {key: value for key, value in atlas['texture_data'].items()
                     if key.startswith('modern_projection_static_chest_')}
    atlas['texture_data'] = {key: value for key, value in atlas['texture_data'].items()
                             if key not in chest_entries}
    atlas['texture_data'].update(chest_entries)
    files[blocks_path], files[atlas_path] = blocks, atlas
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-resource-root', type=Path)
    parser.add_argument('--refresh-source', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.refresh_source and (args.native_resource_root is None or args.check):
        parser.error('--refresh-source requires native sources and cannot be combined with --check')
    spec = json.loads(SOURCE.read_text(encoding='utf8')) if SOURCE.is_file() else None
    if spec is None or args.refresh_source:
        if args.native_resource_root is None:
            parser.error('Capture native plant sources with --native-resource-root')
        spec = capture_source(args.native_resource_root)
        SOURCE.write_text(json.dumps(spec, ensure_ascii=True, indent=2)+'\n', encoding='utf8')
        spec = json.loads(SOURCE.read_text(encoding='utf8'))
    validate(spec, args.native_resource_root)
    stale = []
    for path, value in outputs(spec).items():
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=True, indent=2)+'\n'
        if args.check:
            current = path.read_text(encoding='utf8') if path.is_file() else None
            # Shared registries contain entries from several independent generators.
            matches = (json.loads(current) == value if current is not None and path in
                       (ROOT/'resource_pack/blocks.json', ROOT/'resource_pack/textures/terrain_texture.json')
                       else current == text)
            if not matches:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.write_text(text, encoding='utf8')
    if stale:
        raise SystemExit('Stale static plant proxies: '+', '.join(stale))
    print('%s %d static plant candidates; %d special families excluded' %
          ('Checked' if args.check else 'Generated', len(CANDIDATES), len(SPECIAL)))


if __name__ == '__main__':
    main()
