"""Copper proxy geometry and palette semantics, independent of native visuals."""
import json
from copy import deepcopy
from itertools import product
from pathlib import Path
import sys
import unittest
from PIL import Image
from io import BytesIO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
from projection import block_registry
from projection.block_groups import chest_pair_actor
from projection.cell import actor_data, make_cell
from projection.entity_render import (CHEST_PROXIES, COPPER_CHEST_PROXIES, COPPER_CHEST_STAGES,
                                      CHEST_DIRECTIONS, static_proxy)
from projection.geometry_palette import INTERNAL_RENDER_BLOCKS, prepare_palette
from projection.model import Document
from projection.visible_actor import compose_actor
from generate_copper_chest_proxies import clipped_cube, model, packed_geometry, packed_texture
from generate_shulker_proxies import box_uv
from test_static_shulker_render import world_rotation


class CopperChestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads((ROOT / 'tools/data/copper_chest_static_model_v1.json').read_text(encoding='utf8'))

    def test_all_eight_native_materials_share_correct_oxidation_texture_without_losing_identity(self):
        native = {name for name in block_registry.BLOCKS if name.endswith('copper_chest')}
        self.assertEqual(native, set(COPPER_CHEST_PROXIES))
        for stage in COPPER_CHEST_STAGES:
            name = ('' if stage == 'default' else stage + '_') + 'copper_chest'
            self.assertEqual(COPPER_CHEST_PROXIES['minecraft:' + name],
                             COPPER_CHEST_PROXIES['minecraft:waxed_' + name])
        self.assertEqual(48, len({name for names in COPPER_CHEST_PROXIES.values() for name in names.values()}))

    def test_half_cuboids_partition_original_double_chest_and_keep_unstretched_uv(self):
        for original in self.spec['double']['cubes']:
            main, sub = clipped_cube(original, 'main'), clipped_cube(original, 'sub')
            self.assertEqual(original['size'][0], main['size'][0] + sub['size'][0])
            self.assertEqual(0, main['origin'][0] + main['size'][0])
            self.assertEqual(-16, sub['origin'][0])
            source = box_uv(original['uv'], original['size'])
            for half in (main, sub):
                self.assertEqual(original['size'][1:], half['size'][1:])
                self.assertEqual(original['origin'][1:], half['origin'][1:])
                for face in ('north', 'south', 'up', 'down'):
                    self.assertEqual(source[face]['uv_size'][1], half['uv'][face]['uv_size'][1])
                    self.assertEqual(half['size'][0], abs(half['uv'][face]['uv_size'][0]))
                self.assertEqual(5, len(half['uv']))
            for face in ('north', 'south', 'up', 'down'):
                extent = main['uv'][face]['uv_size'][0]
                self.assertEqual(main['uv'][face]['uv'][0] + extent, sub['uv'][face]['uv'][0])

    def test_generated_bounds_front_vectors_and_native_texture_paths(self):
        fronts = {'north': (0, 0, -1), 'east': (1, 0, 0),
                  'south': (0, 0, 1), 'west': (-1, 0, 0)}
        for stage, direction, part in product(COPPER_CHEST_STAGES, CHEST_DIRECTIONS, ('single', 'main', 'sub')):
            geometry = model(self.spec, stage, direction, part)['netease:block_geometry']
            identifier = geometry['description']['identifier']
            path = ROOT / 'resource_pack/models/netease_block' / (identifier.split(':')[1] + '.json')
            self.assertEqual(geometry, json.loads(path.read_text(encoding='utf8'))['netease:block_geometry'])
            self.assertIn(identifier, INTERNAL_RENDER_BLOCKS)
            bone = geometry['bones'][0]
            vector = world_rotation((0, 0, 1), bone['rotation'])
            for actual, expected in zip(vector, fronts[direction]):
                self.assertAlmostEqual(expected, actual)
            for cube in bone['cubes']:
                for offsets in product((0, 1), repeat=3):
                    point = [cube['origin'][axis] + offsets[axis] * cube['size'][axis] for axis in range(3)]
                    point[0] *= -1
                    rotated = world_rotation([point[axis] - 8 for axis in range(3)], bone['rotation'])
                    self.assertTrue(all(-.00001 <= value + 8 <= 16.00001 for value in rotated),
                                    (stage, direction, part, point, rotated))
                for face in cube['uv'].values():
                    for axis, maximum in enumerate((64, 64)):
                        low, extent = face['uv'][axis], face['uv_size'][axis]
                        self.assertTrue(0 <= low <= maximum and 0 <= low + extent <= maximum)

    def test_double_chest_face_packing_preserves_source_pixels_without_resampling(self):
        source = Image.new('RGBA', (128, 64))
        source.putdata([(x, y, (x * y) % 256, 255) for y in range(64) for x in range(128)])
        for part in ('main', 'sub'):
            cubes, patches = packed_geometry(self.spec, part)
            before = [clipped_cube(original, part) for original in self.spec['double']['cubes']]
            occupied = set()
            with Image.open(BytesIO(packed_texture(source, patches))) as packed:
                self.assertEqual((64, 64), packed.size)
                for rectangle, (x, y) in patches:
                    width, height = rectangle[2] - rectangle[0], rectangle[3] - rectangle[1]
                    self.assertEqual(source.crop(rectangle).tobytes(),
                                     packed.crop((x, y, x + width, y + height)).tobytes())
                    cells = {(x + dx, y + dy) for dx in range(-1, width + 1)
                             for dy in range(-1, height + 1)}
                    self.assertFalse(occupied.intersection(cells))
                    self.assertTrue(all(0 <= px < 64 and 0 <= py < 64 for px, py in cells))
                    occupied.update(cells)
                for original, repacked in zip(before, cubes):
                    self.assertEqual(original['origin'], repacked['origin'])
                    self.assertEqual(original['size'], repacked['size'])
                    self.assertEqual(set(original['uv']), set(repacked['uv']))
                    for face, record in original['uv'].items():
                        candidate = repacked['uv'][face]
                        self.assertEqual(record['uv_size'], candidate['uv_size'])
                        for fraction in (.25, .75):
                            old = tuple(int(record['uv'][axis] + fraction * record['uv_size'][axis])
                                        for axis in range(2))
                            new = tuple(int(candidate['uv'][axis] + fraction * candidate['uv_size'][axis])
                                        for axis in range(2))
                            self.assertEqual(source.getpixel(old), packed.getpixel(new))

    def test_actor_pair_role_and_state_direction_select_render_only_cells(self):
        for direction in CHEST_DIRECTIONS:
            material = block_registry.from_states('minecraft:copper_chest', {'minecraft:cardinal_direction': direction})
            for part in ('single', 'main', 'sub'):
                renderer = {'chestIsLargeChest': part != 'single',
                            'chestMainSubChest': part != 'sub', 'facingDirection': 2}
                actor = compose_actor(renderer, {'id': 'Chest', 'Items': [], 'FutureUnknown': [1, 2]})
                before = deepcopy(actor)
                self.assertEqual((COPPER_CHEST_PROXIES[material[0]][(direction, part)], 0),
                                 static_proxy(material, actor))
                self.assertEqual(before, actor)

    def test_missing_client_pair_fields_use_only_unambiguous_same_material_adjacency(self):
        material = ('minecraft:copper_chest', 2)
        doc = Document((4, 2, 4), {(1, 1, 1): material, (2, 1, 1): material})
        result = prepare_palette(doc.palette_data())
        for part, index in (('main', 21), ('sub', 25)):
            proxy = COPPER_CHEST_PROXIES[material[0]][('north', part)]
            self.assertEqual([index], result['common'][(proxy, 0)])
        doc.blocks[(3, 1, 1)] = material
        result = prepare_palette(doc.palette_data())
        self.assertEqual([21, 25, 29], result['common'][(COPPER_CHEST_PROXIES[material[0]][('north', 'single')], 0)])

    def test_explicit_single_chest_renderer_and_row_boundaries_prevent_false_pairs(self):
        material = ('minecraft:copper_chest', 2)
        doc = Document((2, 2, 2), {(0, 1, 0): material, (1, 1, 0): material})
        for pos, value in list(doc.blocks.items()):
            doc.blocks[pos] = make_cell(value, nbt=compose_actor({'chestIsLargeChest': False}, None))
        result = prepare_palette(doc.palette_data())
        self.assertEqual([4, 6], result['common'][(COPPER_CHEST_PROXIES[material[0]][('north', 'single')], 0)])
        doc = Document((2, 2, 2), {(1, 0, 0): material, (0, 1, 0): material})
        result = prepare_palette(doc.palette_data())
        self.assertEqual([2, 4], result['common'][(COPPER_CHEST_PROXIES[material[0]][('north', 'single')], 0)])

    def test_missing_pair_role_without_neighbors_does_not_guess_the_sub_half(self):
        material = ('minecraft:copper_chest', 2)
        actor = compose_actor({'chestIsLargeChest': True}, None)
        proxy = COPPER_CHEST_PROXIES[material[0]][('north', 'single')]
        self.assertEqual((proxy, 0), static_proxy(material, actor))

    def test_ordinary_trapped_and_ender_chests_use_verified_native_atlases(self):
        for name, stage in (('chest', 'normal'), ('trapped_chest', 'trapped'), ('ender_chest', 'ender')):
            for direction in CHEST_DIRECTIONS:
                parts = ('single',) if name == 'ender_chest' else ('single', 'main', 'sub')
                for part in parts:
                    geometry = model(self.spec, stage, direction, part)['netease:block_geometry']
                    self.assertEqual(CHEST_PROXIES['minecraft:' + name][(direction, part)], geometry['description']['identifier'])
                    self.assertIn(geometry['description']['identifier'], INTERNAL_RENDER_BLOCKS)

    def test_document_shares_nbt_and_layers_keep_original_copper_after_rendering(self):
        material = ('minecraft:copper_chest', 2)
        doc = Document((2, 1, 1))
        for pos, partner in (((0, 0, 0), (1, 0, 0)), ((1, 0, 0), (0, 0, 0))):
            value = make_cell(material, ('minecraft:water', 0), compose_actor({}, {'id': 'Chest', 'Items': []}))
            doc.blocks[pos] = chest_pair_actor(value, pos, partner)
        original = deepcopy(doc.to_data())
        source = doc.palette_data()
        source_before = deepcopy(source)
        result = prepare_palette(source)
        self.assertEqual(original, doc.to_data())
        self.assertEqual(source_before, source)
        self.assertNotIn(material[0], result['actor'])
        self.assertEqual([0], result['common'][(COPPER_CHEST_PROXIES[material[0]][('north', 'main')], 0)])
        self.assertEqual([1], result['common'][(COPPER_CHEST_PROXIES[material[0]][('north', 'sub')], 0)])
        self.assertEqual({('minecraft:water', 0): [0, 1]}, result['extra'])
        self.assertNotIn('preview_copper', json.dumps(original))


if __name__ == '__main__':
    unittest.main()
