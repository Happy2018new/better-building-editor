"""Independent analytic and source-document contracts for the product water style."""
import copy
from fractions import Fraction
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
import generate_liquid_product_shapes as generate
from projection import liquid_product_shape_data as data, liquid_shape_data, liquid_flow_top_data
from projection.cell import AIR, make_cell, transform
from projection.debug_blueprints import material
from projection.liquid_flow_top import rotation_code, top_uv
from projection.liquid_product_flow_top import SnapshotFlowTop
from projection.liquid_native_shapes import product_check_version, product_shape_provider, shape_provider
from projection.liquid_render_plan import iter_groups
from projection.liquid_shape import (LiquidCornerSamples, LiquidFlowNeighbor, LiquidFlowSamples,
                                     ModernLiquidHeightRule, LiquidSnapshotFlowRule)
from projection.liquid_transport import pack_group
from projection.model import Document


def water(depth=0, name='water'):
    return material(name, {'liquid_depth': depth})


def surface(document, pos=(2, 2, 2), layer=0):
    provider = product_shape_provider(document)
    return provider.surface(document, pos, layer, document.get_layer(pos, layer))


class ProductWaterCornerTests(unittest.TestCase):
    def setUp(self):
        self.rule = ModernLiquidHeightRule(*data.HEIGHT_RULE)
        self.air = (None, False, False)

    def corner(self, center, first=None, second=None, diagonal=None):
        values = tuple(self.air if depth is None else (depth, False, False)
                       for depth in (center, first, second, diagonal))
        return self.rule.corner_context(LiquidCornerSamples(*values))

    def assert_corners(self, expected, actual):
        for height in actual:
            self.assertAlmostEqual(float(expected), height, places=14)

    def test_independent_fraction_examples_distinguish_old_and_modern_rules(self):
        for depths, expected in (((0, None, None, None), Fraction(20, 27)),
                                 ((3, None, None, None), Fraction(5, 27)),
                                 ((3, None, None, 3), Fraction(5, 27)),
                                 ((0, 3, None, None), Fraction(85, 117))):
            with self.subTest(depths=depths):
                self.assertAlmostEqual(float(expected), self.corner(*depths), places=14)
        self.assertNotAlmostEqual(float(Fraction(44, 63)), self.corner(0), places=10)

    def test_diagonal_only_liquid_does_not_connect_disjoint_low_water(self):
        document = Document((5, 4, 5), {(2, 2, 2): water(3), (1, 2, 1): water(3)})
        self.assert_corners(Fraction(5, 27), surface(document).heights)
        joined = Document((5, 4, 5), {(2, 2, 2): water(3), (1, 2, 2): water(3),
                                     (1, 2, 1): water(3)})
        self.assertAlmostEqual(float(Fraction(5, 12)), surface(joined).heights[0])

    def test_above_requires_same_family_in_sample_cell_and_diagonal_admission(self):
        # Above an empty orthogonal/diagonal sample is not a full liquid column.
        floating = Document((5, 5, 5), {(2, 2, 2): water(3),
                                        (1, 3, 2): water(), (1, 3, 1): water()})
        self.assert_corners(Fraction(5, 27), surface(floating).heights)
        isolated_diagonal = Document((5, 5, 5), {(2, 2, 2): water(3),
            (1, 2, 1): water(), (1, 3, 1): water()})
        self.assert_corners(Fraction(5, 27), surface(isolated_diagonal).heights)
        connected = Document((5, 5, 5), {(2, 2, 2): water(3), (1, 2, 2): water(3),
            (1, 2, 1): water(), (1, 3, 1): make_cell(AIR, water())})
        self.assertEqual(1., surface(connected).heights[0])

    def test_all_sixteen_states_and_aliases_preserve_uniform_pool_heights(self):
        for name in ('water', 'flowing_water'):
            for depth in range(16):
                with self.subTest(name=name, depth=depth):
                    document = Document((5, 4, 5), {(x, 2, z): water(depth, name)
                        for x in range(1, 4) for z in range(1, 4)})
                    shape = surface(document)
                    self.assert_corners(data.FLOW_OWN_HEIGHTS[depth], shape.heights)
                    self.assertEqual('still_water_grey', shape.texture_key)
                    self.assertEqual(33, shape.faces)

    def test_all_adjacent_depth_pairs_have_identical_shared_edge_quantization(self):
        for left_depth in range(16):
            for right_depth in range(16):
                document = Document((5, 4, 5), {(2, 2, 2): water(left_depth),
                                                (3, 2, 2): water(right_depth, 'flowing_water')})
                left, right = surface(document), surface(document, (3, 2, 2))
                self.assertEqual((left.heights[1], left.heights[2]),
                                 (right.heights[0], right.heights[3]))
                self.assertFalse(left.faces & 16)
                self.assertFalse(right.faces & 8)

    def test_roles_depths_and_unordered_calls_are_rejected(self):
        for samples in ((0, None, None, None), LiquidCornerSamples(self.air, self.air, self.air, self.air)):
            with self.assertRaises(ValueError):
                self.rule.corner_context(samples)
        with self.assertRaisesRegex(ValueError, 'labelled'):
            self.rule.corner(((0, False, False),) * 4)
        for depth in (-1, 16, True, .5):
            with self.assertRaises(ValueError):
                self.corner(depth)


