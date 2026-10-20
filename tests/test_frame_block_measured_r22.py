"""Exact pair deployment, native shader ownership and plain/glint separation."""
import json
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'behavior_pack/modern_projection'), str(ROOT / 'tests')]
from projection import frame_block_measured_profile as profile
from projection import frame_block_measured_data as data
from projection.cell import make_cell
from projection.model import Document
from projection.item_sprite_plan import sprite_item, sprite_content, iter_render_steps
from projection.item_sprite_profile import measured_frame_block_candidate_profile, production_profile
from tests.test_static_frame_items import actor, frame


class MeasuredFrameBlocks(unittest.TestCase):
    def test_exact_three_candidates_preserve_enchantment_and_unsupported_aux(self):
        candidates = measured_frame_block_candidate_profile(data.ENGINE_VERSION)
        self.assertEqual(profile.ITEMS, set(candidates.items))
        self.assertEqual({}, profile.production_items(data.ENGINE_VERSION))
        self.assertIsNone(candidates.items.get(('minecraft:stone', 1)))
        self.assertIsNone(candidates.items.get(('minecraft:quartz', 0)))
        for key, row in candidates.items.items():
            self.assertIs(row['supports_enchantment'], True)
            self.assertTrue(row['ui_model'].startswith('modern_projection_measured_frame_block_'))

    def test_plain_qualification_does_not_admit_artificial_glint_or_other_pairs(self):
        key = ('minecraft:stone', 0)
        with patch.multiple(data, PRODUCTION_QUALIFIED=True, POSE=dict(data.POSE, accepted=True),
                QUALIFICATION_SHA256='a' * 64, QUALIFICATION_RESOURCE_SHA256=data.RESOURCE_SHA256,
                QUALIFIED_ITEMS=(key,), QUALIFIED_ENCHANTMENTS=(), QUALIFIED_FRAME_POSES={key: ((2, 0),)}):
            rows = profile.production_items(data.ENGINE_VERSION)
            self.assertEqual({key}, set(rows))
            item = {'newItemName': key[0], 'newAuxValue': 0, 'isEnchanted': False, 'userData': {}}
            self.assertEqual(key, sprite_item(item, rows))
            enchanted = dict(item, isEnchanted=True, userData={'ench': []})
            self.assertIsNone(sprite_item(enchanted, rows))
            with patch.object(data, 'QUALIFIED_ENCHANTMENTS', (key,)):
                self.assertEqual(key, sprite_item(enchanted, profile.production_items(data.ENGINE_VERSION)))
            with patch.object(data, 'QUALIFICATION_RESOURCE_SHA256', 'b' * 64):
                with self.assertRaises(ValueError):
                    profile.production_items(data.ENGINE_VERSION)

    def test_plain_deployment_renders_only_accepted_normal_frame_pose_in_both_routes(self):
        key = ('minecraft:stone', 0)
        cells = {}
        for name in ('minecraft:frame', 'minecraft:glow_frame'):
            for facing in range(6):
                material = profile.block_registry.from_states(name, {'facing_direction': facing,
                    'item_frame_map_bit': False, 'item_frame_photo_bit': False})
                for rotation in range(8):
                    index = len(cells)
                    cells[(index % 48, index // 48, 0)] = make_cell(material, nbt=actor(rotation * 45., item=key[0]))
        document = Document((48, 2, 1), cells)
        saved = deepcopy(document.to_data())
        with patch.multiple(data, PRODUCTION_QUALIFIED=True, POSE=dict(data.POSE, accepted=True),
                QUALIFICATION_SHA256='a' * 64, QUALIFICATION_RESOURCE_SHA256=data.RESOURCE_SHA256,
                QUALIFIED_ITEMS=(key,), QUALIFIED_ENCHANTMENTS=(), QUALIFIED_FRAME_POSES={key: ((2, 0),)}):
            product = production_profile(data.ENGINE_VERSION)
            for world in (False, True):
                groups = [row for row in iter_render_steps(document, product, world=world) if row is not None]
                self.assertEqual(1, len(groups))
                self.assertEqual(1, groups[0].uniforms[3][1])
                self.assertEqual(128., groups[0].uniforms[0][0])
                self.assertEqual(data.ITEMS[key]['world_model' if world else 'ui_model'], groups[0].model_name)
        self.assertEqual(saved, document.to_data())
        candidates = measured_frame_block_candidate_profile(data.ENGINE_VERSION)
        self.assertIsNotNone(sprite_content(frame(5), actor(315., item=key[0]), candidates.items))

    def test_pair_acceptance_cannot_omit_or_expand_the_frame_pose_contract(self):
        key = ('minecraft:stone', 0)
        for poses in ({}, {key: ()}, {key: ((3, 0),)}, {key: ((2, 1),)}, {key: ((2, False),)}):
            with patch.multiple(data, PRODUCTION_QUALIFIED=True, POSE=dict(data.POSE, accepted=True),
                    QUALIFICATION_SHA256='a' * 64, QUALIFICATION_RESOURCE_SHA256=data.RESOURCE_SHA256,
                    QUALIFIED_ITEMS=(key,), QUALIFIED_ENCHANTMENTS=(), QUALIFIED_FRAME_POSES=poses):
                with self.assertRaises(ValueError):
                    profile.production_items(data.ENGINE_VERSION)

    def test_material_gate_cannot_admit_unknown_aux_or_special_geometry(self):
        for key in (('minecraft:stone', 1), ('minecraft:oak_stairs', 0)):
            with patch.multiple(data, PRODUCTION_QUALIFIED=True, POSE=dict(data.POSE, accepted=True),
                    QUALIFICATION_SHA256='a' * 64, QUALIFICATION_RESOURCE_SHA256=data.RESOURCE_SHA256,
                    QUALIFIED_ITEMS=(key,)):
                with self.assertRaises(ValueError):
                    profile.production_items(data.ENGINE_VERSION)

    def test_measured_registered_assets_use_only_their_own_pose_and_default_shader(self):
        registration = json.loads((ROOT / 'tools/data/frame_block_measured_item_registrations_r22.json').read_bytes())
        self.assertEqual(6, len(registration['models']))
        self.assertEqual(2, len(registration['materials']))
        for model, row in registration['models'].items():
            self.assertTrue(model.startswith('modern_projection_measured_frame_block_'))
            self.assertIn('/frame_block_measured/', row['mesh'])
        for row in registration['materials'].values():
            for key in ('vertexShader', 'fragmentShader'):
                self.assertIn('modern_projection_measured_frame_block', row[key])
                source = (ROOT / 'resource_pack' / row[key]).read_text()
                self.assertNotIn('frameBlockBaseLight', source)
                self.assertNotIn('itemLight*0.93', source)
                if key == 'vertexShader':
                    self.assertIn('vec3(0.0,0.0,0.4375))/0.25', source)
        self.assertIs(data.POSE['accepted'], False)


if __name__ == '__main__':
    unittest.main()
