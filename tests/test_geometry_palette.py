import copy
import json
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.block_registry import aux_values, states
from projection.geometry_palette import LEAF_PROXIES, PLANT_PROXIES, prepare_palette
from projection.cell import make_cell
from projection.large_preview import SurfacePalette
from projection.model import Document
from projection.visible_actor import compose_actor


class GeometryPaletteTests(unittest.TestCase):
    def test_all_legacy_species_and_lifecycle_bits_use_the_matching_proxy(self):
        species = ('oak', 'spruce', 'birch', 'jungle', 'acacia', 'dark_oak')
        for index, name in enumerate(species):
            family = 'leaves' if index < 4 else 'leaves2'
            leaf_type = index if index < 4 else index - 4
            for bits in (0, 4, 8, 12):
                value = ('minecraft:' + family, leaf_type + bits)
                data = prepare_palette({'common': {value: [3]}})
                self.assertEqual({('modern_projection:preview_' + name + '_leaves', 0): [3]},
                                 data['common'])
                self.assertEqual({}, data['states'])

    def test_modern_leaf_states_merge_without_mutating_the_source(self):
        for native, proxy in LEAF_PROXIES.items():
            values = aux_values(native)
            self.assertEqual((0, 1, 2, 3), values)
            source = {'common': dict(((native, aux), [3 - aux]) for aux in values)}
            saved = copy.deepcopy(source)
            result = prepare_palette(source)
            self.assertEqual({(proxy, 0): [0, 1, 2, 3]}, result['common'])
            self.assertEqual({}, result['states'])
            self.assertEqual(saved, source)
            result['common'][(proxy, 0)].append(9)
            self.assertEqual(saved, source)

    def test_rendering_preserves_document_and_archived_leaf_identities(self):
        blocks = {(0, 0, 0): ('minecraft:leaves', 12),
                  (1, 0, 0): ('minecraft:dark_oak_leaves', 3),
                  (2, 0, 0): ('minecraft:quartz_block', 0)}
        doc = Document((3, 1, 1), blocks, biome='pale_garden')
        saved = copy.deepcopy(doc.to_data())
        render = prepare_palette(doc.palette_data())
        self.assertEqual(saved, doc.to_data())
        self.assertEqual(blocks, dict(doc.blocks.items()))
        self.assertEqual('pale_garden', Document.from_data(saved).biome)
        self.assertEqual(blocks, dict(Document.from_data(saved).blocks.items()))
        self.assertIn(('modern_projection:preview_dark_oak_leaves', 0), render['common'])

    def test_unaffected_blocks_keep_their_native_state_and_texture_identity(self):
        values = (('minecraft:cyan_stained_glass', 0), ('custom:leaves', 7))
        source = {'common': dict((value, [i]) for i, value in enumerate(values))}
        result = prepare_palette(source)
        self.assertEqual(source['common'], result['common'])
        for value in values[:-1]:
            self.assertEqual(states(value), result['states'][value])
        self.assertNotIn(values[-1], result['states'])

    def test_grass_plants_keep_their_two_block_halves(self):
        source = {'common': dict((value, [index]) for index, value
                                 in enumerate(PLANT_PROXIES))}
        saved = copy.deepcopy(source)
        result = prepare_palette(source)
        for index, proxy in enumerate(PLANT_PROXIES.values()):
            self.assertEqual([index], result['common'][(proxy, 0)])
        self.assertEqual({}, result['states'])
        self.assertEqual(saved, source)

    def test_grass_plant_proxies_have_cross_models_and_grass_colormap(self):
        appearances = json.loads((ROOT / 'resource_pack/blocks.json').read_text(encoding='utf8'))
        for proxy in PLANT_PROXIES.values():
            name = proxy.split(':')[1]
            definition = json.loads((ROOT / 'behavior_pack/netease_blocks' /
                                     (name + '.json')).read_text(encoding='utf8'))['minecraft:block']
            model = json.loads((ROOT / 'resource_pack/models/netease_block' /
                                (name + '.json')).read_text(encoding='utf8'))['netease:block_geometry']
            self.assertFalse(definition['description']['register_to_creative_menu'])
            self.assertNotIn('register_to_create_menu', definition['description'])
            self.assertEqual('alpha', definition['components']['netease:render_layer']['value'])
            self.assertTrue(definition['components']['netease:water_source']['value'])
            self.assertTrue(definition['components']['netease:water_flow_source']['value'])
            self.assertEqual(proxy, model['description']['identifier'])
            self.assertEqual(2, len(model['bones']))
            self.assertEqual(proxy, appearances[proxy]['netease_model'])
            self.assertEqual('textures/colormap/grass', appearances[proxy]['use_colormap'])

    def test_grass_geometry_is_centered_inside_its_block(self):
        # Native palette conversion mirrors the model's X axis: a block spans
        # X=-16..0 and Y/Z=0..16. Verified from front/side orthographic views.
        # Check vertices in block coordinates, including both tall halves.
        for proxy in PLANT_PROXIES.values():
            path = ROOT / 'resource_pack/models/netease_block' / (proxy.split(':')[1] + '.json')
            model = json.loads(path.read_text(encoding='utf8'))['netease:block_geometry']
            for bone in model['bones']:
                pivot = bone['pivot']
                angle = math.radians(bone['rotation'][1])
                for cube in bone['cubes']:
                    origin, size = cube['origin'], cube['size']
                    vertices = []
                    for x in (origin[0], origin[0] + size[0]):
                        for z in (origin[2], origin[2] + size[2]):
                            dx, dz = x - pivot[0], z - pivot[2]
                            vertices.append((-(pivot[0] + dx * math.cos(angle) - dz * math.sin(angle)),
                                             pivot[2] + dx * math.sin(angle) + dz * math.cos(angle)))
                    for axis in (0, 1):
                        values = [v[axis] for v in vertices]
                        self.assertAlmostEqual(8., sum(values) / len(values), msg=proxy)
                        self.assertGreaterEqual(min(values), 0., proxy)
                        self.assertLessEqual(max(values), 16., proxy)
                    self.assertEqual((0, 16), (origin[1], origin[1] + size[1]))

    def test_full_cells_keep_background_states_and_actor_data_in_geometry_palette(self):
        chest_data = {'id': 'Chest', 'Items': [], 'x': 1, 'y': 2, 'z': 3}
        surface = SurfacePalette((3, 1, 1))
        surface.add((0, 0, 0), make_cell(
            ('minecraft:oak_leaves', 0), ('minecraft:snow_layer', 3)))
        surface.add((1, 0, 0), make_cell(
            ('minecraft:chest', 0), ('minecraft:water', 0), chest_data))
        surface.add((2, 0, 0), ('minecraft:stone', 0))

        native_data = surface.palette_data()
        saved = copy.deepcopy(native_data)
        render = prepare_palette(native_data)

        self.assertEqual({('minecraft:snow_layer', 3): [0],
                          ('minecraft:water', 0): [1]}, render['extra'])
        self.assertIn(('minecraft:water', 0), render['extraStates'])
        self.assertIn(('minecraft:snow_layer', 3), render['extraStates'])
        self.assertEqual({('modern_projection:preview_oak_leaves', 0): [0],
                          ('minecraft:chest', 0): [1],
                          ('minecraft:stone', 0): [2]}, render['common'])
        self.assertEqual({'minecraft:chest': {1: chest_data}}, render['actor'])
        self.assertEqual(saved, native_data)

    def test_native_actor_boundary_only_exposes_client_render_payload(self):
        render = {'facingDirection': 2, 'chestIsLargeChest': True,
                  'chestMainSubChest': True, 'chestModelOffset': 0.0}
        nbt = {'Items': {'__type__': 9, '__value__': [
            {'Name': {'__type__': 8, '__value__': 'minecraft:diamond'}}]}}
        source = {'common': {('minecraft:chest', 2): [0, 1, 2],
                             ('minecraft:purple_shulker_box', 0): [3, 4]},
                  'actor': {'minecraft:chest': {0: compose_actor(render, nbt),
                                               1: nbt, 2: compose_actor(None, nbt)},
                            'minecraft:purple_shulker_box': {
                                3: compose_actor({}, nbt), 4: {}}}}
        saved = copy.deepcopy(source)

        result = prepare_palette(source)

        self.assertEqual({'minecraft:chest': {0: render}}, result['actor'])
        self.assertEqual([3, 4], result['common'][('modern_projection:preview_shulker_purple_1', 0)])
        self.assertEqual(saved, source)
        self.assertNotIn('Items', result['actor']['minecraft:chest'][0])

    def test_native_actor_boundary_drops_names_with_no_client_payload(self):
        typed = {'__type__': 10, '__value__': {
            'Items': {'__type__': 9, '__value__': []}}}
        self.assertEqual({}, prepare_palette({
            'actor': {'minecraft:chest': {0: typed}}})['actor'])

    def test_background_only_cells_render_in_common_without_changing_document_layers(self):
        water = ('minecraft:water', 0)
        plant = ('minecraft:short_grass', 0)
        fern = ('minecraft:fern', 0)
        doc = Document((4, 1, 1), {
            (0, 0, 0): make_cell(back=water),
            (1, 0, 0): make_cell(back=plant),
            (2, 0, 0): make_cell(back=fern),
            (3, 0, 0): make_cell(back=('custom:background', 7))})
        saved = copy.deepcopy(doc.to_data())

        result = prepare_palette(doc.palette_data())

        self.assertEqual({water: [0], ('modern_projection:preview_short_grass', 0): [1],
                          ('modern_projection:preview_fern', 0): [2],
                          ('custom:background', 7): [3]}, result['common'])
        self.assertEqual({}, result['extra'])
        self.assertEqual({}, result['extraStates'])
        self.assertEqual(saved, doc.to_data())

    def test_snow_in_either_logical_layer_uses_native_snow_front_and_plant_back(self):
        grass = ('minecraft:short_grass', 0)
        snow = ('minecraft:snow_layer', 2)
        covered = ('minecraft:snow_layer', 10)
        doc = Document((4, 1, 1), {
            (0, 0, 0): make_cell(grass, snow),
            (1, 0, 0): make_cell(covered, grass),
            (2, 0, 0): make_cell(back=covered),
            (3, 0, 0): covered})
        source = doc.palette_data()
        saved = copy.deepcopy(source)

        result = prepare_palette(source)

        self.assertEqual({covered: [0, 1], snow: [2, 3]}, result['common'])
        self.assertEqual({grass: [0, 1]}, result['extra'])
        self.assertEqual(states(covered), result['states'][covered])
        self.assertEqual(states(snow), result['states'][snow])
        self.assertEqual(states(grass), result['extraStates'][grass])
        self.assertEqual(saved, source)

    def test_unsupported_legacy_dual_layers_keep_both_materials_in_native_input(self):
        fence = ('minecraft:oak_fence', 0)
        snow = ('minecraft:snow_layer', 3)
        result = prepare_palette({'common': {fence: [0]}, 'extra': {snow: [0]}})
        self.assertEqual({fence: [0]}, result['common'])
        self.assertEqual({snow: [0]}, result['extra'])

    def test_water_in_either_logical_layer_uses_measured_native_foreground_and_liquid_back(self):
        water = ('minecraft:water', 0)
        fence = ('minecraft:oak_fence', 0)
        stone = ('minecraft:stone', 0)
        slab = ('minecraft:oak_slab', 1)
        doc = Document((5, 1, 1), {
            (0, 0, 0): make_cell(fence, water),
            (1, 0, 0): make_cell(water, fence),
            (2, 0, 0): make_cell(water, stone),
            (3, 0, 0): make_cell(back=water),
            (4, 0, 0): make_cell(water, ('minecraft:wooden_slab', 8))})
        source = doc.palette_data()
        saved = copy.deepcopy(source)
        with patch('projection.native_layers.is_waterloggable',
                   side_effect=lambda value: value in (fence, slab)):
            result = prepare_palette(source)

        self.assertEqual({fence: [0, 1], water: [2, 3], slab: [4]}, result['common'])
        self.assertEqual({water: [0, 1, 4], stone: [2]}, result['extra'])
        self.assertEqual(states(fence), result['states'][fence])
        self.assertEqual(states(slab), result['states'][slab])
        self.assertEqual(states(water), result['extraStates'][water])
        self.assertEqual(saved, source)
        self.assertEqual(('minecraft:water', 0), tuple(doc.blocks[(1, 0, 0)]))

    def test_water_normalization_respects_partial_native_aux_capabilities(self):
        water = ('minecraft:water', 0)
        bottom = ('minecraft:oak_stairs', 0)
        top = ('minecraft:oak_stairs', 1)
        source = {'common': {water: [0, 1]}, 'extra': {bottom: [0], top: [1]}}
        with patch('projection.native_layers.is_waterloggable',
                   side_effect=lambda value: value == bottom):
            result = prepare_palette(source)
        self.assertEqual({bottom: [0], water: [1]}, result['common'])
        self.assertEqual({water: [0], top: [1]}, result['extra'])

    def test_mixed_background_promotion_respects_foreground_occupancy_and_native_states(self):
        water = ('minecraft:water', 0)
        stone = ('minecraft:stone', 0)
        custom = ('custom:background', 7)
        source = {'common': {('minecraft:air', 0): [0, 1, 2], stone: [1]},
                  'extra': {water: [0, 1], custom: [2]},
                  'extraStates': {custom: {'some_flag': True}}}
        result = prepare_palette(source)
        self.assertEqual({water: [0], stone: [1], custom: [2]}, result['common'])
        self.assertEqual({water: [1]}, result['extra'])
        self.assertEqual({'some_flag': True}, result['states'][custom])
        self.assertEqual([0, 1, 2], source['common'][('minecraft:air', 0)])

    def test_every_proxy_has_a_hidden_cutout_resource_with_its_own_species_texture(self):
        appearances = json.loads((ROOT / 'resource_pack/blocks.json').read_text(encoding='utf8'))
        for native, proxy in LEAF_PROXIES.items():
            name = proxy.split(':')[1]
            definition = json.loads((ROOT / 'behavior_pack/netease_blocks' /
                                     (name + '.json')).read_text(encoding='utf8'))['minecraft:block']
            self.assertEqual(proxy, definition['description']['identifier'])
            self.assertFalse(definition['description']['register_to_creative_menu'])
            self.assertNotIn('register_to_create_menu', definition['description'])
            self.assertEqual('optionalAlpha', definition['components']['netease:render_layer']['value'])
            self.assertTrue(definition['components']['netease:water_source']['value'])
            self.assertTrue(definition['components']['netease:water_flow_source']['value'])
            self.assertIn('netease:no_crop_face_block', definition['components'])
            appearance = appearances[proxy]
            species = native.split(':')[1]
            if species in ('spruce_leaves', 'birch_leaves'):
                # These native species have fixed colors. Their precolored
                # carried textures avoid the projection's seasonal tint pass.
                self.assertEqual(species + '_carried', appearance['textures'])
                self.assertNotIn('use_colormap', appearance)
            elif species in ('oak_leaves', 'jungle_leaves', 'acacia_leaves',
                             'dark_oak_leaves', 'mangrove_leaves'):
                self.assertEqual('big_oak_leaves' if species == 'dark_oak_leaves' else species,
                                 appearance['textures'])
                self.assertEqual('textures/colormap/foliage', appearance['use_colormap'])
            else:
                self.assertEqual(species, appearance['textures'])
                self.assertNotIn('use_colormap', appearance)


if __name__ == '__main__':
    unittest.main()
