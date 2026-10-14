"""Measured icon-family boundaries, aliases, shared slots and source retention."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT/'tools'))
sys.path.insert(0, str(ROOT/'tests'))

from projection import item_icon_data, visible_item_slot_data
from projection.cell import make_cell, actor_data
from projection.debug_blueprints import material, build, BLUEPRINTS
from projection.debug_item_blueprints import (CATALOGUE_CASES, CATALOGUE_METADATA,
                                               catalogue_document, slot_observations, orientation_document)
from projection.entity_overlays import native_item
from projection.item_sprite_plan import iter_render_steps, sprite_content, validate_uniforms
from projection.item_sprite_profile import candidate_profile, production_profile
from projection.model import Document
from projection.nbt_spatial import root_payload, scalar
from projection.visible_actor import compose_actor
from projection.visible_item_contents import content_slots
from test_static_frame_items import actor, frame
import generate_item_icon_catalog as generator

ENGINE = '3.10.0.420447'


def groups(document):
    return tuple(row for row in iter_render_steps(document, candidate_profile(ENGINE)) if row is not None)


class IconCatalogTests(unittest.TestCase):
    def test_catalog_covers_measured_flat_names_with_exact_engine_gate(self):
        profile = candidate_profile(ENGINE)
        self.assertGreaterEqual(len(profile.items.by_name), 400)
        self.assertIsNone(production_profile(ENGINE))
        self.assertIsNone(production_profile('3.11.0'))
        with self.assertRaises(ValueError):
            candidate_profile('3.11.0')
        self.assertEqual(1, len(candidate_profile().items))

    def test_item_type_and_render_tags_exclude_special_content(self):
        base = {'itemType': '', 'tags': [], 'itemCategory': 'equipment'}
        self.assertEqual('flat_icon_candidate', generator.classify('minecraft:apple', base, 'textures/items/apple'))
        for name, patch, texture, expected in (
            ('minecraft:stone', {'itemType': 'block'}, 'textures/blocks/stone', 'block_geometry'),
            ('minecraft:potion', {'itemType': 'potion'}, 'textures/items/potion_bottle_drinkable', 'tinted_potion'),
            ('minecraft:filled_map', {}, 'textures/items/map_filled', 'map_surface'),
            ('minecraft:shield', {}, 'textures/items/sign', 'patterned_geometry'),
            ('minecraft:zombie_spawn_egg', {'tags': ['minecraft:spawn_egg']}, 'textures/items/egg', 'tinted_spawn_egg'),
            ('minecraft:leather_helmet', {'tags': ['minecraft:leather_tier']}, 'textures/items/leather_helmet', 'tinted_leather')):
            self.assertEqual(expected, generator.classify(name, dict(base, **patch), texture))

    def test_upward_frame_pose_is_versioned_separately_from_other_visible_slots(self):
        self.assertEqual(180., generator.POSE['upward_base_rotation_degrees'])
        self.assertEqual(-1., generator.POSE['rotation_sign'])
        self.assertIn('facing>0.5 && facing<1.5 && itemLayout<0.5',
                      (ROOT/'resource_pack/shaders/glsl/modern_projection_item_icon.vertex').read_text(encoding='ascii'))

    def test_frame_and_glow_frame_have_identical_owned_content_for_all_48_poses(self):
        for face in range(6):
            for rotation in range(8):
                suffix = '_f%d_r%d' % (face,rotation)
                self.assertEqual(groups(orientation_document('frame'+suffix)),
                                 groups(orientation_document('glow_frame'+suffix)))

    def test_native_glint_uses_versioned_bitmap_squared_blend_and_continuous_clock_wrap(self):
        catalog = json.loads((ROOT/'tools/data/item_icon_catalog_nemc_3.10.0.420447.json').read_bytes())
        fragment = (ROOT/'resource_pack/shaders/glsl/modern_projection_item_icon.fragment').read_text(encoding='ascii')
        self.assertIn('glint*glint',fragment)
        self.assertIn('texture2D(TEXTURE_1',fragment)
        self.assertIn('if(texel.a<0.5) discard;',fragment)
        self.assertEqual('squared_two_native_texture_layers',catalog['glint']['blend'])
        for rate in catalog['glint']['cycles_per_second']:
            self.assertEqual(round(rate*210.),rate*210.)

    def test_candidate_and_production_reject_stale_layout_or_resource_acceptance(self):
        with patch.object(item_icon_data, 'LAYOUT_VERSION', 999):
            with self.assertRaises(ValueError):
                candidate_profile(ENGINE)
        with patch.object(item_icon_data, 'PRODUCTION_QUALIFIED', True), \
                patch.object(item_icon_data, 'QUALIFICATION_SHA256', 'a' * 64):
            with self.assertRaises(ValueError):
                production_profile(ENGINE)
            with patch.object(item_icon_data, 'QUALIFICATION_RESOURCE_SHA256', item_icon_data.RESOURCE_SHA256):
                with self.assertRaises(ValueError):
                    production_profile(ENGINE)
                with patch.object(item_icon_data, 'QUALIFIED_FAMILIES', ('frame',)):
                    self.assertEqual(('frame',), production_profile(ENGINE).content_families)

    def test_frame_acceptance_does_not_enable_unqualified_visible_slot_families(self):
        profile = candidate_profile(ENGINE)
        profile.content_families = ('frame',)
        for row in slot_observations():
            document = Document((4,4,4), {(1,2,1): make_cell(material(row['name']),
                nbt=compose_actor({}, row['after']))})
            self.assertEqual((), tuple(value for value in iter_render_steps(document, profile) if value))
        self.assertTrue(tuple(value for value in iter_render_steps(
            Document((1,1,1), {(0,0,0): make_cell(frame(), nbt=actor())}), profile) if value))

    def test_durability_uses_measured_resource_and_preserves_typed_damage(self):
        profile = candidate_profile(ENGINE)
        payload = actor()
        payload['Item']['__value__']['Damage']['__value__'] = 1550
        saved = copy.deepcopy(payload)
        self.assertEqual(('minecraft:diamond_sword', 0), sprite_content(frame(), payload, profile.items)[0])
        self.assertEqual(saved, payload)
        payload['Item']['__value__']['Damage']['__value__'] = 1562
        self.assertIsNone(sprite_content(frame(), payload, profile.items))

    def test_unknown_aux_and_special_render_userdata_are_opaque(self):
        profile = candidate_profile(ENGINE)
        for name in ('minecraft:stone', 'minecraft:potion', 'minecraft:filled_map', 'minecraft:banner'):
            self.assertIsNone(sprite_content(frame(), actor(item=name), profile.items))
        payload = actor(item='minecraft:apple', user_data={'CustomColor': {'__type__': 3, '__value__': 1}})
        self.assertIsNone(sprite_content(frame(), payload, profile.items))
        payload = actor(item='minecraft:apple')
        payload['Item']['__value__']['Damage']['__value__'] = 17
        self.assertIsNone(sprite_content(frame(), payload, profile.items))

    def test_catalogue_pages_are_public_and_near_view_preserves_payloads(self):
        public = {row[0] for row in BLUEPRINTS}
        self.assertTrue({row[0] for row in CATALOGUE_METADATA}.issubset(public))
        seen = set()
        for identity, rows in CATALOGUE_CASES.items():
            self.assertLessEqual(len(rows), 24)
            seen.update(row['item'] for row in rows)
        self.assertEqual(set(item_icon_data.ITEMS), seen)
        identity = CATALOGUE_METADATA[0][0]
        source = build(identity)
        case = CATALOGUE_CASES[identity][0]
        isolated = catalogue_document(identity, case['id'])
        for mode, target in (('plain', (2,3,2)), ('enchanted', (5,3,2))):
            original = source.get(case[mode])
            # Spatial coordinates alone may be rebased; the typed Item is exact.
            first = root_payload(actor_data(original))['Item']
            second = root_payload(actor_data(isolated.get(target)))['Item']
            self.assertEqual(first, second)


class NativeSlotTests(unittest.TestCase):
    def setUp(self):
        self.rows = {row['name']: row for row in slot_observations()}

    def test_observed_shelf_uses_positional_three_slot_list_and_one_enchanted_center(self):
        row = self.rows['minecraft:oak_shelf']
        saved = copy.deepcopy(row['after'])
        slots = content_slots(material(row['name']), compose_actor({}, row['after']), ENGINE)
        self.assertEqual(1, len(slots))
        self.assertEqual(('shelf', 1, 'south'), (slots[0].family, slots[0].index, slots[0].direction))
        self.assertTrue(slots[0].item['isEnchanted'])
        self.assertEqual(saved, row['after'])
        unknown = copy.deepcopy(row['after'])
        unknown['Items'].append(copy.deepcopy(unknown['Items'][0]))
        self.assertIsNone(content_slots(material(row['name']), compose_actor({}, unknown), ENGINE))
        self.assertIsNone(content_slots(material(row['name']), compose_actor({}, row['after']), '3.11.0'))

    def test_four_campfire_foods_and_lectern_book_have_independent_layout_families(self):
        for name, family, count in (('minecraft:campfire', 'campfire', 4), ('minecraft:lectern', 'lectern', 1)):
            row = self.rows[name]
            slots = content_slots(material(name), compose_actor({}, row['after']), ENGINE)
            self.assertEqual(count, len(slots))
            self.assertTrue(all(slot.family == family for slot in slots))
            self.assertEqual((), content_slots(material(name), compose_actor({}, row['before']), ENGINE))
        invalid = copy.deepcopy(self.rows['minecraft:lectern']['after'])
        invalid['hasBook']['__value__'] = 0
        self.assertIsNone(content_slots(material('lectern'), compose_actor({}, invalid), ENGINE))

    def test_shared_plan_batches_observed_slots_and_clears_visibility_together(self):
        for name, expected, layout in (('minecraft:oak_shelf', 1, (2.,)),
                                       ('minecraft:campfire', 4, (4.,5.,6.,7.))):
            row = self.rows[name]
            document = Document((4,4,4), {(1,2,1): make_cell(material(name), nbt=compose_actor({}, row['after']))})
            before = copy.deepcopy(document.to_data())
            plan = groups(document)
            self.assertEqual(1, len(plan))
            self.assertEqual(expected, int(plan[0].uniforms[3][1]))
            self.assertEqual(layout, plan[0].uniforms[1][:expected])
            validate_uniforms(plan[0].uniforms)
            self.assertEqual((), tuple(row for row in iter_render_steps(document,candidate_profile(ENGINE),lambda pos:False) if row))
            self.assertEqual(before, document.to_data())
        row = self.rows['minecraft:lectern']
        self.assertEqual((), groups(Document((4,4,4), {(1,2,1): make_cell(material('lectern'),
                                     nbt=compose_actor({}, row['after']))})))

    def test_layout_face_and_unused_slot_corruption_are_rejected(self):
        row = self.rows['minecraft:campfire']
        plan = groups(Document((4,4,4), {(1,2,1): make_cell(material('campfire'), nbt=compose_actor({}, row['after']))}))[0]
        for packet in (
            ((0.,)*4,) + plan.uniforms[1:],
            plan.uniforms[:1] + ((8.,0.,0.,0.),) + plan.uniforms[2:],
            plan.uniforms[:3] + ((plan.uniforms[3][0],1.,0.,1.),)):
            with self.assertRaises(ValueError):
                validate_uniforms(packet)

    def test_shared_item_compound_is_strict_but_preserves_raw_native_enchantments(self):
        item = self.rows['minecraft:oak_shelf']['after']['Items'][1]
        saved = copy.deepcopy(item)
        self.assertTrue(native_item(item)['isEnchanted'])
        self.assertEqual(saved, item)
        self.assertIsNone(native_item([]))


if __name__ == '__main__':
    unittest.main()
