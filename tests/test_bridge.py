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


class Runtime:
    def __init__(self):
        self.timers = []
        self.created = []
        self.destroyed = []
        self.attached = []
        self.success = True

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
