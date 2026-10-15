"""Inventory native flipbook candidates against every dumped block state.

Resource associations identify cases to test, never successful projection
animation. Model, entity and particle animation need their own observations.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ('blocks.json', 'textures/terrain_texture.json', 'textures/flipbook_textures.json')
DEFAULT_SOURCE = ROOT / 'docs/reference/native_animations/nemc_3.9.0.401155'
DEFAULT_REPORT = ROOT / 'tools/data/native_animated_blocks_nemc_3.9.0.401155.json'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def resource_name(name):
    name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    return name if ':' in name else 'minecraft:' + name


def image_name(value):
    return str(Path(value).with_suffix('')).replace('\\', '/')


def inventory(palette, blocks, terrain, flipbooks):
    """Join explicit tile IDs and equivalent image resources, preserving gaps."""
    states = defaultdict(list)
    for row in palette['blocks']:
        states[row['name']].append(row['data'])
    by_tile, by_image = defaultdict(set), defaultdict(set)
    for index, row in enumerate(flipbooks):
        if not isinstance(row, dict) or not isinstance(row.get('atlas_tile'), str):
            raise ValueError('Flipbook entry needs an explicit atlas tile')
        if not isinstance(row.get('flipbook_texture'), str):
            raise ValueError('Flipbook entry needs an explicit source image')
        by_tile[row['atlas_tile']].add(index)
        by_image[image_name(row['flipbook_texture'])].add(index)
    rows, resolved_names, referenced = [], set(), set()
    unmapped = []
    for definition, value in sorted(blocks.items()):
        if not isinstance(value, dict):
            continue
        name = resource_name(definition)
        if name in states:
            resolved_names.add(name)
        associations = []
        for usage in ('textures', 'carried_textures'):
            for tile in sorted(set(strings(value.get(usage)))):
                indexes = set(by_tile.get(tile, ()))
                # Flattened and legacy atlas IDs can refer to the same image.
                tile_data = terrain.get('texture_data', {}).get(tile, {})
                paths = set(strings(tile_data.get('textures'))) if isinstance(tile_data, dict) else set()
                for path in paths:
                    indexes.update(by_image.get(image_name(path), ()))
                if indexes:
                    associations.append({'usage': usage, 'tile': tile,
                                         'flipbook_indexes': sorted(indexes)})
                    referenced.update(indexes)
        if not associations:
            continue
        result = {'name': name, 'definition_key': definition,
                  'aux_values': sorted(set(states.get(name, ()))),
                  'associations': associations, 'pixel_acceptance': False}
        (rows if name in states else unmapped).append(result)
    return {'candidate_names': len(rows),
            'candidate_states': sum(len(row['aux_values']) for row in rows),
            'rows': rows, 'animated_definitions_missing_from_dump': unmapped,
            'dump_names_without_direct_definition': sorted(set(states) - resolved_names),
            'flipbook_entries_without_block_association': [i for i in range(len(flipbooks)) if i not in referenced]}


def report(source, manifest, palette_raw):
    snapshots, parsed = {}, {}
    for relative in RESOURCES:
        raw = (source / relative).read_bytes()
        snapshots[relative] = {'sha256': digest(raw), 'bytes': len(raw)}
        parsed[relative] = json.loads(raw)
    if digest(palette_raw).lower() != manifest['source_sha256'].lower():
        raise ValueError('Dump bytes do not match the registry manifest')
    palette = json.loads(palette_raw)
    if len(palette['blocks']) != manifest['record_count']:
        raise ValueError('Dump state coverage differs from the registry manifest')
    return dict(schema_version=1, game_version=manifest['game_version'],
                palette_sha256=digest(palette_raw), checked_states=len(palette['blocks']),
                checked_names=len({row['name'] for row in palette['blocks']}),
                resources=snapshots, flipbooks=parsed[RESOURCES[2]],
                **inventory(palette, parsed[RESOURCES[0]], parsed[RESOURCES[1]], parsed[RESOURCES[2]]),
                scope='Resource-linked flipbook candidates only. No model, particle, entity or pixel acceptance.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--output', type=Path, default=DEFAULT_REPORT)
    parser.add_argument('--vanilla-pack', type=Path)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    if args.capture and (args.check or args.vanilla_pack is None):
        parser.error('--capture needs --vanilla-pack and cannot be combined with --check')
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_bytes())
    if args.capture:
        for relative in RESOURCES:
            destination = args.source / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.vanilla_pack / relative, destination)
    data = report(args.source, manifest, (ROOT / manifest['source_file']).read_bytes())
    if args.vanilla_pack is not None:
        installed = report(args.vanilla_pack, manifest, (ROOT / manifest['source_file']).read_bytes())
        if installed != data:
            raise ValueError('Installed animation resources differ from the archived source')
    if args.check:
        if json.loads(args.output.read_bytes()) != data:
            raise ValueError('Native animated block audit needs regeneration')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='ascii')
    print('%d names / %d states scanned; %d names / %d states need flipbook checks; %d unassociated entries' % (
        data['checked_names'], data['checked_states'], data['candidate_names'], data['candidate_states'],
        len(data['flipbook_entries_without_block_association'])))


if __name__ == '__main__':
    main()
