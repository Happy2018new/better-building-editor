"""World replies preserve readable failures and clear the public busy state."""
import json
import unittest

import test_bridge as client_fixture
import test_server_stream as server_fixture
from modern_projection import server_system as server
from projection.error_text import error_text
from projection.model import Document, Editor
from projection.projection_target import ProjectionTarget, placement_target


STONE = ('minecraft:stone', 0)


class WorldFeedbackTests(unittest.TestCase):
    read_entity = server_fixture.ServerStreamTests.read_entity
    read_palette = server_fixture.ServerStreamTests.read_palette
    write = server_fixture.ServerStreamTests.write
    write_palette = server_fixture.ServerStreamTests.write_palette
    set_actor = server_fixture.ServerStreamTests.set_actor
    set_liquid = server_fixture.ServerStreamTests.set_liquid

    def setUp(self):
        server_fixture.ServerStreamTests.setUp(self)
        client_fixture.ProjectionLifecycleTests.setUp(self)
        self.addCleanup(client_fixture.ProjectionLifecycleTests.tearDown, self)
        self.bridge.entity = None
        self.bridge.session.origin = (11, 70, -13)
        self.bridge.session.editor = Editor(Document((2, 1, 1), {
            (0, 0, 0): ('minecraft:bed', 0), (1, 0, 0): STONE}))
        target = ProjectionTarget(self.bridge.session)
        while not target.advance():
            pass
        self.bridge.projection_target = target
        self.bridge.session.projection_active = True
        self.events = []
        self.runtime.NotifyToServer = lambda event, data: self.host.request(
            dict(data, __id__='player'))
        self.host.reply = lambda player, request, **data: server.ModernProjectionServerSystem.reply(
            self.host, player, request, **data)
        self.host.NotifyToClient = self.receive

    def receive(self, player, event, data):
        self.events.append(data)
        self.bridge.receive(json.loads(json.dumps(data)))

    def drain(self):
        for unused in range(500):
            if not self.runtime.timers:
                return
            self.runtime.timers.pop(0)()
        self.fail('upload callbacks did not finish')

    def finish(self):
        for unused in range(20):
            if not self.host.jobs:
                return
            self.host.tick()
        self.fail('world feedback did not finish')

    def start(self):
        target = self.bridge.projection_target
        self.bridge.apply_world()
        self.drain()
        self.assertIn('player', self.host.jobs)
        # A setting callback racing with the server reply cannot validate the
        # previous publication against the newly selected direction.
        self.bridge.session.set_projection_rotation('rotate_y90')
        return target

    def assert_finished(self, target, reason):
        b, session = self.bridge, self.bridge.session
        self.assertIsNone(b.pending)
        self.assertFalse(session.busy)
        self.assertIs(target, b.projection_target)
        self.assertIn(reason, session.editor.message)
        message = session.editor.message
        b.receive({'request': 1, 'done': False, 'message': 'obsolete progress'})
        self.assertEqual(message, session.editor.message)
        with self.assertRaisesRegex(ValueError, '先更新投影'):
            placement_target(b)

    def test_bed_failure_reaches_client_with_coordinate_and_keeps_later_writes(self):
        target = self.start()
        self.finish()
        self.assert_finished(target, '多格方块缺少对应部件：minecraft:bed')
        self.assertIn('首处失败 (11, 70, -13)', self.bridge.session.editor.message)
        self.assertEqual([(12, 70, -13)], self.writes)
        self.assertEqual({'total': 2, 'processed': 2, 'written': 1, 'failed': 1},
                         self.events[-1]['progress'])

    def test_sdk_utf8_bytes_reach_client_as_text_and_do_not_interrupt_later_cells(self):
        target = self.start()
        adapter = self.host.jobs['player'][3]
        original = adapter.write
        adapter.validate_write = lambda *args: None
        self.host.jobs['player'][2].validate_write = adapter.validate_write

        def write(pos, value, origin):
            if pos == (11, 70, -13):
                raise RuntimeError('原生写入接口失败'.encode('utf8'))
            return original(pos, value, origin)

        adapter.write = write
        self.finish()
        self.assert_finished(target, '原生写入接口失败')
        self.assertNotIn("b'", self.bridge.session.editor.message)
        self.assertEqual([(12, 70, -13)], self.writes)

    def test_cancel_preserves_bed_reason_and_prevents_future_writes(self):
        target = self.start()
        job = self.host.jobs['player'][2]
        job.step(1)
        self.bridge.cancel_world()
        self.assert_finished(target, '多格方块缺少对应部件：minecraft:bed')
        self.assertIn('操作已取消', self.bridge.session.editor.message)
        self.assertNotIn('player', self.host.jobs)
        self.assertEqual([], self.writes)

    def test_public_apply_action_displays_stale_target_reason_without_upload(self):
        session = self.bridge.session
        session.set_projection_rotation('rotate_y90')
        self.assertFalse(session.action(self.bridge.confirm_apply_world))
        self.assertIn('先更新投影', session.editor.message)
        self.assertEqual({}, self.host.jobs)
        self.assertEqual({}, self.host.uploads)
        self.assertIsNone(self.bridge.pending)

    def test_error_details_preserve_unicode_bytes_and_ascii_and_replace_invalid_utf8(self):
        for error, expected in ((ValueError('中文失败'), '中文失败'),
                                (ValueError('中文失败'.encode('utf8')), '中文失败'),
                                (ValueError(b'bad\xffreason'), 'bad\ufffdreason'),
                                (TypeError('ASCII reason'), 'ASCII reason')):
            with self.subTest(error=repr(error)):
                self.assertEqual(expected, error_text(error))


if __name__ == '__main__':
    unittest.main()
