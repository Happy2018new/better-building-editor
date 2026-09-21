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
        self.uniforms = {}
        self.actor_positions = {}
        self.world = {}

    def NotifyToServer(self, event, data):
        self.sent.append(data)

    def CreateClientEntityByTypeStr(self, identifier, pos, rotation):
        entity = 'actor_%d' % len(self.created)
        self.created.append(entity)
        self.actor_positions[entity] = (identifier, pos)
        return entity

    def DestroyClientEntity(self, entity):
        self.destroyed.append(entity)

    def CreateGame(self, level):
        return self

    def AddTimer(self, delay, callback):
        self.timers.append(callback)

    def CreateBlockInfo(self, level):
        return self

    def GetBlock(self, pos):
        return self.world.get(pos, AIR)

    def CreateActorRender(self, entity):
        self.rendering = entity
        return self

    def AddActorBlockGeometry(self, name, offset=(0, 0, 0), rotation=(0, 0, 0)):
        self.attached.append(self.rendering)
        self.geometry_transform = (offset, rotation)
        return self.success

    def SetEntityExtraUniforms(self, index, values):
        self.uniforms[self.rendering] = values
        return True

    def SetConfigData(self, key, value, global_config):
        self.preferences = value
        return True

    def CreateConfigClient(self, level):
        return self

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
        self.assertEqual(((-.5, 0., -.5), (0., 180., 0.)), self.runtime.geometry_transform)

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
            if observed:
                break
        self.assertEqual([('minecraft:stone', 0)], observed)
        b.stop_projection()
        callbacks, self.runtime.timers = self.runtime.timers, []
        for callback in callbacks:
            callback()
        self.assertEqual([], self.runtime.timers)
        self.assertTrue(all(actor in self.runtime.destroyed for actor in self.runtime.created))

    def test_outline_toggle_keeps_projected_snapshot_and_never_rebuilds_blocks(self):
        b, s = self.bridge, self.bridge.session
        s.origin = (-30, 64, 5)
        b.project()
        # Pending settings changes must not move/resize the committed projection.
        s.origin = (100, 80, 100)
        s.editor = Editor(Document((64, 128, 64)))
        self.runtime.timers.pop(0)()
        outline = b.projection_outline
        self.assertEqual(((-30, 64, 5), (24, 16, 24)), outline.bounds)
        self.assertEqual((-18., 72., 17.), self.runtime.actor_positions[outline.entity][1])
        self.assertEqual((24., 16., 24., .5), self.runtime.uniforms[outline.entity])
        b.geometry = lambda *args: self.fail('Outline changes must not build geometry')
        s.set('projection_outline', False)
        self.assertIsNone(outline.entity)
        self.assertTrue(s.projection_active)
        self.assertFalse(self.runtime.preferences['projection_outline'])
        s.set('projection_outline', True)
        self.assertEqual((-18., 72., 17.), self.runtime.actor_positions[outline.entity][1])
        self.assertEqual(['actor_0'], self.runtime.attached)
        s.set('reduced_motion', True)
        self.assertEqual(0., self.runtime.uniforms[outline.entity][3])
        b.stop_projection()
        self.assertIsNone(outline.bounds)
        for callback in self.runtime.timers:
            callback()
        self.assertTrue(all(actor in self.runtime.destroyed for actor in self.runtime.created))

    def test_failed_replacement_preserves_old_outline_until_projection_succeeds(self):
        b = self.bridge
        b.project()
        self.runtime.timers.pop(0)()
        previous = b.projection_outline.entity
        previous_bounds = b.projection_outline.bounds
        self.runtime.success = False
        b.session.origin = (150, 80, 5)
        b.project()
        for callback in list(self.runtime.timers):
            callback()
        self.assertEqual(previous, b.projection_outline.entity)
        self.assertEqual(previous_bounds, b.projection_outline.bounds)
        self.assertNotIn(previous, self.runtime.destroyed)

    def test_maximum_projection_has_one_full_outline_and_clears_on_dimension_change(self):
        b, s = self.bridge, self.bridge.session
        s.editor = Editor(Document((64, 128, 64), {(0, 0, 0): ('minecraft:stone', 0)}))
        b.player_origin = lambda: (10, 50, -40)
        b.project_large((10, 50, -40))
        outline = b.projection_outline
        self.assertEqual((42., 114., -8.), self.runtime.actor_positions[outline.entity][1])
        self.assertEqual((64., 128., 64., .5), self.runtime.uniforms[outline.entity])
        b.dimension_changed(None)
        for callback in self.runtime.timers:
            callback()
        self.assertIsNone(outline.entity)
        self.assertIsNone(outline.bounds)
        self.assertEqual(1, len(self.runtime.created))

    def test_filter_toggle_resolves_legacy_palette_then_immediately_rebuilds(self):
        b,s=self.bridge,self.bridge.session
        old=('minecraft:planks',0)
        s.origin=(0,0,0)
        s.editor=Editor(Document((3,1,1),dict(((x,0,0),old) for x in range(3))))
        self.runtime.world={(0,0,0):('minecraft:oak_planks',0),(1,0,0):('minecraft:stone',0)}
        observed=[]
        def geometry(doc,visible=None):
            observed.append([p for p in doc.blocks if visible is None or visible(p)])
            return 'model' if observed[-1] else None
        b.geometry=geometry
        b.toggle_missing()
        self.assertTrue(s.projection_missing)
        self.assertEqual('resolve',self.runtime.sent[-1]['action'])
        b.receive({'request':b.pending,'done':True,'palette':[['minecraft:oak_planks',0]]})
        self.assertEqual([[(1,0,0),(2,0,0)]],observed)
        self.runtime.timers.pop(0)()
        b.toggle_missing()
        self.assertEqual([(0,0,0),(1,0,0),(2,0,0)],observed[-1])
        self.assertFalse(s.projection_missing)

    def test_completed_projection_retains_bounds_and_can_restore_all_blocks(self):
        b,s=self.bridge,self.bridge.session
        value=('minecraft:stone',0)
        s.origin=(0,0,0);s.editor=Editor(Document((1,1,1),{(0,0,0):value}))
        b.projection_palette[value]=value
        self.runtime.world[(0,0,0)]=value
        b.geometry=lambda doc,visible=None: 'model' if visible is None or visible((0,0,0)) else None
        b.toggle_missing()
        self.assertIsNone(b.entity)
        self.assertTrue(s.projection_active)
        self.assertEqual(((0,0,0),(1,1,1)),b.projection_outline.bounds)
        b.toggle_missing()
        for callback in list(self.runtime.timers): callback()
        self.assertIsNotNone(b.entity)

    def test_stopping_while_palette_is_in_flight_cannot_resurrect_projection(self):
        b=self.bridge
        b.session.projection_missing=True
        b.project();request=b.pending
        b.stop_projection()
        b.receive({'request':request,'done':True,'palette':b.pending_data[1]['palette']})
        self.assertFalse(b.session.projection_active)
        self.assertIsNone(b.preparing_entity)

    def test_unloaded_cell_is_not_misclassified_as_completed(self):
        self.runtime.world[(0,0,0)]=None
        with self.assertRaises(ValueError):
            self.bridge.needs_projection(self.runtime,(0,0,0),('minecraft:stone',0))
