import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.block_registry import aux_values, states
from projection.geometry_palette import LEAF_PROXIES, PLANT_PROXIES, prepare_palette
from projection.model import Document


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
            self.assertFalse(definition['description']['register_to_create_menu'])
            self.assertEqual('alpha', definition['components']['netease:render_layer']['value'])
            self.assertEqual(proxy, model['description']['identifier'])
            self.assertEqual(2, len(model['bones']))
            self.assertEqual(proxy, appearances[proxy]['netease_model'])
            self.assertEqual('textures/colormap/grass', appearances[proxy]['use_colormap'])

    def test_every_proxy_has_a_hidden_cutout_resource_with_its_own_species_texture(self):
        appearances = json.loads((ROOT / 'resource_pack/blocks.json').read_text(encoding='utf8'))
        for native, proxy in LEAF_PROXIES.items():
            name = proxy.split(':')[1]
            definition = json.loads((ROOT / 'behavior_pack/netease_blocks' /
                                     (name + '.json')).read_text(encoding='utf8'))['minecraft:block']
            self.assertEqual(proxy, definition['description']['identifier'])
            self.assertFalse(definition['description']['register_to_create_menu'])
            self.assertEqual('optionalAlpha', definition['components']['netease:render_layer']['value'])
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
