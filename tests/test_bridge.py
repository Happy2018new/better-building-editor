"""Client actors must outlive one frame before geometry can be attached."""
import sys
import types
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))

for name in ('mod', 'mod.client', 'mod.client.extraClientApi'):
    sys.modules.setdefault(name, types.ModuleType(name))
from projection import bridge as boundary
from projection.session import Session
from projection.model import Document, Editor, AIR
from projection.transfer import Receiver


class Runtime:
    def __init__(self):
        self.timers = []
        self.created = []
        self.destroyed = []
        self.attached = []
        self.success = True
        self.sent = []

    def NotifyToServer(self, event, data):
        self.sent.append(data)

    def CreateClientEntityByTypeStr(self, identifier, pos, rotation):
        entity = 'actor_%d' % len(self.created)
        self.created.append(entity)
        return entity

    def DestroyClientEntity(self, entity):
        self.destroyed.append(entity)

    def CreateGame(self, level):
        return self

    def AddTimer(self, delay, callback):
        self.timers.append(callback)

    def CreateBlockInfo(self, level):
        return self

    def CreateActorRender(self, entity):
        self.attached.append(entity)
        return self

    def AddActorBlockGeometry(self, name):
        return self.success

    def EnableActorBlockGeometryTransparent(self, name, enabled):
        return True

    def SetActorBlockGeometryTransparency(self, name, opacity):
        return True


class ProjectionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.original_api = boundary.clientApi
        boundary.clientApi = types.SimpleNamespace(GetEngineCompFactory=lambda: self.runtime,
            GetLevelId=lambda: 'level', GetLocalPlayerId=lambda: 'player')
        self.bridge = boundary.ClientBridge(self.runtime)
        self.bridge.geometry = lambda *unused: 'model'
        self.bridge.session = Session(self.bridge)
        self.bridge.entity = 'previous_projection'
        self.bridge.session.projection_active = True

    def tearDown(self):
        boundary.clientApi = self.original_api

    def test_model_waits_for_actor_initialization_and_replaces_old_projection(self):
        self.bridge.project()
        self.assertEqual([], self.runtime.attached)
        self.assertEqual([], self.runtime.destroyed)
        self.runtime.timers.pop()()
        self.assertEqual(['actor_0'], self.runtime.attached)
        self.assertEqual(['previous_projection'], self.runtime.destroyed)
        self.assertEqual('actor_0', self.bridge.entity)

    def test_stop_cancels_staged_actor_and_ignores_delayed_callback(self):
        self.bridge.project()
        self.bridge.stop_projection()
        self.runtime.timers.pop()()
        self.assertEqual([], self.runtime.attached)
        self.assertEqual({'actor_0', 'previous_projection'}, set(self.runtime.destroyed))
        self.assertFalse(self.bridge.session.projection_active)

    def test_failed_attachment_retains_previous_projection(self):
        self.runtime.success = False
        self.bridge.project()
        self.runtime.timers.pop()()
        self.assertEqual(['actor_0'], self.runtime.destroyed)
        self.assertEqual('previous_projection', self.bridge.entity)
        self.assertTrue(self.bridge.session.projection_active)

    def test_new_request_discards_stale_preparation(self):
        self.bridge.project()
        self.bridge.project()
        for callback in self.runtime.timers:
            callback()
        self.assertEqual(['actor_1'], self.runtime.attached)
        self.assertEqual('actor_1', self.bridge.entity)

    def test_stream_upload_is_snapshot_and_ack_driven(self):
        b = self.bridge
        b.session.editor = Editor(Document((64, 100, 64), {(0, 0, 0): ('minecraft:stone', 0)}))
        b.request('check', {'origin': (0, 0, 0), 'document': b.session.editor.document})
        b.session.editor.document.blocks[(0, 0, 0)] = AIR
        receiver = Receiver()
        for unused in range(12):
            self.assertEqual(1, len(self.runtime.sent))
            data = self.runtime.sent.pop()
            packet = data['stream']
            receiver.feed(packet)
            if receiver.result is not None:
                break
            b.receive({'request': b.pending, 'done': False, 'uploadAck': packet['seq']})
            self.runtime.timers.pop()()
        self.assertEqual(('minecraft:stone', 0), receiver.result.get((0, 0, 0)))

    def test_capture_replaces_old_orbit_center_and_pending_focus(self):
        b = self.bridge
        s = b.session
        s.camera_pivot = (50., 90., 55.)
        s.camera_pan = (4., -3.)
        s.camera_view(70., 30., 25.)
        s.focused = (50, 90, 55)
        s.locate_selected()
        previous_reset = s.camera_reset_revision
        b.request('capture', {'origin': (10, 20, 30)})
        doc = Document((4, 5, 6), {(2, 3, 4): ('minecraft:stone', 0)})
        b.receive({'request': b.pending, 'done': True, 'document': doc.to_data()})
        self.assertEqual((4, 5, 6), s.editor.document.size)
        self.assertEqual((10, 20, 30), s.origin)
        self.assertIsNone(s.camera_pivot)
        self.assertIsNone(s.camera_focus_request)
        self.assertEqual((0., 0.), s.camera_pan)
        self.assertEqual((35., 25., 1.), s.camera_pose)
        self.assertEqual(previous_reset + 1, s.camera_reset_revision)

    def test_large_projection_snapshot_and_stop_cancel_all_future_actors(self):
        b = self.bridge
        b.player_origin = lambda: (0, 0, 0)
        b.session.editor = Editor(Document((64, 100, 64), {(0, 0, 0): ('minecraft:stone', 0)}))
        observed = []
        b.geometry = lambda doc: observed.append(doc.get((0, 0, 0))) or 'model'
        b.project_large((0, 0, 0))
        b.session.editor.document.blocks[(0, 0, 0)] = AIR
        for unused in range(20):
            self.runtime.timers.pop(0)()
            if self.runtime.created:
                break
        self.assertEqual([('minecraft:stone', 0)], observed)
        b.stop_projection()
        callbacks, self.runtime.timers = self.runtime.timers, []
        for callback in callbacks:
            callback()
        self.assertEqual([], self.runtime.timers)
        self.assertTrue(all(actor in self.runtime.destroyed for actor in self.runtime.created))
