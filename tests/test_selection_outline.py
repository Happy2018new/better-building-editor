import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.scene_lines import outline_target
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

    def target(self, cursor=None, error=None):
        s = self.session
        selected = bounds(s.editor.selection) if s.editor.selection else None
        return outline_target(selected, s.direct_mode, s.box_anchor, cursor, error)

    def test_completed_box_survives_hover_and_every_mode(self):
        expected = (((2, 2, 2), (5, 5, 5)), None)
        s = self.session
        revision = s.editor.selection_revision
        for mode in ('box', 'browse', 'select', 'place', 'paint', 'erase', 'pick'):
            s.choose_mode(mode)
            for cursor in (None, (3, 3, 3), (6, 6, 6), (8, 7, 7)):
                with self.subTest(mode=mode, cursor=cursor):
                    self.assertEqual(expected, self.target(cursor, 'invalid hover target'))
        self.assertEqual(revision, s.editor.selection_revision)
        self.assertEqual(64, len(s.editor.selection))

    def test_batch_tool_and_selection_erase_keep_the_same_scope(self):
        s = self.session
        before = self.target()
        s.choose_tool('shell')
        self.assertEqual(before, self.target((3, 3, 3)))
        s.choose_mode('erase')
        self.assertEqual('selection', s.erase_scope)
        self.assertFalse(s.point_action((3, 3, 3)))
        self.assertEqual(before, self.target((3, 3, 3)))
        self.assertEqual(64, len(s.editor.selection))

    def test_next_box_replaces_region_and_follows_second_corner(self):
        s = self.session
        s.point_action((6, 6, 6))
        self.assertEqual((((6, 6, 6), (6, 6, 6)), None), self.target())
        self.assertEqual((((3, 2, 1), (6, 6, 6)), None), self.target((3, 2, 1)))
        self.assertEqual(1, len(s.editor.selection))
        s.point_action((3, 2, 1))
        self.assertIsNone(s.box_anchor)
        self.assertEqual((((3, 2, 1), (6, 6, 6)), None), self.target((4, 4, 4)))

    def test_switching_mode_resolves_different_box_with_stationary_cursor(self):
        s = self.session
        s.point_action((6, 6, 6))
        before = self.target((3, 3, 3))
        s.choose_mode('select')
        self.assertNotEqual(before, self.target((3, 3, 3)))
        self.assertEqual((((3, 3, 3), (3, 3, 3)), None), self.target((3, 3, 3)))

    def test_successful_placement_releases_region_and_retains_hover_errors(self):
        s = self.session
        s.choose_mode('place')
        self.assertTrue(s.point_action((1, 1, 1)))
        self.assertEqual(1, len(s.editor.selection))
        self.assertEqual((((1, 1, 1), (1, 1, 1)), None), self.target())
        self.assertEqual((((2, 1, 1), (2, 1, 1)), None), self.target((2, 1, 1)))
        self.assertEqual((((8, 1, 1), (8, 1, 1)), 'out of bounds'), self.target((8, 1, 1), 'out of bounds'))
        self.assertEqual((((1, 1, 1), (1, 1, 1)), None), self.target())

    def test_empty_selection_can_still_preview_a_cell(self):
        self.assertEqual((None, None), outline_target(None, 'select', None, None))
        self.assertEqual((((3, 3, 3), (3, 3, 3)), None),
                         outline_target(None, 'select', None, (3, 3, 3)))


if __name__ == '__main__':
    unittest.main()
