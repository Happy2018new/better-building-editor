"""Frame directions follow independent 3D vectors while typed item data stays opaque."""
import copy
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry, frame_rotation_data
from projection.cell import actor_data, foreground, make_cell, transform
from projection.nbt_spatial import scalar, root_payload
from projection.visible_actor import compose_actor, entity_nbt, render_actor

OPERATIONS = ('rotate_y90', 'rotate_y180', 'rotate_y270', 'mirror_x', 'mirror_y', 'mirror_z')
FACES = ((0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0))
RIGHT = ((1, 0, 0), (1, 0, 0), (-1, 0, 0), (1, 0, 0), (0, 0, 1), (0, 0, -1))
UP = ((0, 0, 1), (0, 0, -1), (0, 1, 0), (0, 1, 0), (0, 1, 0), (0, 1, 0))


def moved(value, operation):
    x, y, z = value
    if operation.startswith('rotate_y'):
        for unused in range(int(operation[8:]) // 90):
            x, z = -z, x
    elif operation == 'mirror_x':
        x = -x
    elif operation == 'mirror_y':
        y = -y
    elif operation == 'mirror_z':
        z = -z
    return x, y, z


def top_vector(angle, facing):
    radians = math.radians(angle)
    return tuple(math.sin(radians) * RIGHT[facing][axis] +
                 math.cos(radians) * UP[facing][axis] for axis in range(3))


def tag(value, kind):
    return {'__type__': kind, '__value__': value}


class FrameOrientationTests(unittest.TestCase):
    def source(self, name, angle, facing):
        material = registry.from_states(name, {'facing_direction': facing,
            'item_frame_map_bit': False, 'item_frame_photo_bit': False})
        entity = {'id': tag('GlowItemFrame' if 'glow' in name else 'ItemFrame', 8),
                  'ItemRotation': dict(tag(angle, 5), future=42),
                  'Item': tag({'Name': tag('minecraft:diamond_sword', 8),
                               'tag': tag({'ItemRotation': tag(91., 5)}, 10)}, 10),
                  'future': {'ItemRotation': tag(82., 5)}}
        return make_cell(material, nbt=compose_actor({}, entity))

    def test_all_native_angles_and_six_faces_follow_independent_3d_top_vectors(self):
        for name in ('minecraft:frame', 'minecraft:glow_frame'):
            for face in range(6):
                for angle in range(0, 360, 45):
                    original = self.source(name, float(angle), face)
                    original_actor = actor_data(original)
                    for operation in OPERATIONS:
                        changed = transform(original, operation)
                        changed_actor = actor_data(changed)
                        target_face = registry.states(foreground(changed))['facing_direction']
                        self.assertEqual(FACES.index(moved(FACES[face], operation)), target_face)
                        actual = top_vector(scalar(entity_nbt(changed_actor), 'ItemRotation'), target_face)
                        expected = moved(top_vector(angle, face), operation)
                        for left, right in zip(expected, actual):
                            self.assertAlmostEqual(left, right)
                        changed_nbt = entity_nbt(changed_actor)
                        self.assertEqual(5, changed_nbt['ItemRotation']['__type__'])
                        self.assertEqual(42, changed_nbt['ItemRotation']['future'])
                        self.assertEqual(original_actor['nbt']['Item'], changed_nbt['Item'])
                        self.assertEqual(original_actor['nbt']['future'], changed_nbt['future'])
                        self.assertEqual({}, render_actor(changed_actor))
                    self.assertEqual(original_actor, actor_data(original))

    def test_inverse_and_four_turn_closure_preserve_cells_and_share_formats(self):
        from projection.model import Document
        from projection.sharing_codec import encode_steps, decode_steps
        for name in ('minecraft:frame', 'minecraft:glow_frame'):
            for face in range(6):
                original = self.source(name, 22.5, face)
                current = original
                for unused in range(4):
                    current = transform(current, 'rotate_y90')
                self.assertEqual(original, current)
                for operation in OPERATIONS:
                    inverse = {'rotate_y90': 'rotate_y270', 'rotate_y270': 'rotate_y90'}.get(operation, operation)
                    self.assertEqual(original, transform(transform(original, operation), inverse))
                changed = transform(original, 'mirror_x')
                doc = Document((1, 1, 1), {(0, 0, 0): changed})
                decoded = list(decode_steps(list(encode_steps(doc))[-1]['text']))[-1]['document']
                self.assertEqual(changed, decoded.get((0, 0, 0)))

    def test_unknown_entities_and_invalid_or_missing_fields_are_not_changed(self):
        original = self.source('minecraft:frame', 45., 1)
        for change in ({'id': tag('Unknown', 8)}, {'ItemRotation': tag(2, 1)},
                       {'ItemRotation': tag(-1., 5)}, {'ItemRotation': tag(360., 5)},
                       {'ItemRotation': tag(True, 5)},
                       {'ItemRotation': 45.}, {'ItemRotation': None}):
            payload = copy.deepcopy(entity_nbt(actor_data(original)))
            payload.update(change)
            changed = transform(make_cell(foreground(original), nbt=payload), 'rotate_y90')
            self.assertEqual(payload, actor_data(changed))
        payload = entity_nbt(actor_data(original))
        del payload['ItemRotation']
        changed = transform(make_cell(foreground(original), nbt=payload), 'rotate_y90')
        self.assertEqual(payload, actor_data(changed))

    def test_byte_keys_and_stale_observation_guard(self):
        material = registry.from_states('minecraft:frame', {'facing_direction': 2,
            'item_frame_map_bit': False, 'item_frame_photo_bit': False})
        payload = {b'id': {b'__type__': 8, b'__value__': b'ItemFrame'},
                   b'ItemRotation': {b'__type__': 5, b'__value__': 45.}}
        changed = transform(make_cell(material, nbt=payload), 'mirror_y')
        self.assertEqual(135., scalar(root_payload(actor_data(changed)), 'ItemRotation'))
        self.assertEqual(set(payload), set(actor_data(changed)))
        original = make_cell(material, nbt=payload)
        before = actor_data(original)
        for field, invalid in (('SCHEMA_VERSION', 2), ('SOURCE_VERSION', 'future'),
                               ('PALETTE_SHA256', 'future')):
            with self.subTest(field=field), patch.object(frame_rotation_data, field, invalid):
                with self.assertRaises(ValueError):
                    transform(original, 'mirror_x')
            self.assertEqual(before, actor_data(original))


if __name__ == '__main__':
    unittest.main()
