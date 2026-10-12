"""Generate static native traits from a versioned development metadata export."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


WATER_PROBE_METHOD = ('Native default seed + semantic states and supported head-first paired fixtures '
                      'before/after over water, isLegacy=True, updateNeighbors=False; v5')
SNOW_STATE_METHOD = 'supported native dry palette in verified cold biome then SetSnowBlock heights 1..8; v4'
PAIRED_SNOW_METHOD = 'complete supported tall-plant palette then SetSnowBlock bottom'


def _snow_evidence_rows(observations, paired, data, palette):
    for source, method in ((observations, SNOW_STATE_METHOD), (paired, PAIRED_SNOW_METHOD)):
        if (source.get('schema') != 1 or source.get('game_version') != data['game_version'] or
                source.get('palette_sha256', '').lower() != data['palette_sha256'].lower() or
                source.get('method') != method or not isinstance(source.get('rows'), list)):
            raise ValueError('Snow evidence is not a matching native probe export')
    if (observations.get('done') is not True or observations.get('restored') is not True or
            observations.get('running') is not False or observations.get('active') is not None or
            observations.get('failure') or observations.get('cleanup_failure') or
            observations.get('cleanup_residue') or not observations.get('biome_before') or
            observations.get('biome_after') != observations.get('biome_before')):
        raise ValueError('Native snow state observations are incomplete or unrestored')
    if (observations.get('biome_fixture') != 'minecraft:ice_plains' or
            observations.get('biome_measured') != 'ice_plains' or
            observations.get('delayed_seconds') != .25 or observations.get('supports') != {
                'default': 'minecraft:dirt', 'minecraft:brown_mushroom': 'minecraft:podzol',
                'minecraft:red_mushroom': 'minecraft:podzol'}):
        raise ValueError('Native snow state observations differ from the recorded probe context')
    states = dict(((row['name'], row['data']),
                   dict((state['name'], bool(state['value']) if state['type'] == 'byte' else state['value'])
                        for state in row['states'])) for row in palette['blocks'])
    heights, supported, unsupported = {}, {}, {}
    for row in observations['rows']:
        material, height = (row['name'], row['aux']), row['height']
        if (type(row['aux']) is not int or material not in states or type(height) is not int or
                not 1 <= height <= 8 or height in heights.get(material, ())):
            raise ValueError('Invalid or duplicate native snow state observation')
        dry = row['dry']
        if (row.get('set_snow') is not True or dry['front'] != list(material) or
                dry['states'] != states[material] or dry['back'] != ['minecraft:air', 0]):
            raise ValueError('Native snow dry readback differs from the recorded state')
        expected = {'covered_bit': True, 'height': height - 1}
        for phase in ('immediate', 'delayed'):
            value = row[phase]
            if (value['front'][0] != 'minecraft:snow_layer' or
                    states.get(tuple(value['front'])) != expected or value['states'] != expected or
                    value['back'] != list(material) or value['back_states'] != states[material]):
                raise ValueError('Native snow layered readback differs from the recorded state')
        heights.setdefault(material, set()).add(height)
    if (set(observations.get('names', ())) != set(name for name, aux in heights) or
            any(values != set(range(1, 9)) for values in heights.values())):
        raise ValueError('Native snow state observations lack declared names or heights')
    for name, aux in heights:
        supported.setdefault(name, set()).add(aux)
    seen = set()
    for row in paired['rows']:
        material = (row['name'], row['aux'])
        dry = row['dry']
        if (type(row['aux']) is not int or material not in states or material in seen or
                row.get('dry_verified') is not True or type(row.get('set_snow')) is not bool or
                type(row.get('paired')) is not bool or len(dry) != 2 or
                dry[0]['front'] != {'name': material[0], 'aux': material[1]}):
            raise ValueError('Invalid or duplicate native paired snow observation')
        seen.add(material)
        selected = dry if row['paired'] else dry[:1]
        for cell in selected:
            value = (cell['front']['name'], cell['front']['aux'])
            if (value not in states or cell['states'] != states[value] or
                    cell['layers'] != {'common': [[value[0], value[1], [0]]], 'extra': []}):
                raise ValueError('Native paired snow dry readback differs from the palette')
        if row['paired'] and (dry[1]['front']['name'] != material[0] or
                dry[0]['states'].get('upper_block_bit') is not False or
                dry[1]['states'] != dict(dry[0]['states'], upper_block_bit=True) or
                dry[1]['pos'] != [dry[0]['pos'][0], dry[0]['pos'][1] + 1, dry[0]['pos'][2]]):
            raise ValueError('Native paired snow fixture is not a complete lower/upper pair')
        if row['set_snow']:
            continue
        if not row['paired'] or row['snowy'] != dry or material in heights:
            raise ValueError('Native paired snow negative readback changed or conflicts')
        # Only the lower material received SetSnowBlock; the upper half was a fixture.
        unsupported.setdefault(material[0], set()).add(material[1])
    return (dict((name, sorted(values)) for name, values in supported.items()),
            dict((name, sorted(values)) for name, values in unsupported.items()))


def _water_rows(water, data, palette):
    if (water.get('schema') != 1 or water.get('game_version') != data['game_version'] or
            water.get('palette_sha256', '').lower() != data['palette_sha256'].lower() or
            water.get('method') != WATER_PROBE_METHOD or not isinstance(water.get('blocks'), dict)):
        raise ValueError('Water capabilities are not a matching native placement export')
    expected = {}
    for row in palette['blocks']:
        if row['name'].startswith('minecraft:'):
            expected.setdefault(row['name'], set()).add(row['data'])
    state_count = sum(len(values) for values in expected.values())
    if (set(water['blocks']) != set(expected) or
            water.get('tested_states') != state_count or water.get('total_states') != state_count or
            water.get('verified_states') != state_count):
        raise ValueError('Water capability export is incomplete')
    names, partial = [], {}
    for name, accepted in sorted(water['blocks'].items()):
        if accepted is True:
            names.append(name)
        elif accepted is False:
            continue
        elif (not isinstance(accepted, list) or
              any(type(aux) is not int for aux in accepted) or
              len(set(accepted)) != len(accepted) or not set(accepted).issubset(expected[name])):
            raise ValueError('Water capability export contains invalid state IDs: ' + name)
        elif set(accepted) == expected[name]:
            names.append(name)
        elif accepted:
            partial[name] = sorted(accepted)
    return names, partial


def generate(source, check=False, snow_source=None, water_source=None,
             snow_state_source=None, paired_snow_source=None):
    data = json.loads(source.read_text(encoding='utf8'))
    if data.get('schema') != 1 or not isinstance(data.get('blocks'), dict):
        raise ValueError('Unsupported native block metadata schema')
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    if (data['palette_sha256'].lower() != manifest['source_sha256'].lower() or
            data['game_version'] != manifest['game_version']):
        raise ValueError('Native traits and state palette refer to different game versions')
    names = sorted(name for name, row in data['blocks'].items()
                   if row.get('solid') is True)
    snow_source = snow_source or source.with_name(
        'native_snow_overlays_nemc_%s.json' % data['game_version'].split()[-1])
    snow = json.loads(snow_source.read_text(encoding='utf8'))
    if (snow.get('schema') != 1 or snow.get('game_version') != data['game_version'] or
            snow.get('palette_sha256') != data['palette_sha256']):
        raise ValueError('Snow capabilities and native traits refer to different versions')
    snow_names = sorted(name for name, accepted in snow['blocks'].items() if accepted is True)
    water_source = water_source or source.with_name(
        'native_water_overlays_nemc_%s.json' % data['game_version'].split()[-1])
    water = json.loads(water_source.read_text(encoding='utf8'))
    palette = json.loads((ROOT / manifest['source_file']).read_text(encoding='utf8'))
    water_names, water_aux = _water_rows(water, data, palette)
    snow_state_source = snow_state_source or source.with_name(
        'native_snow_states_nemc_%s.json' % data['game_version'].split()[-1])
    paired_snow_source = paired_snow_source or source.with_name(
        'native_paired_snow_nemc_%s.json' % data['game_version'].split()[-1])
    snow_supported, snow_unsupported = _snow_evidence_rows(
        json.loads(snow_state_source.read_text(encoding='utf8')),
        json.loads(paired_snow_source.read_text(encoding='utf8')), data, palette)
    lines = ['# Generated by tools/generate_block_traits.py; do not edit.',
             'from __future__ import unicode_literals',
             'SCHEMA_VERSION = 1',
             'SOURCE_VERSION = ' + repr(data['game_version']),
             'SOURCE_SHA256 = ' + repr(data['palette_sha256']),
             'SNOW_SOURCE_SHA256 = ' + repr(hashlib.sha256(snow_source.read_bytes()).hexdigest()),
             'SNOW_STATE_SOURCE_SHA256 = ' + repr(hashlib.sha256(snow_state_source.read_bytes()).hexdigest()),
             'PAIRED_SNOW_SOURCE_SHA256 = ' + repr(hashlib.sha256(paired_snow_source.read_bytes()).hexdigest()),
             'WATER_SOURCE_SHA256 = ' + repr(hashlib.sha256(water_source.read_bytes()).hexdigest()),
             'SOLID_BLOCKS = frozenset((']
    lines.extend('    ' + repr(name) + ',' for name in names)
    lines.extend(('))', 'SNOW_COVERABLE_BLOCKS = frozenset(('))
    lines.extend('    ' + repr(name) + ',' for name in snow_names)
    lines.append('))')
    for key, rows in (('SNOW_SUPPORTED_AUX', snow_supported), ('SNOW_UNSUPPORTED_AUX', snow_unsupported)):
        lines.append(key + ' = {')
        lines.extend('    %r: frozenset(%r),' % (name, tuple(values)) for name, values in sorted(rows.items()))
        lines.append('}')
    lines.extend(('WATERLOGGABLE_COMPLETE = True', 'WATERLOGGABLE_BLOCKS = frozenset(('))
    lines.extend('    ' + repr(name) + ',' for name in water_names)
    lines.extend(('))', 'WATERLOGGABLE_AUX = {'))
    lines.extend('    %r: frozenset(%r),' % (name, tuple(values))
                 for name, values in sorted(water_aux.items()))
    lines.extend(('}', ''))
    text = '\n'.join(lines)
    target = ROOT / 'behavior_pack/modern_projection/projection/block_traits_data.py'
    if check:
        if not target.exists() or target.read_text(encoding='utf8') != text:
            raise ValueError('Generated block traits are stale')
    else:
        target.write_text(text, encoding='utf8')
    print('%d native block definitions, %d solid names, %d snow-coverable names, '
          '%d waterloggable names and %d partial state sets' %
          (len(data['blocks']), len(names), len(snow_names), len(water_names), len(water_aux)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', type=Path,
                        default=ROOT / 'tools/data/native_block_metadata_nemc_3.9.0.401155.json')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--snow-source', type=Path)
    parser.add_argument('--water-source', type=Path)
    parser.add_argument('--snow-state-source', type=Path)
    parser.add_argument('--paired-snow-source', type=Path)
    args = parser.parse_args()
    generate(args.source, args.check, args.snow_source, args.water_source,
             args.snow_state_source, args.paired_snow_source)
