"""Server stream lifecycle and read failures without a running game."""
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack'))
for name in ('mod', 'mod.server', 'mod.server.extraServerApi'):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules['mod.server.extraServerApi'].GetServerSystemCls = lambda: object
from HelloScript import HelloServerSystem as server
from HelloScript.projection.model import Document, AIR
from HelloScript.projection.transfer import packets, Receiver


class ServerStreamTests(unittest.TestCase):
    def setUp(self):
        self.host = object.__new__(server.HelloServerSystem)
        self.host.jobs = {}
        self.host.uploads = {}
        self.host.undo_records = {}
        self.replies = []
        self.host.reply = lambda player, request, **data: self.replies.append((player, request, data))

    def test_upload_cancellation_and_timeout_release_state(self):
        first = next(packets(Document((256, 384, 256))))
        self.host.request({'__id__': 'real_player', 'player': 'forged', 'request': 12, 'action': 'check', 'stream': first})
        self.assertIn('real_player', self.host.uploads)
        self.assertNotIn('forged', self.host.uploads)
        self.assertEqual(0, self.replies[-1][2]['uploadAck'])
        self.host.request({'__id__': 'real_player', 'request': 12, 'action': 'cancel'})
        self.assertEqual({}, self.host.uploads)
        self.assertTrue(self.replies[-1][2]['done'])
        self.host.request({'__id__': 'real_player', 'request': 13, 'action': 'check', 'stream': first})
        entry = self.host.uploads['real_player']
        self.host.uploads['real_player'] = entry[:3] + (0.,)
        self.host.tick()
        self.assertEqual({}, self.host.uploads)
        self.assertIn('超时', self.replies[-1][2]['error'])

    def test_bad_packet_releases_upload_and_anonymous_requests_ignored(self):
        self.host.request({'request': 1, 'action': 'check', 'stream': {}})
        self.assertEqual([], self.replies)
        self.host.request({'__id__': 'player', 'request': 1, 'action': 'check', 'stream': {}})
        self.assertEqual({}, self.host.uploads)
        self.assertTrue(self.replies[-1][2]['done'])

    def test_capture_yields_packets_then_publishes_one_complete_document(self):
        stone = ('minecraft:stone', 0)
        adapter = types.SimpleNamespace(read=lambda p: stone if p == (0, 0, 0) else AIR)
        doc = Document((17, 16, 16))
        for unused in self.host.read_job('player', 7, 'capture', adapter, doc, (0, 0, 0)):
            pass
        receiver = Receiver()
        for unused_player, unused_request, data in self.replies:
            if 'documentPacket' in data:
                receiver.feed(data['documentPacket'])
        self.assertTrue(self.replies[-1][2]['streamed'])
        self.assertEqual(stone, receiver.result.get((0, 0, 0)))
        self.assertEqual(1, len(receiver.result.blocks))

    def test_read_exception_finishes_job_with_error(self):
        def broken():
            raise ValueError('test read error')
            yield None
        self.host.jobs['player'] = (8, 'capture', broken(), None, 0)
        self.host.tick()
        self.assertEqual({}, self.host.jobs)
        self.assertEqual('test read error', self.replies[-1][2]['error'])


if __name__ == '__main__':
    unittest.main()
