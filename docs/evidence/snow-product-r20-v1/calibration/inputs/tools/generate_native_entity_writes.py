"""Generate tile rebuild rules from restored native before/after observations."""
import argparse
import hashlib
import json
from pathlib import Path

from generate_entity_blueprints import snapshot_fingerprint

ROOT = Path(__file__).resolve().parents[1]
METHOD = 'Native pot layer-preserving tile replacement; four directions, dry/wet repeated palette and typed NBT; complete server NBT and client layers; v3'
TRANSITIONS = ('dry_to_dry', 'dry_to_wet', 'wet_to_dry', 'wet_to_wet')
CASES = tuple('direction_'+str(aux)+'_'+case for aux in range(4) for case in TRANSITIONS)
POT = 'minecraft:decorated_pot'
STAGES = {'dry': [['minecraft:air', 0], ['minecraft:air', 0]], 'wet': [['minecraft:oak_fence', 0]]}


def inspect_report(report, manifest, positive):
    if (report.get('schema_version') != 1 or report.get('method') != METHOD or
            report.get('game_version') != manifest['game_version'] or
            report.get('palette_sha256', '').lower() != manifest['source_sha256'].lower() or
            report.get('completed') is not True or report.get('restored') is not True or
            report.get('error') or report.get('cleanup_error') or
            report.get('cleanup', {}).get('restored') is not True or
            report.get('cleanup', {}).get('remaining') != []):
        raise ValueError('Native tile rewrite evidence is incomplete, unrestored or mismatching')
    source_hash = report.get('server_source_sha256', '')
    if len(source_hash) != 64 or any(value not in '0123456789abcdef' for value in source_hash):
        raise ValueError('Native tile rewrite source fingerprint is absent')
    if tuple(case['id'] for case in report['cases']) != CASES or report.get('pot_auxes') != [0,1,2,3]:
        raise ValueError('Native tile rewrite transition coverage changed')
    failures = 0
    for case in report['cases']:
        initial, final = case['id'].split('_', 2)[-1].split('_to_')
        aux = case['aux']
        if case['id'] != 'direction_'+str(aux)+'_'+initial+'_to_'+final:
            raise ValueError('Native tile rewrite direction identity changed')
        if len(case['writes']) != 3:
            raise ValueError('Native tile rewrite repeat coverage is incomplete')
        for stage, row in enumerate(case['writes']):
            wet = (initial if stage == 0 else final) == 'wet'
            item, count = ('minecraft:diamond', 11) if stage == 0 else ('minecraft:emerald', 23)
            if (row['stage'] != stage or row['wet'] != wet or row['expected_item'] != item or
                    row['expected_count'] != count or row['logical_unchanged'] is not True):
                raise ValueError('Native tile rewrite source identity changed')
            if not positive:
                if row['air_staging']:
                    raise ValueError('Negative evidence already uses tile rebuild')
                failures += row['passed'] is False
                continue
            expected_back = 'minecraft:water' if wet else 'minecraft:air'
            back = row['liquid'] or {'name': 'minecraft:air', 'aux': 0}
            client = row['replication']['last']
            extras = client['extra']
            if (row['passed'] is not True or row['returned'] is not True or
                    row['layer_match'] is not True or row['inventory_match'] is not True or
                    row['nbt_match'] is not True or row['surroundings_match'] is not True or
                    row['nbt'] != row['requested_world_nbt'] or
                    row['foreground'] != {'name': POT, 'aux': aux} or
                    back != {'name': expected_back, 'aux': 0} or
                    row['replication']['matched'] is not True or
                    client['pot_sherds'] != row['expected_sherds'] or
                    client['common'] != [{'material': [POT, aux], 'positions': [0]}] or
                    extras != ([{'material': ['minecraft:water', 0], 'positions': [0]}] if wet else [])):
                raise ValueError('Native tile rewrite has a failed NBT, layer or replication check')
            inventory = row['nbt']['item']
            if inventory['Name']['__value__'] != item or inventory['Count']['__value__'] != count:
                raise ValueError('Native tile rewrite inventory differs from its source')
            calls = row['air_staging']
            stages = STAGES['wet' if wet else 'dry']
            if len(calls) != len(stages) or any(
                    call['method'] != 'SetBlockNew' or
                    call['position'] != report['setup']['targets']['set_block'] or
                    call['block'] != {'name': material[0], 'aux': material[1]} or
                    call['arguments'] != [0, report['setup']['dimension'], True, False]
                    for call, material in zip(calls, stages)):
                raise ValueError('Native tile rebuild call sequence changed')
    if not positive and (not failures or report['passed'] is not False):
        raise ValueError('Negative native evidence does not demonstrate the original failure')
    if positive and report['passed'] is not True:
        raise ValueError('Native tile rewrite evidence does not pass')


def inspect(snapshot, manifest):
    if (snapshot.get('schema_version') != 1 or snapshot.get('game_version') != manifest['game_version'] or
            snapshot.get('palette_sha256', '').lower() != manifest['source_sha256'].lower()):
        raise ValueError('Native tile write source identity differs from the registry')
    if snapshot.get('rules') != {POT: STAGES} or snapshot.get('aux_values') != [0,1,2,3]:
        raise ValueError('Only the observed native pot layer-preserving rebuild is supported')
    for name in ('before', 'after'):
        raw = (json.dumps(snapshot[name], ensure_ascii=False, indent=2)+'\n').encode('utf8')
        fingerprints = {hashlib.sha256(raw).hexdigest(), hashlib.sha256(raw.replace(b'\n', b'\r\n')).hexdigest()}
        if snapshot.get('report_sha256', {}).get(name) not in fingerprints:
            raise ValueError('Native tile rewrite report fingerprint changed')
    inspect_report(snapshot['before'], manifest, False)
    inspect_report(snapshot['after'], manifest, True)
    return snapshot['rules']


def generate(check=False, root=ROOT):
    manifest = json.loads((root / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    version = manifest['game_version'].removeprefix('NEMC ')
    snapshot = json.loads((root / 'tools/data' / ('native_entity_writes_nemc_'+version+'.json')).read_bytes())
    rules = inspect(snapshot, manifest)
    lines = ['# Generated by tools/generate_native_entity_writes.py; do not edit.',
             'from __future__ import unicode_literals', 'SCHEMA_VERSION = 1',
             'SOURCE_VERSION = '+repr(manifest['game_version']),
             'PALETTE_SHA256 = '+repr(manifest['source_sha256'].lower()),
             'SOURCE_SHA256 = '+repr(snapshot_fingerprint(snapshot)),
             "SOURCE_HASH_FORMAT = 'canonical-json-v1'", 'PROBE_METHOD = '+repr(METHOD),
             'OBSERVED_AUX_VALUES = '+repr(tuple(snapshot['aux_values'])),
             'TILE_REBUILD_STAGES = '+repr(dict((name, dict((mode, tuple(tuple(material) for material in stages))
                                                               for mode, stages in modes.items()))
                                                for name, modes in rules.items()))]
    text = '\n'.join(lines)+'\n'
    output = root / 'behavior_pack/modern_projection/projection/native_entity_write_data.py'
    if check:
        if output.read_text(encoding='utf8') != text:
            raise ValueError('Native entity write rules need regeneration')
    else:
        output.write_text(text, encoding='ascii')
    print('Verified %d native tile rebuild rules from restored before/after evidence' % len(rules))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    generate(parser.parse_args().check)
