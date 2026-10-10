import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import make_cell
from projection.entity_render import CHEST_DIRECTIONS, CHEST_PROXIES
from projection.debug_blueprints import BLUEPRINTS, build, material
from projection.model import Document
from projection.render_context import (MAX_CONTEXT_CHUNK_CACHE, TARGETS_PER_UNIT,
                                       ContextPaletteBuilder, prepare_context_palette)
from projection.render_layout import (CONTEXT_BASE, OVERLAY_BASE, context_center,
                                      context_position, logical_position,
                                      native_mesh_position)
from projection.visible_actor import compose_actor


def index(pos, volume):
    return (pos[1] * volume[1] + pos[0]) * volume[0] + pos[2]


def position(value, volume):
    return (value // volume[0] % volume[1], value // (volume[0] * volume[1]), value % volume[0])


class RenderContextTests(unittest.TestCase):
    def assert_incremental_matches_reference(self, document, targets):
        expected = prepare_context_palette(document.palette_data(), targets)
        builder = ContextPaletteBuilder(document, targets)
        for unused in builder.prepare():
            pass
        actual = copy.deepcopy(builder.data)
        for layer in ('common', 'extra'):
            actual[layer] = dict((value, sorted(entries))
                                 for value, entries in actual[layer].items())
        self.assertEqual(expected, actual)
        return builder

    def test_incremental_preparation_matches_complete_palette_for_eight_blueprints(self):
        for name, unused_category, unused_label, unused_size, unused_block in BLUEPRINTS:
            if name == 'test.registry.vanilla':
                continue
            with self.subTest(blueprint=name):
                document = build(name)
                targets = document.palette_data(lambda pos: pos[1] > 0)
                self.assert_incremental_matches_reference(document, targets)

    def test_chunk_decode_cache_stays_bounded_and_eviction_keeps_all_targets(self):
        stone = material('stone')
        values = {(x * 16 + 1, y * 16 + 1, z * 16 + 1): stone
                  for y in range(8) for x in range(4) for z in range(4)}
        document = Document((64, 128, 64), values)
        saved = document.blocks.copy()
        builder = self.assert_incremental_matches_reference(document, document.palette_data())
        self.assertEqual(MAX_CONTEXT_CHUNK_CACHE, len(builder.chunk_cache))
        self.assertEqual(len(values), len(builder.positions))
        self.assertEqual(saved, document.blocks)

    def test_preparation_batches_remain_bounded_and_yield_final_partial_unit(self):
        stone = material('stone')
        document = Document((33, 1, 1), {(x, 0, 0): stone for x in range(33)})
        builder = ContextPaletteBuilder(document, document.palette_data())
        observed = []
        with patch.object(builder, 'put_target', wraps=builder.put_target) as put:
            previous = 0
            for unused in builder.prepare():
                count = put.call_count - previous
                self.assertLessEqual(count, TARGETS_PER_UNIT)
                if count:
                    observed.append(count)
                previous = put.call_count
        self.assertEqual([16, 16, 1], observed)
        self.assertEqual(33, sum(observed))

    def test_hidden_neighbor_stairs_and_both_layers_survive_in_one_context_tile(self):
        stair = lambda direction: material('oak_stairs', {'weirdo_direction': direction})
        base, neighbor = (15, 1, 8), (16, 1, 8)
        water = material('water')
        doc = Document((32, 16, 16), {base: make_cell(stair(0), water),
                                    neighbor: make_cell(stair(3), water)})
        source = doc.palette_data()
        saved = copy.deepcopy(source)
        result = prepare_context_palette(source, doc.palette_data(lambda pos: pos == base))
        volume = result['volume']
        self.assertEqual((36, 64, CONTEXT_BASE + 8), volume)
        center_index = index(context_position(base), volume)
        neighbor_index = index(context_position(base, (1, 0, 0)), volume)
        self.assertEqual([center_index], result['common'][stair(0)])
        self.assertEqual([neighbor_index], result['common'][stair(3)])
        self.assertEqual({center_index, neighbor_index}, set(result['extra'][water]))
        visible_centers = {logical_position(tuple(axis + .5 for axis in position(cell, volume)))
                           for entries in result['common'].values() for cell in entries
                           if context_center(native_mesh_position(
                               tuple(axis + .5 for axis in position(cell, volume))))}
        self.assertEqual({(15.5, 1.5, 8.5)}, visible_centers)
        self.assertEqual(saved, source)

    def test_each_target_has_independent_neighbor_geometry_across_chunk_boundary(self):
        doc = Document((32, 4, 4), {(15, 1, 1): material('oak_fence'),
                                  (16, 1, 1): material('stone')})
        result = prepare_context_palette(doc.palette_data(), doc.palette_data())
        volume = result['volume']
        for target in doc.blocks:
            for original, value in doc.blocks.items():
                delta = tuple(original[axis] - target[axis] for axis in range(3))
                self.assertIn(index(context_position(target, delta), volume), result['common'][value])

    def test_actor_absolute_positions_pair_coordinates_and_nested_item_data_are_independent(self):
        first, second = (5, 2, 3), (6, 2, 3)
        chest = material('barrel')
        actor = {'x': 6, 'y': 2, 'z': 3, 'pairx': 5, 'pairz': 3,
                 'chestIsLargeChest': True, 'chestModelOffset': -.5,
                 'opaque': {'x': 99, 'y': 98, 'z': 97}}
        nbt = {'id': {'__type__': 8, '__value__': 'Chest'},
               'x': {'__type__': 3, '__value__': 6}}
        doc = Document((8, 4, 5), {first: chest, second: make_cell(chest, nbt=compose_actor(actor, nbt))})
        source = doc.palette_data()
        saved = copy.deepcopy(source)
        result = prepare_context_palette(source, source)
        values = []
        for target in (first, second):
            delta = tuple(second[axis] - target[axis] for axis in range(3))
            encoded = context_position(target, delta)
            payload = result['actor'][chest[0]][index(encoded, result['volume'])]
            self.assertEqual(encoded, tuple(payload[axis] for axis in ('x', 'y', 'z')))
            self.assertEqual(encoded[0] - 1, payload['pairx'])
            self.assertEqual(encoded[2], payload['pairz'])
            self.assertEqual(actor['opaque'], payload['opaque'])
            self.assertNotIn('nbt', payload)
            values.append(payload)
        values[0]['opaque']['x'] = 0
        self.assertEqual(99, values[1]['opaque']['x'])
        self.assertEqual(saved, source)

    def test_snow_overlay_remains_in_its_own_region_and_hidden_plants_are_not_overlaid(self):
        source = build('test.layers.snow')
        target = (3, 1, 9)
        result = prepare_context_palette(source.palette_data(), source.palette_data(lambda pos: pos == target))
        volume = result['volume']
        proxy = ('modern_projection:preview_short_grass', 0)
        overlay = index((target[0], target[1] + OVERLAY_BASE, target[2]), volume)
        self.assertEqual([overlay], result['common'][proxy])
        self.assertEqual((3, 257, 9), position(overlay, volume))
        snow = material('snow_layer', {'height': 0, 'covered_bit': True})
        self.assertEqual([index(context_position(target), volume)], result['common'][snow])
        grass = material('short_grass')
        self.assertEqual([index(context_position(target), volume)], result['extra'][grass])

    def test_native_static_shulker_pose_survives_context_without_actor_reintroduction(self):
        source = build('test.transforms.directions')
        target = (3 + 5 * 5, 3, 28)
        result = prepare_context_palette(source.palette_data(), source.palette_data(lambda pos: pos == target))
        proxy = ('modern_projection:preview_shulker_purple_5', 0)
        self.assertEqual([index(context_position(target), result['volume'])], result['common'][proxy])
        self.assertEqual({}, result['actor'])

    def test_hidden_chest_partner_keeps_each_static_half_in_incremental_context(self):
        deltas = {'north': (1, 0, 0), 'south': (-1, 0, 0),
                  'east': (0, 0, 1), 'west': (0, 0, -1)}
        for name in CHEST_PROXIES:
            if name == 'minecraft:ender_chest':
                continue
            for direction in CHEST_DIRECTIONS:
                front = registry.from_states(name, {'minecraft:cardinal_direction': direction})
                first = (15, 1, 15)
                second = tuple(first[axis] + deltas[direction][axis] for axis in range(3))
                doc = Document((32, 4, 32), {first: front, second: front})
                saved = copy.deepcopy(doc.to_data())
                for visible in (first, second):
                    with self.subTest(name=name, direction=direction, visible=visible):
                        target = doc.palette_data(lambda pos: pos == visible)
                        builder = self.assert_incremental_matches_reference(doc, target)
                        result = builder.data
                        self.assertEqual({}, result['actor'])
                        for original, part in ((first, 'main'), (second, 'sub')):
                            delta = tuple(original[axis] - visible[axis] for axis in range(3))
                            proxy = (CHEST_PROXIES[name][(direction, part)], 0)
                            self.assertEqual([index(context_position(visible, delta), result['volume'])],
                                             result['common'][proxy])
                        centers = {logical_position(tuple(axis + .5 for axis in position(cell, result['volume'])))
                                   for entries in result['common'].values() for cell in entries
                                   if context_center(tuple(axis + .5 for axis in position(cell, result['volume'])))}
                        self.assertEqual({tuple(axis + .5 for axis in visible)}, centers)
                self.assertEqual(saved, doc.to_data())

    def test_explicit_single_chest_is_not_inferred_as_a_pair_by_either_context_path(self):
        chest = material('copper_chest', {'minecraft:cardinal_direction': 'north'})
        doc = Document((4, 2, 4), {(1, 1, 1): chest, (2, 1, 1): make_cell(
            chest, nbt=compose_actor({'chestIsLargeChest': False}, None))})
        builder = self.assert_incremental_matches_reference(doc, doc.palette_data())
        proxy = (CHEST_PROXIES[chest[0]][('north', 'single')], 0)
        self.assertEqual({proxy}, set(builder.data['common']))

    def test_no_visible_targets_and_boundary_cells_do_not_manufacture_neighbors(self):
        doc = Document((1, 1, 1), {(0, 0, 0): material('stone')})
        blank = prepare_context_palette(doc.palette_data(), doc.palette_data(lambda pos: False))
        self.assertEqual({}, blank['common'])
        result = prepare_context_palette(doc.palette_data(), doc.palette_data())
        self.assertEqual(1, sum(len(entries) for entries in result['common'].values()))
        self.assertEqual((4, 4, CONTEXT_BASE + 4), result['volume'])

    def test_invalid_target_and_geometry_budget_fail_without_mutating_source(self):
        doc = Document((3, 3, 3), {(1, 1, 1): material('stone'), (2, 1, 1): material('stone')})
        source = doc.palette_data()
        saved = copy.deepcopy(source)
        with patch('projection.render_context.MAX_SURFACE_BLOCKS', 1):
            with self.assertRaisesRegex(ValueError, 'budget'):
                prepare_context_palette(source, source)
        invalid = dict(source, volume=(3, 4, 3))
        with self.assertRaisesRegex(ValueError, 'matching'):
            prepare_context_palette(source, invalid)
        invalid = dict(source, common={material('stone'): [27]})
        with self.assertRaisesRegex(ValueError, 'outside'):
            prepare_context_palette(source, invalid)
        self.assertEqual(saved, source)


if __name__ == '__main__':
    unittest.main()
