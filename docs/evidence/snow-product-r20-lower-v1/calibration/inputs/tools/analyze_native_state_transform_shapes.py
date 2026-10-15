"""Replay native shape observations against independently transformed coordinates."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection import state_transform
from capture_native_state_transform_shapes import pair, rays, states_exact, write

OPERATIONS = ('rotate_y90', 'rotate_y180', 'rotate_y270', 'mirror_x', 'mirror_y', 'mirror_z')
COORDINATE_TOLERANCE = .00001


def vector(value, operation):
    x, y, z = value
    if operation == 'rotate_y90':
        return -z, y, x
    if operation == 'rotate_y180':
        return -x, y, -z
    if operation == 'rotate_y270':
        return z, y, -x
    if operation == 'mirror_x':
        return -x, y, z
    if operation == 'mirror_y':
        return x, -y, z
    if operation == 'mirror_z':
        return x, y, -z
    raise ValueError('Unknown coordinate operation: %s' % operation)


def rounded(value):
    return tuple(round(axis, 6) for axis in value)


def point(value, operation):
    return rounded(tuple(axis + .5 for axis in vector(tuple(axis - .5 for axis in value), operation)))


def box(value, pos):
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {'min', 'max'}:
        raise ValueError('Expected a native AABB: %r' % value)
    bounds = [value[key] for key in ('min', 'max')]
    if not all(isinstance(axes, (list, tuple)) and len(axes) == 3 and
               all(type(axis) in (int, float) and math.isfinite(axis) for axis in axes)
               for axes in bounds):
        raise ValueError('Malformed native AABB: %r' % value)
    if any(bounds[0][axis] > bounds[1][axis] for axis in range(3)):
        raise ValueError('Inverted native AABB: %r' % value)
    return tuple(rounded(tuple(bounds[bound][axis] - pos[axis] for axis in range(3)))
                 for bound in range(2))


def reflected_box(value, operation):
    if value is None:
        return None
    corners = [point(corner, operation) for corner in itertools.product(*zip(*value))]
    return (tuple(min(corner[axis] for corner in corners) for axis in range(3)),
            tuple(max(corner[axis] for corner in corners) for axis in range(3)))


def native_hit(value, pos):
    if value is None or value == []:
        return None
    if not isinstance(value, list) or len(value) != 1:
        raise ValueError('Non-through native ray must have at most one hit: %r' % value)
    hit = value[0]
    if not isinstance(hit, dict) or hit.get('type') != 'Block':
        raise ValueError('OnlyBlocks ray returned a non-block: %r' % hit)
    if tuple(hit.get('pos', ())) != tuple(pos):
        raise ValueError('Fixture ray hit an external block: %r' % hit)
    position = hit.get('hitPos')
    if not isinstance(position, (tuple, list)) or len(position) != 3 or not all(
            type(axis) in (int, float) and math.isfinite(axis) for axis in position):
        raise ValueError('Malformed native ray hit position: %r' % hit)
    return rounded(tuple(position[axis] - pos[axis] for axis in range(3)))


def shape(row, sampling):
    if len(row['rays']) != len(sampling):
        raise ValueError('Native ray sample count differs from the fixed plan')
    pos = tuple(row['pos'])
    return {'clip': box(row['clip'], pos), 'collision': box(row['collision'], pos),
            'rays': tuple(native_hit(value, pos) for value in row['rays'])}


def reflected_shape(source, sampling, operation):
    indices = {(tuple(ray['start']), tuple(ray['direction'])): index
               for index, ray in enumerate(sampling)}
    hits = [None] * len(sampling)
    for ray, hit in zip(sampling, source['rays']):
        key = (point(ray['start'], operation), rounded(vector(ray['direction'], operation)))
        if key not in indices:
            raise ValueError('Ray plan is not closed under coordinate transforms')
        hits[indices[key]] = point(hit, operation) if hit is not None else None
    return {'clip': reflected_box(source['clip'], operation),
            'collision': reflected_box(source['collision'], operation), 'rays': tuple(hits)}


def coordinates_equal(first, second):
    if first is None or second is None:
        return first is second
    if isinstance(first, (list, tuple)) and isinstance(second, (list, tuple)):
        return len(first) == len(second) and all(coordinates_equal(a, b) for a, b in zip(first, second))
    return (type(first) in (int, float) and type(second) in (int, float) and
            abs(first - second) <= COORDINATE_TOLERANCE)


def shapes_equal(first, second):
    return all(coordinates_equal(first[key], second[key]) for key in ('clip', 'collision', 'rays'))


def discrimination(rows, shapes):
    names = sorted({pair(row['value'])[0] for row in rows if not row['control']})
    result = []
    for name in names:
        selected = [row for row in rows if pair(row['value'])[0] == name]
        properties = selected[0]['states']
        minimum = (8 if 'weirdo_direction' in properties else
                   4 if 'door_hinge_bit' in properties else
                   6 if 'direction' in properties and 'upside_down_bit' in properties else None)
        representatives = []
        for row in selected:
            native = shapes[pair(row['value'])]
            if not any(shapes_equal(native, prior) for prior in representatives):
                representatives.append(native)
        distinct = len(representatives)
        result.append({'name': name, 'records': len(selected), 'distinct_native_shapes': distinct,
                       'minimum_discriminating_shapes': minimum,
                       'discriminating': minimum is not None and distinct >= minimum,
                       'limits': 'Symmetric native states can share shapes; textures and neighbor corners are not checked.'})
    return result


def verify_provenance(raw):
    instance = raw.get('instance', {})
    if (not isinstance(instance, dict) or
            any(type(instance.get(key)) is not int or instance[key] <= 0
            for key in ('game_pid', 'mcdk_pid')) or
            any(not isinstance(instance.get(key), str) or not instance[key].isdigit() or
                int(instance[key]) <= 0 for key in ('game_identity', 'mcdk_identity')) or
            any(not isinstance(instance.get(key), str) or not instance[key]
                for key in ('id', 'owner', 'project', 'mcp_url', 'game_executable')) or
            not isinstance(raw.get('session_file'), str) or not raw['session_file']):
        raise ValueError('Native schema 2 requires explicit owned process and session provenance')
    protection = raw.get('noactivation', {})
    if not isinstance(protection, dict) or not all(protection.get(key) is True for key in
                                                ('requested', 'background_safe', 'window_noactivate')):
        raise ValueError('Native schema 2 requires verified launch protection provenance')
    sources = raw.get('host_sources', {})
    if not isinstance(sources, dict):
        raise ValueError('Native schema 2 requires explicit source paths and SHA256 records')
    for record in [sources.get(key, {}) for key in ('probe', 'mcp_wrapper', 'session_loader')] + \
            [protection.get(key, {}) for key in ('mcdk', 'dll')]:
        digest = record.get('sha256') if isinstance(record, dict) else None
        if (not isinstance(record, dict) or not isinstance(record.get('path'), str) or not record['path'] or
                not isinstance(digest, str) or len(digest) != 64 or
                any(character not in '0123456789abcdef' for character in digest)):
            raise ValueError('Native schema 2 requires explicit source paths and SHA256 records')
    if (sources['probe']['sha256'] != raw.get('probe_source_sha256') or
            raw.get('mutation_attempted') is not True):
        raise ValueError('Native schema 2 probe or mutation provenance is inconsistent')


def verify_capture(raw):
    if type(raw.get('schema')) is not int or raw['schema'] not in (1, 2) or \
            not raw.get('completed') or not raw.get('restored') or raw.get('error'):
        raise ValueError('Native capture must be complete and restored without capture errors')
    if raw['schema'] == 2:
        verify_provenance(raw)
    if not raw.get('cleanup', {}).get('restored') or raw.get('cleanup_error'):
        raise ValueError('Native capture cleanup was not verified')
    reserved = {tuple(pos) for pos in raw['setup']['reserved']}
    cleaned = raw['client_air_after_cleanup']
    if (len(reserved) != len(raw['setup']['reserved']) or len(cleaned) != len(reserved) or
            {tuple(row['pos']) for row in cleaned} != reserved or
            any(pair(row['value']) != ('minecraft:air', 0) for row in cleaned)):
        raise ValueError('Native client cleanup was not verified for every reserved cell')
    if raw.get('game_version') != registry.source_version() or raw.get('palette_sha256') != registry.fingerprint():
        raise ValueError('Native capture provenance differs from the current palette')
    if raw.get('rays') != rays():
        raise ValueError('Native capture did not use the fixed symmetric ray plan')
    requested = raw['requested']
    positions = {tuple(row['pos']): row for row in requested}
    if len(positions) != len(requested):
        raise ValueError('Duplicate requested native positions')
    expected_values = [tuple(row['value']) for row in requested if not row['control']]
    if len(set(expected_values)) != len(expected_values):
        raise ValueError('Duplicate requested native records')
    complete = {(name, aux) for name in raw['names'] for aux in registry.aux_values(name)}
    if set(expected_values) != complete:
        raise ValueError('Capture does not cover every record of its selected names')
    reference = None
    runtime = raw['preflight']['runtime']
    for key in ('server_first', 'client_first', 'server_later', 'client_later'):
        snapshot = raw[key]
        observed = {tuple(row['pos']): row for row in snapshot['rows']}
        if len(observed) != len(snapshot['rows']) or set(observed) != set(positions):
            raise ValueError('Native positions differ in %s' % key)
        if snapshot['runtime'] != runtime:
            raise ValueError('Native runtime differs in %s' % key)
        current = {}
        for pos, expected in positions.items():
            row = observed[pos]
            value = tuple(expected['value'])
            if pair(row['value']) != value or not states_exact(row['states'], registry.states(value)):
                raise ValueError('Native typed states differ in %s at %r' % (key, pos))
            current[value] = shape(row, raw['rays'])
        if reference is not None and not all(shapes_equal(current[value], reference[value]) for value in current):
            raise ValueError('Native shapes changed across side/time in %s' % key)
        reference = current
    stone, air = reference[('minecraft:stone', 0)], reference[('minecraft:air', 0)]
    unit = ((0., 0., 0.), (1., 1., 1.))
    if (not coordinates_equal(stone['clip'], unit) or not coordinates_equal(stone['collision'], unit) or
            any(hit is None for hit in stone['rays'])):
        raise ValueError('Native unit stone control failed')
    if any(hit is not None for hit in air['rays']):
        raise ValueError('Native air ray control failed')
    return reference


def analyze(raw, target_selector=state_transform.transform):
    shapes = verify_capture(raw)
    mismatches = []
    checks = 0
    for row in raw['requested']:
        if row['control']:
            continue
        source = tuple(row['value'])
        for operation in OPERATIONS:
            target = target_selector(source, operation)
            if target not in shapes:
                raise ValueError('Native target was not captured: %r' % (target,))
            expected = reflected_shape(shapes[source], raw['rays'], operation)
            actual = shapes[target]
            different = [key for key in ('clip', 'collision', 'rays')
                         if not coordinates_equal(expected[key], actual[key])]
            if different:
                mismatches.append({'source': source, 'source_states': row['states'], 'operation': operation,
                                   'target': target, 'target_states': registry.states(target),
                                   'different': different, 'expected': expected, 'actual': actual})
            checks += 1
    coverage = discrimination(raw['requested'], shapes)
    return {'schema': 1, 'capture_schema': raw['schema'], 'completed': True, 'restored': True, 'checks': checks,
            'coordinate_tolerance': COORDINATE_TOLERANCE,
            'mismatches': mismatches, 'discrimination': coverage,
            'native_shape_consistency': not mismatches,
            'physical_orientation_accepted': not mismatches and all(row['discriminating'] for row in coverage),
            'limits': 'Native clip/collision and fixed rays only; no texture, renderer or neighbor-corner acceptance.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.source.resolve() == args.output.resolve():
        parser.error('Replay output must be fresh and differ from the native source')
    raw_bytes = args.source.read_bytes()
    report = analyze(json.loads(raw_bytes))
    report.update(source={'path': str(args.source.resolve()), 'sha256': hashlib.sha256(raw_bytes).hexdigest()},
                  analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  candidate_transform_sha256=hashlib.sha256(Path(state_transform.__file__).read_bytes()).hexdigest())
    write(args.output, report)
    print(json.dumps({key: report[key] for key in ('completed', 'checks', 'native_shape_consistency',
                                                 'physical_orientation_accepted', 'discrimination')}))
    return 0 if report['native_shape_consistency'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
