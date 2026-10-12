"""Selection and NBT transfer state transitions without a Minecraft instance."""
import copy
import json
import types
import unittest
import sys
from unittest.mock import patch

import test_bridge as client_fixture
import test_server_stream as server_fixture


def overdeep_packet(sequence):
    row = 'invalid'
    for unused in range(sys.getrecursionlimit() + 1):
        row = [row]
    return {'seq': sequence, 'kind': 'palette', 'rows': [row]}


class SelectionServerProtocolTests(unittest.TestCase):
    setUp = server_fixture.ServerStreamTests.setUp
    read_entity = server_fixture.ServerStreamTests.read_entity
    read_palette = server_fixture.ServerStreamTests.read_palette
    write = server_fixture.ServerStreamTests.write
    write_palette = server_fixture.ServerStreamTests.write_palette
    set_actor = server_fixture.ServerStreamTests.set_actor
    set_liquid = server_fixture.ServerStreamTests.set_liquid
    finish = server_fixture.ServerStreamTests.finish

    def test_capture_upload_authorizes_and_locks_at_begin_only(self):
        doc = server_fixture.Document((1, 1, 1))
        stream = list(server_fixture.packets(doc))
        region = (0, (0, 64, 0), doc.size)
        self.host.world_regions['player'] = region
        self.creative = False
        self.abilities = dict(op=False, build=False, mine=False)
        initial = {'__id__': 'player', 'request': 81, 'action': 'capture',
                   'clientCapture': True, 'origin': region[1], 'size': region[2],
                   'stream': stream[0]}
        sent = []
        self.host.NotifyToClient = lambda player, event, payload: sent.append(payload)
        with patch.object(self.host, 'validate_target', wraps=self.host.validate_target) as validate:
            self.host.request(initial)
            self.assertTrue(self.host.selection_locked('player'))
            self.host.world_tool_request({'__id__': 'player', 'action': 'reset'})
            click = {'entityId': 'player', 'itemDict': {'newItemName': 'modern_projection:survey_wand'},
                     'dimensionId': 0, 'x': 3, 'y': 64, 'z': 0, 'face': 4}
            self.host.tool_use_on(click)
            self.assertEqual([{'success': False, 'silent': True, 'createBounds': False}] * 2, sent)
            self.assertFalse(click.get('ret', False))
            self.assertEqual(region, self.host.world_regions['player'])
            self.factory.CreatePos = lambda player: types.SimpleNamespace(GetFootPos=lambda: (2000, 64, 0))
            for packet in stream[1:]:
                self.host.request({'__id__': 'player', 'request': 81, 'action': 'upload', 'stream': packet})
            self.assertTrue(self.host.selection_locked('player'))
            self.finish()
            self.assertEqual(1, validate.call_count)
        self.assertTrue(self.replies[-1][2]['clientCapture'])
        self.assertEqual(0, self.allowed_checks)
        self.assertFalse(self.host.selection_locked('player'))
        self.assertEqual([], self.writes)
        self.assertEqual([], self.actor_writes)

    def test_unregistered_capture_upload_is_rejected_before_allocating_receiver(self):
        stream = list(server_fixture.packets(server_fixture.Document((1, 1, 1))))
        self.host.request({'__id__': 'player', 'request': 82, 'action': 'capture',
                           'clientCapture': True, 'origin': (0, 64, 0), 'size': (1, 1, 1),
                           'stream': stream[0]})
        self.assertFalse(self.host.uploads)
        self.assertFalse(self.host.jobs)
        self.assertIn('error', self.replies[-1][2])
        self.assertEqual([], self.palette_reads)
        self.assertEqual([], self.entity_reads)
        self.assertEqual([], self.writes)

    def test_duplicate_upload_packets_preserve_state_and_start_one_job(self):
        doc = server_fixture.Document((1, 1, 1), {(0, 0, 0): ('minecraft:stone', 0)})
        stream = list(server_fixture.packets(doc))
        initial = {'__id__': 'player', 'request': 83, 'action': 'check',
                   'origin': (0, 64, 0), 'stream': stream[0]}
        self.host.request(initial)
        receiver = self.host.uploads['player'][2]
        self.host.request(initial)
        self.assertIs(receiver, self.host.uploads['player'][2])
        self.assertEqual(1, receiver.sequence)
        for packet in stream[1:-1]:
            args = {'__id__': 'player', 'request': 83, 'action': 'upload', 'stream': packet}
            self.host.request(args)
            sequence = receiver.sequence
            self.host.request(args)
            self.assertEqual(sequence, receiver.sequence)
        end = {'__id__': 'player', 'request': 83, 'action': 'upload', 'stream': stream[-1]}
        self.host.request(end)
        job = self.host.jobs['player'][2]
        self.host.request(end)
        self.assertIs(job, self.host.jobs['player'][2])
        self.assertFalse(any(data.get('done') for player, request, data in self.replies))
        self.finish()
        self.assertEqual([], self.writes)

    def test_duplicate_capture_request_preserves_active_job_and_download(self):
        args = {'__id__': 'player', 'request': 84, 'action': 'capture',
                'clientCapture': True, 'origin': (0, 64, 0), 'size': (1, 1, 1)}
        self.host.world_regions['player'] = (0, args['origin'], args['size'])
        self.host.request(args)
        job = self.host.jobs['player'][2]
        self.host.request(args)
        self.assertIs(job, self.host.jobs['player'][2])
        self.assertEqual([], self.replies)
        self.finish()
        self.assertEqual(1, sum(bool(data.get('done')) for player, request, data in self.replies))
        self.assertEqual([], self.writes)

    def test_disconnect_releases_capture_and_upload_without_world_mutation(self):
        self.host.world_regions['player'] = (0, (0, 64, 0), (1, 1, 1))
        self.host.request({'__id__': 'player', 'request': 85, 'action': 'capture',
                           'clientCapture': True, 'origin': (0, 64, 0), 'size': (1, 1, 1)})
        self.host.tick()
        self.host.tick()
        self.host.request({'__id__': 'real_player', 'request': 86, 'action': 'check',
                           'origin': (0, 64, 0),
                           'stream': next(server_fixture.packets(server_fixture.Document((1, 1, 1))))})
        self.host.leave({'id': 'player'})
        self.host.leave({'id': 'real_player'})
        self.assertFalse(self.host.jobs)
        self.assertFalse(self.host.uploads)
        self.assertFalse(self.host.world_regions)
        self.assertFalse(self.host.selection_locked('player'))
        self.assertEqual([], self.writes)
        self.assertEqual([], self.actor_writes)

    def test_overdeep_upload_releases_state_without_world_mutation(self):
        self.host.request({'__id__': 'player', 'request': 87, 'action': 'check',
                           'origin': (0, 64, 0),
                           'stream': next(server_fixture.packets(server_fixture.Document((1, 1, 1))))})
        self.host.request({'__id__': 'player', 'request': 87, 'action': 'upload',
                           'stream': overdeep_packet(1)})
        self.assertFalse(self.host.uploads)
        self.assertFalse(self.host.jobs)
        self.assertTrue(self.replies[-1][2]['done'])
        self.assertIn('error', self.replies[-1][2])
        self.assertEqual([], self.writes)
        self.assertEqual([], self.actor_writes)


