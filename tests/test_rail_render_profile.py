"""Protect slope ownership at the editor/world/missing geometry boundary."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection import rail_render_profile as profile
from projection.cell import make_cell
from projection.model import Document
from projection.render_context import (ContextPaletteBuilder, prepare_context_batches,
                                       prepare_context_palette)
from projection.render_layout import OVERLAY_BASE, context_position


def index(point, volume):
    return (point[1] * volume[1] + point[0]) * volume[0] + point[2]


def position(value, volume):
    return (value // volume[0] % volume[1], value // (volume[0] * volume[1]),
            value % volume[0])


def points(palette, material):
    return tuple(position(value, palette['volume'])
                 for value in palette['common'].get(material, ()))


class RailRenderProfileTests(unittest.TestCase):
    def setUp(self):
        self.candidate = patch.object(profile, 'CANDIDATE_ENABLED', True)
        self.candidate.start()
        self.addCleanup(self.candidate.stop)

    def test_unqualified_candidate_retains_the_original_production_route(self):
        with patch.object(profile, 'CANDIDATE_ENABLED', False):
            self.assertFalse(any(profile.independent_body(value) for value in profile.MATERIALS))

    def test_only_registered_slopes_are_independent_including_each_power_state(self):
        self.assertEqual(4, len(profile.RAIL_NAMES))
        expected = set()
        for name in profile.RAIL_NAMES:
            observed = set()
            for aux in registry.aux_values(name):
                material = (name, aux)
                state = registry.states(material)
                slope = state['rail_direction'] in (2, 3, 4, 5)
                self.assertEqual(slope, profile.independent_body(material), material)
                if slope:
                    expected.add(material)
                    observed.add((state['rail_direction'], state.get('rail_data_bit')))
            bits = (None,) if name == 'minecraft:rail' else (False, True)
            self.assertEqual(set((shape, bit) for shape in (2, 3, 4, 5)
                                 for bit in bits), observed)
        self.assertEqual(expected, profile.MATERIALS)
        for value in (None, ('minecraft:stone', 0), ('minecraft:rail', 123456),
                      ('example:rail', 2)):
            self.assertFalse(profile.independent_body(value))

    def test_all_slopes_have_one_unclipped_world_draw_and_native_state(self):
        for material in sorted(profile.MATERIALS):
            with self.subTest(material=material):
                doc = Document((32, 4, 32), {
                    (15, 1, 15): material,
                    (15, 0, 15): ('minecraft:stone', 0),
                    (16, 1, 15): ('minecraft:stone', 0)})
                saved = copy.deepcopy(doc.to_data())
                output = prepare_context_batches(doc, doc.palette_data())
                emitted = []
                for origin, packed, palette in output['_context_batches']:
                    for local in points(palette, material):
                        self.assertFalse(packed, 'Slope must bypass center-cell clipping')
                        emitted.append(tuple(origin[axis] + local[axis] for axis in range(3)))
                        self.assertEqual(registry.states(material), palette['states'][material])
                self.assertEqual([(15, 1, 15)], emitted)
                self.assertEqual(saved, doc.to_data())

    def test_occupied_slope_is_absent_while_its_secondary_water_stays_in_context(self):
        slope = registry.from_states('minecraft:rail', {'rail_direction': 2})
        flat = registry.from_states('minecraft:rail', {'rail_direction': 1})
        water = ('minecraft:water', 0)
        low, middle, high = (14, 1, 15), (15, 1, 15), (16, 2, 15)
        doc = Document((32, 4, 32), {low: flat, middle: make_cell(slope, water), high: flat})
        saved = copy.deepcopy(doc.to_data())
        for visible in ((low,), (high,), (low, high), (middle,), (low, middle, high)):
            with self.subTest(visible=visible):
                output = prepare_context_batches(doc, doc.palette_data(lambda pos: pos in visible))
                copies = sum(len(palette['common'].get(slope, ()))
                             for unused, unused2, palette in output['_context_batches'])
                self.assertEqual(int(middle in visible), copies)
                if low in visible or high in visible:
                    water_copies = sum(len(palette[layer].get(water, ()))
                                       for unused, packed, palette in output['_context_batches']
                                       if packed for layer in ('common', 'extra'))
                    self.assertGreater(water_copies, 0)
                self.assertEqual(saved, doc.to_data())

    def test_legacy_center_context_would_duplicate_slope_in_occupied_neighbor_tiles(self):
        slope = registry.from_states('minecraft:golden_rail',
                                     {'rail_direction': 2, 'rail_data_bit': True})
        lower, upper = (15, 1, 15), (16, 2, 15)
        doc = Document((32, 4, 32), {lower: slope, upper: ('minecraft:stone', 0)})
        targets = doc.palette_data(lambda pos: pos == upper)
        with patch('projection.render_context.independent_rail_body', return_value=False):
            legacy = prepare_context_batches(doc, targets)
        self.assertTrue(any(slope in palette['common'] for unused, packed, palette
                            in legacy['_context_batches'] if packed))
        fixed = prepare_context_batches(doc, targets)
        self.assertFalse(any(slope in palette['common'] for unused, unused2, palette
                             in fixed['_context_batches']))

    def test_small_reference_and_incremental_context_share_slope_ownership(self):
        slope = registry.from_states('minecraft:rail', {'rail_direction': 5})
        target, neighbor = (2, 1, 2), (2, 2, 3)
        doc = Document((5, 4, 5), {target: slope, neighbor: ('minecraft:stone', 0)})
        expected = prepare_context_palette(doc.palette_data(), doc.palette_data())
        builder = ContextPaletteBuilder(doc, doc.palette_data())
        for unused in builder.prepare():
            pass
        for palette in (expected, builder.data):
            self.assertEqual(((target[0], target[1] + OVERLAY_BASE, target[2]),),
                             points(palette, slope))
            self.assertNotIn(index(context_position(target), palette['volume']),
                             palette['common'][slope])
        self.assertEqual(expected, builder.data)

    def context_plans(self, doc, targets):
        reference = prepare_context_palette(doc.palette_data(), targets)
        incremental = ContextPaletteBuilder(doc, targets)
        for unused in incremental.prepare():
            pass
        self.assertEqual(reference, incremental.data)
        batched = prepare_context_batches(doc, targets)
        return (('reference', (reference,)), ('incremental', (incremental.data,)),
                ('batched', tuple(row[2] for row in batched['_context_batches'])))

    def test_slope_only_target_does_not_copy_support_into_an_unowned_neighbor_tile(self):
        slope = registry.from_states('minecraft:activator_rail',
                                     {'rail_direction': 2, 'rail_data_bit': False})
        target, support = (2, 1, 2), (2, 0, 2)
        doc = Document((5, 4, 5), {target: slope, support: ('minecraft:stone', 0)})
        saved = copy.deepcopy(doc.to_data())
        targets = doc.palette_data(lambda pos: pos == target)
        for name, palettes in self.context_plans(doc, targets):
            with self.subTest(planner=name):
                self.assertEqual(1, len(palettes))
                palette = palettes[0]
                self.assertEqual({slope}, set(palette['common']))
                self.assertEqual(1, len(palette['common'][slope]))
                self.assertEqual({}, palette['extra'])
                self.assertEqual({slope: registry.states(slope)}, palette['states'])
        self.assertEqual(saved, doc.to_data())

    def test_secondary_water_keeps_slope_neighbor_tile_in_all_planners(self):
        slope = registry.from_states('minecraft:rail', {'rail_direction': 4})
        water, stone = ('minecraft:water', 0), ('minecraft:stone', 0)
        target, support, wet_neighbor = (2, 1, 2), (2, 0, 2), (2, 1, 3)
        doc = Document((5, 4, 5), {target: make_cell(slope, water), support: stone,
                                  wet_neighbor: make_cell(('minecraft:rail', 0), water)})
        targets = doc.palette_data(lambda pos: pos == target)
        for name, palettes in self.context_plans(doc, targets):
            with self.subTest(planner=name):
                self.assertEqual(1, sum(len(p['common'].get(slope, ())) for p in palettes))
                self.assertEqual(1, sum(len(p['common'].get(stone, ())) for p in palettes))
                # The water at the owner and the wet neighbor both remain as
                # native input, even if layer normalization promotes one copy.
                self.assertEqual(2, sum(len(p[layer].get(water, ()))
                                         for p in palettes for layer in ('common', 'extra')))

    def test_regular_target_keeps_its_own_support_context_beside_an_independent_slope(self):
        slope = registry.from_states('minecraft:rail', {'rail_direction': 2})
        flat = registry.from_states('minecraft:rail', {'rail_direction': 1})
        stone = ('minecraft:stone', 0)
        owner, support, regular = (2, 1, 2), (2, 0, 2), (3, 1, 2)
        doc = Document((5, 4, 5), {owner: slope, support: stone, regular: flat})
        saved = copy.deepcopy(doc.to_data())
        for selected in ((owner, regular), (regular,)):
            targets = doc.palette_data(lambda pos: pos in selected)
            for name, palettes in self.context_plans(doc, targets):
                with self.subTest(planner=name, selected=selected):
                    self.assertEqual(int(owner in selected),
                                     sum(len(p['common'].get(slope, ())) for p in palettes))
                    # Only the regular target's tile needs its native support
                    # context. Do not delete this source cell or copy it twice.
                    self.assertEqual(1, sum(len(p['common'].get(stone, ())) for p in palettes))
                    self.assertEqual(1, sum(len(p['common'].get(flat, ())) for p in palettes))
        self.assertEqual(saved, doc.to_data())

    def test_xyz_chunk_corner_and_hidden_view_keep_only_the_visible_slope_owner(self):
        slope = registry.from_states('minecraft:activator_rail',
                                     {'rail_direction': 2, 'rail_data_bit': True})
        flat = registry.from_states('minecraft:activator_rail',
                                    {'rail_direction': 1, 'rail_data_bit': True})
        lower, upper = (15, 15, 15), (16, 16, 15)
        doc = Document((32, 32, 32), {lower: slope, upper: flat})
        for visible, expected in (((lower, upper), ((15, 15, 15),)),
                                  ((lower,), ((15, 15, 15),)), ((upper,), ())):
            with self.subTest(visible=visible):
                data = prepare_context_batches(doc, doc.palette_data(lambda pos: pos in visible))
                actual = []
                for origin, packed, palette in data['_context_batches']:
                    for point in points(palette, slope):
                        self.assertFalse(packed)
                        self.assertEqual((16, 16, 16), palette['volume'])
                        actual.append(tuple(point[i] + origin[i] for i in range(3)))
                self.assertEqual(expected, tuple(actual))
        # Layer suppression is independent of missing-only target selection.
        data = prepare_context_batches(doc, doc.palette_data(lambda pos: pos == upper),
                                        visible_layer=lambda y: y != 15)
        self.assertFalse(any(slope in palette['common']
                             for unused, unused2, palette in data['_context_batches']))


if __name__ == '__main__':
    unittest.main()
