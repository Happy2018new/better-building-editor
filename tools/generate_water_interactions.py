"""Generate automatic editing rules from bounded native item-use observations."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHOD = 'UseItemToPos on basin support; no post-use SetBlockStates; v2'


def state_key(properties):
    return tuple(sorted((key, type(value).__name__, value) for key, value in properties.items()))


def native_states(record):
    return {row['name']: bool(row['value']) if row['type'] == 'byte' else row['value']
            for row in record['states']}


def load_observations(path, manifest, profile):
    data = json.loads(path.read_text(encoding='utf8'))
    if (data.get('schema') != 1 or data.get('method') != METHOD or data.get('profile') != profile
            or data.get('game_version') != manifest['game_version']
            or data.get('palette_sha256', '').lower() != manifest['source_sha256'].lower()
            or not data.get('done') or data.get('running') or data.get('failure')
            or not data.get('restored') or data.get('cleanup_residue') or data.get('cleanup_failure')):
        raise ValueError('Incomplete, unrestored or mismatching water evidence: ' + str(path))
    return data


def validated_seed(row, records):
    pair = (row['name'], row['aux'])
    if (pair not in records or row['action'] != 'add_source' or not row['dry_valid']
            or row['expected_seed'] != records[pair]
            or row['before']['states'] != records[pair]
            or row['before']['front']['name'] != pair[0]
            or not row.get('item_result') or row['item_result']['newItemName'] != 'minecraft:bucket'):
        raise ValueError('Water observation has an invalid dry seed: %r' % (pair,))
    liquid = row['delayed']['liquid']
    if not liquid or liquid['name'] not in ('minecraft:water', 'minecraft:flowing_water') or liquid['aux'] != 0:
        raise ValueError('Water observation did not retain a source: %r' % (pair,))
    return pair


def rules(palette, water, extinguish, stability):
    records = {(row['name'], row['data']): native_states(row) for row in palette['blocks']}
    reverse = {(name, state_key(properties)): aux for (name, aux), properties in records.items()}
    expected = set()
    for pair, properties in records.items():
        accepted = water['blocks'].get(pair[0])
        if ('lit' in properties or 'extinguished' in properties) and (
                accepted is True or isinstance(accepted, list) and pair[1] in accepted):
            expected.add(pair)
    changes, observed = {}, set()
    for row in extinguish['rows']:
        pair = validated_seed(row, records)
        if pair in observed or row['delayed']['front']['name'] != pair[0]:
            raise ValueError('Duplicate or destroyed extinguish seed: %r' % (pair,))
        observed.add(pair)
        result = reverse.get((pair[0], state_key(row['delayed']['states'])))
        if result is None:
            raise ValueError('Observed water state is absent from the native palette')
        if result != pair[1]:
            changes[pair] = result
    if observed != expected:
        raise ValueError('Water-sensitive state coverage is incomplete or has extra states')
    grouped = {}
    for row in stability['rows']:
        pair = validated_seed(row, records)
        names = grouped.setdefault(pair[0], {})
        if pair[1] in names:
            raise ValueError('Duplicate source stability seed: %r' % (pair,))
        after = row['delayed']['front']['name']
        if after not in (pair[0], 'minecraft:water', 'minecraft:flowing_water'):
            raise ValueError('Unsupported source stability outcome: ' + after)
        names[pair[1]] = after != pair[0]
    destroyed = []
    for name, outcomes in sorted(grouped.items()):
        if set(outcomes) != {aux for block, aux in records if block == name}:
            raise ValueError('Incomplete source stability family: ' + name)
        # Mixed outcomes, such as cactus, remain diagnostic evidence. A timed
        # readback is not enough to establish their eventual tick behaviour.
        if all(outcomes.values()):
            destroyed.append(name)
    return changes, sorted({name for name, aux in observed}), destroyed, len(observed)


def generate(check=False, root=ROOT):
    manifest = json.loads((root / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    version = manifest['game_version'].split()[-1]
    base = root / 'tools/data'
    paths = {key: base / ('native_water_' + key + '_nemc_' + version + '.json')
             for key in ('extinguish', 'source_stability')}
    extinguish = load_observations(paths['extinguish'], manifest, 'extinguish_states')
    stability = load_observations(paths['source_stability'], manifest, 'source_stability_states')
    palette = json.loads((root / manifest['source_file']).read_text(encoding='utf8'))
    water = json.loads((base / ('native_water_overlays_nemc_' + version + '.json')).read_text(encoding='utf8'))
    if (water.get('game_version') != manifest['game_version']
            or water.get('palette_sha256', '').lower() != manifest['source_sha256'].lower()):
        raise ValueError('Static water observations do not match the native palette')
    changes, names, destroyed, count = rules(palette, water, extinguish, stability)
    lines = ['# Generated by tools/generate_water_interactions.py; do not edit.',
             'from __future__ import unicode_literals', 'SCHEMA_VERSION = 1',
             'SOURCE_VERSION = ' + repr(manifest['game_version']),
             'PALETTE_SHA256 = ' + repr(manifest['source_sha256'].lower())]
    for key, path in sorted(paths.items()):
        lines.append(key.upper() + '_SOURCE_SHA256 = ' + repr(hashlib.sha256(path.read_bytes()).hexdigest()))
    lines.extend(['VERIFIED_SOURCE_STATES = %d' % count, 'SOURCE_STATE_CHANGES = {'])
    lines.extend('    %r: %r,' % (pair, result) for pair, result in sorted(changes.items()))
    lines.extend(['}', 'WATER_SENSITIVE_BLOCKS = frozenset(('])
    lines.extend('    %r,' % name for name in names)
    lines.extend(['))', 'SOURCE_DESTROYED_BLOCKS = frozenset(('])
    lines.extend('    %r,' % name for name in destroyed)
    lines.extend(['))', ''])
    content = '\n'.join(lines)
    target = root / 'behavior_pack/modern_projection/projection/water_interaction_data.py'
    if check:
        if not target.exists() or target.read_text(encoding='utf8') != content:
            raise ValueError('Generated water interaction rules are stale')
    else:
        target.write_text(content, encoding='utf8')
    print('%d native states, %d source transitions, %d destroyed source families' %
          (count, len(changes), len(destroyed)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    generate(parser.parse_args().check)