class SelectionClientProtocolTests(unittest.TestCase):
    setUp = client_fixture.ProjectionLifecycleTests.setUp
    tearDown = client_fixture.ProjectionLifecycleTests.tearDown

    def test_duplicate_upload_acks_advance_one_packet_until_next_ack(self):
        b = self.bridge
        b.request('check', {'origin': (0, 64, 0), 'document': b.session.editor.document})
        request = b.pending
        ack = {'request': request, 'done': False, 'uploadAck': 0}
        b.receive(ack)
        b.receive(ack)
        timers, self.runtime.timers = self.runtime.timers, []
        for timer in timers:
            timer()
        self.assertEqual([0, 1], [item['stream']['seq'] for item in self.runtime.sent])
        b.receive(ack)
        b.receive({'request': request, 'done': False, 'uploadAck': True})
        self.assertFalse(self.runtime.timers)
        self.assertEqual(1, b.upload_sequence)
        b.receive({'request': request, 'done': False, 'uploadAck': 1})
        self.runtime.timers.pop()()
        self.assertEqual(2, b.upload_sequence)

    def test_duplicate_download_packets_are_acked_without_cancel_or_partial_publish(self):
        b = self.bridge
        local = client_fixture.Document((1, 1, 1), {(0, 0, 0): ('minecraft:stone', 0)})
        b.request('capture', {'origin': (0, 64, 0), 'size': local.size,
                              'clientCapture': True, 'captureDocument': local})
        old_editor = b.session.editor
        request = b.pending
        for packet in client_fixture.boundary.packets(client_fixture.Document(local.size)):
            reply = {'request': request, 'done': False, 'documentPacket': packet}
            b.receive(reply)
            expected = b.download.sequence
            b.receive(copy.deepcopy(reply))
            self.assertEqual(expected, b.download.sequence)
            self.assertEqual(request, b.pending)
            self.assertIs(old_editor, b.session.editor)
            self.assertEqual('captureAck', self.runtime.sent[-1]['action'])
            self.assertEqual(packet['seq'], self.runtime.sent[-1]['sequence'])
        b.receive({'request': request, 'done': True, 'streamed': True, 'clientCapture': True})
        self.assertIs(local, b.session.editor.document)
        self.assertIsNone(b.download)
        self.assertFalse(b.session.busy)
        self.assertFalse(any(item.get('action') == 'cancel' for item in self.runtime.sent))

    def test_stale_or_idle_responses_do_not_change_client_state(self):
        b = self.bridge
        original = b.session.editor
        for reply in ({}, None, {'request': 1, 'done': True}, {'request': None, 'done': True}):
            b.receive(reply)
        b.request('capture', {'origin': (0, 64, 0)})
        request = b.pending
        for reply in ({'request': request + 1, 'done': True}, {'request': True, 'done': True}, None):
            b.receive(reply)
        self.assertEqual(request, b.pending)
        self.assertIs(original, b.session.editor)
        self.assertTrue(b.session.busy)

    def test_failed_upload_preparation_does_not_leave_pending_or_busy_state(self):
        b = self.bridge
        with patch.object(client_fixture.boundary, 'packets', side_effect=ValueError('invalid upload')):
            with self.assertRaises(ValueError):
                b.request('check', {'origin': (0, 64, 0), 'document': b.session.editor.document})
        self.assertIsNone(b.pending)
        self.assertIsNone(b.pending_data)
        self.assertIsNone(b.upload)
        self.assertFalse(b.session.busy)
        self.assertEqual([], self.runtime.sent)

    def test_completed_capture_discards_download_after_draft_changes(self):
        b = self.bridge
        b.request('capture', {'origin': (0, 64, 0)})
        request = b.pending
        for packet in client_fixture.boundary.packets(client_fixture.Document((1, 1, 1))):
            b.receive({'request': request, 'done': False, 'documentPacket': packet})
        current = b.session.editor
        current.revision += 1
        b.receive({'request': request, 'done': True, 'streamed': True})
        self.assertIs(current, b.session.editor)
        self.assertIsNone(b.pending)
        self.assertIsNone(b.download)
        self.assertFalse(b.session.busy)

    def test_bad_download_packet_cancels_and_releases_state_without_editor_changes(self):
        b = self.bridge
        b.request('capture', {'origin': (0, 64, 0)})
        old_editor = b.session.editor
        b.receive({'request': b.pending, 'done': False, 'documentPacket': {'seq': 9, 'kind': 'end'}})
        self.assertEqual('cancel', self.runtime.sent[-1]['action'])
        self.assertIs(old_editor, b.session.editor)
        self.assertIsNone(b.pending)
        self.assertIsNone(b.download)
        self.assertFalse(b.session.busy)

    def test_overdeep_download_cancels_without_partial_editor_changes(self):
        b = self.bridge
        b.request('capture', {'origin': (0, 64, 0)})
        old_editor = b.session.editor
        b.receive({'request': b.pending, 'done': False, 'documentPacket': overdeep_packet(0)})
        self.assertEqual('cancel', self.runtime.sent[-1]['action'])
        self.assertIs(old_editor, b.session.editor)
        self.assertIsNone(b.pending)
        self.assertIsNone(b.download)
        self.assertFalse(b.session.busy)


