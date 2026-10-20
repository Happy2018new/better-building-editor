"""Barrier marker is render-only: saved/world palette identities remain native."""
import copy
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
from projection.barrier_render import INTERNAL_BLOCKS, MARKER_NAME, NATIVE_NAME, PROXIES, STYLE
from projection.cell import background, foreground
from projection.debug_barrier_blueprints import BARRIERS, VISUAL_CASE, build as build_barrier
from projection.geometry_palette import INTERNAL_RENDER_BLOCKS, prepare_palette
from projection.model import Document


class BarrierRenderTests(unittest.TestCase):
    def test_native_world_and_serialized_id_stay_barrier_with_no_proxy_cell_persisted(self):
        document = build_barrier()
        original = copy.deepcopy(document.to_data())
        for pos in BARRIERS:
            cell = document.get(pos)
            self.assertEqual((NATIVE_NAME, 0), foreground(cell))
            self.assertEqual(('minecraft:air', 0), background(cell))
        restored = Document.from_data(json.loads(json.dumps(original)))
        for pos in BARRIERS:
            self.assertEqual((NATIVE_NAME, 0), foreground(restored.get(pos)))
        self.assertEqual(original, restored.to_data())
        self.assertNotIn(MARKER_NAME, json.dumps(original))

    def test_full_and_partial_missing_inputs_render_markers_without_changing_native_cells(self):
        document = build_barrier()
        logical = document.palette_data()
        before = copy.deepcopy(logical)
        occupied = set(VISUAL_CASE['partial_occupancy'])
        sources = (('full', logical, BARRIERS),
                   ('missing', document.palette_data(lambda pos: pos not in occupied),
                    tuple(pos for pos in BARRIERS if pos not in occupied)))
        for mode, source, positions in sources:
            saved = copy.deepcopy(source)
            result = prepare_palette(source)
            indices = sorted((pos[1] * document.size[0] + pos[0]) * document.size[2] + pos[2]
                             for pos in positions)
            marker_indices = result['common'].get((MARKER_NAME, 0))
            self.assertIsNotNone(marker_indices, mode)
            self.assertEqual(indices, marker_indices, mode)
            self.assertNotIn((MARKER_NAME, 0), result['states'])
            self.assertNotIn((NATIVE_NAME, 0), result['common'])
            self.assertEqual(saved, source)
            self.assertEqual(before, document.palette_data())

    def test_proxy_is_marked_internal_and_zero_plane_sprite_stays_in_cell(self):
        self.assertEqual({NATIVE_NAME: MARKER_NAME}, PROXIES)
        self.assertIn(MARKER_NAME, INTERNAL_BLOCKS)
        self.assertIn(MARKER_NAME, INTERNAL_RENDER_BLOCKS)
        from generate_barrier_marker_r23 import model
        geometry = model()['netease:block_geometry']
        self.assertEqual('three_axis_double_sided_native_sprite', STYLE)
        self.assertEqual(3, len(geometry['bones']))
        faces = []
        for bone in geometry['bones']:
            self.assertEqual(1, len(bone['cubes']))
            cube = bone['cubes'][0]
            self.assertEqual(1, cube['size'].count(0))
            for axis in range(3):
                minimum, maximum = cube['origin'][axis], cube['origin'][axis] + cube['size'][axis]
                if axis == 0:
                    minimum, maximum = -maximum, -minimum
                self.assertGreaterEqual(minimum, 2)
                self.assertLessEqual(maximum, 14)
            self.assertEqual(2, len(cube['uv']))
            for face in cube['uv'].values():
                for axis in range(2):
                    self.assertTrue(0 <= face['uv'][axis] <= 16)
                    self.assertTrue(0 <= face['uv'][axis] + face['uv_size'][axis] <= 16)
            faces.extend(cube['uv'])
        self.assertEqual({'north', 'south', 'east', 'west', 'up', 'down'}, set(faces))

    def test_marker_cannot_replace_non_barrier_neighbor(self):
        stone = ('minecraft:stone', 0)
        source = {'common': {('minecraft:barrier', 0): [0], stone: [1]},
                  'volume': (2, 1, 1)}
        before = copy.deepcopy(source)
        result = prepare_palette(source)
        self.assertEqual([0], result['common'][(MARKER_NAME, 0)])
        self.assertEqual([1], result['common'][stone])
        self.assertEqual(before, source)

    def test_world_write_uses_native_barrier_after_render_palette_has_been_prepared(self):
        from projection.world import WorldJob
        from test_world import World, complete
        document = build_barrier()
        before = document.blocks.copy()
        prepare_palette(document.palette_data())
        world = World()
        origin = (100, 64, -100)
        job = WorldJob(world, document, origin)
        complete(job)
        self.assertFalse(job.error)
        self.assertEqual(before, document.blocks)
        for pos in BARRIERS:
            actual = tuple(origin[i] + pos[i] for i in range(3))
            self.assertEqual((NATIVE_NAME, 0), foreground(world.blocks[actual]))
        self.assertFalse(any(foreground(value)[0] == MARKER_NAME for value in world.blocks.values()))

    def test_generated_resources_match_pinned_native_sprite_and_six_explicit_faces(self):
        from generate_barrier_marker_r23 import check
        source = check(registered=True)
        self.assertFalse(source['pixel_acceptance'])
        self.assertFalse(source['geometry']['solid_cube'])
        self.assertEqual(6, source['geometry']['explicit_faces'])
        self.assertEqual(186, source['texture_bytes'])
        self.assertEqual('144dc5d61706124c91e19c4b7e2b410da58b240e6eeb01ca421330b90dbb18a4',
                         source['native_texture_sha256'])

    def test_marker_has_a_front_face_from_all_cardinal_and_diagonal_view_directions(self):
        from generate_barrier_marker_r23 import model
        normals = {'east': (1, 0, 0), 'west': (-1, 0, 0),
                   'up': (0, 1, 0), 'down': (0, -1, 0),
                   'south': (0, 0, 1), 'north': (0, 0, -1)}
        faces = [face for bone in model()['netease:block_geometry']['bones']
                 for cube in bone['cubes'] for face in cube['uv']]
        for direction in ((x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1)
                          for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)):
            length = math.sqrt(sum(component * component for component in direction))
            projected = [sum(normals[face][axis] * direction[axis] for axis in range(3)) / length
                         for face in faces]
            self.assertGreaterEqual(max(projected) + 1e-12, 1 / math.sqrt(3), direction)

    def test_native_alpha_is_preserved_instead_of_filling_a_red_quad(self):
        from PIL import Image
        with Image.open(ROOT / 'resource_pack/textures/blocks/modern_projection/barrier_marker.png') as image:
            alpha = list(image.getchannel('A').getdata())
        self.assertEqual((138, 118), (alpha.count(0), alpha.count(255)))
        self.assertEqual(256, len(alpha))


if __name__ == '__main__':
    unittest.main()
