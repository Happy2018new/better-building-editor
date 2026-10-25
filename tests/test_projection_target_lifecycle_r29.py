"""Exercise frozen target publication/confirmation with the existing fake SDK."""
import contextlib
import io
import unittest
from unittest.mock import patch

import test_bridge as fixture
from projection.model import Document, Editor
from projection.projection_target import ProjectionTarget, placement_target
from projection.transfer import Receiver


STONE = ('minecraft:stone', 0)
GOLD = ('minecraft:gold_block', 0)


class ProjectionTargetLifecycleTests(unittest.TestCase):
    def setUp(self):
        fixture.ProjectionLifecycleTests.setUp(self)
        self.bridge.entity = None
        self.bridge.session.projection_active = False
        self.bridge.session.editor = Editor(Document(
            (4, 3, 2), {(0, 0, 0): STONE, (3, 2, 1): GOLD}, name='Frozen target R29'))
        self.bridge.session.origin = (11, 70, -13)
        self.errors = io.StringIO()
        self.redirect = contextlib.redirect_stderr(self.errors)
        self.redirect.__enter__()

    def tearDown(self):
        self.redirect.__exit__(None, None, None)
        fixture.ProjectionLifecycleTests.tearDown(self)

    def drain(self):
        for unused in range(500):
            if not self.runtime.timers:
                return
            self.runtime.timers.pop(0)()
        self.fail('target work failed to finish')

    def publish(self):
        self.bridge.project()
        self.drain()
        self.assertTrue(self.bridge.session.projection_active)
        self.assertIsNotNone(self.bridge.projection_target)
        return self.bridge.projection_target

    def transferred(self):
        b, runtime = self.bridge, self.runtime
        for unused in range(100):
            if b.upload is None:
                break
            b.receive({'request': b.pending, 'done': False, 'uploadAck': b.upload_sequence})
            self.drain()
        self.assertIsNone(b.upload)
        receiver = Receiver()
        sent = [event for event in runtime.sent if 'stream' in event]
        for event in sent:
            receiver.feed(event['stream'])
        self.assertIsNotNone(receiver.result)
        return sent[0], receiver.result

    def test_target_captures_document_and_parameters_before_first_frame(self):
        session = self.bridge.session
        session.projection_transform = ('rotate_y90',)
        target = ProjectionTarget(session)
        session.editor.document.set_cell((0, 0, 0), GOLD)
        session.origin = (30, 80, 40)
        session.projection_transform = ('mirror_z',)
        while not target.advance():
            pass
        self.assertEqual((11, 70, -13), target.origin)
        self.assertEqual(('rotate_y90',), target.operations)
        self.assertEqual((2, 3, 4), target.document.size)
        self.assertEqual(STONE, target.document.get((1, 0, 0)))
        self.assertEqual(GOLD, session.editor.document.get((0, 0, 0)))

    def test_vertical_mirror_maps_hidden_and_solo_layers(self):
        session = self.bridge.session
        session.editor.hidden_layers = {0}
        session.editor.layer = 0
        session.solo_layer = True
        session.projection_transform = ('mirror_y', 'rotate_y90')
        target = ProjectionTarget(session)
        self.assertEqual(frozenset((2,)), target.hidden)
        self.assertEqual(2, target.layer)
        self.assertEqual({0}, session.editor.hidden_layers)
        self.assertEqual(0, session.editor.layer)

    def assert_mirrored_visibility(self, hidden=(), solo=False, occupied=False, bulk=False):
        b, session = self.bridge, self.bridge.session
        size = (17, 17, 17) if bulk else (4, 3, 2)
        top = size[1] - 1
        source = Document(size, {(0, 0, 0): STONE, (1, top, 0): GOLD})
        session.editor = Editor(source)
        session.editor.hidden_layers = set(hidden)
        session.editor.layer = 0
        session.solo_layer = solo
        session.projection_missing = True
        session.projection_transform = ('mirror_y',)
        expected = (0, top, 0)
        excluded = (1, 0, 0)
        if occupied:
            self.runtime.world[tuple(a + c for a, c in zip(session.origin, expected))] = STONE
        palettes = []
        b.geometry = lambda doc, **kwargs: palettes.append(doc.palette_data()) or (
            (kwargs.get('name') or 'model') if doc.count else None)
        self.publish()
        work, tracker = b.projection_work, b.projection_occupancy
        self.assertTrue(work.ready)
        self.assertIsNotNone(tracker)
        self.assertIs(work.occupancy, tracker)
        self.assertEqual({top - y for y in hidden}, work.hidden)
        self.assertEqual(work.hidden, tracker.hidden)
        self.assertEqual(top if solo else None, work.layer)
        self.assertEqual(work.layer, tracker.layer)
        self.assertEqual({expected}, set(tracker.positions()))
        self.assertTrue(work.visible_layer(top))
        self.assertTrue(tracker.visible_layer(top))
        self.assertFalse(work.visible_layer(0))
        self.assertFalse(tracker.visible_layer(0))
        self.assertEqual(STONE, work.document.get(expected))
        self.assertEqual(GOLD, tracker.document.get(excluded))
        self.assertEqual(2 if occupied else 1, tracker.state[tracker.index(expected)])
        self.assertEqual(0, tracker.state[tracker.index(excluded)])
        self.assertEqual(set(hidden), session.editor.hidden_layers)
        self.assertEqual(0, session.editor.layer)
        self.assertEqual(STONE, source.get((0, 0, 0)))
        self.assertEqual(GOLD, source.get((1, top, 0)))
        self.assertEqual(bulk, tracker.bulk is not None)
        if occupied:
            self.assertTrue(palettes)
            self.assertTrue(all(not palette['common'] for palette in palettes))
            self.assertEqual(-1, tracker.slots[tracker.index(expected)])
        else:
            self.assertTrue(palettes)
            for palette in palettes:
                self.assertEqual({STONE: [top * size[0] * size[2]]}, palette['common'])

    def test_vertical_mirror_hidden_layers_reach_initial_missing_filter(self):
        self.assert_mirrored_visibility(hidden={2})

    def test_vertical_mirror_solo_layer_reaches_initial_missing_filter(self):
        self.assert_mirrored_visibility(solo=True)

    def test_vertical_mirror_hidden_layers_reach_bulk_missing_filter(self):
        self.assert_mirrored_visibility(hidden={16}, bulk=True)

    def test_vertical_mirror_solo_layer_reaches_bulk_missing_filter(self):
        self.assert_mirrored_visibility(solo=True, bulk=True)

    def test_mirrored_occupied_target_is_tracked_without_being_rendered(self):
        self.assert_mirrored_visibility(hidden={2}, occupied=True)

    def test_session_transform_settings_use_canonical_order_and_clear_progress(self):
        session = self.bridge.session
        changes = [('set_projection_rotation', 'rotate_y90', ('rotate_y90',)),
                   ('toggle_projection_mirror', 'mirror_z', ('rotate_y90', 'mirror_z')),
                   ('toggle_projection_mirror', 'mirror_y', ('rotate_y90', 'mirror_y', 'mirror_z')),
                   ('toggle_projection_mirror', 'mirror_x', ('rotate_y90', 'mirror_x', 'mirror_y', 'mirror_z')),
                   ('set_projection_rotation', 'rotate_y270', ('rotate_y270', 'mirror_x', 'mirror_y', 'mirror_z')),
                   ('set_projection_rotation', '', ('mirror_x', 'mirror_y', 'mirror_z')),
                   ('toggle_projection_mirror', 'mirror_y', ('mirror_x', 'mirror_z')),
                   ('toggle_projection_mirror', 'mirror_y', ('mirror_x', 'mirror_y', 'mirror_z'))]
        for method, operation, expected in changes:
            with self.subTest(method=method, operation=operation):
                session.progress = {'correct': 2}
                getattr(session, method)(operation)
                self.assertEqual(expected, session.projection_transform)
                self.assertIsNone(session.progress)
        session.progress = {'correct': 2}
        session.reset_projection_transform()
        self.assertEqual((), session.projection_transform)
        self.assertIsNone(session.progress)

    def test_invalid_session_transform_preserves_settings_and_progress(self):
        session = self.bridge.session
        session.projection_transform = ('rotate_y90', 'mirror_x')
        progress = {'correct': 2}
        for method, operation in [('set_projection_rotation', 'mirror_y'),
                                  ('toggle_projection_mirror', 'rotate_y180')]:
            with self.subTest(method=method):
                session.progress = progress
                with self.assertRaises(ValueError):
                    getattr(session, method)(operation)
                self.assertEqual(('rotate_y90', 'mirror_x'), session.projection_transform)
                self.assertIs(progress, session.progress)

    def test_new_target_is_not_published_until_native_attachment_succeeds(self):
        b, runtime = self.bridge, self.runtime
        original = self.publish()
        old_entity = b.entity
        b.session.projection_transform = ('rotate_y90',)
        b.project()
        self.assertIs(original, b.projection_target)
        self.assertEqual(old_entity, b.entity)
        self.drain()
        self.assertIsNot(original, b.projection_target)
        self.assertEqual(('rotate_y90',), b.projection_target.operations)
        self.assertEqual((2, 3, 4), b.projection_target.document.size)
        self.assertNotEqual(old_entity, b.entity)

    def test_failed_update_keeps_previous_target_and_rejects_unpublished_placement(self):
        b, runtime = self.bridge, self.runtime
        original = self.publish()
        old_entity = b.entity
        b.session.projection_transform = ('mirror_x',)
        runtime.success = False
        b.project()
        self.drain()
        self.assertIs(original, b.projection_target)
        self.assertEqual(old_entity, b.entity)
        self.assertTrue(b.session.projection_active)
        with self.assertRaisesRegex(ValueError, '更新投影'):
            b.apply_world()
        self.assertEqual([], runtime.sent)

    def test_failed_rebuild_with_unchanged_settings_keeps_old_target_usable(self):
        b = self.bridge
        original = self.publish()
        self.runtime.success = False
        b.project()
        self.drain()
        self.assertTrue(b.projection_work.error)
        selected = placement_target(b)
        self.assertIsNot(original, selected)
        self.assertEqual(original.source_key, selected.source_key)
        self.assertEqual(original.document.to_data(), selected.document.to_data())
        selected.document.set_cell((0, 0, 0), GOLD)
        self.assertEqual(STONE, original.document.get((0, 0, 0)))

    def test_stop_invalidates_queued_preparation_without_creating_or_uploading(self):
        b = self.bridge
        with patch.object(ProjectionTarget, 'advance', return_value=False):
            b.project()
            self.assertIsNotNone(b.projection_preparation)
            self.assertTrue(b.session.busy)
            b.stop_projection()
            self.drain()
        self.assertIsNone(b.projection_preparation)
        self.assertIsNone(b.projection_target)
        self.assertFalse(b.session.projection_active)
        self.assertFalse(b.session.busy)
        self.assertEqual([], self.runtime.created)
        self.assertEqual([], self.runtime.sent)

    def test_new_preparation_supersedes_old_queued_transformation(self):
        b = self.bridge
        advance = ProjectionTarget.advance
        with patch.object(ProjectionTarget, 'advance', lambda target: advance(target, budget=1)):
            b.session.projection_transform = ('rotate_y90',)
            b.project()
            abandoned = b.projection_preparation
            self.assertIsNotNone(abandoned)
            b.session.projection_transform = ('mirror_x',)
            b.project()
            self.drain()
        self.assertTrue(b.session.projection_active)
        self.assertEqual(('mirror_x',), b.projection_target.operations)
        self.assertEqual((4, 3, 2), b.projection_target.document.size)
        anchors = [entity for entity in self.runtime.created
                   if self.runtime.actor_positions[entity][0] == b'modern_projection:anchor']
        self.assertEqual(1, len(anchors))
        self.assertIsNone(abandoned.target.document)

    def test_running_transformation_preparation_blocks_placement_even_for_old_matching_target(self):
        b = self.bridge
        self.publish()
        with patch.object(ProjectionTarget, 'advance', return_value=False):
            b.project()
            with self.assertRaisesRegex(ValueError, '正在|完成|准备'):
                placement_target(b)
            b.cancel_world()
            self.drain()
        self.assertFalse(b.session.busy)
        self.assertEqual([], self.runtime.sent)

    def test_confirmation_freezes_origin_operations_air_and_document_before_accept(self):
        b, session = self.bridge, self.bridge.session
        session.projection_transform = ('rotate_y90',)
        session.apply_air = True
        published = self.publish()
        before = published.document.to_data()
        b.confirm_apply_world()
        title = session.pending_confirm[0]
        self.assertIn('11, 70, -13', title)
        self.assertIn('2 × 3 × 4', title)
        self.assertIn('90', title)
        self.assertIn('空气', title)
        # Direct mutations model callbacks racing with the confirmation panel.
        published.document.set_cell((1, 0, 0), GOLD)
        session.editor.document.set_cell((0, 0, 0), GOLD)
        session.origin = (41, 80, 43)
        session.projection_transform = ('mirror_z',)
        session.apply_air = False
        session.accept()
        first, uploaded = self.transferred()
        self.assertEqual((11, 70, -13), first['origin'])
        self.assertTrue(first['includeAir'])
        self.assertEqual(before, uploaded.to_data())
        self.assertEqual((2, 3, 4), uploaded.size)

    def test_changed_transform_rejects_old_check_result(self):
        b, session = self.bridge, self.bridge.session
        b.check_progress()
        self.drain()
        request = b.pending
        self.assertIsNotNone(request)
        session.projection_transform = ('mirror_z',)
        b.receive({'request': request, 'done': True,
                   'progress': {'total': 2, 'correct': 2, 'missing': 0, 'wrong': 0}})
        self.assertIsNone(session.progress)
        self.assertIn('改变', session.editor.message)
        self.assertFalse(session.busy)

    def test_capture_accepts_a_result_after_only_projection_settings_change(self):
        b, session = self.bridge, self.bridge.session
        document = Document((2, 3, 4), {(1, 2, 3): GOLD})
        b.request('capture', {'origin': (31, 70, 37)})
        session.set_projection_rotation('rotate_y90')
        b.receive({'request': b.pending, 'done': True, 'document': document.to_data()})
        self.assertEqual(document.to_data(), session.editor.document.to_data())
        self.assertEqual((31, 70, 37), session.origin)
        self.assertEqual(('rotate_y90',), session.projection_transform)
        self.assertFalse(session.busy)

    def test_capture_uses_its_valid_selected_origin_despite_an_invalid_projection_origin(self):
        b, session = self.bridge, self.bridge.session
        session.origin = (30000001, 64, 0)
        document = Document((1, 1, 1), {(0, 0, 0): GOLD})
        b.request('capture', {'origin': (0, 64, 0)})
        self.assertIsNotNone(b.pending)
        b.receive({'request': b.pending, 'done': True, 'document': document.to_data()})
        self.assertEqual((0, 64, 0), session.origin)
        self.assertEqual(GOLD, session.editor.document.get((0, 0, 0)))
        self.assertIsNone(b.pending)

    def test_invalid_request_state_does_not_reserve_an_unsent_request(self):
        b = self.bridge
        b.session.origin = None
        with self.assertRaises(TypeError):
            b.request('capture', {'origin': (0, 64, 0)})
        self.assertIsNone(b.pending)
        self.assertIsNone(b.pending_data)
        self.assertIsNone(b.pending_state)
        self.assertEqual(0, b.request_id)
        self.assertFalse(b.session.busy)
        self.assertEqual([], self.runtime.sent)

    def test_palette_resolution_is_independent_of_projection_transform_settings(self):
        b = self.bridge
        b.request('resolve', {'palette': [STONE]})
        b.session.toggle_projection_mirror('mirror_x')
        b.receive({'request': b.pending, 'done': True, 'palette': [GOLD]})
        self.assertEqual(GOLD, b.projection_palette[STONE])
        self.assertFalse(b.session.busy)

    def test_failed_initial_preparation_does_not_reactivate_on_a_display_toggle(self):
        b = self.bridge
        with patch.object(ProjectionTarget, 'advance', side_effect=ValueError('无法变换')):
            b.project()
        self.assertFalse(b.projection_requested)
        self.assertIsNone(b.projection_preparation)
        self.assertFalse(b.session.busy)
        self.assertEqual('无法变换', b.session.editor.message)
        b.toggle_missing()
        self.assertIsNone(b.projection_work)
        self.assertEqual([], self.runtime.created)

    def test_canceled_initial_preparation_does_not_reactivate_on_a_display_toggle(self):
        b = self.bridge
        with patch.object(ProjectionTarget, 'advance', return_value=False):
            b.project()
            b.cancel_world()
            self.drain()
        self.assertFalse(b.projection_requested)
        self.assertIsNone(b.projection_preparation)
        self.assertFalse(b.session.busy)
        b.toggle_missing()
        self.assertIsNone(b.projection_work)
        self.assertEqual([], self.runtime.created)

    def test_refused_projection_does_not_record_a_successful_request(self):
        b = self.bridge
        b.pending = 7
        with self.assertRaisesRegex(ValueError, '当前世界操作'):
            b.project()
        self.assertFalse(b.projection_requested)
        self.assertIsNone(b.projection_preparation)
        self.assertEqual([], self.runtime.created)


if __name__ == '__main__':
    unittest.main()
