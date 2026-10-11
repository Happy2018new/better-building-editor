"""Contract properties for explicit liquid rules; not native formula evidence."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.cell import AIR, foreground, make_cell
from projection.debug_blueprints import material
from projection.liquid_render_plan import iter_groups
from projection.liquid_shape import DocumentLiquidShapes, LiquidHeightRule
from projection.model import Document


def provider(document):
    # Deliberately synthetic values, distinct from any alleged native formula.
    rule = LiquidHeightRule([.8 - (depth % 8) * .1 for depth in range(16)],
                            [4. if depth % 8 == 0 else 1. for depth in range(16)], 1., 1.)
    blocked = lambda cell: foreground(cell)[0] == 'minecraft:stone'
    return DocumentLiquidShapes(document, {'water': rule, 'lava': rule}, blocked,
                                lambda cell, face: blocked(cell),
                                ('minecraft:water', 'minecraft:lava'))


class LiquidShapeTests(unittest.TestCase):
    def test_corner_invariant_to_sample_order_and_solid_replacement(self):
        rule = LiquidHeightRule([.8] * 16, [4.] * 16, 1., 1.)
        samples = [(0, False, False), (None, False, False),
                   (None, False, False), (None, True, False)]
        self.assertAlmostEqual(.8 * 4 / 6, rule.corner(samples))
        self.assertEqual(rule.corner(samples), rule.corner(reversed(samples)))
        self.assertEqual(1., rule.corner(samples[:-1] + [(None, False, True)]))

    def test_adjacent_different_depths_have_exact_shared_edges(self):
        document = Document((6, 4, 6), {(2, 1, 2): material('water', {'liquid_depth': 0}),
                                      (3, 1, 2): material('water', {'liquid_depth': 3})})
        shapes = provider(document)
        left = shapes.surface(document, (2, 1, 2), 0, document.get((2, 1, 2)))
        right = shapes.surface(document, (3, 1, 2), 0, document.get((3, 1, 2)))
        self.assertEqual((left.heights[1], left.heights[2]), (right.heights[0], right.heights[3]))
        self.assertFalse(left.faces & (1 << 4))
        self.assertFalse(right.faces & (1 << 3))

    def test_waterlogged_layers_use_same_context_without_mutating_data(self):
        water, fence = material('water'), material('oak_fence')
        document = Document((4, 4, 4), {(1, 1, 1): make_cell(fence, water, {'test': [1, 2]})})
        before = deepcopy(document.to_data())
        first, = list(iter_groups(document, provider(document)))
        self.assertEqual(before, document.to_data())
        swapped_document = Document((4, 4, 4), {(1, 1, 1): make_cell(water, fence, {'test': [1, 2]})})
        swapped, = list(iter_groups(swapped_document, provider(swapped_document)))
        self.assertEqual(first.surfaces[0].heights, swapped.surfaces[0].heights)
        self.assertEqual(first.surfaces[0].faces, swapped.surfaces[0].faces)
        self.assertEqual(1, first.surfaces[0].layer)
        self.assertEqual(0, swapped.surfaces[0].layer)
        self.assertEqual(before, document.to_data())

    def test_missing_targets_cannot_change_neighbor_heights_or_faces(self):
        document = Document((5, 3, 5), {(1, 1, 1): material('water'),
                                      (2, 1, 1): material('water', {'liquid_depth': 2})})
        full = list(iter_groups(document, provider(document)))
        targets = document.palette_data(lambda pos: pos == (1, 1, 1))
        missing, = list(iter_groups(document, provider(document), targets))
        first = next(shape for group in full for shape in group.surfaces if shape.position == (1, 1, 1))
        self.assertEqual((first.heights, first.faces), (missing.surfaces[0].heights, missing.surfaces[0].faces))

    def test_rotating_asymmetric_neighborhood_rotates_corners_and_face_masks(self):
        blocks = {(2, 1, 2): material('water'),
                  (3, 1, 2): material('water', {'liquid_depth': 2}),
                  (2, 1, 1): material('stone'),
                  (1, 1, 3): material('water', {'liquid_depth': 5})}
        document = Document((6, 3, 6), blocks)
        rotated = Document((6, 3, 6), {(5 - z, y, x): value for (x, y, z), value in blocks.items()})
        shape = provider(document).surface(document, (2, 1, 2), 0, document.get((2, 1, 2)))
        turned = provider(rotated).surface(rotated, (3, 1, 2), 0, rotated.get((3, 1, 2)))
        self.assertEqual(tuple(shape.heights[index] for index in (3, 0, 1, 2)), turned.heights)
        face_map = (0, 4, 3, 1, 2, 5)
        expected = sum((1 << new) for old, new in enumerate(face_map) if shape.faces & (1 << old))
        self.assertEqual(expected, turned.faces)

    def test_above_water_in_either_layer_sets_touched_corners_and_culls_top(self):
        for cell in (material('water'), make_cell(AIR, material('water'))):
            document = Document((4, 4, 4), {(1, 1, 1): material('water'), (1, 2, 1): cell})
            shape = provider(document).surface(document, (1, 1, 1), 0, document.get((1, 1, 1)))
            self.assertEqual((1.,) * 4, shape.heights)
            self.assertFalse(shape.faces & 1)

    def test_opposite_fluid_families_do_not_share_height_or_hide_faces(self):
        document = Document((4, 3, 4), {(1, 1, 1): material('water'), (2, 1, 1): material('lava')})
        shape = provider(document).surface(document, (1, 1, 1), 0, document.get((1, 1, 1)))
        self.assertTrue(shape.faces & (1 << 4))
        self.assertEqual((.8 * 4 / 7,) * 4, shape.heights)

    def test_document_identity_and_unverified_alias_are_rejected(self):
        document = Document((4, 3, 4), {(1, 1, 1): material('water')})
        shapes = provider(document)
        with self.assertRaises(ValueError):
            shapes.surface(Document((4, 3, 4)), (1, 1, 1), 0, document.get((1, 1, 1)))
        document.set_cell((2, 1, 1), material('flowing_water'))
        with self.assertRaises(ValueError):
            shapes.surface(document, (1, 1, 1), 0, document.get((1, 1, 1)))

    def test_conflicting_depths_in_same_cell_are_explicitly_rejected(self):
        document = Document((4, 3, 4), {(1, 1, 1): make_cell(
            material('water'), material('water', {'liquid_depth': 3}))})
        with self.assertRaises(ValueError):
            list(iter_groups(document, provider(document)))

    def test_neighbor_cache_is_bounded(self):
        document = Document((64, 3, 64))
        shapes = provider(document)
        shapes.CACHE_SIZE = 8
        for x in range(20):
            shapes._sample((x, 1, 1), 'water')
        self.assertEqual(8, len(shapes.cache))
        self.assertNotIn(((0, 1, 1), 'water'), shapes.cache)

    def test_invalid_rule_cannot_default_to_full_height(self):
        for heights, weights in (([.8] * 15, [1.] * 16), ([True] * 16, [1.] * 16),
                                 ([.8] * 16, [0.] * 16), ([float('nan')] * 16, [1.] * 16)):
            with self.assertRaises(ValueError):
                LiquidHeightRule(heights, weights, 1., 1.)
