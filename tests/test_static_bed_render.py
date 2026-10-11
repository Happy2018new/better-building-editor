"""Bed half geometry, neighbor colors and occupancy source preservation."""
from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
from projection import block_registry
from projection.block_groups import from_states, group_partner
from projection.cell import actor_data, foreground, make_cell, rebase
from projection.debug_blueprints import build
from projection.geometry_palette import INTERNAL_RENDER_BLOCKS, prepare_palette
from projection.model import Document, Editor
from projection.nbt_spatial import root_payload
from projection.render_context import ContextPaletteBuilder, prepare_context_batches
from projection.storage import Selection
from projection.static_bed import BED_COLORS, BED_DIRECTIONS, BED_PROXIES, bed_proxy
from projection.visible_actor import compose_actor, entity_nbt
from generate_bed_proxies import half_cube, model, outputs
from generate_shulker_proxies import netease_box_uv
from test_static_shulker_render import world_rotation


def cell(direction, head, color):
    material = from_states('minecraft:bed', {'direction': direction,
        'head_piece_bit': head, 'occupied_bit': False})
    nbt = {'id': {'__type__': 8, '__value__': 'Bed'},
           'color': {'__type__': 1, '__value__': color},
           'unknown': {'__type__': 8, '__value__': 'preserved'}}
    return make_cell(material, nbt=compose_actor(None, nbt))


class StaticBedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads((ROOT / 'tools/data/bed_static_model_v1.json').read_text(encoding='utf8'))

    def test_native_length_clipping_partitions_every_cube_and_retains_texel_density(self):
        for bone in self.spec['geometry']['bones']:
            for original in bone['cubes']:
                halves = [half_cube(original, head) for head in (False, True)]
                self.assertEqual(original['size'][1], sum(half['size'][1] for half in halves if half))
                source = netease_box_uv(original['uv'], original['size'])
                for half in halves:
                    if half is None:
                        continue
                    self.assertEqual(original['size'][::2], half['size'][::2])
                    for face in ('east', 'west', 'north', 'south'):
                        self.assertEqual(source[face]['uv_size'][0], half['uv'][face]['uv_size'][0])
                        self.assertEqual(half['size'][1], abs(half['uv'][face]['uv_size'][1]))

    def test_all_generated_rotations_stay_in_one_cell_and_have_native_head_vectors(self):
        self.assertEqual(128, len(BED_PROXIES))
        for color, direction, head in product(BED_COLORS, range(4), (False, True)):
            geometry = model(self.spec, color, direction, head)['netease:block_geometry']
            identifier = geometry['description']['identifier']
            self.assertIn(identifier, INTERNAL_RENDER_BLOCKS)
            path = ROOT / 'resource_pack/models/netease_block' / (identifier.split(':')[1] + '.json')
            self.assertEqual(geometry, json.loads(path.read_text(encoding='utf8'))['netease:block_geometry'])
            bone = geometry['bones'][0]
            vector = world_rotation((0, 1, 0), bone['rotation'])
            for actual, expected in zip(vector, BED_DIRECTIONS[direction]):
                self.assertAlmostEqual(expected, actual)
            for cube in bone['cubes']:
                for offsets in product((0, 1), repeat=3):
                    point = [cube['origin'][axis] + offsets[axis] * cube['size'][axis] for axis in range(3)]
                    point[0] *= -1
                    rotated = world_rotation([point[axis] - 8 for axis in range(3)], bone['rotation'])
                    self.assertTrue(all(-.00001 <= value + 8 <= 16.00001 for value in rotated), (identifier, rotated))
                for face in cube['uv'].values():
                    for axis in range(2):
                        low, extent = face['uv'][axis], face['uv_size'][axis]
                        self.assertTrue(0 <= low <= 64 and 0 <= low + extent <= 64)

    def test_complete_palette_and_partial_context_take_color_from_correct_head_in_all_directions(self):
        for direction in range(4):
            foot = (2, 1, 2)
            head = tuple(foot[axis] + BED_DIRECTIONS[direction][axis] for axis in range(3))
            doc = Document((5, 3, 5), {foot: cell(direction, False, 0), head: cell(direction, True, 8)})
            before = deepcopy(doc.to_data())
            prepared = prepare_palette(doc.palette_data())
            self.assertEqual({}, prepared['actor'])
            self.assertEqual({(BED_PROXIES[('silver', direction, False)], 0),
                              (BED_PROXIES[('silver', direction, True)], 0)}, set(prepared['common']))
            for kept in (foot, head):
                targets = doc.palette_data(lambda pos: pos == kept)
                result = prepare_context_batches(doc, targets)
                self.assertTrue(all(not palette['actor'] for unused, unused_packed, palette in result['_context_batches']))
                builder = ContextPaletteBuilder(doc, targets)
                for pos, is_head in ((foot, False), (head, True)):
                    self.assertEqual((BED_PROXIES[('silver', direction, is_head)], 0), builder.material(*pos)[0]['common'])
            self.assertEqual(before, doc.to_data())

    def test_partner_color_cache_does_not_leak_between_identical_foot_cells(self):
        doc = Document((8, 3, 5), {(1, 1, 1): cell(0, False, 0), (1, 1, 2): cell(0, True, 8),
                                 (5, 1, 1): cell(0, False, 0), (5, 1, 2): cell(0, True, 3)})
        builder = ContextPaletteBuilder(doc, doc.palette_data())
        self.assertEqual((BED_PROXIES[('silver', 0, False)], 0), builder.material(1, 1, 1)[0]['common'])
        self.assertEqual((BED_PROXIES[('light_blue', 0, False)], 0), builder.material(5, 1, 1)[0]['common'])

    def test_unknown_color_tag_type_does_not_silently_render_white(self):
        value = cell(0, True, 8)
        nbt = entity_nbt(actor_data(value))
        nbt['color']['__type__'] = 3
        self.assertIsNone(bed_proxy(foreground(value), compose_actor(None, nbt)))

    def test_static_proxy_requires_the_observed_native_registry(self):
        value = cell(0, True, 8)
        with patch('projection.native_appearance.SOURCE_VERSION', 'unobserved version'):
            with self.assertRaises(ValueError):
                bed_proxy(foreground(value), actor_data(value))

    def test_old_bed_models_are_rejected_even_after_other_appearance_rules_are_updated(self):
        value = cell(0, True, 8)
        for name, changed in (('SOURCE_VERSION', 'NEMC old'), ('PALETTE_SHA256', '0' * 64)):
            with self.subTest(metadata=name), patch('projection.static_bed.' + name, changed):
                with self.assertRaisesRegex(ValueError, 'Native bed models need sources'):
                    bed_proxy(foreground(value), actor_data(value))

    def test_generator_refuses_bed_sources_for_a_different_registry(self):
        for key, changed in (('game_version', 'NEMC old'), ('palette_sha256', '0' * 64)):
            source = deepcopy(self.spec)
            source[key] = changed
            with self.subTest(metadata=key), self.assertRaisesRegex(ValueError, 'Native bed sources'):
                outputs(source)

    def test_public_bed_mirrors_equal_cardinal_source_layouts_without_swapping_roles(self):
        public = build('test.entities.appearances')
        points = ((9, 1, 19), (9, 1, 20))
        source = Document((7, 3, 7), dict(
            ((3, 1, 3 + index), rebase(public.get(pos),
             tuple((3, 1, 3 + index)[axis] - pos[axis] for axis in range(3))))
            for index, pos in enumerate(points)))
        before = deepcopy(source.to_data())

        def transformed(document, operation):
            result = Document(document.size, dict(document.blocks.items()))
            editor = Editor(result)
            editor.selection = Selection(result.blocks)
            editor._transform(operation)
            return result

        def normalized(document):
            foot = next(pos for pos, value in document.blocks.items()
                        if block_registry.states(foreground(value))['head_piece_bit'] is False)
            return dict((tuple(pos[axis] - foot[axis] for axis in range(3)),
                         rebase(value, tuple(-v for v in foot)))
                        for pos, value in document.blocks.items())

        cardinal = [source] + [transformed(source, 'rotate_y' + str(turn)) for turn in (90, 180, 270)]
        layouts = [normalized(document) for document in cardinal]
        for direction, document in enumerate(cardinal):
            original_nbt = dict((block_registry.states(foreground(value))['head_piece_bit'],
                root_payload(entity_nbt(actor_data(value)))) for value in layouts[direction].values())
            for operation in ('mirror_x', 'mirror_z'):
                mirrored = normalized(transformed(document, operation))
                self.assertIn(mirrored, layouts)
                foot = mirrored[(0, 0, 0)]
                delta, head_material = group_partner(foreground(foot))
                self.assertEqual(head_material, foreground(mirrored[delta]))
                for pos, value in mirrored.items():
                    expected = original_nbt[block_registry.states(foreground(value))['head_piece_bit']]
                    nbt = root_payload(entity_nbt(actor_data(value)))
                    self.assertEqual(expected['color'], nbt['color'])
                    self.assertEqual(1, nbt['color']['__type__'])
                    self.assertEqual(set(expected), set(nbt))
                    self.assertEqual(dict((key, tag) for key, tag in expected.items() if key not in ('x', 'y', 'z')),
                                     dict((key, tag) for key, tag in nbt.items() if key not in ('x', 'y', 'z')))
                    for axis, coordinate in zip('xyz', pos):
                        self.assertEqual({'__type__': 3, '__value__': coordinate}, nbt[axis])
        self.assertEqual(before, source.to_data())


if __name__ == '__main__':
    unittest.main()
