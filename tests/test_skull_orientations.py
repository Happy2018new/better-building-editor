"""Observed native skull degrees follow independent X/Z vectors, never nested tags."""
import copy
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection import native_appearance
from projection.cell import actor_data, make_cell, transform
from projection.entity_defaults import nbt as default_nbt
from projection.geometry_palette import prepare_palette
from projection.nbt_spatial import scalar
from projection.visible_actor import compose_actor, entity_nbt, render_actor


class SkullOrientationTests(unittest.TestCase):
    def source(self, name, yaw, facing=1):
        material = registry.from_states(name, {'facing_direction': facing})
        native = default_nbt(name, (2, 3, 4))
        native['Rotation']['__value__'] = yaw
        native['unknown'] = {'Rotation': {'__type__': 5, '__value__': 83.}}
        render = {'facingDirection': facing, 'rotation': yaw, 'skullType': 255,
                  'progress': 0.0, 'unknown': {'rotation': 83.}}
        return make_cell(material, nbt=compose_actor(render, native))

    def test_native_floor_yaws_follow_vectors_in_both_payloads_for_all_skull_materials(self):
        operations = ('rotate_y90', 'rotate_y180', 'rotate_y270', 'mirror_x', 'mirror_z')
        for name in native_appearance.SKULL_NAMES:
            for yaw in (0., 22.5, 45., 90., 135., -180., -135., -90.):
                original = self.source(name, yaw)
                before = actor_data(original)
                for operation in operations:
                    result = actor_data(transform(original, operation, (2, 3, 4)))
                    angle = scalar(entity_nbt(result), 'Rotation')
                    x, z = -math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
                    if operation.startswith('rotate'):
                        for unused in range(int(operation[8:]) // 90):
                            x, z = -z, x
                    elif operation == 'mirror_x':
                        x = -x
                    else:
                        z = -z
                    self.assertAlmostEqual(x, -math.sin(math.radians(angle)))
                    self.assertAlmostEqual(z, math.cos(math.radians(angle)))
                    self.assertEqual(angle, render_actor(result)['rotation'])
                    self.assertEqual(5, entity_nbt(result)['Rotation']['__type__'])
                    self.assertEqual(entity_nbt(before)['unknown'], entity_nbt(result)['unknown'])
                    self.assertEqual(render_actor(before)['unknown'], render_actor(result)['unknown'])
                self.assertEqual(before, actor_data(original))

    def test_wall_skulls_follow_block_face_and_keep_unused_yaw(self):
        for facing in (2, 3, 4, 5):
            original = self.source('minecraft:skeleton_skull', 22.5, facing)
            result = actor_data(transform(original, 'rotate_y90'))
            self.assertEqual(22.5, scalar(entity_nbt(result), 'Rotation'))
            self.assertEqual(22.5, render_actor(result)['rotation'])
            self.assertNotEqual(facing, render_actor(result)['facingDirection'])
            self.assertEqual(original, transform(transform(original, 'mirror_x'), 'mirror_x'))

    def test_inverse_and_four_turns_restore_typed_cells_and_share_format(self):
        from projection.model import Document
        from projection.sharing_codec import encode_steps, decode_steps
        original = self.source('minecraft:dragon_head', -135.)
        current = original
        for unused in range(4):
            current = transform(current, 'rotate_y90')
        self.assertEqual(original, current)
        self.assertEqual(original, transform(transform(original, 'rotate_y90'), 'rotate_y270'))
        vertical = transform(original, 'mirror_y')
        self.assertEqual(-135., scalar(entity_nbt(actor_data(vertical)), 'Rotation'))
        self.assertEqual(original, transform(vertical, 'mirror_y'))
        doc = Document((1, 1, 1), {(0, 0, 0): transform(original, 'mirror_z')})
        restored = list(decode_steps(list(encode_steps(doc))[-1]['text']))[-1]['document']
        self.assertEqual(doc.get((0, 0, 0)), restored.get((0, 0, 0)))

    def test_legacy_renderer_and_new_cells_gain_native_tags_before_transform(self):
        material = registry.from_states('minecraft:skeleton_skull', {'facing_direction': 1})
        value = make_cell(material, nbt={'facingDirection': 1, 'skullType': 255, 'rotation': 22.5})
        result = actor_data(transform(value, 'mirror_x'))
        self.assertEqual(-22.5, scalar(entity_nbt(result), 'Rotation'))
        self.assertEqual(-22.5, render_actor(result)['rotation'])
        fresh = actor_data(transform(material, 'rotate_y90'))
        self.assertEqual(90., scalar(entity_nbt(fresh), 'Rotation'))

    def test_native_palette_adapter_uses_verified_fields_without_mutating_saved_payloads(self):
        value = transform(self.source('minecraft:dragon_head', 45.), 'rotate_y90')
        payload = actor_data(value)
        source = {'common': {tuple(value): [0]}, 'actor': {value[0]: {0: payload}}}
        saved = copy.deepcopy(source)
        result = prepare_palette(source)['actor'][value[0]][0]
        self.assertEqual(135., result['rotation'])
        self.assertEqual(1, result['facingDirection'])
        self.assertNotIn('Rotation', result)
        self.assertNotIn('id', result)
        self.assertEqual(saved, source)
        source['actor'][value[0]][0] = entity_nbt(payload)
        result = prepare_palette(source)['actor'][value[0]][0]
        self.assertEqual({'skullType': 255, 'rotation': 135., 'facingDirection': 1, 'progress': 0.}, result)

    def test_stale_observations_and_non_native_tag_types_are_not_silently_applied(self):
        original = self.source('minecraft:skeleton_skull', 45.)
        with patch.object(native_appearance, 'SOURCE_VERSION', 'future'):
            with self.assertRaises(ValueError):
                transform(original, 'rotate_y90')
        material = tuple(original)
        payload = entity_nbt(actor_data(original))
        payload['Rotation']['__type__'] = 1
        result = actor_data(transform(make_cell(material, nbt=payload), 'rotate_y90'))
        self.assertEqual(payload['Rotation'], result['Rotation'])


if __name__ == '__main__':
    unittest.main()
