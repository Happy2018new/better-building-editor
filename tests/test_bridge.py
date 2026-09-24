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
        self.render_distance = 72.
        self.shadows = {}
        self.uniform_slots = {}
        self.camera_pos = (0., 64., 0.)
        self.camera_forward = (0., 0., 1.)
        self.moves = []
        self.offsets = {}

    def CreateCamera(self, level):
        return self

    def GetPosition(self):
        return self.camera_pos

    def GetForward(self):
        return self.camera_forward

    def CreatePos(self, entity):
        self.moving = entity
        return self

    def SetPosForClientEntity(self, position):
        self.moves.append((self.moving, position))
        identity, unused = self.actor_positions[self.moving]
        self.actor_positions[self.moving] = (identity, position)
        return True

    def SetActorBlockGeometryOffset(self, name, offset):
        self.offsets[self.rendering] = offset
        return True

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

    def CreateModel(self, entity):
        self.shadow_entity = entity
        return self

    def SetEntityShadowShow(self, value):
        self.shadows[self.shadow_entity] = value

    def GetEntityRenderDistance(self):
        return self.render_distance

    def SetEntityRenderDistance(self, value):
        self.render_distance = value
        return True

    def AddActorBlockGeometry(self, name, offset=(0, 0, 0), rotation=(0, 0, 0)):
        self.attached.append(self.rendering)
        self.geometry_transform = (offset, rotation)
        return self.success

    def SetEntityExtraUniforms(self, index, values):
        self.uniforms[self.rendering] = values
        self.uniform_slots[self.rendering, index] = values
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
    def test_outline_styles_keep_committed_building_and_independent_preferences(self):
        b, r, s = self.bridge, self.runtime, self.bridge.session
        self.assertEqual('rainbow', s.outline_style)
        b.project()
        r.timers.pop(0)()
        building, bounds = b.entity, b.projection_outline.bounds
        b.geometry = lambda *a, **k: self.fail('Style change must not rebuild building')
        s.origin = (100,100,100)
        for style in ('golden', 'starry', 'rainbow', 'golden'):
            old = b.projection_outline.entity
            s.set('outline_style', style)
            b.follow_projection()
            self.assertIn(old, r.destroyed)
            self.assertEqual(building, b.entity)
            self.assertEqual(bounds, b.projection_outline.bounds)
            self.assertEqual([building], r.attached)
        ids = [item['id'] for item in b.projection_outline.effects.layers]
        s.outline_parameter('golden', 'speed', 4.)
        s.outline_parameter('golden', 'brightness', .8)
        self.assertEqual(ids, [item['id'] for item in b.projection_outline.effects.layers])
        for entity in ids:
            self.assertGreater(r.uniform_slots[entity,1][3], 1.5)
            self.assertEqual((.8,.1,1.), r.uniform_slots[entity,3][1:])
        self.assertEqual(3., s.outline_options['rainbow']['speed'])
        self.assertEqual(1., s.outline_options['starry']['speed'])
        while r.timers:
            r.timers.pop(0)()
        self.assertEqual(4., r.preferences['outline_options']['golden']['speed'])
        s.set('projection_outline', False)
        self.assertEqual(building, b.entity)
        self.assertTrue(all(entity in r.destroyed for entity in ids))
        self.assertFalse(b.projection_outline.effects.active())
        s.set('projection_outline', True)
        b.stop_projection()
        self.assertIsNone(b.projection_outline.bounds)
        self.assertFalse(b.projection_outline.effects.active())

    def test_biome_updates_live_and_pending_ghost_without_rebuilding(self):
        from projection.biomes import actor_uniform
        b, r = self.bridge, self.runtime
        b.project()
        r.timers.pop(0)()
        entity = b.entity
        b.geometry = lambda *args, **kwargs: self.fail('tint must not rebuild geometry')
        b.session.set_biome('desert')
        self.assertEqual(entity, b.entity)
        self.assertEqual(actor_uniform('desert'), r.uniform_slots[entity, 4])
        b.geometry = lambda *args, **kwargs: 'pending_biome_model'
        b.project_large((0, 64, 0))
        b.session.set_biome('jungle')
        for unused in range(200):
            if not r.timers:
                break
            r.timers.pop(0)()
        self.assertTrue(b.projection_work.ready)
        self.assertEqual('jungle', b.projection_work.document.biome)
        self.assertEqual(actor_uniform('jungle'), r.uniform_slots[b.entity, 4])

    def test_camera_anchor_retries_transient_native_failure_without_camera_motion(self):
        b, r = self.bridge, self.runtime
        b.session.origin = (0,64,0)
        b.project()
        r.timers.pop(0)()
        setter = r.SetActorBlockGeometryOffset
        r.SetActorBlockGeometryOffset = lambda *a: False
        b.follow_projection()
        self.assertIsNone(b._projection_follow_position)
        r.SetActorBlockGeometryOffset = setter
        b.follow_projection()
        self.assertIsNotNone(b._projection_follow_position)
        self.assertEqual((0.,64.,4.), b.projection_mesh[3])

    def test_camera_anchor_preserves_world_coordinates_without_rebuilding(self):
        b, r = self.bridge, self.runtime
        b.session.origin = (-30, 64, 5)
        b.project()
        r.timers.pop(0)()
        mesh, outline = b.entity, b.projection_outline.entity
        b.geometry = lambda *a: self.fail('camera movement must not rebuild geometry')
        for position, forward in [((0., 66., 0.), (0., 0., 1.)),
                                  ((-30., 65., 5.), (0., -1., 0.)),
                                  ((-18., 72., 17.), (1., 0., 0.))]:
            r.camera_pos, r.camera_forward = position, forward
            b.follow_projection()
            anchor = tuple(position[i]+forward[i]*4. for i in range(3))
            self.assertEqual(anchor, r.actor_positions[mesh][1])
            ox, oy, oz = r.offsets[mesh]
            self.assertEqual((-30., 64., 5.), (anchor[0]-ox-.5, anchor[1]+oy, anchor[2]-oz-.5))
            correction = r.uniform_slots[outline, 2]
            self.assertEqual((-18., 72., 17.), tuple(anchor[i]+correction[i] for i in range(3)))
            calls = len(r.moves)
            b.follow_projection()
            self.assertEqual(calls, len(r.moves), 'stationary frames submit no transforms')
        self.assertEqual([mesh], r.attached)
        b.stop_projection()
        self.assertIsNone(b.projection_mesh)
        calls = len(r.moves)
        b.follow_projection()
        self.assertEqual(calls, len(r.moves))

    def test_pending_replacement_and_outline_toggle_follow_committed_snapshot(self):
        b, r = self.bridge, self.runtime
        b.session.origin = (-30, 64, 5)
        b.project()
        r.timers.pop(0)()
        mesh = b.entity
        b.follow_projection()
        b.session.set('projection_outline', False)
        b.session.set('projection_outline', True)
        b.follow_projection()
        self.assertEqual((0., 64., 4.), r.actor_positions[b.projection_outline.entity][1])
        b.session.editor = Editor(Document((64,128,64), {(0,0,0):('minecraft:stone',0)}))
        b.project_large((100,100,100))
        r.camera_pos = (10., 70., 20.)
        b.follow_projection()
        self.assertEqual(mesh, b.entity)
        self.assertEqual((-30,64,5), b.projection_mesh[2])
        self.assertEqual((40.-.5, -6., 19.-.5), r.offsets[mesh])

    def test_default_render_distance_is_leased_and_restored(self):
        self.runtime.render_distance=-1.
        self.bridge.ensure_projection_distance((64,128,64))
        self.assertEqual(256.,self.runtime.render_distance)
        self.bridge.restore_projection_distance()
        self.assertEqual(-1.,self.runtime.render_distance)

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

    def test_frame_watchdog_and_failed_callback_preserve_other_jobs(self):
        import contextlib
        import io
        observed = []
        self.bridge.attach_frame_pump()
        def broken():
            raise RuntimeError('injected frame callback failure')
        self.bridge.next_frame(broken)
        self.bridge.next_frame(lambda: observed.append('continued'))
        self.assertEqual(1, len(self.runtime.timers))
        with contextlib.redirect_stderr(io.StringIO()) as log:
            self.runtime.timers.pop()()
        self.assertEqual(['continued'], observed)
        self.assertIn('injected frame callback failure', log.getvalue())
        self.assertFalse(self.bridge.frame_work)

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
        b.geometry = lambda doc: observed.extend(doc.palette_data()['common']) or 'model'
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
        self.assertEqual((24., 16., 24., .5), self.runtime.uniform_slots[outline.entity, 1])
        self.assertIs(self.runtime.shadows[outline.entity],False)
        self.assertIs(self.runtime.shadows[b.entity],False)
        b.geometry = lambda *args: self.fail('Outline changes must not build geometry')
        s.set('projection_outline', False)
        self.assertIsNone(outline.entity)
        self.assertTrue(s.projection_active)
        self.assertFalse(self.runtime.preferences['projection_outline'])
        s.set('projection_outline', True)
        self.assertEqual((-18., 72., 17.), self.runtime.actor_positions[outline.entity][1])
        self.assertEqual(['actor_0'], self.runtime.attached)
        s.set('reduced_motion', True)
        self.assertEqual(0., self.runtime.uniform_slots[outline.entity, 1][3])
        b.stop_projection()
        self.assertIsNone(outline.bounds)
        for callback in self.runtime.timers:
            callback()
        self.assertTrue(all(actor in self.runtime.destroyed for actor in self.runtime.created))

    def test_all_128_world_tiles_submit_one_complete_model_and_finish_idle(self):
        b = self.bridge
        keys = [(x,y,z) for x in range(4) for y in range(8) for z in range(4)]
        values = dict((tuple(v*16 for v in k), ('minecraft:planks',k[1]%6)) for k in keys)
        b.session.editor = Editor(Document((64,128,64),values))
        b.player_origin = lambda: (0,0,0)
        palettes = []
        b.geometry = lambda doc: palettes.append(doc.palette_data()) or 'model'
        b.project_large((0,0,0))
        b.player_origin = lambda: (1000,1000,1000)
        for unused in range(1000):
            if not self.runtime.timers:
                break
            self.runtime.timers.pop(0)()
        self.assertFalse(b.projection_entities)
        self.assertEqual(set(keys),b.projection_work.completed)
        self.assertTrue(b.projection_work.ready)
        self.assertEqual(1,len(palettes))
        self.assertEqual((64,64,128),palettes[0]['volume'])
        self.assertEqual(128,sum(len(v) for v in palettes[0]['common'].values()))
        self.assertFalse(self.runtime.timers)
        self.assertEqual(256.,self.runtime.render_distance)
        self.assertEqual((19487., 1., 0., 0.), self.runtime.uniforms[b.entity])
        b.stop_projection()
        self.assertEqual(72.,self.runtime.render_distance)
        self.assertTrue(all(a in self.runtime.destroyed for a in self.runtime.created))

    def test_full_projection_respects_layer_filters_and_partial_tile_coordinates(self):
        b = self.bridge
        b.player_origin = lambda: (0,0,0)
        b.session.editor = Editor(Document((33,40,35), {
            (32,39,34):('minecraft:planks',3), (16,0,16):('minecraft:stone',0)}))
        b.session.editor.hidden_layers.add(0)
        palettes = []
        b.geometry = lambda doc: palettes.append(doc.palette_data()) or ('model' if doc.count else None)
        b.project_large((10,20,30))
        for unused in range(80):
            if not self.runtime.timers: break
            self.runtime.timers.pop(0)()
        self.assertFalse(b.projection_entities)
        self.assertTrue(b.projection_work.ready)
        last = next(p for p in palettes if p['common'])
        self.assertEqual((35,33,40),last['volume'])
        self.assertEqual({('minecraft:planks',3):[39*33*35+32*35+34]},last['common'])
        entity = b.entity
        self.assertEqual((26.5,40.,47.5),self.runtime.actor_positions[entity][1])
        offset, rotation = self.runtime.geometry_transform
        self.assertEqual((0.,180.,0.), rotation)
        # Rotation is applied after offset: X/Z reverse, Y is unchanged.
        anchor = self.runtime.actor_positions[entity][1]
        self.assertEqual((10.,20.,30.),
                         (anchor[0]-offset[0]-.5,anchor[1]+offset[1],anchor[2]-offset[2]-.5))

    def test_failed_full_attachment_retains_old_model_and_allows_explicit_retry(self):
        b = self.bridge
        b.player_origin = lambda: (0,0,0)
        b.session.editor = Editor(Document((64,128,64),{(63,127,63):('minecraft:stone',0)}))
        built = []
        b.geometry = lambda doc: built.append(True) or 'model'
        self.runtime.success = False
        b.project_large((0,0,0))
        for unused in range(40):
            if not self.runtime.timers: break
            self.runtime.timers.pop(0)()
            if b.projection_work.error: break
        self.assertFalse(b.projection_entities)
        self.assertFalse(b.projection_work.ready)
        self.assertEqual('previous_projection',b.entity)
        self.assertIsNone(b.preparing_entity)
        self.runtime.success = True
        b.project_large((0,0,0))
        for unused in range(80):
            if not self.runtime.timers: break
            self.runtime.timers.pop(0)()
        self.assertEqual({(3,7,3)},b.projection_work.completed)
        self.assertTrue(b.projection_work.ready)
        self.runtime.render_distance = 400. # Another mod/user changed the setting.
        b.stop_projection()
        self.assertEqual(400.,self.runtime.render_distance)

    def test_native_mesh_failure_stops_and_preserves_old_model_until_explicit_retry(self):
        b = self.bridge
        b.player_origin = lambda: (0,0,0)
        b.session.editor = Editor(Document((64,128,64),{(63,127,63):('minecraft:stone',0)}))
        b.geometry = lambda doc: None
        b.project_large((0,0,0))
        for unused in range(40):
            if not self.runtime.timers: break
            self.runtime.timers.pop(0)()
            if b.projection_work.error: break
        self.assertFalse(b.projection_work.ready)
        self.assertIsNone(b.projection_work.model)
        self.assertEqual('previous_projection', b.entity)
        self.assertFalse(self.runtime.timers)
        b.geometry = lambda doc: 'recovered'
        b.project_large((0,0,0))
        for unused in range(80):
            if not self.runtime.timers: break
            self.runtime.timers.pop(0)()
        self.assertEqual({(3,7,3)},b.projection_work.completed)
        self.assertTrue(b.projection_work.ready)

    def test_plank_species_use_explicit_states_without_mutating_source_or_losing_aliases(self):
        from projection.large_preview import SurfacePalette
        PLANK_SPECIES = ('oak','spruce','birch','jungle','acacia','dark_oak')
        b = self.bridge
        del b.geometry
        palette = SurfacePalette((9,1,1))
        for i in range(6): palette.add((i,0,0),('minecraft:planks',i))
        palette.add((6,0,0),('minecraft:spruce_planks',0))
        palette.add((7,0,0),('minecraft:stone',2))
        palette.add((8,0,0),('custom:test_planks',3))
        original = dict((k,list(v)) for k,v in palette.common.items())
        observed = []
        native_palette = types.SimpleNamespace(DeserializeBlockPalette=lambda data: observed.append(data) or True)
        self.runtime.CreateBlock = lambda level: types.SimpleNamespace(GetBlankBlockPalette=lambda: native_palette)
        builds = []
        self.runtime.CreateBlockGeometry = lambda level: types.SimpleNamespace(
            CombineBlockPaletteToGeometry=lambda p,name,mode: builds.append(name) or name)
        name = b.geometry(palette)
        data = observed[0]
        self.assertEqual(set(('minecraft:'+wood+'_planks',0) for wood in PLANK_SPECIES) | {('minecraft:polished_granite',0)},set(data['states']))
        self.assertEqual([1,6],data['common'][('minecraft:spruce_planks',0)])
        self.assertEqual([7],data['common'][('minecraft:polished_granite',0)])
        self.assertEqual([8],data['common'][('custom:test_planks',3)])
        self.assertEqual(9,sum(len(v) for v in data['common'].values()))
        self.assertEqual(original,palette.common)
        self.assertEqual(name,b.geometry(palette))
        self.assertEqual(1,len(builds))

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
        b.entity = None
        b.project_large((10, 50, -40))
        outline = b.projection_outline
        self.assertEqual((42., 114., -8.), self.runtime.actor_positions[outline.entity][1])
        self.assertEqual((64., 128., 64., .5), self.runtime.uniform_slots[outline.entity, 1])
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
