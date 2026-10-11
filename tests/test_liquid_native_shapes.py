"""Version drift and complete-source contracts for the native shape candidate."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
import generate_liquid_shapes as generate
from projection.cell import AIR, make_cell
from projection.debug_blueprints import material
from projection.liquid_native_shapes import shape_provider
from projection.liquid_render_plan import iter_groups
from projection.model import Document


class NativeLiquidShapeTests(unittest.TestCase):
    def snapshot(self):
        data = json.loads(generate.DEFAULT_SOURCE.read_text(encoding='utf8'))
        manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
        return data, manifest

    def test_generated_source_matches_candidate_without_acceptance_promotion(self):
        data, manifest = self.snapshot()
        generate.validate(data, manifest)
        self.assertEqual(generate.DEFAULT_OUTPUT.read_text(encoding='ascii'), generate.runtime_source(data))
        self.assertFalse(data['accepted'])
        self.assertFalse(data['evidence']['production_accepted'])
        self.assertIn('PRODUCTION_ACCEPTED = False', generate.runtime_source(data))

    def test_generator_rejects_partial_invalid_rules_and_version_drift(self):
        data, manifest = self.snapshot()
        variants = [dict(data, schema_version=2), dict(data, game_version='future'),
                    dict(data, palette_sha256='0' * 64), dict(data, supported_names=['minecraft:stone']),
                    dict(data, supported_names=['minecraft:water', 'minecraft:water']),
                    dict(data, supported_names=['minecraft:lava'])]
        for field, value in (('heights', [1.] * 15), ('weights', [0] * 16), ('above_height', True)):
            changed = copy.deepcopy(data)
            changed['rules']['water'][field] = value
            variants.append(changed)
        for changed in variants:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                generate.validate(changed, manifest)

    def test_runtime_rejects_stale_shapes_and_stale_native_block_traits(self):
        for module in ('source', 'block_traits_data'):
            with patch('projection.liquid_native_shapes.' + module + '.SOURCE_VERSION', 'future'):
                with self.assertRaisesRegex(ValueError, 'regeneration'):
                    shape_provider(Document((4, 4, 4)))

    def test_native_stone_neighbors_change_corners_and_cull_only_matching_face(self):
        water = material('water')
        document = Document((4, 4, 4), {(1, 1, 1): water})
        before = shape_provider(document).surface(document, (1, 1, 1), 0, water)
        document.set_cell((2, 1, 1), material('stone'))
        after = shape_provider(document).surface(document, (1, 1, 1), 0, water)
        self.assertEqual(before.heights[0], after.heights[0])
        self.assertGreater(after.heights[1], before.heights[1])
        self.assertTrue(before.faces & 16)
        self.assertFalse(after.faces & 16)
        self.assertEqual(before.faces & ~16, after.faces)

    def test_background_only_and_waterlogged_copy_keep_layers_and_actor_isolation(self):
        water = material('water')
        document = Document((6, 3, 6), {(1, 1, 1): make_cell(AIR, water),
            (2, 1, 1): make_cell(material('oak_fence'), water, {'tag': {'value': [1, 2]}})})
        original = copy.deepcopy(document.to_data())
        full = {shape.position: shape for group in iter_groups(document, shape_provider(document))
                for shape in group.surfaces}
        targets = document.palette_data(lambda pos: pos == (2, 1, 1))
        selected = next(iter_groups(document, shape_provider(document), targets)).surfaces[0]
        self.assertEqual(full[selected.position].heights, selected.heights)
        self.assertEqual(full[selected.position].faces, selected.faces)
        self.assertEqual(1, selected.layer)
        self.assertEqual(original, document.to_data())

    def test_unverified_flowing_name_is_not_silently_normalized(self):
        document = Document((4, 3, 4), {(1, 1, 1): material('flowing_water')})
        with self.assertRaisesRegex(ValueError, 'validated shape profile'):
            list(iter_groups(document, shape_provider(document)))