class ProductWaterFlowTests(unittest.TestCase):
    def test_lower_neighbor_counterexample_changes_flow_without_changing_corners(self):
        original = Document((5, 4, 5), {(2, 2, 2): water()})
        draining = Document((5, 4, 5), {(2, 2, 2): water(), (2, 1, 1): water()})
        still, moving = surface(original), surface(draining)
        self.assertEqual(still.heights, moving.heights)
        self.assertIsNone(still.flow_uv)
        self.assertEqual((0., -8. / 9.), product_shape_provider(draining).flow_vector(
            draining, (2, 2, 2), 0, water()))
        self.assertEqual((data.TOP_TEMPLATE, 128), moving.flow_uv)
        # Legacy corner-gradient candidate remains a different diagnostic policy.
        self.assertEqual(shape_provider(original).surface(original, (2, 2, 2), 0, water()).heights,
                         shape_provider(draining).surface(draining, (2, 2, 2), 0, water()).heights)

    def test_all_horizontal_slope_and_drop_directions_select_java_oriented_uv(self):
        for offset, expected in (((1, 0), 192), ((0, 1), 0), ((-1, 0), 64), ((0, -1), 128)):
            for below in (False, True):
                neighbor = (2 + offset[0], 1 if below else 2, 2 + offset[1])
                document = Document((5, 4, 5), {(2, 2, 2): water(), neighbor: water(7)})
                self.assertEqual((data.TOP_TEMPLATE, expected), surface(document).flow_uv)
        east = SnapshotFlowTop(data.TOP_TEMPLATE, data.TOP_ROTATION_OFFSET)((1., 0.))[1][1]
        self.assertEqual(192, east)
        for actual, expected in zip(top_uv(0., 0., east), (.75, .25)):
            self.assertAlmostEqual(expected, actual, places=14)

    def test_stone_and_opposing_fluid_prevent_air_drop_flow(self):
        for neighbor in (material('stone'), material('lava'), make_cell(AIR, material('flowing_lava'))):
            document = Document((5, 4, 5), {(2, 2, 2): water(), (2, 2, 1): neighbor,
                                            (2, 1, 1): water()})
            self.assertIsNone(surface(document).flow_uv)
        for below in (material('lava'), make_cell(water(), material('lava'))):
            document = Document((5, 4, 5), {(2, 2, 2): water(), (2, 1, 1): below})
            self.assertIsNone(surface(document).flow_uv)

    def test_falling_saved_states_have_explicit_own_height_without_simulation(self):
        for depth in range(8, 16):
            document = Document((5, 5, 5), {(2, 2, 2): water(depth),
                                             (3, 2, 2): water(7), (2, 3, 2): water()})
            shape = surface(document)
            self.assertEqual((1.,) * 4, shape.heights)
            self.assertEqual((data.TOP_TEMPLATE, 192), shape.flow_uv)
            self.assertAlmostEqual(7. / 9., product_shape_provider(document).flow_vector(
                document, (2, 2, 2), 0, water(depth))[0])

    def test_symmetric_snapshot_is_still_and_vector_is_independent_of_heights(self):
        document = Document((5, 4, 5), {(2, 2, 2): water(),
            (1, 2, 2): water(7), (3, 2, 2): water(7), (2, 1, 1): water(), (2, 1, 3): water()})
        self.assertEqual((0., 0.), product_shape_provider(document).flow_vector(document, (2, 2, 2), 0, water()))
        self.assertIsNone(surface(document).flow_uv)

    def test_flow_requires_complete_roles_and_valid_finite_inputs(self):
        rule = LiquidSnapshotFlowRule(data.FLOW_OWN_HEIGHTS, data.FLOW_BELOW_DROP)
        neighbor = LiquidFlowNeighbor(None, False, None, True, True)
        for samples in ((), LiquidFlowSamples(None, neighbor, neighbor, neighbor, neighbor),
                        LiquidFlowSamples(0, None, neighbor, neighbor, neighbor)):
            with self.assertRaises(ValueError):
                rule.vector(samples)
        for heights, drop in (([.8] * 15, .8), ([.8] * 16, True), ([.8] * 16, 0),
                              ([float('nan')] * 16, .8)):
            with self.assertRaises(ValueError):
                LiquidSnapshotFlowRule(heights, drop)
        top = SnapshotFlowTop(data.TOP_TEMPLATE, data.TOP_ROTATION_OFFSET)
        for vector in ((float('nan'), 0), (float('inf'), 0), (True, 0), (0,)):
            with self.assertRaises(ValueError):
                top(vector)

    def test_all_encoded_uv_codes_preserve_the_explicit_quarter_turn_offset(self):
        selector = SnapshotFlowTop(data.TOP_TEMPLATE, -64)
        for code in range(256):
            angle = code * 2. * math.pi / 256.
            selected = selector((math.cos(angle), math.sin(angle)))
            self.assertEqual((data.TOP_TEMPLATE, (code - 64) % 256), selected[1])


