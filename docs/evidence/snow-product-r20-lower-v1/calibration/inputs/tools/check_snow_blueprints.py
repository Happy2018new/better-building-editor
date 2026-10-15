"""Reject public snow cases that drift from complete versioned native readbacks."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import background, foreground
from projection.debug_blueprints import build
from projection.debug_snow_blueprints import VISUAL_CASE


def check(snapshot, manifest):
    if (snapshot.get('game_version') != manifest['game_version'] or
            snapshot.get('palette_sha256', '').lower() != manifest['source_sha256'].lower() or
            not snapshot.get('done') or not snapshot.get('restored') or
            snapshot.get('failure') or snapshot.get('cleanup_failure')):
        raise ValueError('Snow observations are incomplete or belong to another registry')
    evidence = {}
    for row in snapshot['rows']:
        key = (row['name'], row['aux'], row['height'] - 1)
        if key in evidence:
            raise ValueError('Duplicate native snow observation: %r' % (key,))
        expected = {'covered_bit': True, 'height': key[2]}
        dry = row['dry']
        if (not row['set_snow'] or dry['front'] != list(key[:2]) or
                dry['states'] != registry.states(key[:2])):
            raise ValueError('Invalid native dry snow seed: %r' % (key,))
        for phase in ('immediate', 'delayed'):
            value = row[phase]
            if (value['front'][0] != 'minecraft:snow_layer' or value['states'] != expected or
                    value['back'] != list(key[:2]) or value['back_states'] != dry['states']):
                raise ValueError('Native snow readback differs: %r %s' % (key, phase))
        evidence[key] = row
    document = build(VISUAL_CASE['fixture'])
    actual, occupied = set(), set()
    for row in VISUAL_CASE['cells']:
        dry = document.get(row['standalone'])
        expected_aux = registry.aux_values('minecraft:' + row['plant'])
        if tuple(expected_aux) != (dry[1],):
            raise ValueError('Snow fixture needs new native plant states: ' + row['plant'])
        for height, position in row['covered']:
            if position in occupied or position == row['standalone']:
                raise ValueError('Snow fixture cells overlap')
            occupied.add(position)
            cell = document.get(position)
            front, back = foreground(cell), background(cell)
            key = (back[0], back[1], height)
            if back != dry or registry.states(front) != {'height': height, 'covered_bit': True}:
                raise ValueError('Public snow case differs from its dry control: %r' % (key,))
            actual.add(key)
    if actual != set(evidence):
        raise ValueError('Public snow cases do not cover the measured native states/heights')
    return {'plants': len(VISUAL_CASE['cells']), 'cases': len(actual),
            'fixture_schema': VISUAL_CASE['schema'], 'passed': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify without changing any assets')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    version = manifest['game_version'].removeprefix('NEMC ')
    path = ROOT / ('tools/data/native_snow_states_nemc_' + version + '.json')
    raw = path.read_bytes()
    result = check(json.loads(raw), manifest)
    result.update(game_version=manifest['game_version'], evidence=str(path.relative_to(ROOT)),
                  evidence_sha256=hashlib.sha256(raw).hexdigest(),
                  scope='Public blueprint data matches native readbacks; pixels are separately verified')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
