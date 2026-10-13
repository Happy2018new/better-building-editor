"""Derive support only from restored true-state semantic placement segments.

Actual legacy aux values may differ from dump indices. Typed state equality,
both-layer cleanup and unchanged support across all phases establish identity.
Failed conversions, missing states and changed snapshots remain unknown.
"""
from collections import defaultdict

import probe_scaffold_state_lifecycle as common
import probe_scaffold_runtime_catalogue as probe
from scaffold_native_palette_readback import valid as valid_air_palette

ACCEPTANCE = {'editor': 'pending', 'full': 'pending', 'missing': 'pending'}


def _same_support(actual, pair, states):
    front = actual.get('front') if isinstance(actual, dict) else None
    return (isinstance(front, dict) and front.get('name') == pair[0] and type(front.get('aux')) is int
            and isinstance(actual.get('states'), dict)
            and common.state_key(actual['states']) == common.state_key(states))


def _typed_key(value):
    if isinstance(value, dict):
        return ('dict', tuple(sorted((key, _typed_key(item)) for key, item in value.items())))
    if isinstance(value, (tuple, list)):
        return (type(value).__name__, tuple(_typed_key(item) for item in value))
    return (type(value).__name__, value)


def _same_layers(actual, previous):
    if (not isinstance(actual, dict) or not isinstance(previous, dict)
            or not isinstance(actual.get('palette'), dict) or 'liquid' not in actual
            or not isinstance(previous.get('palette'), dict) or 'liquid' not in previous):
        return False
    return (_typed_key(actual['palette']) == _typed_key(previous['palette'])
            and _typed_key(actual['liquid']) == _typed_key(previous['liquid']))


def classify(row, air_encoding):
    """A changed or unavailable measurement is not an unsupported block."""
    pair, expected = row['requested'], row['expected_states']
    if (row.get('conversion_failed') or type(row.get('converted_aux')) is not int or row['converted_aux'] < 0
            or not isinstance(row.get('conversion_states'), dict)
            or common.state_key(row['conversion_states']) != common.state_key(expected)
            or type(row.get('semantic_set_returned')) is not bool
            or not _same_support(row.get('support_written'), pair, expected)):
        return None
    immediate, delayed = row.get('scaffold_written', {}), row.get('delayed', {})
    if (not _same_support(immediate.get('support'), pair, expected)
            or not _same_support(delayed.get('support'), pair, expected)
            or not _same_layers(immediate.get('support'), row.get('support_written'))
            or not _same_layers(delayed.get('support'), row.get('support_written'))):
        return None
    # Overwriting a pre-existing door half does not measure an isolated support.
    upper = row.get('upper_before_scaffold', {})
    if (upper.get('front') != {'name': 'minecraft:air', 'aux': 0}
            or type(upper.get('front', {}).get('aux')) is not int
            or upper.get('liquid') is not None or not valid_air_palette(upper.get('palette'), air_encoding)):
        return None
    scaffold = delayed.get('scaffold', {})
    front, states = scaffold.get('front'), scaffold.get('states')
    if (not isinstance(front, dict) or front.get('name') != 'minecraft:scaffolding'
            or type(front.get('aux')) is not int or not isinstance(states, dict)
            or type(states.get('stability')) is not int or states['stability'] not in (0, 7)
            or common.registry.from_states('minecraft:scaffolding', states) is None):
        return None
    return states['stability'] == 0


def _resets(reset, expected, air):
    if (not isinstance(reset, dict) or {tuple(row.get('pos', ())) for row in reset.get('returns', [])} != expected
            or len(reset.get('returns', [])) != len(expected)
            or any(type(row.get('returned')) is not bool for row in reset.get('returns', []))
            or {tuple(row.get('pos', ())) for row in reset.get('readbacks', [])} != expected
            or len(reset.get('readbacks', [])) != len(expected)):
        raise ValueError('Runtime segment reset observations are incomplete')
    for row in reset['readbacks']:
        if (row.get('front') != {'name': 'minecraft:air', 'aux': 0} or type(row['front'].get('aux')) is not int
                or row.get('states') not in (None, {}) or row.get('liquid') is not None
                or not valid_air_palette(row.get('palette'), air)):
            raise ValueError('Runtime segment reset did not prove both layers dry')