class ProductWaterDocumentTests(unittest.TestCase):
    def asymmetric(self, body='oak_stairs'):
        wet = make_cell(material(body), water(3), {'custom': {'typed': [1, 2]}})
        return Document((7, 5, 7), {(3, 2, 3): wet, (4, 2, 3): water(7),
            (3, 2, 2): material('stone'), (2, 1, 3): water(), (4, 2, 4): water(2)})

    def test_waterlogged_fence_slab_and_stair_keep_logical_layers_and_actor(self):
        for body in ('oak_fence', 'oak_slab', 'oak_stairs'):
            document = self.asymmetric(body)
            before = copy.deepcopy(document.to_data())
            shape = surface(document, (3, 2, 3), 1)
            other = copy.deepcopy(document)
            other.set_cell((3, 2, 3), make_cell(water(3), material(body), {'custom': {'typed': [1, 2]}}))
            swapped = surface(other, (3, 2, 3), 0)
            self.assertEqual((shape.heights, shape.faces, shape.flow_uv),
                             (swapped.heights, swapped.faces, swapped.flow_uv))
            self.assertEqual(1, shape.layer)
            self.assertEqual(0, swapped.layer)
            self.assertEqual(before, document.to_data())

    def test_filtering_missing_projection_targets_retains_all_context_and_transport(self):
        document = self.asymmetric()
        before = copy.deepcopy(document.to_data())
        complete = list(iter_groups(document, product_shape_provider(document)))
        targets = document.palette_data(lambda pos: pos == (3, 2, 3))
        missing = list(iter_groups(document, product_shape_provider(document), targets))
        expected = [shape for group in complete for shape in group.surfaces if shape.position == (3, 2, 3)]
        actual = [shape for group in missing for shape in group.surfaces]
        signature = lambda shape: (shape.position, shape.layer, shape.heights, shape.faces,
                                   shape.texture_key, shape.flow_uv)
        self.assertEqual([signature(shape) for shape in expected], [signature(shape) for shape in actual])
        shape, = actual
        packed = pack_group((0, 0, 0), tuple(actual), (255, 255, 255), None, 1.)
        self.assertEqual(shape.flow_uv[1], int(packed[0][0]) // 4096)
        self.assertEqual(before, document.to_data())

    def test_horizontal_rotation_and_mirrors_transform_height_faces_and_snapshot_flow(self):
        document = self.asymmetric()
        original = surface(document, (3, 2, 3), 1)
        direction = product_shape_provider(document).flow_vector(document, (3, 2, 3), 1, water(3))
        cases = (
            ('rotate_y90', lambda x, y, z: (6-z, y, x), (3, 0, 1, 2), (0, 4, 3, 1, 2, 5),
             lambda x, z: (-z, x)),
            ('mirror_x', lambda x, y, z: (6-x, y, z), (1, 0, 3, 2), (0, 1, 2, 4, 3, 5),
             lambda x, z: (-x, z)),
            ('mirror_z', lambda x, y, z: (x, y, 6-z), (3, 2, 1, 0), (0, 2, 1, 3, 4, 5),
             lambda x, z: (x, -z)))
        for operation, point, corner_order, face_order, vector in cases:
            changed = Document(document.size, {point(*pos): transform(cell, operation)
                                               for pos, cell in document.blocks.items()})
            shape = surface(changed, (3, 2, 3), 1)
            self.assertEqual(tuple(original.heights[index] for index in corner_order), shape.heights)
            expected_faces = sum(1 << new for old, new in enumerate(face_order) if original.faces & (1 << old))
            self.assertEqual(expected_faces, shape.faces)
            expected_direction = vector(*direction)
            self.assertEqual(expected_direction, product_shape_provider(changed).flow_vector(
                changed, (3, 2, 3), 1, water(3)))
            self.assertEqual((rotation_code(*expected_direction) - 64) % 256, shape.flow_uv[1])

    def test_partial_neighbor_faces_remain_and_only_opaque_full_cube_face_is_culled(self):
        for body in ('oak_fence', 'oak_slab', 'oak_stairs', 'glass_pane', 'trapdoor'):
            document = Document((5, 4, 5), {(2, 2, 2): water(), (3, 2, 2): material(body)})
            self.assertTrue(surface(document).faces & 16, body)
        document = Document((5, 4, 5), {(2, 2, 2): water(), (3, 2, 2): material('stone')})
        self.assertEqual(47, surface(document).faces)

    def test_provider_lifetime_requires_source_identity_and_bounded_queries(self):
        document = Document((64, 4, 64), {(0, 0, 0): water()})
        provider = product_shape_provider(document)
        edge = provider.surface(document, (0, 0, 0), 0, water())
        self.assertIsNone(edge.flow_uv)
        with self.assertRaises(ValueError):
            provider.flow_vector(Document(document.size), (0, 0, 0), 0, water())
        provider.CACHE_SIZE = 8
        for x in range(32):
            provider._sample((x, 1, 1), 'water')
        self.assertEqual(8, len(provider.cache))
        self.assertNotIn(((0, 1, 1), 'water'), provider.cache)
        self.assertIsNone(getattr(provider.flow_top, 'provider', None))


class ProductWaterProvenanceTests(unittest.TestCase):
    def snapshot(self):
        return (json.loads(generate.DEFAULT_SOURCE.read_text(encoding='utf8')),
                json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8')),
                json.loads((ROOT / 'tools/data/java_liquid_reference_sources_20261013.json').read_text(encoding='utf8')))

    def test_reproducible_source_fingerprint_and_no_native_acceptance_promotion(self):
        source, manifest, references = self.snapshot()
        generate.validate(source, manifest, references)
        self.assertEqual(generate.runtime_source(source), generate.DEFAULT_OUTPUT.read_text(encoding='ascii'))
        self.assertEqual(data.PRODUCT_RULES_SHA256, generate.digest(source))
        self.assertFalse(data.NATIVE_PARITY_CLAIMED)
        self.assertFalse(liquid_shape_data.PRODUCTION_ACCEPTED)
        self.assertFalse(liquid_flow_top_data.PRODUCTION_ACCEPTED)

    def test_generator_rejects_stale_registry_rule_uv_and_reference_contracts(self):
        source, manifest, references = self.snapshot()
        for field, value in (('schema_version', 2), ('game_version', 'future'),
                              ('palette_sha256', '0'*64), ('supported_names', ['minecraft:water']),
                              ('product_style_version', 'future'), ('height_policy', 'legacy'),
                              ('native_parity_claimed', True), ('top_rotation_offset', 0),
                              ('rotation_steps', True)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                generate.validate(dict(source, **{field: value}), manifest, references)
        for field, value in (('heights', [.5]*16), ('weights', [1]*16),
                              ('flow_below_drop', .5), ('falling_depth_policy', 'implicit')):
            changed = copy.deepcopy(source)
            changed['water'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                generate.validate(changed, manifest, references)
        with self.assertRaisesRegex(ValueError, 'provenance'):
            generate.validate(source, manifest, dict(references, game_code_in_repository=True))

    def test_runtime_product_profile_drift_is_independent_of_legacy_diagnostics(self):
        for field, value in (('SOURCE_VERSION', 'future'), ('PALETTE_SHA256', '0'*64),
                              ('HEIGHT_POLICY', 'legacy'), ('NATIVE_PARITY_CLAIMED', True)):
            with patch.object(data, field, value), self.assertRaisesRegex(ValueError, 'regeneration'):
                product_check_version()
        with patch('projection.liquid_native_shapes.block_traits_data.SOURCE_VERSION', 'future'):
            with self.assertRaisesRegex(ValueError, 'regeneration'):
                product_shape_provider(Document((3, 3, 3)))
        with patch('projection.liquid_native_shapes.source.SOURCE_VERSION', 'future'):
            product_shape_provider(Document((3, 3, 3)))
        with self.assertRaises(ValueError):
            product_shape_provider(Document((3, 3, 3)), supported_names=('minecraft:lava',))


if __name__ == '__main__':
    unittest.main()
