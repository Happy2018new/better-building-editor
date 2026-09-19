import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.camera import OrbitCamera, raycast, layer_hit
from projection.model import Document, Editor, AIR
from projection.session import Session

STONE = ('minecraft:stone', 0)


class Bridge:
    def later(self, delay, callback):
        pass


class CameraTests(unittest.TestCase):
    def test_unbounded_zoom_and_panned_ray_keep_voxel_accuracy(self):
        doc = Document((13, 9, 11))
        pos = (6, 4, 5)
        doc.blocks[pos] = STONE
        for zoom in (4., 50., 10000.):
            c = OrbitCamera(35, 25)
            c.aim(35, 25, zoom)
            c.pan_target = (.3, -.2)
            c.advance(.05, False)
            self.assertEqual(zoom, c.zoom)
            screen = c.project(tuple(v+.5 for v in pos), doc.size, 600, 400, zoom)
            origin, direction = c.ray(*screen, doc.size, 600, 400, zoom)
            self.assertEqual(pos, raycast(doc, origin, direction)[0])
        c.aim(0, 0, .001)
        c.advance(.05, False)
        self.assertEqual(.25, c.zoom)

    def test_horizontal_grab_and_release_follow_pointer(self):
        for yaw in (0, 90, 180, 270, 359):
            for dx in (-20, 20):
                c = OrbitCamera(yaw, 0)
                # A point on the currently facing side must follow the hand.
                toward = c.basis()[2]
                point = tuple(5 + 3 * v for v in toward)
                before = c.project(point, (10, 10, 10), 400, 300, 10)[0]
                c.drag(dx, 0, .05)
                dragged = c.project(point, (10, 10, 10), 400, 300, 10)[0]
                c.advance(1 / 60.)
                released = c.project(point, (10, 10, 10), 400, 300, 10)[0]
                self.assertGreater((dragged - before) * dx, 0)
                self.assertGreater((released - dragged) * dx, 0)

    def test_preset_takes_shortest_path_and_converges(self):
        c = OrbitCamera(350, 25, 1)
        c.aim(10, 90, 2)
        c.advance(1 / 60.)
        self.assertTrue(350 < c.yaw < 370)
        self.assertTrue(25 < c.pitch < 90)
        for unused in range(120):
            c.advance(1 / 60.)
        self.assertAlmostEqual(c.yaw, 370, places=3)
        self.assertAlmostEqual(c.zoom, 2, places=3)

    def test_inertia_is_time_based_and_settles(self):
        positions = []
        for fps in (30, 60, 120):
            c = OrbitCamera()
            c.drag(20, 4, .03)
            for unused in range(fps * 2):
                c.advance(1. / fps)
            positions.append(c.yaw)
            self.assertEqual(c.velocity, (0., 0.))
        self.assertLess(max(positions) - min(positions), .03)

    def test_projection_and_pick_agree_at_all_angles(self):
        doc = Document((13, 9, 11))
        pos = (3, 5, 7)
        doc.blocks[pos] = STONE
        for yaw in (0, 35, 90, 180, 270, 357):
            for pitch in (-60, 0, 25, 90):
                c = OrbitCamera(yaw, pitch)
                screen = c.project(tuple(v + .5 for v in pos), doc.size, 600, 400, 17)
                origin, direction = c.ray(screen[0], screen[1], doc.size, 600, 400, 17)
                self.assertEqual(raycast(doc, origin, direction)[0], pos, (yaw, pitch))

    def test_reduced_motion_stops_inertia_without_a_jump(self):
        c = OrbitCamera()
        c.drag(20, 0, .03)
        yaw = c.yaw
        c.advance(.016, False)
        self.assertEqual(c.yaw, yaw)
        self.assertEqual(c.velocity, (0., 0.))

    def test_occlusion_hidden_layers_normals_and_empty_space(self):
        doc = Document((8, 8, 8))
        doc.blocks[(3, 6, 3)] = STONE
        doc.blocks[(3, 2, 3)] = STONE
        origin, direction = (3.5, 20., 3.5), (0., -1., 0.)
        self.assertEqual(raycast(doc, origin, direction), ((3, 6, 3), (0, 1, 0)))
        self.assertEqual(raycast(doc, origin, direction, lambda p: p[1] != 6)[0], (3, 2, 3))
        self.assertIsNone(raycast(doc, (9., 20., 3.), direction))
        self.assertEqual(layer_hit(doc, origin, direction, 4), (3, 4, 3))
        self.assertIsNone(layer_hit(doc, origin, (1., 0., 0.), 4))

    def test_all_six_entry_faces(self):
        doc = Document((3, 3, 3))
        doc.blocks[(1, 1, 1)] = STONE
        for axis in range(3):
            for sign in (-1, 1):
                origin = [1.5] * 3
                origin[axis] = 1.5 + sign * 10
                direction = tuple(-sign if i == axis else 0 for i in range(3))
                self.assertEqual(raycast(doc, origin, direction),
                                 ((1, 1, 1), tuple(sign if i == axis else 0 for i in range(3))))