class SelectionPacketBoundsTests(unittest.TestCase):
    def test_oversized_direct_palette_is_rejected_before_publishing_cells(self):
        from projection.cell import make_cell
        from projection.transfer import Receiver, packets
        doc = client_fixture.Document((1, 1, 1), {(0, 0, 0): make_cell(
            ('minecraft:chest', 0), nbt={'text': 'x' * 24000})})
        stream = list(packets(doc))
        receiver = Receiver()
        receiver.feed(stream[0])
        receiver.feed(stream[1])
        receiver.feed(stream[2])
        parts = [packet['text'] for packet in stream if packet['kind'] == 'palette_part']
        row = json.loads(''.join(parts))
        with self.assertRaises(ValueError):
            receiver.feed({'seq': receiver.sequence, 'kind': 'palette', 'rows': [row]})
        self.assertIsNone(receiver.result)
        self.assertFalse(receiver.document.blocks)

    def test_fragmented_nbt_with_same_payload_round_trips_within_packet_bounds(self):
        from projection.cell import make_cell
        from projection.transfer import Receiver, packets
        doc = client_fixture.Document((1, 1, 1), {(0, 0, 0): make_cell(
            ('minecraft:chest', 0), nbt={'text': 'x' * 24000})})
        receiver = Receiver()
        for packet in packets(doc):
            receiver.feed(packet)
        self.assertEqual(doc.blocks, receiver.result.blocks)

    def test_oversized_material_packet_is_rejected_before_decoding(self):
        from projection.transfer import Receiver, packets
        stream = list(packets(client_fixture.Document((1, 1, 1))))
        receiver = Receiver()
        receiver.feed(stream[0])
        oversized = ['example:block', {'key': 'x' * 12000}]
        with patch('projection.transfer.semantic_wire.decode_material') as decode:
            with self.assertRaises(ValueError):
                receiver.feed({'seq': 1, 'kind': 'materials', 'rows': [oversized]})
        decode.assert_not_called()
        self.assertEqual([], receiver.materials)
        self.assertIsNone(receiver.result)


if __name__ == '__main__':
    unittest.main()
