"""Check generated registry provenance and audit transforms for every native state."""
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))

from generate_block_registry import generate
from projection import block_registry as registry
from projection import state_transform


# Independent world-space fixtures: +X east, +Y up, +Z south. These do not use
# the transformer's direction arrays or aux arithmetic.
FACE_VECTORS = {'east': (1, 0, 0), 'west': (-1, 0, 0),
                'up': (0, 1, 0), 'down': (0, -1, 0),
                'south': (0, 0, 1), 'north': (0, 0, -1)}
NUMERIC_FACES = {
    'facing_direction': {0: 'down', 1: 'up', 2: 'north', 3: 'south', 4: 'west', 5: 'east'},
    'weirdo_direction': {0: 'east', 1: 'west', 2: 'south', 3: 'north'},
    'direction': {0: 'south', 1: 'west', 2: 'north', 3: 'east'},
    'coral_direction': {0: 'west', 1: 'east', 2: 'north', 3: 'south'},
}
BIT_FACES = {'vine_direction_bits': {1: 'south', 2: 'west', 4: 'north', 8: 'east'},
             'multi_face_direction_bits': {1: 'down', 2: 'up', 4: 'south',
                                           8: 'west', 16: 'north', 32: 'east'}}
RAIL_POINTS = {
    0: {(0, 0, -1), (0, 0, 1)}, 1: {(-1, 0, 0), (1, 0, 0)},
    2: {(-1, -1, 0), (1, 1, 0)}, 3: {(-1, 1, 0), (1, -1, 0)},
    4: {(0, 1, -1), (0, -1, 1)}, 5: {(0, -1, -1), (0, 1, 1)},
    6: {(0, 0, 1), (1, 0, 0)}, 7: {(0, 0, 1), (-1, 0, 0)},
    8: {(0, 0, -1), (-1, 0, 0)}, 9: {(0, 0, -1), (1, 0, 0)},
}
MUSHROOM_FACES = {1: ('north', 'west'), 2: ('north',), 3: ('north', 'east'),
                  4: ('west',), 5: (), 6: ('east',), 7: ('south', 'west'),
                  8: ('south',), 9: ('south', 'east')}
INVERSES = {'rotate_y90': 'rotate_y270', 'rotate_y180': 'rotate_y180',
            'rotate_y270': 'rotate_y90', 'mirror_x': 'mirror_x',
            'mirror_y': 'mirror_y', 'mirror_z': 'mirror_z'}


def reflect_point(point, operation):
    x, y, z = point
    if operation == 'rotate_y90':
        return (-z, y, x)
    if operation == 'rotate_y180':
        return (-x, y, -z)
    if operation == 'rotate_y270':
        return (z, y, -x)
    if operation == 'mirror_x':
        return (-x, y, z)
    if operation == 'mirror_y':
        return (x, -y, z)
    return (x, y, -z)


