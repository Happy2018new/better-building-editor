"""Generate wet actor bucket rules from complete, restored native observations."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import entity_defaults
from projection.block_traits import is_waterloggable
from projection.cell import AIR, thaw
from projection.world_capture import native_palette_layers
from generate_entity_blueprints import snapshot_fingerprint

METHOD = 'native dual-layer palette and GetBlockEntityData; six adjacent supports; legal horizontal facing; no bucket corrections; v2'
SIDES = ('server_immediate', 'server_delayed', 'client_delayed')


def palette(tree):
    if tree is None:
        return None
    value = thaw(tree)
    if value is None:
        return None
    return {(key.decode('utf8') if isinstance(key, bytes) else key): item
            for key, item in value.items()}


def cases(names):
    result = [{'id': name + ('_wet' if wet else '_dry'),
               'cells': [[name, [0, 0, 0], wet]]}
              for name in names for wet in (False, True)]
    result.extend({'id': 'mixed_sign_pot_' + str(wet), 'cells': [
        ['minecraft:standing_sign', [0, 0, 0], True],
        ['minecraft:decorated_pot', [3, 0, 0], wet]]} for wet in (False, True))
    result.append({'id': 'mixed_wet_pot_dry_sign', 'cells': [
        ['minecraft:decorated_pot', [0, 0, 0], True],
        ['minecraft:standing_sign', [3, 0, 0], False]]})
    return result


def inspect(report, manifest):
    if (report.get('schema_version') != 1 or report.get('method') != METHOD or
            report.get('game_version') != manifest['game_version'] or
            report.get('palette_sha256', '').lower() != manifest['source_sha256'].lower() or
            not report.get('completed') or not report.get('restored') or report.get('error') or
            report.get('cleanup') != {'restored': True, 'residue': []}):
        raise ValueError('Incomplete, unrestored or mismatching native palette evidence')
    names = sorted(name for name in entity_defaults.source.DEFAULTS
                   if is_waterloggable(entity_defaults.material(name)))
    expected = cases(names)
    if report['names'] != names or report['cases'] != expected:
        raise ValueError('Native palette actor coverage differs from native templates')
    if [row['id'] for row in report['rows']] != [row['id'] for row in expected]:
        raise ValueError('Native palette cases are missing, reordered or duplicated')
    aliases, unusable = set(), []
    for case, row in zip(expected, report['rows']):
        if len(row['observed']) != len(case['cells']):
            raise ValueError('Native palette seed coverage is incomplete')
        if any(not observed['write_ok'] for observed in row['observed']):
            unusable.extend((row['id'], side, 'native single-cell write failed') for side in SIDES)
            continue
        failed_reads = [side for side in SIDES if row[side].get('read_error')]
        if failed_reads:
            unusable.extend((row['id'], side, 'native palette read failed') for side in failed_reads)
            continue
        size = tuple(row['high'][i] - row['low'][i] + 1 for i in range(3))
        seeds = {}
        for (name, local, wet), observed in zip(case['cells'], row['observed']):
            pos = [report['origin'][i] + local[i] for i in range(3)]
            if (observed['name'] != name or observed['pos'] != pos or
                    observed['local'] != local or observed['wet'] != wet):
                raise ValueError('Native palette seed identity changed')
            offset = tuple(pos[i] - row['low'][i] for i in range(3))
            index = (offset[1] * size[0] + offset[0]) * size[2] + offset[2]
            seeds[index] = (name, wet, observed)
        resolved = []
        prepared = {}
        missing = []
        for side in SIDES:
            source = palette(row[side]['palette'])
            if source is None:
                missing.append((row['id'], side, 'native palette omitted'))
                continue
            fronts, backs = native_palette_layers(source, size)
            if any(fronts.get(index, AIR)[0] != observed['front'][0] or
                   backs.get(index, AIR) != tuple(observed['back'])
                   for index, (name, wet, observed) in seeds.items()):
                missing.append((row['id'], side, 'native palette foreground omitted or changed'))
            prepared[side] = source, fronts, backs
        if missing:
            unusable.extend(missing)
            continue
        for side in SIDES:
            source, fronts, backs = prepared[side]
            seen, found = set(), set()
            for bucket, entries in source.get('actor', {}).items():
                name = bucket.decode('utf8') if isinstance(bucket, bytes) else bucket
                for index, payload in entries.items():
                    if type(index) is not int or not 0 <= index < size[0] * size[1] * size[2] or index in seen:
                        raise ValueError('Invalid or duplicated native actor index')
                    seen.add(index)
                    front, back = fronts.get(index, AIR), backs.get(index, AIR)
                    if not isinstance(payload, dict) or front == AIR:
                        raise ValueError('Native actor has no foreground or payload')
                    if name == front[0]:
                        continue
                    if name != 'minecraft:water' or back[0] != name or index not in seeds:
                        raise ValueError('Unexplained native actor bucket mismatch')
                    wanted, wet, observed = seeds[index]
                    if (not observed['write_ok'] or not wet or front[0] != wanted or
                            back != ('minecraft:water', 0)):
                        raise ValueError('Misnamed actor is not a verified wet seed')
                    found.add(wanted)
            for index, (name, wet, observed) in seeds.items():
                if not observed['write_ok']:
                    unusable.append((row['id'], side, 'native single-cell write failed'))
                    continue
                # Redstone daylight levels may change between immediate and
                # delayed reads; this rule concerns actor ownership, not ticks.
                if (fronts.get(index, AIR)[0] != observed['front'][0] or
                        backs.get(index, AIR) != tuple(observed['back'])):
                    raise ValueError('Native seed changed before palette readback: %r' %
                                     ((row['id'], side, index, observed['front'], observed['back'],
                                       fronts.get(index, AIR), backs.get(index, AIR)),))
            resolved.append(found)
        if resolved[0] != resolved[1] or resolved[0] != resolved[2]:
            raise ValueError('Native actor bucket mismatch differs by side or readback time')
        aliases.update(resolved[0])
    return sorted(aliases), sorted(set(unusable))


def generate(check=False, root=ROOT):
    manifest = json.loads((root / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    version = manifest['game_version'].removeprefix('NEMC ')
    path = root / 'tools/data' / ('native_palette_actors_nemc_' + version + '.json')
    raw = path.read_bytes()
    report = json.loads(raw)
    names, unusable = inspect(report, manifest)
    lines = ['# Generated by tools/generate_native_palette_adapter.py; do not edit.',
             'from __future__ import unicode_literals', 'SCHEMA_VERSION = 1',
             'SOURCE_VERSION = ' + repr(manifest['game_version']),
             'PALETTE_SHA256 = ' + repr(manifest['source_sha256'].lower()),
             'SOURCE_SHA256 = ' + repr(snapshot_fingerprint(report)),
             "SOURCE_HASH_FORMAT = 'canonical-json-v1'",
             'PROBE_METHOD = ' + repr(METHOD), 'WET_ACTOR_NAMES = frozenset((']
    lines.extend('    %r,' % name for name in names)
    lines.extend(['))', 'UNUSABLE_NATIVE_CASES = ('])
    lines.extend('    %r,' % (row,) for row in unusable)
    lines.append(')')
    text = '\n'.join(lines) + '\n'
    output = root / 'behavior_pack/modern_projection/projection/native_palette_actor_data.py'
    if check:
        if output.read_text(encoding='utf8') != text:
            raise ValueError('Native palette actor rules need regeneration')
    else:
        output.write_text(text, encoding='ascii')
    print('Verified %d wet actor names; %d explicit unusable observations' % (len(names), len(unusable)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    generate(args.check)
