import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.scene_lines import outline_targets, cursor_depth_plane, clip_depth, cursor_hue, cursor_uv, cuboid, clip_line, segment_fractions
from projection.model import bounds, Document, Editor
from projection.session import Session


class Bridge:
    def later(self, delay, callback):
        pass


class SelectionOutlineTests(unittest.TestCase):
    def setUp(self):
        self.session = Session(Bridge())
        self.session.editor = Editor(Document((8, 8, 8)))
        self.session.choose_mode('box')
        self.session.point_action((2, 2, 2))
        self.session.point_action((5, 5, 5))

    def target(self, cursor=None, touch=False):
        s = self.session
        selected = bounds(s.editor.selection) if s.editor.selection else None
        return outline_targets(selected, s.direct_mode, s.box_anchor, cursor, touch)

    def test_completed_box_survives_hover_and_every_mode(self):
        expected = ((2, 2, 2), (5, 5, 5))
        s = self.session
        revision = s.editor.selection_revision
        for mode in ('box', 'browse', 'select', 'place', 'paint', 'erase', 'pick'):
            s.choose_mode(mode)
            for cursor in (None, (3, 3, 3), (6, 6, 6), (8, 7, 7)):
                with self.subTest(mode=mode, cursor=cursor):
                    selected, hovered = self.target(cursor)
                    self.assertEqual(expected, selected)
                    self.assertEqual((cursor, cursor) if cursor else None, hovered)
        self.assertEqual(revision, s.editor.selection_revision)
        self.assertEqual(64, len(s.editor.selection))

    def test_batch_tool_and_selection_erase_keep_the_same_scope(self):
        s = self.session
        before = self.target()[0]
        s.choose_tool('shell')
        self.assertEqual(before, self.target((3, 3, 3))[0])
        s.choose_mode('erase')
        self.assertEqual('selection', s.erase_scope)
        self.assertFalse(s.point_action((3, 3, 3)))
        self.assertEqual(before, self.target((3, 3, 3))[0])
        self.assertEqual(64, len(s.editor.selection))

    def test_next_box_replaces_region_and_follows_second_corner(self):
        s = self.session
        s.point_action((6, 6, 6))
        self.assertEqual((None, ((6, 6, 6), (6, 6, 6))), self.target())
        self.assertEqual((None, ((3, 2, 1), (6, 6, 6))), self.target((3, 2, 1)))
        self.assertEqual(1, len(s.editor.selection))
        s.point_action((3, 2, 1))
        self.assertIsNone(s.box_anchor)
        self.assertEqual((((3, 2, 1), (6, 6, 6)), ((4, 4, 4), (4, 4, 4))), self.target((4, 4, 4)))

    def test_switching_mode_resolves_different_box_with_stationary_cursor(self):
        s = self.session
        s.point_action((6, 6, 6))
        before = self.target((3, 3, 3))
        s.choose_mode('select')
        self.assertNotEqual(before, self.target((3, 3, 3)))
        self.assertEqual((((6, 6, 6), (6, 6, 6)), ((3, 3, 3), (3, 3, 3))), self.target((3, 3, 3)))

    def test_placement_and_invalid_hover_do_not_replace_each_others_bounds(self):
        s = self.session
        s.choose_mode('place')
        self.assertTrue(s.point_action((1, 1, 1)))
        self.assertEqual(1, len(s.editor.selection))
        self.assertEqual((((1, 1, 1), (1, 1, 1)), None), self.target())
        self.assertEqual((((1, 1, 1), (1, 1, 1)), ((2, 1, 1), (2, 1, 1))), self.target((2, 1, 1)))
        target, error = s.cursor_target((7, 1, 1), (1, 0, 0))
        self.assertTrue(error)
        self.assertEqual((((1, 1, 1), (1, 1, 1)), ((8, 1, 1), (8, 1, 1))), self.target(target))
        self.assertEqual(5.5, cursor_uv(0, .25, 0, invalid=True)[0][1])
        self.assertEqual((((1, 1, 1), (1, 1, 1)), None), self.target())

    def test_empty_selection_can_still_preview_a_cell(self):
        self.assertEqual((None, None), outline_targets(None, 'select', None, None))
        self.assertEqual((None, ((3, 3, 3), (3, 3, 3))),
                         outline_targets(None, 'select', None, (3, 3, 3)))

    def test_single_selection_updates_on_click_and_survives_continued_hover(self):
        s = self.session
        s.choose_mode('select')
        for pos in ((3, 3, 3), (4, 4, 4)):
            s.point_action(pos)
            for cursor in (pos, (1, 1, 1), None):
                self.assertEqual((pos, pos), self.target(cursor)[0])
                self.assertEqual(1, len(s.editor.selection))

    def test_touch_has_one_colored_selection_and_never_a_hover_box(self):
        s = self.session
        for mode in ('box', 'browse', 'select', 'place', 'paint', 'erase', 'pick'):
            s.choose_mode(mode)
            self.assertEqual((None, ((2, 2, 2), (5, 5, 5))), self.target((3, 3, 3), True))
        s.choose_mode('select'); s.point_action((1, 1, 1))
        self.assertEqual((None, ((1, 1, 1), (1, 1, 1))), self.target((3, 3, 3), True))
        s.choose_mode('box'); s.point_action((2, 2, 2))
        self.assertEqual((None, ((2, 2, 2), (2, 2, 2))), self.target((4, 4, 4), True))
        self.assertEqual((None, None), outline_targets(None, 'select', None, (3, 3, 3), True))

    def test_touch_first_corner_stays_fixed_until_second_tap(self):
        s = self.session
        s.point_action((1, 1, 1))
        for cursor in (None, (4, 3, 2), (7, 7, 7)):
            self.assertEqual((None, ((1, 1, 1), (1, 1, 1))), self.target(cursor, True))
            self.assertEqual(1, len(s.editor.selection))
        s.point_action((4, 3, 2))
        self.assertEqual((None, ((1, 1, 1), (4, 3, 2))), self.target((7, 7, 7), True))

    def test_large_box_uses_one_continuous_spectrum_without_exceeding_palette(self):
        lo, hi, size = (0, 0, 0), (64, 128, 64), (64, 128, 64)
        samples = {}
        for a, b in cuboid(lo, hi):
            start, end = cursor_hue(a, lo, size), cursor_hue(b, lo, size)
            uv, uv_size = cursor_uv(start, end, 5.9999)
            self.assertLess(uv[0] + uv_size[0], 1025)
            self.assertGreater(uv_size[0], 0)
            samples.setdefault(a, []).append(uv[0])
            samples.setdefault(b, []).append(uv[0] + uv_size[0])
        for colors in samples.values():
            self.assertAlmostEqual(min(colors), max(colors))

    def test_spectrum_joins_all_three_edges_at_each_of_the_eight_corners(self):
        lo, hi = (3, 5, 8), (4, 6, 9)
        samples = {}
        for a, b in cuboid(lo, hi):
            start, end = cursor_hue(a, lo), cursor_hue(b, lo)
            self.assertGreater(end, start)
            uv, size = cursor_uv(start, end, 1.5)
            samples.setdefault(a, []).append(uv[0])
            samples.setdefault(b, []).append(uv[0] + size[0])
        self.assertEqual(8, len(samples))
        for values in samples.values():
            self.assertEqual(3, len(values))
            self.assertAlmostEqual(min(values), max(values))
        self.assertEqual(cursor_uv(0, .25, 0), cursor_uv(0, .25, 6))
        self.assertEqual(cursor_uv(0, .25, 0, False), cursor_uv(0, .25, 2, False))

    def test_clipping_preserves_the_original_gradient_at_viewport_edges(self):
        a, b = (-40., 20.), (120., 60.)
        clipped = clip_line(a, b, 80, 80)
        self.assertEqual((.25, .75), segment_fractions(a, b, clipped))
        self.assertEqual((0., 1.), segment_fractions(a, a, (a, a)))

    def test_depth_keeps_editing_extents_complete_on_both_input_modes(self):
        edges = list(cuboid((1, 1, 1), (5, 5, 5)))
        for depth in (0., 2., 4.):
            plane = ((0., 0., 1.), depth)
            # Pending PC box, committed touch box, touch first corner and paste
            # all share spectrum ink, but represent an extent, not a hover.
            for mode, anchor, touch, paste in [('box', (1, 1, 1), False, False),
                    ('select', None, True, False), ('box', (1, 1, 1), True, False),
                    ('browse', None, False, True)]:
                cut = cursor_depth_plane(plane, mode, anchor, touch, paste)
                self.assertEqual(edges, [clip_depth(a, b, cut) for a, b in edges])
            hover_cut = cursor_depth_plane(plane, 'select', None)
            self.assertNotEqual(edges, [clip_depth(a, b, hover_cut) for a, b in edges])
        # Ignoring the model's cut never disables the viewport's own clipping.
        self.assertEqual(((0., 20.), (80., 20.)), clip_line((-40., 20.), (120., 20.), 80, 80))


if __name__ == '__main__':
    unittest.main()
