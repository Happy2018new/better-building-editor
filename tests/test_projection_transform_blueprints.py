"""The small public projection card keeps literal direction controls usable."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import AIR, actor_data, background, foreground
from projection.debug_blueprints import BLUEPRINTS, VISUAL_CASES, build, entries, open_blueprint
from projection.debug_projection_transform_blueprints import METADATA, MARKERS, MESSAGE, VISUAL_CASE
from projection.model import Document
from projection.projection_transform import snapshot
from projection.session import Session


class ProjectionTransformBlueprintTests(unittest.TestCase):
    def test_small_card_is_public_and_only_contains_legal_static_native_cells(self):
        self.assertIn(METADATA, entries('transforms'))
        self.assertEqual(1, sum(row[0] == METADATA[0] for row in BLUEPRINTS))
        self.assertIs(VISUAL_CASE, VISUAL_CASES['projection_transform'])
        document = build(METADATA[0])
        self.assertEqual((7, 4, 5), document.size)
        self.assertEqual(17, len(document.blocks))
        for position, cell in document.blocks.items():
            self.assertTrue(document.contains(position))
            self.assertEqual(foreground(cell), registry.canonical(foreground(cell)))
            self.assertEqual(AIR, background(cell))
            self.assertIsNone(actor_data(cell))
        for position, color in MARKERS:
            self.assertEqual('minecraft:' + color, foreground(document.get(position))[0])
        self.assertEqual(document.to_data(), Document.from_data(document.to_data()).to_data())
        self.assertEqual(document.to_data(), build(METADATA[0]).to_data())

    def test_settings_move_markers_to_literal_expected_positions_and_keep_editing_document(self):
        document = build(METADATA[0])
        original = document.to_data()
        for operation, expected in VISUAL_CASE['expected'].items():
            with self.subTest(operation=operation):
                target = snapshot(document, (operation,))
                self.assertEqual(expected['size'], target.size)
                for position, color in expected['markers']:
                    self.assertEqual('minecraft:' + color, foreground(target.get(position))[0])
                self.assertEqual(original, document.to_data())
        rotated = snapshot(document, ('rotate_y90',))
        self.assertEqual({'upside_down_bit': False, 'weirdo_direction': 2},
                         registry.states(foreground(rotated.get((3, 1, 2)))))
        self.assertEqual({'upside_down_bit': True, 'weirdo_direction': 0},
                         registry.states(foreground(rotated.get((1, 2, 4)))))
        for position, axis in (((2, 1, 1), 'z'), ((2, 1, 3), 'y'), ((2, 1, 5), 'x')):
            self.assertEqual(axis, registry.states(foreground(rotated.get(position)))['pillar_axis'])
        inverted = snapshot(document, ('mirror_y',))
        self.assertTrue(registry.states(foreground(inverted.get((2, 2, 1))))['upside_down_bit'])
        self.assertFalse(registry.states(foreground(inverted.get((4, 1, 3))))['upside_down_bit'])

    def test_public_load_preserves_projection_settings_and_saved_user_library(self):
        session = Session(object())
        session.refresh_preview = lambda: None
        session.origin = (101, 75, -201)
        session.projection_transform = ('rotate_y270', 'mirror_z')
        session.library = [{'id': 123, 'data': {'name': 'user-saved'}}]
        saved = session.library
        open_blueprint(session, METADATA[0])
        self.assertEqual('workspace', session.page)
        self.assertEqual((101, 75, -201), session.origin)
        self.assertEqual(('rotate_y270', 'mirror_z'), session.projection_transform)
        self.assertEqual(MESSAGE, session.editor.message)
        self.assertEqual(VISUAL_CASE['focus'], session.camera_focus_request)
        self.assertIs(saved, session.library)
        self.assertEqual([], session.editor.undo_stack)
        self.assertEqual([], session.editor.redo_stack)


if __name__ == '__main__':
    unittest.main()
