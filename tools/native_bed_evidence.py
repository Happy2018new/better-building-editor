"""Validate complete paired-bed observations independently of palette actors."""
from projection import block_groups, block_registry as registry
from projection.cell import AIR, thaw
from projection.nbt_spatial import root_payload, scalar
from projection.world_capture import native_palette_layers

METHOD = 'Complete production-written bed pair, exact/padded native palettes, typed color; v1'
NAME = 'minecraft:bed'


def cases():
    return [{'aux': aux, 'wet': wet, 'color': 7}
            for aux in registry.aux_values(NAME) for wet in (False, True)]


def source_palette(tree):
    source = thaw(tree)
    if not isinstance(source, dict):
        raise ValueError('Paired-bed native palette is missing')
    return {(key.decode('utf8') if isinstance(key, bytes) else key): value
            for key, value in source.items()}


def expected_pair(origin, case):
    value = (NAME, case['aux'])
    delta, partner = block_groups.group_partner(value)
    pair = [(tuple(origin), value),
            (tuple(origin[i] + delta[i] for i in range(3)), partner)]
    return sorted(pair, key=lambda row: not registry.states(row[1])['head_piece_bit'])


def validate_actors(row, pair, case):
    actors = row['server']['actors']
    if len(actors) != 2:
        raise ValueError('Both native bed halves must have captured NBT')
    for observed, (pos, material) in zip(actors, pair):
        nbt = thaw(observed['nbt'])
        root = root_payload(nbt)
        coordinates = [scalar(root, axis) for axis in ('x', 'y', 'z')]
        identity = scalar(root, 'id')
        if isinstance(identity, bytes):
            identity = identity.decode('utf8')
        if (observed['pos'] != list(pos) or observed['coordinates'] != list(pos) or
                coordinates != list(pos) or observed['id'] != 'Bed' or identity != 'Bed' or
                observed['color'] != case['color'] or scalar(root, 'color') != case['color']):
            raise ValueError('Native bed NBT identity, position or color changed')


def validate_palette(source, pair, case, low, high):
    size = tuple(high[i] - low[i] + 1 for i in range(3))
    fronts, backs = native_palette_layers(source, size)
    indices = []
    for pos, material in pair:
        local = tuple(pos[i] - low[i] for i in range(3))
        indices.append((local[1] * size[0] + local[0]) * size[2] + local[2])
    head_index, foot_index = indices
    if fronts.get(head_index) != pair[0][1] or foot_index in fronts:
        raise ValueError('Native bed foreground omission differs from the observed pattern')
    water = ('minecraft:water', 0) if case['wet'] else AIR
    if backs.get(head_index, AIR) != water or foot_index in backs:
        raise ValueError('Native bed background differs from its wet/dry seed')
    entries = source.get('actor', {})
    if len(entries) != 1:
        raise ValueError('Native bed has unexpected actor buckets')
    bucket, payloads = next(iter(entries.items()))
    if isinstance(bucket, bytes):
        bucket = bucket.decode('utf8')
    if bucket != ('minecraft:water' if case['wet'] else NAME) or set(payloads) != {head_index}:
        raise ValueError('Native bed actor ownership or omission differs from observations')
    root = root_payload(payloads[head_index])
    if (scalar(root, 'color') != case['color'] or
            scalar(root, 'direction') != registry.states(pair[0][1])['direction']):
        raise ValueError('Native bed actor does not match the seeded color and direction')


def inspect(report, manifest):
    if (report.get('schema_version') != 1 or report.get('method') != METHOD or
            report.get('game_version') != manifest['game_version'] or
            report.get('palette_sha256', '').lower() != manifest['source_sha256'].lower() or
            not report.get('completed') or not report.get('restored') or report.get('error') or
            report.get('cleanup') != {'restored': True, 'residue': []}):
        raise ValueError('Incomplete, unrestored or mismatching paired-bed evidence')
    expected = cases()
    if report.get('cases') != expected or [row['case'] for row in report['rows']] != expected:
        raise ValueError('Paired-bed evidence must cover all native states, dry and wet')
    checked = 0
    for row, case in zip(report['rows'], expected):
        pair = expected_pair(report['origin'], case)
        water = ('minecraft:water', 0) if case['wet'] else AIR
        observed = [{'pos': list(pos), 'front': list(material), 'back': list(water)}
                    for pos, material in pair]
        if row.get('observed') != observed or row['server'].get('read_error') or row['client'].get('read_error'):
            raise ValueError('Paired-bed seed/readback changed or failed')
        low = tuple(min(pos[i] for pos, material in pair) for i in range(3))
        high = tuple(max(pos[i] for pos, material in pair) for i in range(3))
        if (row['low'] != list(low) or row['high'] != list(high) or
                row['padded_low'] != [value - 1 for value in low] or
                row['padded_high'] != [value + 1 for value in high]):
            raise ValueError('Native bed palette bounds differ from the complete pair')
        validate_actors(row, pair, case)
        for side in ('server', 'client'):
            for scope in ('exact', 'padded'):
                tree = row[side]['palettes'][scope]
                if side == 'server':
                    tree = tree['palette']
                bounds = (low, high) if scope == 'exact' else (row['padded_low'], row['padded_high'])
                validate_palette(source_palette(tree), pair, case, *bounds)
                checked += 1
    return [NAME], checked
