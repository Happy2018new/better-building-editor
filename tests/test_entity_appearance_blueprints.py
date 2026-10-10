"""Every observed appearance has a stable blueprint coordinate and typed payload."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.block_groups import group_partner
from projection.cell import actor_data, foreground, make_cell, transform
from projection.debug_appearance_blueprints import CASE_NAMES, CASE_POSITIONS, IDENTITY, observations
from projection.debug_blueprints import build
from projection.entity_render import native_actor
from projection.nbt_spatial import scalar
from projection.visible_actor import compose_actor, entity_nbt, render_actor


class AppearanceBlueprintTests(unittest.TestCase):
    def test_all_native_samples_have_unique_positions_and_raw_tags_rebased_to_each_part(self):
        doc = build(IDENTITY)
        self.assertEqual(25, len(CASE_NAMES))
        self.assertEqual(25, len(set(CASE_POSITIONS.values())))
        for row in observations():
            pos = CASE_POSITIONS[row['case']]
            value = doc.get(pos)
            root = entity_nbt(actor_data(value))
            self.assertEqual(row['observed_id'], scalar(root, 'id'))
            self.assertEqual(pos, tuple(scalar(root, axis) for axis in ('x', 'y', 'z')))
            self.assertEqual((row['block']['name'], row['block']['aux']), foreground(value))
            if row['case'].startswith('skull_floor') or row['case'].endswith('floor_yaw45'):
                self.assertEqual(row['observed_rotation'], scalar(root, 'Rotation'))
                self.assertEqual(row['observed_rotation'], render_actor(actor_data(value))['rotation'])
            if row.get('fill_observed'):
                self.assertEqual('minecraft:diamond_sword', scalar(root['Item'], 'Name'))
            if row['name'] == 'minecraft:banner':
                self.assertEqual(row['observed_type'], scalar(root, 'Type'))

    def test_nondefault_bed_head_colours_have_legal_reciprocal_halves_and_native_adapters(self):
        doc = build(IDENTITY)
        for case, color in (('bed_silver', 8), ('bed_light_blue', 3)):
            foot = CASE_POSITIONS[case]
            first = doc.get(foot)
            offset, partner = group_partner(foreground(first))
            head = tuple(foot[index] + offset[index] for index in range(3))
            second = doc.get(head)
            self.assertEqual(partner, foreground(second))
            self.assertEqual(0, scalar(entity_nbt(actor_data(first)), 'color'))
            self.assertEqual(color, scalar(entity_nbt(actor_data(second)), 'color'))
            adapter = native_actor(foreground(second), actor_data(second))
            self.assertEqual({'color': color, 'direction': 0}, adapter)

    def test_visible_bed_direction_tracks_every_material_transform_without_rewriting_nbt(self):
        doc = build(IDENTITY)
        foot = CASE_POSITIONS['bed_light_blue']
        offset, unused = group_partner(foreground(doc.get(foot)))
        head = tuple(foot[index] + offset[index] for index in range(3))
        first = doc.get(head)
        before = actor_data(first)
        for operation in ('rotate_y90', 'rotate_y180', 'rotate_y270', 'mirror_x', 'mirror_y', 'mirror_z'):
            result = transform(first, operation)
            direction = registry.states(foreground(result))['direction']
            self.assertEqual(direction, render_actor(actor_data(result))['direction'])
            self.assertEqual(direction, native_actor(foreground(result), actor_data(result))['direction'])
            self.assertEqual(3, native_actor(foreground(result), actor_data(result))['color'])
            self.assertEqual(entity_nbt(before), entity_nbt(actor_data(result)))
        self.assertEqual(before, actor_data(first))

    def test_bed_adapter_does_not_mutate_envelopes_or_map_unobserved_tag_types(self):
        doc = build(IDENTITY)
        foot = CASE_POSITIONS['bed_silver']
        payload = actor_data(doc.get(foot))
        saved = copy.deepcopy(payload)
        renderer = native_actor(('minecraft:bed', 0), payload)
        self.assertEqual(0, renderer['color'])
        self.assertEqual(saved, payload)
        typed = entity_nbt(payload)
        typed['color']['__type__'] = 5
        actor = compose_actor(None, typed)
        self.assertIsNone(native_actor(('minecraft:bed', 0), actor))
        unknown = make_cell(('minecraft:bed', 0), nbt={'id': 'Other', 'direction': 2})
        self.assertEqual(actor_data(unknown), actor_data(transform(unknown, 'rotate_y90')))


if __name__ == '__main__':
    unittest.main()
