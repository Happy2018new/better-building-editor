"""Pot artwork follows transformed world faces, using measured native face order."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import actor_data, make_cell, transform
from projection.nbt_spatial import field_key, root_payload, scalar, transform_pair
from projection.visible_actor import compose_actor, entity_nbt, render_actor

EVIDENCE = json.loads((ROOT / 'tools/data/native_pot_face_mapping_r4_v1.json').read_text())
SHERDS = tuple(row['name'] for row in EVIDENCE['sherds'])
NORMALS = {'north': (0, -1), 'west': (-1, 0), 'east': (1, 0), 'south': (0, 1)}
FACES = {row['direction']: row['index_to_world_face'] for row in EVIDENCE['directions']}
OPERATIONS = ('rotate_y90', 'rotate_y180', 'rotate_y270', 'mirror_x', 'mirror_y', 'mirror_z')


def nbt_payload():
    return {'__type__': 10, '__value__': {
        'id': {'__type__': 8, '__value__': 'DecoratedPot'},
        'sherds': [{'__type__': 8, '__value__': name, 'marker': index}
                   for index, name in enumerate(SHERDS)],
        'item': {'tag': {'sherds': list(SHERDS)}}, 'foreign': {'x': 7}}}


def render_payload(direction):
    data = {'direction': direction, 'decoratedPotShredNamesSize': 4, 'foreign': {'x': 7}}
    data.update(('decoratedPotShredNames' + str(index), name)
                for index, name in enumerate(SHERDS))
    return data


def world_artwork(direction, names):
    return dict((NORMALS[face], name) for face, name in zip(FACES[direction], names))


def geometric_normal(normal, operation):
    x, z = normal
    if operation == 'mirror_x':
        return -x, z
    if operation == 'mirror_z':
        return x, -z
    if operation == 'mirror_y':
        return x, z
    for unused in range(int(operation[8:]) // 90):
        x, z = -z, x
    return x, z


class NativePotSpatialTests(unittest.TestCase):
    def test_every_direction_and_operation_places_nbt_artwork_on_geometric_face(self):
        for direction in range(4):
            for operation in OPERATIONS:
                with self.subTest(direction=direction, operation=operation):
                    source = nbt_payload()
                    value = make_cell(('minecraft:decorated_pot', direction), nbt=source)
                    result = transform(value, operation)
                    root = root_payload(entity_nbt(actor_data(result)))
                    names = [scalar(tag, '__value__') for tag in root['sherds']]
                    expected = {geometric_normal(face, operation): name
                                for face, name in world_artwork(direction, SHERDS).items()}
                    self.assertEqual(expected, world_artwork(registry.states(result)['direction'], names))
                    self.assertEqual(source, actor_data(value))
                    self.assertEqual(source['__value__']['item'], root['item'])
                    self.assertEqual(source['__value__']['foreign'], root['foreign'])
                    for tag in root['sherds']:
                        self.assertEqual(SHERDS[tag['marker']], scalar(tag, '__value__'))

    def test_cached_renderer_and_envelope_follow_same_world_faces_once(self):
        for direction in range(4):
            for operation in OPERATIONS:
                for full_nbt in (False, True):
                    with self.subTest(direction=direction, operation=operation, full_nbt=full_nbt):
                        renderer = render_payload(direction)
                        payload = compose_actor(renderer, nbt_payload() if full_nbt else None)
                        before = copy.deepcopy(payload)
                        result = transform(make_cell(('minecraft:decorated_pot', direction), nbt=payload), operation)
                        actor = actor_data(result)
                        root = root_payload(render_actor(actor))
                        names = [scalar(root, 'decoratedPotShredNames' + str(index)) for index in range(4)]
                        expected = {geometric_normal(face, operation): name
                                    for face, name in world_artwork(direction, SHERDS).items()}
                        self.assertEqual(expected, world_artwork(registry.states(result)['direction'], names))
                        if full_nbt:
                            self.assertEqual(names, [scalar(tag, '__value__')
                                                   for tag in root_payload(entity_nbt(actor))['sherds']])
                        self.assertEqual(before, payload)

    def test_each_mirror_is_an_involution_and_rotations_do_not_reorder_slots(self):
        for direction in range(4):
            value = make_cell(('minecraft:decorated_pot', direction),
                              nbt=compose_actor(render_payload(direction), nbt_payload()))
            for operation in ('mirror_x', 'mirror_y', 'mirror_z'):
                self.assertEqual(value, transform(transform(value, operation), operation))
            result = value
            for unused in range(4):
                result = transform(result, 'rotate_y90')
                self.assertEqual(SHERDS, tuple(scalar(tag, '__value__')
                                             for tag in root_payload(entity_nbt(actor_data(result)))['sherds']))
            self.assertEqual(value, result)

    def test_byte_keys_and_typed_renderer_wrappers_keep_identity(self):
        nbt = {b'id': {b'__type__': 8, b'__value__': b'DecoratedPot'},
               b'sherds': [{b'__type__': 8, b'__value__': name.encode('ascii'), b'marker': index}
                           for index, name in enumerate(SHERDS)]}
        render = {key.encode('ascii'): {'__type__': 8 if isinstance(value, str) else 3,
                                       '__value__': value, 'slot': key}
                  for key, value in render_payload(0).items() if key != 'foreign'}
        result = transform_pair(compose_actor(render, nbt), (0, 0, 0), 'mirror_x',
                                ('minecraft:decorated_pot', 0))
        self.assertEqual(set(nbt), set(entity_nbt(result)))
        tags = entity_nbt(result)[b'sherds']
        self.assertEqual([0, 2, 1, 3], [tag[b'marker'] for tag in tags])
        root = render_actor(result)
        for index in range(4):
            field = 'decoratedPotShredNames' + str(index)
            tag = root[field_key(root, field)]
            self.assertEqual(field, tag['slot'])
            self.assertEqual(8, tag['__type__'])
        self.assertEqual(SHERDS[2], scalar(root, 'decoratedPotShredNames1'))

    def test_incomplete_invalid_and_unrelated_payloads_remain_opaque(self):
        bad_nbt = []
        for mutate in (lambda root: root['sherds'].pop(),
                       lambda root: root['sherds'][1].update(__type__=3),
                       lambda root: root['sherds'][2].update(__value__=7),
                       lambda root: root['id'].update(__value__='Chest')):
            payload = nbt_payload()
            mutate(payload['__value__'])
            bad_nbt.append(payload)
        partial = render_payload(0)
        del partial['decoratedPotShredNames2']
        invalid = render_payload(0)
        invalid['decoratedPotShredNames1'] = 7
        wrong_size = render_payload(0)
        wrong_size['decoratedPotShredNamesSize'] = 3
        for payload in bad_nbt + [partial, invalid, wrong_size]:
            self.assertEqual(payload, transform_pair(payload, (0, 0, 0), 'mirror_x',
                                                    ('minecraft:decorated_pot', 0)))
        for material in (None, ('minecraft:chest', 0)):
            self.assertEqual(nbt_payload(), transform_pair(nbt_payload(), (0, 0, 0), 'mirror_z', material))


if __name__ == '__main__':
    unittest.main()
