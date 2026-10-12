"""Generate static adjacency capabilities from versioned native observations."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHOD = 'Explicit legacy-state placement, updateNeighbors=True, native .12s timer readback'
GATE_ACTIONS = ('initial', 'one_wall', 'both_walls', 'erase_first', 'erase_both', 'wrong_axis')
MOSS_ACTIONS = tuple('extend_' + str(i) for i in range(1, 6)) + (
    'erase_tip', 'erase_middle', 'rejoin_middle')
CARPET_ACTIONS = ('initial', 'side_support', 'upper_support', 'upper_snapshot',
                  'erase_upper_support', 'erase_upper', 'erase_side')
CARPET_NAME = 'minecraft:pale_moss_carpet'
CARPET_SUPPORT_VALUES = (('minecraft:air', 0), ('minecraft:stone', 0))


def native_states(record):
    return {row['name']: bool(row['value']) if row['type'] == 'byte' else row['value']
            for row in record['states']}


def capabilities(data, palette, manifest):
    if (data.get('schema') != 1 or data.get('method') != METHOD
            or data.get('game_version') != manifest['game_version']
            or data.get('palette_sha256', '').lower() != manifest['source_sha256'].lower()
            or not data.get('completed') or not data.get('restored') or data.get('error')):
        raise ValueError('Incomplete, unrestored or mismatching static neighbor evidence')
    records = {(row['name'], row['data']): native_states(row) for row in palette['blocks']}
    gate_names = {name for (name, aux), states in records.items() if 'in_wall_bit' in states}
    groups, moss_names = defaultdict(list), set()
    rows = data.get('native', {}).get('rows', [])
    if len(rows) != 620 or data['native'].get('cases') != 102 or data['native'].get('case') != 102:
        raise ValueError('Incomplete native static neighbor matrix')
    for row in rows:
        metadata = row['metadata']
        groups[row['case']].append(row)
        for write in row['writes']:
            before = write['before']
            unchanged = (before['name'], before['aux']) == tuple(write['value'])
            if write['returned'] is not True and not unchanged:
                raise ValueError('A native neighbor write failed')
        cells = {tuple(cell['pos']): cell for cell in row['cells']}
        for cell in cells.values():
            pair = (cell['value']['name'], cell['value']['aux'])
            if pair not in records or records[pair] != cell['states']:
                raise ValueError('Native state is absent from the current palette: %r' % (pair,))
        if metadata['family'] == 'gate':
            cell = cells[(0, 2, 0)]
            states = cell['states']
            expected = row['action'] in ('one_wall', 'both_walls', 'erase_first')
            if (cell['value']['name'] != metadata['name']
                    or states['minecraft:cardinal_direction'] != metadata['direction']
                    or states['open_bit'] != metadata['open'] or states['in_wall_bit'] != expected):
                raise ValueError('Gate observations contradict the perpendicular-wall rule')
        elif metadata['family'] == 'hanging_moss':
            for pos, cell in cells.items():
                name = cell['value']['name']
                if name != 'minecraft:pale_hanging_moss':
                    continue
                below = cells.get((pos[0], pos[1] - 1, pos[2]))
                expected = below is None or below['value']['name'] != name
                if cell['states']['tip'] != expected:
                    raise ValueError('Hanging moss observations contradict the below-neighbor rule')
                moss_names.add(name)
        elif metadata['family'] == 'moss_carpet':
            center = cells.get((0, 2, 0))
            if center is None or center['value']['name'] != CARPET_NAME:
                raise ValueError('Native moss carpet lower snapshot is absent')
            connection = ('tall' if row['action'] == 'upper_snapshot' else
                          'none' if row['action'] in ('initial', 'erase_side') else 'short')
            expected = dict(('pale_moss_carpet_side_' + face,
                             connection if face == metadata['face'] else 'none')
                            for face in ('north', 'east', 'south', 'west'))
            expected['upper_block_bit'] = False
            if center['states'] != expected:
                raise ValueError('Native moss carpet observations contradict the observed side transitions')
            if row['action'] == 'upper_snapshot':
                upper = cells.get((0, 3, 0))
                expected = dict(expected, upper_block_bit=True)
                expected['pale_moss_carpet_side_' + metadata['face']] = 'short'
                if upper is None or upper['value']['name'] != CARPET_NAME or upper['states'] != expected:
                    raise ValueError('Native carpet upper snapshot differs from the observed short side')
            for write in row['writes']:
                value = tuple(write['value'])
                if value[0] != CARPET_NAME and value not in CARPET_SUPPORT_VALUES:
                    raise ValueError('Native carpet support differs from the declared observed states')
    gate_cases, moss_cases, carpet_faces = set(), set(), set()
    for group in groups.values():
        metadata = group[0]['metadata']
        if any(row['metadata'] != metadata for row in group):
            raise ValueError('Inconsistent native case metadata')
        actions = tuple(row['action'] for row in group)
        if metadata['family'] == 'gate':
            identity = (metadata['name'], metadata['direction'], metadata['open'])
            if actions != GATE_ACTIONS or identity in gate_cases:
                raise ValueError('Duplicate or incomplete gate action coverage')
            gate_cases.add(identity)
        elif metadata['family'] == 'hanging_moss':
            if actions != MOSS_ACTIONS or metadata['supplied_tip'] in moss_cases:
                raise ValueError('Duplicate or incomplete hanging moss action coverage')
            moss_cases.add(metadata['supplied_tip'])
        elif metadata['family'] == 'moss_carpet':
            if actions != CARPET_ACTIONS or metadata['face'] in carpet_faces:
                raise ValueError('Duplicate or incomplete moss carpet diagnostic coverage')
            carpet_faces.add(metadata['face'])
        else:
            raise ValueError('Unknown native static neighbor family')
    expected = {(name, direction, opened) for name in gate_names
                for direction in ('north', 'east', 'south', 'west') for opened in (False, True)}
    if (gate_cases != expected or moss_cases != {False, True}
            or carpet_faces != {'north', 'east', 'south', 'west'} or len(moss_names) != 1):
        raise ValueError('Native static neighbor family coverage does not match the palette')
    return sorted(gate_names), sorted(moss_names)


def generate(check=False, root=ROOT):
    manifest = json.loads((root / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    version = manifest['game_version'].split()[-1]
    source = root / 'tools/data' / ('native_static_neighbors_nemc_' + version + '.json')
    palette = json.loads((root / manifest['source_file']).read_text(encoding='utf8'))
    data = json.loads(source.read_text(encoding='utf8'))
    gates, moss = capabilities(data, palette, manifest)
    content = ('# -*- coding: utf-8 -*-\n'
               '"""Generated static capabilities; support deletion and growth are out of scope."""\n'
               'from __future__ import unicode_literals\n\n'
               'SCHEMA_VERSION = 1\nSOURCE_VERSION = %r\nPALETTE_SHA256 = %r\nEVIDENCE_SHA256 = %r\n'
               'SOURCE_METHOD = %r\nGATE_NAMES = %r\nHANGING_MOSS_NAMES = %r\n'
               'CARPET_NAME = %r\nCARPET_SUPPORT_VALUES = %r\n') % (
                   manifest['game_version'], manifest['source_sha256'].lower(),
                   hashlib.sha256(source.read_bytes()).hexdigest(), METHOD, tuple(gates), tuple(moss),
                   CARPET_NAME, CARPET_SUPPORT_VALUES)
    target = root / 'behavior_pack/modern_projection/projection/static_neighbor_data.py'
    if check:
        if not target.is_file() or target.read_text(encoding='utf8') != content:
            raise ValueError('Generated static neighbor capabilities are stale')
    else:
        target.write_text(content, encoding='utf8', newline='\n')
    return {'gates': len(gates), 'hanging_moss': len(moss), 'native_rows': len(data['native']['rows']),
            'scope': 'Static gate wall states, hanging moss tips, and observed stone/air lower carpet sides.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    print(json.dumps(generate(args.check), sort_keys=True))


if __name__ == '__main__':
    main()