def _geometry(properties):
    result = {}
    for key, faces in NUMERIC_FACES.items():
        if key not in properties:
            continue
        if key == 'direction' and 'upside_down_bit' in properties:
            faces = NUMERIC_FACES['weirdo_direction']
        result[key] = {FACE_VECTORS[faces[properties[key]]]}
    for key in ('minecraft:cardinal_direction', 'minecraft:facing_direction', 'minecraft:block_face'):
        if key in properties:
            result[key] = {FACE_VECTORS[properties[key]]}
    for key, bits in BIT_FACES.items():
        if key in properties:
            result[key] = {FACE_VECTORS[face] for bit, face in bits.items() if properties[key] & bit}
    for key in ('pillar_axis', 'portal_axis'):
        axis = properties.get(key)
        if axis in ('x', 'y', 'z'):
            face = {'x': 'east', 'y': 'up', 'z': 'south'}[axis]
            vector = FACE_VECTORS[face]
            result[key] = {vector, tuple(-coordinate for coordinate in vector)}
    if 'ground_sign_direction' in properties:
        angle = properties['ground_sign_direction'] * math.pi / 8
        result['ground_sign_direction'] = {(round(-math.sin(angle), 6), 0, round(math.cos(angle), 6))}
    torch_face = properties.get('torch_facing_direction')
    if torch_face in ('north', 'south', 'east', 'west'):
        result['torch_facing_direction'] = {FACE_VECTORS[torch_face]}
    lever = properties.get('lever_direction')
    if lever in FACE_VECTORS:
        result['lever_direction'] = {FACE_VECTORS[lever]}
    elif lever:
        face, axis = lever.split('_', 1)
        result['lever_attachment'] = {FACE_VECTORS[face]}
        axis_face = 'east' if axis == 'east_west' else 'north'
        vector = FACE_VECTORS[axis_face]
        result['lever_axis'] = {vector, tuple(-coordinate for coordinate in vector)}
    if 'orientation' in properties:
        primary, secondary = properties['orientation'].split('_')
        result['orientation_primary'] = {FACE_VECTORS[primary]}
        if primary in ('up', 'down'):
            result['orientation_secondary'] = {FACE_VECTORS[secondary]}
    if 'rotation' in properties and properties['facing_direction'] in (0, 1):
        secondary = ({0: 'north', 1: 'west', 2: 'south', 3: 'east'}
                     if properties['facing_direction'] == 0 else
                     {0: 'north', 1: 'east', 2: 'south', 3: 'west'})
        result['jigsaw_secondary'] = {FACE_VECTORS[secondary[properties['rotation']]]}
    if properties.get('attachment') in ('standing', 'hanging'):
        result['attachment'] = {(0, -1 if properties['attachment'] == 'standing' else 1, 0)}
    if frozenset(properties) in (frozenset(('hanging',)),
                               frozenset(('hanging', 'dripstone_thickness')),
                               frozenset(('hanging', 'propagule_stage'))):
        result['hanging'] = {(0, 1 if properties['hanging'] else -1, 0)}
    if properties.get('sea_grass_type') in ('double_top', 'double_bot'):
        result['sea_grass_type'] = {(0, 1 if properties['sea_grass_type'] == 'double_top' else -1, 0)}
    if 'rail_direction' in properties:
        result['rail_direction'] = RAIL_POINTS[properties['rail_direction']]
    if properties.get('huge_mushroom_bits') in MUSHROOM_FACES:
        result['mushroom_sides'] = {FACE_VECTORS[face]
                                   for face in MUSHROOM_FACES[properties['huge_mushroom_bits']]}
    if 'door_hinge_bit' in properties:
        forward = FACE_VECTORS[properties['minecraft:cardinal_direction']]
        sign = 1 if properties['door_hinge_bit'] else -1
        result['hinge_side'] = {(sign * forward[2], 0, -sign * forward[0])}
    if 'books_stored' in properties:
        forward = FACE_VECTORS[NUMERIC_FACES['direction'][properties['direction']]]
        result['book_positions'] = {
            ((slot % 3 - 1) * forward[2] + 2 * forward[0],
             1 if slot < 3 else -1,
             -(slot % 3 - 1) * forward[0] + 2 * forward[2])
            for slot in range(6) if properties['books_stored'] & (1 << slot)}
    if 'weirdo_direction' in properties and 'upside_down_bit' in properties:
        high_end = next(iter(result['weirdo_direction']))
        full_y = 1 if properties['upside_down_bit'] else -1
        result['stair_voxels'] = {(x, y, z) for x in (-1, 1) for y in (-1, 1)
                                   for z in (-1, 1)
                                   if y == full_y or x * high_end[0] + z * high_end[2] > 0}
    for key in ('upside_down_bit', 'upper_block_bit', 'minecraft:vertical_half'):
        if key in properties:
            upper = properties[key] == 'top' if key == 'minecraft:vertical_half' else properties[key]
            result[key] = {(0, 1 if upper else -1, 0)}
    for prefix in ('wall_connection_type_', 'pale_moss_carpet_side_', 'minecraft:connection_'):
        for face in ('north', 'south', 'east', 'west'):
            key = prefix + face
            if key in properties and properties[key] != 'none':
                result.setdefault(prefix + properties[key], set()).add(FACE_VECTORS[face])
    return result


def _assert_geometry(value, operation, source, target):
    expected = {key: {reflect_point(point, operation) for point in points}
                for key, points in _geometry(source).items()}
    if expected != _geometry(target):
        raise AssertionError('World-space orientation mismatch: %r %s' % (value, operation))


def _states_after(value, *operations):
    for operation in operations:
        value = state_transform.transform(value, operation)
    return registry.states(value)


def audit_transforms():
    resolved = dict((operation, 0) for operation in state_transform.OPERATIONS)
    for name in registry.BLOCKS:
        for aux in registry.aux_values(name):
            value = (name, aux)
            properties = registry.states(value)
            for operation in state_transform.OPERATIONS:
                actual = state_transform.transform(value, operation)
                if actual[0] != name or actual[1] not in registry.aux_values(name):
                    raise AssertionError('Non-native target state: %r %s -> %r' % (value, operation, actual))
                _assert_geometry(value, operation, properties, registry.states(actual))
                if _states_after(actual, INVERSES[operation]) != properties:
                    raise AssertionError('Inverse did not restore original states: %r %s' % (value, operation))
                resolved[operation] += 1
            if _states_after(value, *(['rotate_y90'] * 4)) != properties:
                raise AssertionError('Four quarter-turns did not close: %r' % (value,))
            if _states_after(value, 'mirror_x', 'mirror_z') != _states_after(value, 'rotate_y180'):
                raise AssertionError('XZ reflection differs from half-turn: %r' % (value,))
            if _states_after(value, 'mirror_x', 'rotate_y90', 'mirror_x') != _states_after(value, 'rotate_y270'):
                raise AssertionError('Reflection/rotation conjugacy failed: %r' % (value,))
            for horizontal in ('rotate_y90', 'mirror_x', 'mirror_z'):
                if _states_after(value, 'mirror_y', horizontal) != _states_after(value, horizontal, 'mirror_y'):
                    raise AssertionError('Vertical/horizontal transform commutation failed: %r %s' % (value, horizontal))
    print('Audited %d records across %d operations' %
          (registry.RECORD_COUNT, len(state_transform.OPERATIONS)))
    for operation in state_transform.OPERATIONS:
        print('%s: %d native targets; orientation and inverse verified' % (operation, resolved[operation]))
    print('Four-turn closure, XZ/half-turn equivalence, reflection conjugacy and Y commutation verified')


if __name__ == '__main__':
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', type=Path, default=ROOT / manifest['source_file'])
    parser.add_argument('--source-version', help='override version inferred from nemc_<version>.json')
    args = parser.parse_args()
    generate(args.source, args.source_version, check=True)
    audit_transforms()
