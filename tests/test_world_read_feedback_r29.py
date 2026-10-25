"""World-read failures keep readable feedback and release owned pending state."""
import contextlib
import io
import json
import types
import unittest
from unittest.mock import patch

import test_bridge as client_fixture
import test_server_stream as server_fixture
from modern_projection import server_system as server
from projection.model import Document
from projection.transfer import Receiver


class WorldReadFeedbackTests(unittest.TestCase):
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
        self.events = []
        self.host.reply = lambda player, request, **data: server.ModernProjectionServerSystem.reply(
            self.host, player, request, **data)
        self.host.NotifyToClient = self.receive

    def receive(self, player, event, data):
        self.events.append(data)
        self.bridge.receive(json.loads(json.dumps(data)))

    def pending_apply(self):
        bridge, session = self.bridge, self.bridge.session
        bridge.pending = 1
        bridge.pending_data = ('apply', {'origin': session.origin})
        bridge.pending_state = None
        session.busy = True

    def assert_finished(self, message):
        bridge, session = self.bridge, self.bridge.session
        self.assertIsNone(bridge.pending)
        self.assertIsNone(bridge.pending_data)
        self.assertIsNone(bridge.pending_state)
        self.assertFalse(session.busy)
        self.assertEqual(message, session.editor.message)

    def test_server_adapter_bytes_produce_one_final_text_reply_and_clear_client(self):
        self.pending_apply()
        reason = '原生读取接口失败'
        with patch.object(server, 'WorldAdapter', side_effect=ValueError(reason.encode('utf8'))):
            self.host.request({'__id__': 'player', 'request': 1, 'action': 'apply'},
                              transferred=server.Document((1, 1, 1)))
        self.assertEqual([{'request': 1, 'done': True, 'error': reason}], self.events)
        self.assert_finished(reason)
        self.assertFalse(self.host.jobs)
        self.assertFalse(self.writes)

    def test_server_read_generator_bytes_release_job_and_ignore_delayed_progress(self):
        self.pending_apply()
        reason = '原生读取接口失败'
        def failed_read():
            raise RuntimeError(reason.encode('utf8'))
            yield None
        self.host.aura_tick = 1
        self.host.jobs['player'] = (1, 'check', failed_read(), None, 0)
        self.host.tick()
        self.assertEqual([{'request': 1, 'done': True, 'error': reason}], self.events)
        self.assert_finished(reason)
        self.assertNotIn('player', self.host.jobs)
        self.bridge.receive({'request': 1, 'done': False, 'message': 'obsolete progress'})
        self.assertEqual(reason, self.bridge.session.editor.message)

    def test_capture_initialization_bytes_clear_capture_owner_and_keep_draft(self):
        bridge, session = self.bridge, self.bridge.session
        previous = session.editor.document
        reason = '原生读取接口失败'
        with patch.object(self.runtime, 'GetCurrentDimension', return_value=0, create=True), \
                patch.object(self.runtime, 'CreateBlock', side_effect=ValueError(reason.encode('utf8'))):
            bridge.capture_region((0, 64, 0), (1, 1, 1))
        self.assertFalse(session.busy)
        self.assertIsNone(bridge.capture_active)
        self.assertIsNone(bridge.capture_dimension)
        self.assertEqual('世界读取初始化失败：'+reason, session.editor.message)
        self.assertIs(previous, session.editor.document)
        self.assertFalse(self.runtime.sent)

    def test_invalid_download_packet_sends_cancel_and_clears_pending_without_ack(self):
        self.pending_apply()
        bridge = self.bridge
        bridge.download = Receiver()
        bridge.receive({'request': 1, 'done': False, 'documentPacket': {'kind': 'bad', 'seq': 0}})
        self.assert_finished('缺少建筑传输头')
        self.assertIsNone(bridge.download)
        self.assertEqual([{'request': 1, 'action': 'cancel'}], self.runtime.sent)

    def test_capture_merge_chinese_reason_clears_download_and_preserves_draft(self):
        bridge, session = self.bridge, self.bridge.session
        previous = session.editor.document
        local = Document((1, 1, 1))
        entities = Document((1, 1, 1), {(0, 0, 0): ('minecraft:stone', 0)})
        bridge.pending = 1
        bridge.pending_data = ('capture', {'clientCapture': True, 'captureDocument': local})
        bridge.pending_state = bridge.world_request_state('capture')
        bridge.download = types.SimpleNamespace(result=entities)
        session.busy = True
        bridge.receive({'request': 1, 'done': True})
        self.assert_finished('读取期间世界方块已变化，请重新导入选区')
        self.assertIsNone(bridge.download)
        self.assertIs(previous, session.editor.document)
        self.assertEqual(0, len(local.blocks))

    def test_entity_cleanup_bytes_keep_failed_owner_and_continue_outline_liquid_then_retry(self):
        bridge = self.bridge
        calls, fail = [], [True]
        shader = types.SimpleNamespace(retire=lambda: calls.append('shader') or [])
        bridge.projection_entity_shaders['owned'] = shader
        def destroy(entity):
            calls.append('entity')
            if fail[0]:
                raise RuntimeError('原生实体回收失败'.encode('utf8'))
        outline = types.SimpleNamespace(clear=lambda: calls.append('outline'))
        liquid = types.SimpleNamespace(close=lambda: calls.append('liquid') or True)
        with patch.object(self.runtime, 'DestroyClientEntity', side_effect=destroy), \
                contextlib.redirect_stderr(io.StringIO()):
            errors = bridge.release_projection_resources(('owned',), (outline,), (liquid,))
            self.assertEqual(['原生实体回收失败'], errors)
            self.assertEqual(['shader', 'entity', 'outline', 'liquid'], calls)
            self.assertEqual({'owned'}, bridge.projection_retired_entities)
            self.assertIs(shader, bridge.projection_entity_shaders['owned'])
            self.assertEqual([], bridge.projection_retired_outlines)
            self.assertEqual([], bridge.projection_retired_liquids)
            fail[0] = False
            self.assertEqual([], bridge.release_projection_resources())
        self.assertEqual(['shader', 'entity', 'outline', 'liquid', 'shader', 'entity'], calls)
        self.assertFalse(bridge.projection_retired_entities)
        self.assertNotIn('owned', bridge.projection_entity_shaders)

    def test_outline_cleanup_bytes_keep_failed_outline_and_continue_liquid_then_retry(self):
        bridge = self.bridge
        calls, fail = [], [True]
        def clear():
            calls.append('outline')
            if fail[0]:
                raise RuntimeError('原生边框回收失败'.encode('utf8'))
        outline = types.SimpleNamespace(clear=clear)
        liquid = types.SimpleNamespace(close=lambda: calls.append('liquid') or True)
        with contextlib.redirect_stderr(io.StringIO()):
            errors = bridge.release_projection_resources(outlines=(outline,), liquids=(liquid,))
            self.assertEqual(['原生边框回收失败'], errors)
            self.assertEqual(['outline', 'liquid'], calls)
            self.assertEqual([outline], bridge.projection_retired_outlines)
            self.assertEqual([], bridge.projection_retired_liquids)
            fail[0] = False
            self.assertEqual([], bridge.release_projection_resources())
        self.assertEqual(['outline', 'liquid', 'outline'], calls)
        self.assertEqual([], bridge.projection_retired_outlines)


if __name__ == '__main__':
    unittest.main()
