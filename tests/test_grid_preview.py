import itertools
import json
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.camera import OrbitCamera
from projection.grid_preview import GRID_BLOCK, GRID_TAG, GridPreview, GridView, grid_center, grid_palette
from projection.geometry_palette import INTERNAL_RENDER_BLOCKS


class Control:
    def __init__(self):
        self.submissions = []

    def SetVisible(self, value, unused):
        self.visible = value

    def SetPosition(self, value):
        self.position = value

    def SetSize(self, value):
        self.size = value

    def asImage(self):
        return self

    def SetSpriteColor(self, value):
        self.color = value

    def asNeteasePaperDoll(self):
        return self

    def RenderBlockGeometryModel(self, params):
        self.submissions.append(params)
        return True


class GridPreviewTests(unittest.TestCase):
    def test_grid_palette_retains_one_mesh_for_all_document_dimensions(self):
        for size in ((1, 1, 1), (7, 8, 9), (24, 16, 24), (64, 128, 64)):
            palette = grid_palette(size)
            self.assertEqual((2,2,2), palette.size)
            indices = palette.common[(GRID_BLOCK, 0)]
            self.assertEqual([0],indices)

    def test_plane_vertices_have_same_depth_as_building_at_focus_and_odd_sizes(self):
        for origin, size, layer in (((0, 0, 0), (24, 16, 24), 5),
                                    ((16, 32, 16), (7, 9, 11), 36)):
            center = grid_center(origin, size, layer)
            for yaw, pitch in itertools.product((0, 35, 90, 180, 270), (-45, 0, 25, 90)):
                toward = OrbitCamera(yaw, pitch).basis()[2]
                for x, z in itertools.product((0, size[0]), (0, size[2])):
                    world = (origin[0]+x, layer, origin[2]+z)
                    model = tuple(world[i]-center[i] for i in range(3))
                    distance = sum((center[i]-origin[i])*toward[i] for i in range(3))
                    actual = distance + sum(model[i]*toward[i] for i in range(3))
                    expected = sum((world[i]-origin[i])*toward[i] for i in range(3))
                    self.assertAlmostEqual(expected, actual)
                    self.assertEqual(0., model[1])

    def test_height_view_and_visibility_changes_reuse_mesh_and_resume_rendering(self):
        builds = []
        session = SimpleNamespace(scene_size=(7, 8, 9), scene_origin=(0, 0, 0),
                                  editor=SimpleNamespace(layer=2), grid=True,
                                  bridge=SimpleNamespace(geometry=lambda palette: builds.append(palette) or 'grid'))
        grid, doll, image = GridPreview(), Control(), Control()
        view = GridView(lambda point: (point[0]*10, point[1]*10), (0, 0, 1),
                        10, (1, -65, 35), (400, 300), (.25, .5), .65, 'first')
        grid.update(session, doll, image, view)
        self.assertTrue(doll.visible)
        self.assertEqual(GRID_TAG, round(image.color[0]*255))
        self.assertAlmostEqual(.65, (image.color[0]*255-GRID_TAG)*8)
        grid.update(session, doll, image, view)
        self.assertEqual(1, len(doll.submissions))
        session.editor.layer = 5
        grid.update(session, doll, image, view)
        self.assertEqual(2, len(doll.submissions))
        session.grid = False
        grid.update(session, doll, image, view)
        self.assertFalse(doll.visible)
        session.grid = True
        grid.update(session, doll, image, view)
        self.assertTrue(doll.visible)
        grid.update(session, doll, image, view._replace(signature='orbit', pose=(2, -45, 90)))
        self.assertEqual(1, len(builds))
        session.editor.layer = 8
        grid.update(session, doll, image, view)
        self.assertFalse(doll.visible)

    def test_render_resource_is_hidden_and_plane_matches_the_calibrated_block_origin(self):
        self.assertIn(GRID_BLOCK, INTERNAL_RENDER_BLOCKS)
        block = json.loads((ROOT / 'behavior_pack/netease_blocks/preview_grid.json').read_text())
        self.assertFalse(block['minecraft:block']['description']['register_to_creative_menu'])
        model = json.loads((ROOT / 'resource_pack/models/netease_block/preview_grid.json').read_text())
        cubes=model['netease:block_geometry']['bones'][0]['cubes']
        self.assertEqual(130,len(cubes))
        for index,cube in enumerate(cubes):
            self.assertEqual([-16-index*32, 0, 0], cube['origin'])
            self.assertEqual([16, 0, 16], cube['size'])
            self.assertEqual({'up', 'down'}, set(cube['uv']))


if __name__ == '__main__':
    unittest.main()
