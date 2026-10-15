"""Public world preparation keeps native lectern ownership paired with books."""
import copy
import unittest
from unittest.mock import patch

import test_book_owner
from test_lectern_body_candidate import bodies
from projection.cell import foreground, make_cell, rebase
from projection.debug_item_blueprints import slot_document
from projection.model import Document, Editor
from projection.render_context import prepare_context_batches


class LecternWorldCandidateTests(unittest.TestCase):
    def setUp(self):
        test_book_owner.BookWorldIntegrationTests.setUp(self)
        self.bridge.session.portal_profile = None
        self.empty, self.book = (0, 1, 1), (2, 1, 1)
        source = slot_document('lectern.book').get((3, 3, 3))
        book = rebase(source, (-1, -2, -2))
        material = foreground(source)
        self.document = Document((4, 4, 3), {
            self.empty: make_cell(material, nbt={}), self.book: book,
            (0, 0, 1): ('minecraft:cyan_concrete', 0),
            (2, 0, 1): ('minecraft:cyan_concrete', 0),
            (0, 2, 1): ('minecraft:stone', 0), (2, 2, 1): ('minecraft:stone', 0),
            (1, 1, 1): ('minecraft:stone', 0)})
        self.bridge.session.editor = Editor(self.document)
        self.prepared = None
        def geometry(document, visible=None, name=None, context_document=None, prepared=None, **kwargs):
            if prepared is not None:
                self.prepared = copy.deepcopy(prepared)
            elif context_document is not None:
                prepare_context_batches(context_document, document.palette_data(visible))
            return name or 'native_body_model'
        self.bridge.geometry = geometry

    def tearDown(self):
        test_book_owner.BookWorldIntegrationTests.tearDown(self)

    def drain(self):
        test_book_owner.BookWorldIntegrationTests.drain(self)

    def assert_projection(self, count, books):
        work = self.bridge.projection_work
        self.assertTrue(work.ready, work.error)
        self.assertEqual(count, len(bodies(self.prepared['_context_batches'])))
        owner = self.bridge.projection_liquid
        self.assertEqual('BookProjection', type(owner).__name__)
        self.assertEqual(books, len(owner.renderer.active))
        self.assertEqual(self.document.to_data(), owner.document.to_data())
        return owner

    def test_real_empty_and_book_inputs_share_native_body_in_full_and_missing_routes(self):
        before = copy.deepcopy(self.document.to_data())
        for missing in (False, True):
            with self.subTest(missing=missing):
                self.bridge.session.projection_missing = missing
                self.bridge.project_large((10, 64, 20))
                self.drain()
                owner = self.assert_projection(2, 1)
                self.assertTrue(owner.committed)
                self.assertTrue(all(row[2] == {} for row in bodies(self.prepared['_context_batches'])))
                self.bridge.stop_projection()
                self.drain()
                self.assertTrue(owner.closed)
                self.assertEqual({}, self.runtime.liquid_models.models)
        self.assertEqual(before, self.document.to_data())

    def test_initial_present_lecterns_leave_only_other_missing_native_targets(self):
        before = copy.deepcopy(self.document.to_data())
        origin = (10, 64, 20)
        for local in (self.empty, self.book):
            world = tuple(origin[axis]+local[axis] for axis in range(3))
            self.runtime.world[world] = foreground(self.document.get(local))
        self.bridge.session.projection_missing = True
        self.bridge.project_large(origin)
        self.drain()
        self.assert_projection(0, 0)
        self.assertEqual(before, self.document.to_data())
        self.bridge.stop_projection()
        self.drain()

    def test_hidden_target_layer_retains_upper_and_lower_neighbors_without_body_or_book(self):
        before = copy.deepcopy(self.document.to_data())
        for hidden in ((1,), ()):
            with patch.object(self.bridge.session, 'preview_hidden', return_value=hidden):
                self.bridge.session.projection_missing = False
                self.bridge.project_large((10, 64, 20))
                self.drain()
                self.assert_projection(0 if hidden else 2, 0 if hidden else 1)
                self.bridge.stop_projection()
                self.drain()
        self.assertEqual(before, self.document.to_data())


if __name__ == '__main__':
    unittest.main(verbosity=2)
