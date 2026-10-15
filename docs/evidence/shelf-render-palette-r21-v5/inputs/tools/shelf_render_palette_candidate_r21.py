"""Narrow render-only shelf substitution; source document identities stay intact."""
SOURCE = ('minecraft:oak_shelf', 0)
PROXY = ('modern_projection:preview_shelf_oak_unpowered_south_context_r21', 0)


def replace_body_palette(source):
    if '_context_batches' in source:
        result = dict(source)
        result['_context_batches'] = [(origin, packed, replace_body_palette(palette))
                                      for origin, packed, palette in source['_context_batches']]
        return result
    selected = source.get('common', {}).get(SOURCE)
    if not selected:
        return source
    records = source.get('states', {})
    if SOURCE in records and records[SOURCE] != {}:
        record = records[SOURCE]
        keys = ('minecraft:cardinal_direction', 'powered_bit', 'powered_shelf_type')
        if not (isinstance(record, dict) and set(record) == set(keys) and
                record['minecraft:cardinal_direction'] == 'south' and
                record['powered_bit'] is False and
                type(record['powered_shelf_type']) is int and record['powered_shelf_type'] == 0):
            return source
    if PROXY in source['common']:
        raise ValueError('The shelf candidate proxy already exists in the input')
    result = dict(source)
    common = dict(source['common'])
    common[PROXY] = common.pop(SOURCE)
    result['common'] = common
    states = dict(source.get('states', {}))
    states.pop(SOURCE, None)
    result['states'] = states
    indices = frozenset(selected)
    actors = {}
    for name, rows in source.get('actor', {}).items():
        if name not in (SOURCE[0], SOURCE[0].encode('ascii')):
            actors[name] = rows
            continue
        kept = dict((index, payload) for index, payload in rows.items() if index not in indices)
        if kept:
            actors[name] = kept
    result['actor'] = actors
    return result
