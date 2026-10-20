"""Generate fixed centered fallbacks for invisible native cross plants."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image

from generate_static_plant_proxies import centered_cross_model, TEMPLATE
from generate_shulker_proxies import behavior
from configure_development_runtime import load_target

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'tools/data/ordinary_plant_profiles_nemc_3.10.0.420447.json'
TEXTURES = PROFILE.with_suffix('')
TABLE = ROOT / 'behavior_pack/modern_projection/projection/ordinary_plant_data.py'
STYLE = {'name': 'fixed_centered_snapshot', 'height': 1, 'cell_span': [0.1, 0.9],
         'native_random_offset': False, 'native_mesh_authority': False, 'snow_qualification': False}
CORALS = frozenset(prefix + family + '_coral'
                   for prefix in ('', 'dead_')
                   for family in ('brain', 'bubble', 'fire', 'horn', 'tube'))
NAMES = CORALS | frozenset(('acacia_sapling', 'peony'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def variants(name, row):
    """Each tall native cell selects its own full-height texture and model."""
    if name != 'peony':
        return ((name, row, row['native_states']),)
    if [half.get('half') for half in row.get('halves', ())] != ['bottom', 'top']:
        raise ValueError('Ordinary peony half coverage changed')
    return tuple((name + '_' + half['half'], half, [row['native_states'][index]])
                 for index, half in enumerate(row['halves']))


def validate(profile, textures=TEXTURES):
    if (profile.get('schema') != 1 or profile.get('style') != STYLE or
            profile.get('registry_version') != registry.source_version() or
            profile.get('palette_sha256') != registry.fingerprint() or
            profile.get('resource_version') != load_target()['resource_version'] or
            set(profile['plants']) != NAMES):
        raise ValueError('Ordinary plant profile version, style or coverage changed')
    if (profile['template']['path'] != TEMPLATE.relative_to(ROOT).as_posix() or
            profile['template']['sha256'] != digest(TEMPLATE.read_bytes())):
        raise ValueError('Ordinary plant cross template changed')
    for name, row in profile['plants'].items():
        expected = ([{'age_bit': False}, {'age_bit': True}] if name == 'acacia_sapling' else
                    [{'upper_block_bit': False}, {'upper_block_bit': True}] if name == 'peony' else [{}])
        if [entry['states'] for entry in row['native_states']] != expected:
            raise ValueError('Ordinary plant legal state coverage changed: ' + name)
        for entry in row['native_states']:
            value = registry.from_states('minecraft:' + name, entry['states'])
            if value is None or list(value) != entry['material'] or registry.states(value) != entry['states']:
                raise ValueError('Ordinary plant state identity differs: ' + name)
        if name == 'peony' and row['native_definition']['textures'] != {
                'up': 'peony_top', 'down': 'peony_bottom', 'side': 'sunflower_additional'}:
            raise ValueError('Ordinary peony native texture slots changed')
        for stem, texture_row, unused_states in variants(name, row):
            key = texture_row['native_texture_key']
            texture = texture_row['native_texture_path'].rsplit('.', 1)[0]
            native_key = ('peony_' + texture_row['half'] if name == 'peony'
                          else row['native_definition']['textures'])
            if (native_key != key or texture_row['native_atlas_record']['textures'] != texture or
                    texture_row['size'] != [16, 16]):
                raise ValueError('Ordinary plant native texture binding differs: ' + stem)
            path = textures / (stem + '.png')
            if digest(path.read_bytes()) != texture_row['native_texture_sha256']:
                raise ValueError('Ordinary plant texture source changed: ' + stem)
            with Image.open(path) as image:
                bounds = image.convert('RGBA').getchannel('A').getbbox()
                if list(image.size) != texture_row['size'] or list(bounds or ()) != texture_row['alpha_bounds']:
                    raise ValueError('Ordinary plant alpha extent differs: ' + stem)


def outputs(profile):
    validate(profile)
    blocks_path = ROOT / 'resource_pack/blocks.json'
    atlas_path = ROOT / 'resource_pack/textures/terrain_texture.json'
    blocks = json.loads(blocks_path.read_bytes())
    atlas = json.loads(atlas_path.read_bytes())
    template = {'template': json.loads(TEMPLATE.read_bytes())}
    result, mappings = {}, {}
    for name, row in sorted(profile['plants'].items()):
        for variant, texture_row, native_states in variants(name, row):
            stem = 'ordinary_' + variant
            identifier = 'modern_projection:' + stem
            key = 'modern_projection_' + stem
            result[ROOT / ('behavior_pack/netease_blocks/' + stem + '.json')] = behavior(identifier, 'alpha')
            result[ROOT / ('resource_pack/models/netease_block/' + stem + '.json')] = centered_cross_model(
                template, identifier, key)
            blocks[identifier] = {'netease_model': identifier, 'sound': row['native_definition'].get('sound', 'grass')}
            atlas['texture_data'][key] = {'textures': texture_row['native_texture_path'].rsplit('.', 1)[0]}
            for entry in native_states:
                mappings[tuple(entry['material'])] = identifier
    lines = ['# Generated by tools/generate_ordinary_plant_proxies.py; do not edit.',
             'from __future__ import unicode_literals', 'SCHEMA_VERSION = 1',
             'SOURCE_VERSION = ' + repr(profile['registry_version']),
             'RESOURCE_VERSION = ' + repr(profile['resource_version']),
             'PALETTE_SHA256 = ' + repr(profile['palette_sha256']),
             'PROFILE_SHA256 = ' + repr(digest(PROFILE.read_bytes().replace(b'\r\n', b'\n'))),
             "STYLE = 'fixed_centered_snapshot'", 'NATIVE_MESH_AUTHORITY = False',
             'SNOW_QUALIFIED = False', 'ORDINARY_PLANT_PROXIES = {']
    lines.extend('    %r: %r,' % (value, identifier) for value, identifier in sorted(mappings.items()))
    lines.extend(('}', ''))
    result[TABLE] = '\n'.join(lines)
    result[blocks_path], result[atlas_path] = blocks, atlas
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    profile = json.loads(PROFILE.read_bytes())
    files = outputs(profile)
    stale = []
    for path, value in files.items():
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=True, indent=2) + '\n'
        if args.check:
            current = path.read_text(encoding='utf8') if path.is_file() else None
            same = (json.loads(current) == value if isinstance(value, dict) and current is not None
                    else current == text)
            if not same:
                stale.append(path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='ascii')
    if stale:
        raise SystemExit('Stale ordinary plant fallbacks: ' + ', '.join(stale))
    print(json.dumps({'checked': args.check, 'files': len(files), 'names': len(profile['plants']),
                      'states': sum(len(row['native_states']) for row in profile['plants'].values()),
                      'native_mesh_authority': False, 'snow_qualified': False}))


if __name__ == '__main__':
    main()
