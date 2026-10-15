"""Book owners have their own preview, world transaction and recovery lifetime."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.book_preview import BookPreview
from projection.book_profile import candidate_profile
from projection.book_projection import BookProjection
from projection.cell import make_cell
from projection.liquid_render import WorldLiquidRenderer
from projection.model import Document, Editor
from projection.portal_profile import candidate_profile as portal_profile
from projection.projection_companions import ProjectionCompanions
import test_bridge as bridge_tests
from test_liquid_projection import ProjectionRuntime
from test_liquid_render import Runtime


def table():
    return make_cell(('minecraft:enchanting_table', 0),
                     nbt={'id': {'__type__': 8, '__value__': 'EnchantTable'}})


class BookPreviewOwnerTests(unittest.TestCase):
    def setUp(self):
        self.hidden = set()
        self.events = []
        self.document = Document((8, 3, 8), {(1, 1, 1): table(), (5, 2, 5): table()})
        self.session = SimpleNamespace(editor=SimpleNamespace(document=self.document,
            revision=0, layer=1), preview_hidden=lambda: tuple(sorted(self.hidden)),
            solo_layer=False, emit=self.events.append)
        self.profile = candidate_profile()
        self.preview = BookPreview(self.session, self.profile)

    def finish(self):
        for unused in range(100):
            if self.preview.advance():
                return
        self.fail('Book preview did not finish')

    def test_hidden_and_solo_layers_restore_without_mutating_source_or_portal_owner(self):
        before = deepcopy(self.document.to_data())
        portal = self.session.portal_preview = object()
        self.finish()
        keys = self.preview.keys
        self.assertEqual(2, len(keys))
        self.hidden.add(2)
        self.finish()
        self.assertEqual(1, len(self.preview.groups))
        self.hidden.clear()
        self.session.solo_layer = True
        self.finish()
        self.assertEqual(1, len(self.preview.groups))
        self.session.solo_layer = False
        self.finish()
        self.assertEqual(keys, self.preview.keys)
        self.assertIs(portal, self.session.portal_preview)
        self.assertEqual(before, self.document.to_data())

    def test_missing_model_latches_then_retry_restores_and_close_stops_work(self):
        self.finish()
        previous = dict(self.preview.groups)
        self.profile.models = {}
        self.session.editor.revision += 1
        self.assertFalse(self.preview.advance())
        self.assertIsInstance(self.preview.error, ValueError)
        self.assertEqual(previous, self.preview.groups)
        for unused in range(4):
            self.assertFalse(self.preview.advance())
        self.profile.models = candidate_profile().models
        self.preview.retry()
        self.finish()
        self.assertIsNone(self.preview.error)
        self.preview.close()
        self.assertFalse(self.preview.advance())
        self.assertEqual({}, self.preview.groups)


class BookProjectionOwnerTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.runtime.session = SimpleNamespace(opacity=.4)
        self.document = Document((8, 3, 8), {(1, 1, 1): table(), (5, 2, 5): table()})
        self.owner = BookProjection(self.runtime, self.document, (10, 64, 20), candidate_profile(), 0)
        self.now = 0.

    def finish(self):
        for unused in range(100):
            self.now += .1
            with patch('projection.liquid_projection.time.time', return_value=self.now):
                if self.owner.advance():
                    return
        self.fail('Book world owner did not finish')

    def test_targets_remain_detached_and_only_publish_after_transaction_with_live_opacity(self):
        targets = self.document.palette_data(lambda pos: pos == (1, 1, 1))
        self.owner.request(targets, deferred=True)
        targets['common'].clear()
        self.finish()
        self.assertEqual(1, len(self.runtime.models))
        self.assertTrue(all(self.runtime.hidden(model) for model in self.runtime.models))
        self.owner.publish()
        identities = set(self.runtime.models)
        self.runtime.session.opacity = .7
        self.assertTrue(self.owner.advance())
        self.assertEqual(identities, set(self.runtime.models))
        self.assertTrue(all(value['uniforms'][4][3] == .7 for value in self.runtime.models.values()))
        self.assertTrue(all(value['name'] == 'modern_projection_book_enchanting_table_world'
                            for value in self.runtime.models.values()))

    def test_failed_plan_keeps_previous_models_and_failed_cleanup_is_retried(self):
        self.owner.request()
        self.finish()
        self.owner.publish()
        previous = deepcopy(self.runtime.models)
        self.owner.profile.world_models = {}
        self.owner.request()
        self.assertFalse(self.owner.advance())
        self.assertIsInstance(self.owner.error, ValueError)
        self.assertEqual(previous, self.runtime.models)
        self.runtime.remove_ok = False
        self.assertFalse(self.owner.close())
        self.assertTrue(all(self.runtime.hidden(model) for model in self.runtime.models))
        self.runtime.remove_ok = True
        self.assertTrue(self.owner.close())
        self.assertEqual({}, self.runtime.models)


class BookWorldIntegrationTests(unittest.TestCase):
    def setUp(self):
        bridge_tests.ProjectionLifecycleTests.setUp(self)
        previous = self.runtime
        self.runtime = ProjectionRuntime()
        self.runtime.timers = previous.timers
        self.bridge.factory = self.bridge.system = self.runtime
        self.bridge.session.book_profile = candidate_profile()
        self.bridge.session.portal_profile = portal_profile()
        self.bridge.session.editor = Editor(Document((4, 3, 4), {(1, 1, 1): table()}))
        self.bridge.geometry = lambda *args, **kwargs: kwargs.get('name') or 'body_model'
        self.settle = patch.object(WorldLiquidRenderer, 'SETTLE_SECONDS', 0.)
        self.settle.start()

    def tearDown(self):
        self.settle.stop()
        bridge_tests.ProjectionLifecycleTests.tearDown(self)

    def drain(self):
        bridge_tests.ProjectionLifecycleTests.drain_projection(self, limit=400)

    def book_owner(self):
        owner = self.bridge.projection_liquid
        self.assertIsInstance(owner, ProjectionCompanions)
        self.assertEqual({'PortalProjection', 'BookProjection'},
                         {type(value).__name__ for value in owner.companions})
        return next(value for value in owner.companions if isinstance(value, BookProjection))

    def test_default_session_keeps_book_gate_closed(self):
        self.assertIsNone(bridge_tests.Session(self.bridge).book_profile)

    def test_full_and_missing_build_use_independent_book_owner_and_release_native_models(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                self.bridge.session.projection_missing = missing
                self.bridge.project_large((10, 64, 20))
                self.drain()
                work = self.bridge.projection_work
                self.assertTrue(work.ready, work.error)
                book = self.book_owner()
                self.assertTrue(book.committed)
                self.assertEqual(1, len(book.renderer.active))
                self.assertEqual(1, len(self.runtime.liquid_models.models))
                self.bridge.stop_projection()
                self.drain()
                self.assertTrue(book.closed)
                self.assertEqual({}, self.runtime.liquid_models.models)

    def test_book_path_does_not_borrow_portal_owner_slot(self):
        self.bridge.session.portal_profile = None
        self.bridge.session.projection_missing = False
        self.bridge.project_large((10, 64, 20))
        self.drain()
        owner = self.bridge.projection_liquid
        self.assertIsInstance(owner, BookProjection)
        self.assertNotEqual('PortalProjection', type(owner).__name__)
        self.assertTrue(owner.committed)
        self.bridge.stop_projection()
        self.drain()
        self.assertTrue(owner.closed)

    def test_missing_projection_hides_and_restores_book_with_occupancy_snapshot(self):
        self.bridge.session.projection_missing = True
        self.bridge.project_large((10, 64, 20))
        self.drain()
        book = self.book_owner()
        tracker = self.bridge.projection_occupancy
        source = deepcopy(book.document.to_data())
        for state, expected in ((2, 0), (1, 1)):
            tracker.snapshot = tracker.rendered[:]
            tracker.snapshot[tracker.index((1, 1, 1))] = state
            for unused in range(100):
                if tracker.replace(tracker.model, tracker.anchor):
                    break
            self.assertIsNone(tracker.pending_pair)
            self.assertEqual(expected, len(book.renderer.active))
            self.assertEqual(expected, len(self.runtime.liquid_models.models))
        self.assertEqual(source, book.document.to_data())

    def test_failed_native_attachment_keeps_old_book_and_reclaims_new_generation(self):
        self.bridge.project_large((10, 64, 20))
        self.drain()
        previous = self.bridge.projection_liquid
        models = set(self.runtime.liquid_models.models)
        self.runtime.success = False
        self.bridge.project_large((20, 64, 20))
        self.drain()
        self.assertIsNotNone(self.bridge.projection_work.error)
        self.assertIs(previous, self.bridge.projection_liquid)
        self.assertEqual(models, set(self.runtime.liquid_models.models))
        self.assertTrue(all(not self.runtime.liquid_models.hidden(model) for model in models))


if __name__ == '__main__':
    unittest.main()
