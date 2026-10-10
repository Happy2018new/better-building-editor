"""Compare a reference enum with explicit entity observations or native probes."""
import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = ROOT / 'docs/reference/block_entities/nemc_3.9_reference.json'


def scalar(value):
    if isinstance(value, dict) and '__value__' in value:
        return value['__value__']
    return value


def nbt_identifier(data):
    root = scalar(data)
    if not isinstance(root, dict):
        return None
    value = scalar(root.get('id'))
    return value if isinstance(value, str) and value else None


def observations(data):
    """Read only explicit entity names and root NBT IDs, never block labels."""
    if not isinstance(data, dict):
        raise ValueError('Observation JSON must be an object')
    supported = False
    records = []
    for key in ('entities', 'observations'):
        if key not in data:
            continue
        supported = True
        if not isinstance(data[key], list):
            raise ValueError('%s must be a list' % key)
        for row in data[key]:
            if not isinstance(row, dict) or not isinstance(row.get('name'), str) or not row['name']:
                raise ValueError('Explicit entity records require a nonempty name')
            enum_id = row.get('enum_id', row.get('id'))
            if enum_id is not None and (type(enum_id) is not int or enum_id < 0):
                raise ValueError('Explicit enum_id must be a nonnegative integer')
            records.append({'name': row['name'], 'enum_id': enum_id, 'source': key})
    if 'actors' in data:
        supported = True
        if not isinstance(data['actors'], list):
            raise ValueError('actors must be a list')
        for actor in data['actors']:
            if not isinstance(actor, dict):
                continue
            for cell in actor.get('cells', []):
                if not isinstance(cell, dict):
                    continue
                name = nbt_identifier(cell.get('nbt'))
                if name is not None:
                    records.append({'name': name, 'enum_id': None, 'source': 'actors.cells.nbt',
                                    'case': actor.get('name'), 'pos': cell.get('pos'),
                                    'block': cell.get('front')})
    if 'block_entities' in data:
        supported = True
        if not isinstance(data['block_entities'], dict):
            raise ValueError('block_entities must be an object')
        for block, row in sorted(data['block_entities'].items()):
            if not isinstance(row, dict):
                raise ValueError('Native default entity records must be objects')
            name = nbt_identifier(row.get('nbt'))
            if name is not None:
                records.append({'name': name, 'enum_id': None, 'source': 'block_entities.nbt',
                                'block': {'name': block, 'aux': row.get('aux')}})
    if not supported:
        raise ValueError('Expected entities, observations, native actors, or block_entities')
    return records


def compare(reference, observed):
    if reference.get('schema_version') != 1:
        raise ValueError('Unsupported reference schema version')
    expected = {}
    expected_ids = set()
    for row in reference.get('entities', []):
        name, enum_id = row.get('name'), row.get('id')
        if not isinstance(name, str) or not name or type(enum_id) is not int or enum_id < 0:
            raise ValueError('Invalid reference enum record')
        if name in expected or enum_id in expected_ids:
            raise ValueError('Reference enum names and numeric IDs must be unique')
        expected[name] = enum_id
        expected_ids.add(enum_id)
    grouped = {}
    for row in observations(observed):
        grouped.setdefault(row['name'], []).append(row)
    matches, conflicts, unknown = [], [], []
    for name in sorted(grouped):
        rows = grouped[name]
        observed_ids = sorted(set(row['enum_id'] for row in rows if row['enum_id'] is not None))
        item = {'name': name, 'observed_count': len(rows), 'observed_enum_ids': observed_ids,
                'examples': rows[:3]}
        if name not in expected:
            unknown.append(item)
            continue
        item['reference_enum_id'] = expected[name]
        item['numeric_id_verified_by_input'] = observed_ids == [expected[name]]
        if any(enum_id != expected[name] for enum_id in observed_ids):
            conflicts.append(item)
        else:
            matches.append(item)
    return {
        'schema_version': 1,
        'reference_source': reference.get('source'),
        'reference_version': reference.get('version'),
        'observed_version': observed.get('game_version'),
        'observed_palette_sha256': observed.get('palette_sha256'),
        'reference_entity_count': len(expected),
        'observed_entity_name_count': len(grouped),
        'matched_names': matches,
        'numeric_id_conflicts': conflicts,
        'unknown_observed_names': unknown,
        'reference_names_unobserved_in_sample': sorted(set(expected) - set(grouped)),
        'notes': [
            'Root NBT string IDs confirm observed names only, not numeric enum IDs.',
            'Unobserved names are not evidence of missing native support.',
            'Input provenance and native version must be verified independently.',
            'This audit never changes the reference or runtime block entity policy.'
        ]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument('--observed', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    reference_bytes = args.reference.read_bytes()
    observed_bytes = args.observed.read_bytes()
    report = compare(json.loads(reference_bytes.decode('utf-8-sig')),
                     json.loads(observed_bytes.decode('utf-8-sig')))
    report['inputs'] = {
        'reference': {'file': args.reference.name, 'sha256': hashlib.sha256(reference_bytes).hexdigest()},
        'observed': {'file': args.observed.name, 'sha256': hashlib.sha256(observed_bytes).hexdigest()}
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding='utf-8')
    else:
        print(encoded, end='')


if __name__ == '__main__':
    main()