def validate_segment(report, source_sha256=None):
    native, start, cleanup = report.get('native', {}), report.get('start', {}), report.get('cleanup', {})
    if (report.get('schema') != probe.SCHEMA or report.get('method') != probe.METHOD
            or report.get('game_version') != common.registry.SOURCE_VERSION
            or report.get('palette_sha256') != common.registry.SOURCE_SHA256
            or report.get('completed') is not True or report.get('restored') is not True
            or native.get('done') is not True or native.get('timer_pending') is not False or native.get('error')
            or report.get('error') or report.get('cleanup_error') or report.get('acceptance') != ACCEPTANCE
            or cleanup.get('restored') is not True or cleanup.get('rules_restored') is not True
            or cleanup.get('flow_restored') is not True or cleanup.get('errors') != []
            or cleanup.get('remaining') != [] or cleanup.get('rules_actual') is not start.get('original_tile_drops')
            or start.get('runtime') != common.RUNTIME or start.get('fresh_owned_flow_allowed') is not True
            or start.get('source_sha256') != report.get('source_sha256')
            or source_sha256 is not None and report.get('source_sha256') != source_sha256):
        raise ValueError('Runtime support segment is incomplete or has mismatching provenance')
    bounds = report.get('range', [])
    if len(bounds) != 2 or any(type(value) is not int for value in bounds):
        raise ValueError('Runtime support range is missing')
    selected = probe.plans(bounds[0], bounds[1] - bounds[0])
    recorded = report.get('plans', [])
    if (len(recorded) != len(selected) or start.get('range') != bounds or native.get('index') != len(selected)
            or any(row.get('index') != plan['index'] or row.get('requested') != plan['requested']
                   or common.state_key(row.get('expected_states')) != common.state_key(plan['expected_states'])
                   for row, plan in zip(recorded, selected))):
        raise ValueError('Runtime support requested range differs')
    identity, source, air = report.get('identity', {}), report.get('source_sha256'), report.get('air_encoding', {})
    if (not isinstance(source, str) or len(source) != 64 or any(c not in '0123456789abcdef' for c in source)
            or not all(identity.get(key) for key in ('session_id', 'owner', 'game_pid', 'game_identity', 'run_id'))
            or start.get('identity') != identity or start.get('game_version') != common.registry.SOURCE_VERSION
            or start.get('palette_sha256') != common.registry.SOURCE_SHA256):
        raise ValueError('Runtime support source or exact owner identity missing')
    hashes = {name: common.digest(code.encode('utf8')) for name, code in (
        ('start', probe.start_payload(bounds[0], bounds[1] - bounds[0], identity, source, True, air)),
        ('status', probe.STATUS % (probe.MARKER, identity)), ('restore', probe.restore_payload(identity)))}
    if report.get('payload_sha256') != hashes:
        raise ValueError('Runtime support payload closure differs')
    rows = native.get('rows', [])
    if len(rows) != len(selected):
        raise ValueError('Runtime support observations are missing')
    for row, plan in zip(rows, selected):
        if (row.get('index') != plan['index'] or row.get('requested') != plan['requested']
                or common.state_key(row.get('expected_states')) != common.state_key(plan['expected_states'])):
            raise ValueError('Runtime support observations were reordered or retyped')
    slots = start.get('slots', [])
    if len(slots) != probe.SLOTS or any(len(pos) != 3 or any(type(axis) is not int for axis in pos) for pos in slots):
        raise ValueError('Runtime support slots differ')
    expected = {tuple(pos[i] + offset[i] for i in range(3)) for pos in slots for offset in common.OFFSETS}
    if start.get('reserved') != len(expected) or len(native.get('batches', [])) != (len(selected) + probe.SLOTS - 1) // probe.SLOTS:
        raise ValueError('Runtime support reserve or batch count differs')
    for index, batch in enumerate(native['batches']):
        if batch.get('start') != index * probe.SLOTS or len(batch.get('rows', [])) != min(probe.SLOTS, len(selected) - index * probe.SLOTS):
            raise ValueError('Runtime support batch order differs')
        _resets(batch.get('reset'), expected, air)
        _resets(batch.get('after'), expected, air)
    _resets({'returns': cleanup.get('air_reset_returns'), 'readbacks': cleanup.get('air_readbacks')}, expected, air)
    return rows


def capabilities(reports, require_full=False):
    """Strictly union sources; a partial catalogue cannot claim full coverage."""
    states = probe.dump_states()
    observed, sources = {}, set()
    for report in reports:
        sources.add(report.get('source_sha256'))
        for row in validate_segment(report):
            pair = tuple(row['requested'])
            if pair in observed:
                raise ValueError('Overlapping semantic support segment')
            observed[pair] = classify(row, report['air_encoding'])
    if len(sources) != 1:
        raise ValueError('Semantic support segments used different sources')
    if require_full and set(observed) != set(states):
        raise ValueError('Semantic support catalogue does not cover every dumped state')
    buckets = {'supporting': defaultdict(list), 'nonsupporting': defaultdict(list), 'unknown': defaultdict(list)}
    for (name, aux), capability in sorted(observed.items()):
        key = 'unknown' if capability is None else 'supporting' if capability else 'nonsupporting'
        buckets[key][name].append(aux)
    return {'schema': 2, 'source_method': probe.FULL_METHOD if require_full else probe.METHOD,
            'observed_states': len(observed), 'unobserved_states': len(states) - len(observed),
            'scope': 'full_catalogue' if require_full else 'measured_samples',
            'supporting': dict(buckets['supporting']), 'nonsupporting': dict(buckets['nonsupporting']),
            'unknown': dict(buckets['unknown']), 'acceptance': ACCEPTANCE}
