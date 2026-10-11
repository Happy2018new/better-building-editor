"""Explicit supplied shapes verify planning; they do not establish native heights."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cell import AIR, make_cell
from projection.debug_blueprints import material
from projection.model import Document
from projection.liquid_render_plan import (ALL_FACES, FACE_NAMES, LiquidGroup, LiquidSurface,
                                           iter_groups, iter_group_steps, render_steps)


class SuppliedShapeProvider(object):
    def __init__(self, callback=None):
        self.requests, self.callback = [], callback

    def surface(self, document, pos, layer, value):
        self.requests.append((document, pos, layer, value))
        if self.callback is not None:
            return self.callback(document, pos, layer, value)
        texture = 'still_water_grey' if 'water' in value[0] else 'still_lava'
        return LiquidSurface(pos, layer, (.2, .4, .6, .8), ALL_FACES, texture)


class LiquidRenderPlanTests(unittest.TestCase):
    def test_both_logical_layers_and_actor_snapshot_are_preserved(self):
        water, fence = material('water'), material('oak_fence')
        values = {(1, 1, 1): make_cell(fence, water, {'id': 'test', 'value': 3}),
                  (2, 1, 1): make_cell(water, fence)}
        document = Document((4, 4, 4), values)
        before = deepcopy(document.to_data())
        provider = SuppliedShapeProvider()
        groups = list(iter_groups(document, provider))
        self.assertEqual({((1, 1, 1), 1), ((2, 1, 1), 0)},
                         {(shape.position, shape.layer) for group in groups for shape in group.surfaces})
        self.assertEqual(before, document.to_data())
        self.assertTrue(all(request[0] is document for request in provider.requests))

    def test_missing_targets_keep_complete_source_neighbor_context(self):
        water = material('water')
        document = Document((4, 4, 4), {(1, 1, 1): water, (2, 1, 1): water})
        targets = document.palette_data(lambda pos: pos == (1, 1, 1))
        provider = SuppliedShapeProvider()
        groups = list(iter_groups(document, provider, targets))
        self.assertEqual(1, sum(len(group.surfaces) for group in groups))
        self.assertIs(document, provider.requests[0][0])
        self.assertEqual(water, provider.requests[0][0].get((2, 1, 1)))

    def test_full_groups_are_bounded_and_partial_groups_use_their_own_origins(self):
        document = Document((8, 2, 4), {(x, 1, z): material('water') for x in range(8) for z in range(4)})
        groups = list(iter_groups(document, SuppliedShapeProvider()))
        self.assertEqual(8, len(groups))
        self.assertEqual(32, sum(len(group.surfaces) for group in groups))
        for group in groups:
            self.assertEqual(4, len(group.surfaces))
            self.assertTrue(all(0 <= shape.position[axis] - group.origin[axis] < 4
                                for shape in group.surfaces for axis in range(3)))

    def test_group_appearance_uses_final_document_biome_and_preserves_unspecified_opacity(self):
        document = Document((4, 2, 4), {(1, 1, 1): material('water')}, biome='swampland')
        with patch('projection.liquid_render_plan.biomes.water_appearance', return_value=((1, 2, 3), None)) as lookup:
            groups = list(iter_groups(document, SuppliedShapeProvider()))
        lookup.assert_called_once_with('swampland')
        self.assertEqual(('swampland', (1, 2, 3), None),
                         (groups[0].biome, groups[0].tint, groups[0].opacity))

    def test_lava_appearance_does_not_use_biome_water_tint(self):
        document = Document((4, 2, 4), {(1, 1, 1): material('lava')}, biome='swampland')
        with patch('projection.liquid_render_plan.biomes.water_appearance') as lookup:
            group, = list(iter_groups(document, SuppliedShapeProvider()))
        lookup.assert_not_called()
        self.assertEqual(((255, 255, 255), None), (group.tint, group.opacity))

    def test_shape_provider_cannot_silently_omit_shapes_or_move_layers(self):
        document = Document((4, 2, 4), {(1, 1, 1): material('water')})
        callbacks = (lambda doc, pos, layer, value: None,
                     lambda doc, pos, layer, value: LiquidSurface(pos, 1, (.5,) * 4, 1, 'still_water_grey'),
                     lambda doc, pos, layer, value: LiquidSurface(pos, layer, (.5,) * 4, 1, 'still_lava'))
        for callback in callbacks:
            with self.subTest(callback=callback), self.assertRaises(ValueError):
                list(iter_groups(document, SuppliedShapeProvider(callback)))

    def test_explicit_zero_faces_culls_only_the_selected_draw(self):
        document = Document((4, 2, 4), {(1, 1, 1): material('water')})
        provider = SuppliedShapeProvider(lambda doc, pos, layer, value:
                                         LiquidSurface(pos, layer, (.5,) * 4, 0, 'still_water_grey'))
        self.assertEqual([], list(iter_groups(document, provider)))
        self.assertEqual(1, len(provider.requests))

    def test_stale_target_values_invalid_indices_and_duplicate_layer_positions_are_rejected(self):
        document = Document((4, 2, 4), {(1, 1, 1): material('water')})
        targets = document.palette_data()
        for invalid in (dict(targets, volume=(4, 4, 3)),
                        dict(targets, common={material('water'): [99]}),
                        dict(targets, common={material('water'): [21, 21]}),
                        dict(targets, common={material('flowing_water'): [21]})):
            with self.subTest(targets=invalid), self.assertRaises(ValueError):
                list(iter_groups(document, SuppliedShapeProvider(), invalid))

    def test_surface_rejects_missing_heights_invalid_layers_and_unattributed_flow_uvs(self):
        for changes in ({'heights': None}, {'heights': (.1, .2, float('nan'), .4)},
                        {'heights': (.1, .2, True, .4)}, {'layer': True}, {'faces': 64},
                        {'texture_key': 'flowing_water_grey'}, {'flow_uv': ('flow', 256)},
                        {'flow_uv': (['flow'], 0)}, {'flow_uv': (3, 0)}):
            arguments = dict(position=(1, 1, 1), layer=0, heights=(.1, .2, .3, .4),
                             faces=ALL_FACES, texture_key='still_water_grey')
            arguments.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                LiquidSurface(**arguments)

    def test_group_constructor_rejects_incompatible_shapes_and_invalid_appearance(self):
        surface = LiquidSurface((1, 1, 1), 0, (.5,) * 4, ALL_FACES, 'still_water_grey')
        other = LiquidSurface((2, 1, 1), 0, (.5,) * 4, ALL_FACES, 'still_lava')
        for changes in ({'origin': (1, 0, 0)}, {'surfaces': (surface, surface)},
                        {'surfaces': (surface, other)}, {'tint': (256, 0, 0)}, {'opacity': True}):
            arguments = dict(origin=(0, 0, 0), surfaces=(surface,), biome='plains', tint=(255, 255, 255), opacity=None)
            arguments.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                LiquidGroup(**arguments)

    def test_face_order_and_source_scanner_include_standalone_background_liquid(self):
        self.assertEqual(('top', 'north', 'south', 'west', 'east', 'bottom'), FACE_NAMES)
        document = Document((4, 2, 4), {(1, 1, 1): make_cell(AIR, material('water'))})
        group, = list(iter_groups(document, SuppliedShapeProvider()))
        self.assertEqual(1, group.surfaces[0].layer)

    def test_fully_concealed_scan_yields_frame_checkpoints(self):
        document = Document((16, 2, 16), {(x, 1, z): material('water')
                                        for x in range(16) for z in range(16)})
        shapes = SuppliedShapeProvider(lambda doc, pos, layer, value:
                                       LiquidSurface(pos, layer, (.5,) * 4, 0, 'still_water_grey'))
        checkpoints = list(iter_group_steps(document, shapes))
        self.assertGreaterEqual(len(checkpoints), 2)
        self.assertTrue(all(item is None for item in checkpoints))
        self.assertEqual([], list(iter_groups(document, shapes)))

    def test_sparse_mixed_chunks_yield_before_reaching_distant_liquid(self):
        values = {(0, 0, 0): material('stone'), (15, 15, 15): material('water')}
        document = Document((16, 16, 16), values)
        shapes = SuppliedShapeProvider()
        steps = iter_group_steps(document, shapes)
        self.assertIsNone(next(steps))
        self.assertEqual([], shapes.requests)
        result = list(steps)
        self.assertGreaterEqual(sum(item is None for item in result), 30)
        self.assertEqual([(15, 15, 15)], [shape.position for group in result if group is not None
                                        for shape in group.surfaces])

    def test_absent_liquids_skip_chunks_even_after_previous_liquid_was_removed(self):
        document = Document((16, 16, 16), {(0, 0, 0): material('water')})
        document.blocks[(0, 0, 0)] = material('stone')
        class ForbiddenChunks(dict):
            def __iter__(self):
                raise AssertionError('No-liquid plan must not scan chunks')
        document.blocks.chunks = ForbiddenChunks(document.blocks.chunks)
        shapes = SuppliedShapeProvider()
        self.assertEqual([], list(iter_group_steps(document, shapes)))
        self.assertEqual([], shapes.requests)

    def test_visibility_does_not_replace_complete_neighbor_source(self):
        water = material('water')
        document = Document((4, 3, 4), {(1, 1, 1): water, (1, 2, 1): water})
        shapes = SuppliedShapeProvider()
        groups = list(iter_groups(document, shapes, visible=lambda pos: pos[1] == 1))
        self.assertEqual(1, len(shapes.requests))
        self.assertIs(document, shapes.requests[0][0])
        self.assertEqual(water, shapes.requests[0][0].get((1, 2, 1)))
        self.assertEqual([(1, 1, 1)], [shape.position for group in groups for shape in group.surfaces])

    def test_render_slots_stay_stable_across_appearance_and_payload_changes(self):
        document = Document((4, 2, 4), {(x, 1, z): material('water')
                                       for x in range(4) for z in range(4)})
        models = {('still_water_grey', None): 'modern_projection_liquid_still_water_grey'}
        first = list(render_steps(iter_groups(document, SuppliedShapeProvider()), models, .4, 4))
        document.biome = 'swampland'
        changed = list(render_steps(iter_groups(document, SuppliedShapeProvider()), models, .8, 4))
        self.assertEqual([group.key for group in first], [group.key for group in changed])
        self.assertEqual([0, 1, 2, 3], [group.key[2] for group in first])
        self.assertNotEqual(first[0].uniforms, changed[0].uniforms)
        self.assertEqual(.8, changed[0].uniforms[3][3])

    def test_render_planner_has_no_resource_fallback_and_bounds_models(self):
        document = Document((4, 2, 4), {(x, 1, z): material('water')
                                       for x in range(4) for z in range(4)})
        models = {('still_water_grey', None): 'registered_model'}
        for resources, budget in (({}, 4), (models, 3), (models, True)):
            with self.subTest(resources=resources, budget=budget), self.assertRaises(ValueError):
                list(render_steps(iter_groups(document, SuppliedShapeProvider()), resources, .5, budget))
        self.assertEqual([None], list(render_steps(iter((None,)), models, .5, 4)))
