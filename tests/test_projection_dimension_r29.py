# -*- coding: utf-8 -*-
"""Focused real bridge/server-boundary checks; no native process is accessed."""
import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))

import test_world_feedback_r29 as feedback_fixture
from projection.model import Document, Editor

STONE = ('minecraft:stone', 0)
OBSERVATIONS = []


class ConfirmationDimensionTests(unittest.TestCase):
    read_entity = feedback_fixture.WorldFeedbackTests.read_entity
    read_palette = feedback_fixture.WorldFeedbackTests.read_palette
    write = feedback_fixture.WorldFeedbackTests.write
    write_palette = feedback_fixture.WorldFeedbackTests.write_palette
    set_actor = feedback_fixture.WorldFeedbackTests.set_actor
    set_liquid = feedback_fixture.WorldFeedbackTests.set_liquid
    receive = feedback_fixture.WorldFeedbackTests.receive
    drain = feedback_fixture.WorldFeedbackTests.drain
    finish = feedback_fixture.WorldFeedbackTests.finish

    def setUp(self):
        feedback_fixture.WorldFeedbackTests.setUp(self)
        self.client_dimension = 0
        self.runtime.GetCurrentDimension = lambda: self.client_dimension
        self.bridge.projection_target = None
        self.bridge.session.projection_active = False
        self.bridge.session.projection_transform = ('rotate_y90',)
        self.bridge.session.editor = Editor(Document((1, 1, 1), {(0, 0, 0): STONE}))
        self.stderr = io.StringIO()
        redirect = contextlib.redirect_stderr(self.stderr)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)

    def source(self, published):
        if published:
            self.bridge.project()
            self.drain()
            self.assertTrue(self.bridge.session.projection_active)
            self.assertIsNotNone(self.bridge.projection_target.document)
        self.bridge.confirm_apply_world()
        self.assertIsNotNone(self.bridge.session.pending_confirm)

    def change_dimension(self, event=True):
        self.client_dimension = self.dimension = 1
        if event:
            self.bridge.dimension_changed({'playerId': 'player', 'fromDimensionId': 0,
                                           'toDimensionId': 1, 'toPos': (0, 64, 0)})

    def record(self, pending_before_accept=None):
        value = {'test': self._testMethodName,
                 'modal_after_event': pending_before_accept,
                 'writes': self.writes,
                 'write_dimensions': [row[1] for row in self.palette_writes],
                 'pending': self.bridge.pending,
                 'busy': self.bridge.session.busy,
                 'progress': self.bridge.session.progress,
                 'message': self.bridge.session.editor.message}
        OBSERVATIONS.append(value)
        return value

    def check_event(self, published):
        self.source(published)
        self.change_dimension()
        pending = self.bridge.session.pending_confirm is not None
        self.bridge.session.accept()
        self.drain()
        self.finish()
        self.record(pending)
        self.assertFalse(pending, 'dimension event must cancel only the world-write confirmation')
        self.assertEqual([], self.writes)
        self.assertFalse(self.bridge.session.busy)

    def test_published_event_cancels_confirmation(self):
        self.check_event(True)

    def test_unpublished_event_cancels_confirmation(self):
        self.check_event(False)

    def check_delayed_event(self, published):
        self.source(published)
        self.change_dimension(False)
        self.bridge.session.accept()
        self.drain()
        self.finish()
        self.record()
        self.assertEqual([], self.writes)
        self.assertIsNone(self.bridge.pending)
        self.assertFalse(self.bridge.session.busy)
        self.assertIn('维度', self.bridge.session.editor.message)

    def test_published_accept_rechecks_native_dimension(self):
        self.check_delayed_event(True)

    def test_unpublished_accept_rechecks_native_dimension(self):
        self.check_delayed_event(False)

    def check_unchanged(self, published):
        self.source(published)
        self.bridge.session.accept()
        self.drain()
        self.finish()
        self.record()
        self.assertEqual([(11, 70, -13)], self.writes)
        self.assertEqual([0], [row[1] for row in self.palette_writes])
        self.assertFalse(self.bridge.session.busy)

    def test_published_same_dimension_can_apply(self):
        self.check_unchanged(True)

    def test_unpublished_same_dimension_can_apply(self):
        self.check_unchanged(False)

    def test_unrelated_confirmation_survives_dimension_event(self):
        called = []
        self.bridge.session.confirm('generic library deletion', lambda: called.append(True))
        self.change_dimension()
        self.assertIsNotNone(self.bridge.session.pending_confirm)
        self.bridge.session.accept()
        self.assertEqual([True], called)

    def test_incomplete_preparation_rechecks_dimension_before_first_packet(self):
        doc = Document((16, 4, 16), {(x, y, z): STONE for x in range(16)
                                     for y in range(4) for z in range(16)})
        self.bridge.session.editor = Editor(doc)
        self.source(False)
        self.bridge.session.accept()
        self.assertIsNotNone(self.bridge.projection_preparation)
        self.assertIsNone(self.bridge.pending)
        self.change_dimension(False)
        self.drain()
        self.finish()
        self.record()
        self.assertEqual([], self.writes)
        self.assertIsNone(self.bridge.pending)
        self.assertFalse(self.bridge.session.busy)
        self.assertIn('维度', self.bridge.session.editor.message)

    def test_first_packet_race_requires_server_dimension_guard(self):
        self.source(True)
        original = self.runtime.NotifyToServer
        first = []
        def receive_in_other_dimension(event, data):
            if 'stream' in data and not first:
                first.append(dict(data))
                self.dimension = 1
            original(event, data)
        self.runtime.NotifyToServer = receive_in_other_dimension
        self.bridge.session.accept()
        self.drain()
        self.finish()
        self.record()
        self.assertEqual([], self.writes)

    def fail_dimension_query(self):
        raise RuntimeError('原生维度查询失败')

    def assert_query_failure_released(self):
        session = self.bridge.session
        self.assertIn('原生维度查询失败', session.editor.message)
        self.assertIsNone(session.pending_confirm)
        self.assertIsNone(self.bridge.pending)
        self.assertIsNone(self.bridge.projection_preparation)
        self.assertFalse(session.busy)
        self.assertEqual({}, self.host.jobs)
        self.assertEqual({}, self.host.uploads)
        self.assertEqual([], self.writes)

    def test_dimension_query_failure_while_opening_confirmation_is_readable(self):
        self.runtime.GetCurrentDimension = self.fail_dimension_query
        self.assertFalse(self.bridge.session.action(self.bridge.confirm_apply_world))
        self.assert_query_failure_released()

    def test_dimension_query_failure_while_accepting_confirmation_is_readable(self):
        self.source(True)
        self.runtime.GetCurrentDimension = self.fail_dimension_query
        self.bridge.session.accept()
        self.assert_query_failure_released()

    def test_dimension_query_failure_at_start_does_not_reserve_a_job(self):
        self.runtime.GetCurrentDimension = self.fail_dimension_query
        self.assertFalse(self.bridge.session.action(self.bridge.apply_world))
        self.assert_query_failure_released()

    def test_dimension_query_failure_during_preparation_releases_busy(self):
        self.bridge.session.editor = Editor(Document((16, 4, 16), {
            (x, y, z): STONE for x in range(16) for y in range(4) for z in range(16)}))
        self.source(False)
        self.bridge.session.accept()
        self.assertIsNotNone(self.bridge.projection_preparation)
        self.assertIsNone(self.bridge.pending)
        self.runtime.GetCurrentDimension = self.fail_dimension_query
        self.drain()
        self.assert_query_failure_released()

    def test_dimension_query_failure_while_receiving_check_result_is_readable(self):
        deliveries = []
        original = self.host.NotifyToClient
        def hold_final(player, event, data):
            if data.get('done'):
                deliveries.append((player, event, data))
            else:
                original(player, event, data)
        self.host.NotifyToClient = hold_final
        self.bridge.check_progress()
        self.drain()
        self.finish()
        self.assertTrue(deliveries)
        self.assertIsNotNone(self.bridge.pending)
        self.runtime.GetCurrentDimension = self.fail_dimension_query
        for args in deliveries:
            original(*args)
        self.assertIsNone(self.bridge.session.progress)
        self.assert_query_failure_released()

    def test_check_reply_after_dimension_event_is_not_published(self):
        self.source(True)
        self.bridge.session.pending_confirm = None
        deliveries = []
        original = self.host.NotifyToClient
        self.host.NotifyToClient = lambda *args: deliveries.append(args)
        self.bridge.check_progress()
        # Feed acknowledgements synchronously, while retaining only terminal replies.
        for unused in range(200):
            if not deliveries:
                break
            args = deliveries[0]
            if args[2].get('done'):
                break
            deliveries.pop(0)
            original(*args)
            self.drain()
        self.finish()
        self.assertTrue(any(row[2].get('done') for row in deliveries))
        self.change_dimension()
        for args in deliveries:
            original(*args)
        self.record()
        self.assertIsNone(self.bridge.session.progress)
        self.assertIsNone(self.bridge.pending)
        self.assertFalse(self.bridge.session.busy)


class SessionLibraryProgressTests(unittest.TestCase):
    def test_loading_another_library_document_clears_previous_progress(self):
        from test_session import Bridge
        from projection.session import Session
        session = Session(Bridge())
        previous_editor = session.editor
        session.progress = {'total': 17, 'correct': 12, 'missing': 3, 'wrong': 2}
        session.library = [{'id': 9001, 'data': {'version': 1,
            'name': 'New one-cell library document', 'size': [1, 1, 1], 'blocks': []}}]
        session.load(9001)
        self.assertIsNot(previous_editor, session.editor)
        self.assertEqual((1, 1, 1), session.editor.document.size)
        self.assertIsNone(session.progress)


if __name__ == '__main__':
    unittest.main()