class DirectEditingTests(unittest.TestCase):
    def setUp(self):
        self.s = Session(Bridge())
        self.s.editor = Editor(Document((4, 4, 4)))
        self.s.editor.document.blocks[(1, 1, 1)] = STONE

    def test_place_erase_and_undo_are_single_transactions(self):
        s = self.s
        s.choose_mode('place')
        s.point_action((1, 1, 1), (0, 1, 0))
        self.assertNotEqual(s.editor.document.get((1, 2, 1)), AIR)
        self.assertEqual(len(s.editor.undo_stack), 1)
        s.choose_mode('erase')
        s.point_action((1, 2, 1))
        self.assertEqual(s.editor.document.get((1, 2, 1)), AIR)
        s.editor.undo()
        self.assertNotEqual(s.editor.document.get((1, 2, 1)), AIR)

    def test_pick_and_box_do_not_mutate_blocks(self):
        s = self.s
        s.choose_mode('pick')
        s.point_action((1, 1, 1))
        self.assertEqual(s.editor.material, STONE)
        s.choose_mode('box')
        s.point_action((1, 1, 1))
        s.point_action((2, 2, 2))
        self.assertEqual(len(s.editor.selection), 8)
        self.assertEqual(s.editor.revision, 0)

    def test_boundaries_masks_and_locks_are_respected(self):
        s = self.s
        s.choose_mode('place')
        s.point_action((3, 1, 1), (1, 0, 0))
        s.editor.locked_layers.add(2)
        s.point_action((1, 1, 1), (0, 1, 0))
        s.editor.mask = 'solid'
        s.point_action((1, 1, 1), (1, 0, 0))
        self.assertEqual(len(s.editor.undo_stack), 0)
        self.assertEqual(len(s.editor.document.blocks), 1)

    def test_selection_then_place_preserves_selection_and_allows_adjacent_edit(self):
        s = self.s
        for mode in ('select', 'box', 'erase', 'pick', 'browse'):
            s.choose_mode(mode)
            if mode == 'select':
                s.point_action((1, 1, 1))
            elif mode == 'box':
                s.point_action((1, 1, 1))
                s.point_action((1, 1, 1))
            s.choose_mode('place')
            s.direct_selection = True
            self.assertEqual(s.point_action((1, 1, 1), (0, 1, 0)), 0)
            s.direct_selection = False
            self.assertEqual(s.point_action((1, 1, 1), (0, 1, 0)), 1)
            self.assertEqual(s.editor.selection, {(1, 1, 1)})
            s.editor.undo()
        s.direct_selection = True
        self.assertEqual(s.point_action((1, 1, 1), (0, 1, 0)), 0)
        self.assertIn('选区', s.editor.message)

    def test_each_outer_boundary_is_rejected_without_history_or_preview_job(self):
        s = self.s
        s.choose_mode('place')
        for axis in range(3):
            for sign in (-1, 1):
                pos = [1, 1, 1]
                pos[axis] = 0 if sign < 0 else 3
                normal = tuple(sign if i == axis else 0 for i in range(3))
                s.point_action(tuple(pos), normal)
                self.assertIn('超出', s.editor.message)
                self.assertFalse(s.preview_pending)
                self.assertFalse(s.editor.undo_stack)


if __name__ == '__main__':
    unittest.main()
