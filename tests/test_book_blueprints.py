"""Focused public book cards preserve native contents and real planner behavior."""
import copy
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'behavior_pack', 'modern_projection'))
from projection.book_profile import candidate_profile
from projection.book_render_plan import iter_render_steps
from projection.cell import actor_data, background, foreground, AIR
from projection.debug_blueprints import BLUEPRINTS, build, entries, open_blueprint
from projection.debug_book_blueprints import METADATA, VISUAL_CASES
from projection.debug_item_blueprints import slot_document
from projection.model import Document
from projection.nbt_spatial import rebase
from projection.session import Session


def groups(document, targets=None):
    return [group for group in iter_render_steps(document, candidate_profile(), targets) if group]


class BookBlueprintTests(unittest.TestCase):
    def test_cards_are_public_small_and_use_only_native_cells(self):
        for metadata, count in zip(METADATA, (2, 4)):
            identity = metadata[0]
            self.assertIn(metadata, entries('entities'))
            self.assertEqual(1, sum(row[0] == identity for row in BLUEPRINTS))
            document = build(identity)
            self.assertEqual(metadata[3], document.size)
            self.assertEqual(count, len(document.blocks))
            for position, cell in document.blocks.items():
                self.assertTrue(document.contains(position))
                self.assertTrue(foreground(cell)[0].startswith('minecraft:'))
                self.assertEqual(AIR, background(cell))
            self.assertFalse(VISUAL_CASES[identity]['GPU_qualified'])

    def test_lecterns_reuse_complete_existing_native_book_and_empty_payloads(self):
        document = build(METADATA[1][0])
        for case, target in (('lectern.empty', (3, 2, 3)), ('lectern.book', (8, 2, 3))):
            established = slot_document(case).get((3, 3, 3))
            actual = document.get(target)
            self.assertEqual(foreground(established), foreground(actual))
            self.assertEqual(rebase(actor_data(established),
                                    tuple(target[axis] - 3 for axis in range(3))), actor_data(actual))

    def test_real_book_planner_emits_one_companion_and_keeps_empty_control_empty(self):
        for metadata in METADATA:
            document = build(metadata[0])
            before = copy.deepcopy(document.to_data())
            self.assertEqual(1, len(groups(document)))
            self.assertEqual(before, document.to_data())
        document = build(METADATA[1][0])
        only_empty = document.palette_data(lambda position: position == (3, 2, 3))
        only_book = document.palette_data(lambda position: position == (8, 2, 3))
        self.assertEqual([], groups(document, only_empty))
        self.assertEqual(1, len(groups(document, only_book)))

    def test_storage_roundtrip_and_repeated_build_keep_all_typed_actor_data(self):
        for metadata in METADATA:
            document = build(metadata[0])
            before = copy.deepcopy(document.to_data())
            restored = Document.from_data(json.loads(json.dumps(before)))
            self.assertEqual(before, restored.to_data())
            self.assertEqual(before, build(metadata[0]).to_data())
            self.assertEqual(1, len(groups(restored)))

    def test_actual_public_load_and_restore_preserve_saved_library(self):
        session = Session(object())
        session.refresh_preview = lambda: None
        session.library = [{'id': 123, 'data': {'name': 'user-saved'}}]
        saved_library = session.library
        for metadata in METADATA:
            identity = metadata[0]
            open_blueprint(session, identity)
            original = copy.deepcopy(session.editor.document.to_data())
            self.assertEqual(VISUAL_CASES[identity]['focus'], session.camera_focus_request)
            self.assertEqual('workspace', session.page)
            self.assertIs(saved_library, session.library)
            session.editor.document.set_cell((1, 1, 1), ('minecraft:stone', 0))
            open_blueprint(session, identity)
            self.assertEqual(original, session.editor.document.to_data())
            self.assertEqual([], session.editor.undo_stack)
            self.assertEqual([], session.editor.redo_stack)
            self.assertIs(saved_library, session.library)


if __name__ == '__main__':
    unittest.main()
