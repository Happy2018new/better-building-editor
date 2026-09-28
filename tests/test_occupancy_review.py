"""Independent regressions for bounded scans and in-flight occupancy changes."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack'))
from modern_projection.projection.model import Document, AIR
from modern_projection.projection.large_preview import SurfacePalette
from modern_projection.projection.occupancy import ProjectionOccupancy, POLL_LIMIT, MAX_HINTS

STONE = ('minecraft:stone', 0)


class Runtime:
    def __init__(self):
        self.world, self.models = {}, {}
        self.created, self.attached, self.removed, self.timers, self.sent = [], [], [], [], []
        self.camera = (300., 64., 300.)
        self.offsets, self.geometry_calls, self.uniforms = {}, [], {}

    def CreateBlock(self, level):
        return self

    def CreateBlockInfo(self, level):
        return self

    def CreateCamera(self, level):
        return self

    def GetPosition(self):
        return self.camera

    def GetBlock(self, pos):
        return self.world.get(pos, AIR)

    def NotifyToServer(self, event, payload):
        self.sent.append((event, payload))

    def CreateClientEntityByTypeStr(self, identifier, anchor, rotation):
        entity = 'actor_%d' % len(self.created)
        self.created.append((entity, anchor))
        self.models[entity] = set()
        return entity

    def CreateModel(self, entity):
        return self

    def SetEntityShadowShow(self, value):
        return True

    def CreateActorRender(self, entity):
        self.rendering = entity
        return self

    def AddActorBlockGeometry(self, model, offset, rotation):
        self.models[self.rendering].add(model)
        self.attached.append((self.rendering, model))
        self.offsets[self.rendering] = offset
        return True

    def EnableActorBlockGeometryTransparent(self, model, enabled):
        return True

    def SetActorBlockGeometryTransparency(self, model, opacity):
        return True

    def SetEntityExtraUniforms(self, slot, values):
        self.uniforms[slot] = values
        return True

    def SetActorBlockGeometryOffset(self, name, offset):
        self.offsets[name] = offset
        return True

    def DeleteActorBlockGeometry(self, model):
        self.models[self.rendering].remove(model)
        self.removed.append((self.rendering, model))
        return True

    def geometry(self, output, name=None):
        self.geometry_calls.append((name, {key: tuple(values) for key, values in output.common.items()}))
        return name


class OccupancyReviewTests(unittest.TestCase):
    def tracker(self, document=None, occupied=(), hidden=(), layer=None):
        runtime = Runtime()
        document = document or Document((2, 1, 1), {(0, 0, 0): STONE, (1, 0, 0): STONE})
        origin = (10, 64, 20)
        for pos, value in occupied:
            runtime.world[tuple(origin[i]+pos[i] for i in range(3))] = value
        session = types.SimpleNamespace(editor=types.SimpleNamespace(document=document, layer=layer),
            preview_hidden=lambda: hidden, solo_layer=layer is not None, projection_active=True,
            opacity=.5, emit=lambda: None)
        bridge = types.SimpleNamespace(session=session, factory=runtime, system=runtime,
            projection_serial=1, level='level', alive=True, projection_mesh=None, entity=None,
            projection_work=None, preparing_entity=None, projection_occupancy=None,
            later=lambda delay, callback: runtime.timers.append(callback), geometry=runtime.geometry)
        bridge.ensure_projection_distance = lambda size: None
        occupancy = ProjectionOccupancy(bridge, origin)
        visible = [pos for pos in document.blocks if occupancy.initial_visible(pos)]
        entity = model = None
        if visible:
            entity = bridge.entity = runtime.CreateClientEntityByTypeStr('anchor', origin, (0, 0))
            model = occupancy.shader.names[0]
            runtime.models[entity].add(model)
            bridge.projection_mesh = (entity, model, origin, origin)
        occupancy.start(entity, model)
        occupancy.next_poll = float('inf')
        runtime.geometry_calls[:] = []
        runtime.attached[:] = []
        return occupancy, bridge, runtime

    def set_world(self, occupancy, runtime, pos, value):
        runtime.world[tuple(occupancy.origin[i]+pos[i] for i in range(3))] = value
        occupancy.read(pos)

    def prepare(self, occupancy):
        occupancy.snapshot = occupancy.state[:]
        occupancy.after_build.clear()
        occupancy.output = SurfacePalette(occupancy.size)
        for unused in occupancy.prepare():
            pass

    def commit_pending(self, o):
        model, anchor, unused = o.pending_model
        o.pending_model = None
        o.replace(model, anchor)

    def test_nonair_types_hide_and_restore_with_batched_buffers(self):
        for value in (('minecraft:glass', 0), ('minecraft:stone_slab', 3),
                      ('minecraft:water', 0), ('custom:unrelated_block', 7)):
            with self.subTest(value=value):
                o, b, r = self.tracker()
                entity, names = o.entity, set(r.models[o.entity])
                self.set_world(o, r, (0, 0, 0), value)
                self.prepare(o); o.submit(); self.commit_pending(o)
                self.assertEqual({STONE: (1,)}, r.geometry_calls[-1][1])
                self.set_world(o, r, (0, 0, 0), AIR)
                self.prepare(o); o.submit(); self.commit_pending(o)
                self.assertEqual({0, 1}, set(r.geometry_calls[-1][1][STONE]))
                self.assertEqual(entity, o.entity)
                self.assertEqual(names, r.models[o.entity])
                self.assertFalse(r.attached or r.removed)
                self.assertEqual({4}, set(r.uniforms))

    def test_reversal_and_second_change_during_build_survive_shader_commit(self):
        o, b, r = self.tracker()
        self.set_world(o, r, (0, 0, 0), STONE)
        self.prepare(o)
        self.set_world(o, r, (0, 0, 0), AIR)
        self.set_world(o, r, (1, 0, 0), STONE)
        o.submit()
        self.assertEqual({1}, o.changed)
        self.assertEqual({STONE: (1,)}, r.geometry_calls[-1][1])
        self.assertEqual(o.shader.names[0], o.model)
        self.commit_pending(o)
        self.assertEqual({0, 1}, o.changed)
        self.prepare(o)
        o.submit()
        self.commit_pending(o)
        self.assertFalse(o.changed)
        self.assertEqual({STONE: (0,)}, r.geometry_calls[-1][1])
        self.assertEqual(1, len(r.created))
        self.assertEqual(2, len(r.models[o.entity]))
        self.assertFalse(r.attached or r.removed)

    def test_all_changes_reverting_before_submit_skip_native_rebuild(self):
        o, b, r = self.tracker()
        self.set_world(o, r, (0, 0, 0), STONE)
        self.prepare(o)
        self.set_world(o, r, (0, 0, 0), AIR)
        o.submit()
        self.assertFalse(r.geometry_calls)
        self.assertEqual(set(o.shader.names), r.models[o.entity])
        self.assertFalse(o.changed)
        self.assertIsNone(o.snapshot)

    def test_deferred_first_actor_waits_for_manual_projection_work(self):
        o, b, r = self.tracker(occupied=(((0, 0, 0), STONE), ((1, 0, 0), STONE)))
        self.set_world(o, r, (0, 0, 0), AIR)
        self.prepare(o)
        o.submit()
        b.preparing_entity = 'manual_actor'
        r.timers.pop()()
        o.tick()
        self.assertFalse(r.attached)
        b.preparing_entity = None
        b.projection_work = types.SimpleNamespace(ready=False, error=None)
        o.tick()
        self.assertFalse(r.attached)
        b.projection_work.error = 'manual build failed'
        o.tick()
        self.assertEqual(2, len(r.attached))
        self.assertIsNone(o.pending_model)

    def test_stale_deferred_callback_cannot_attach_to_new_projection(self):
        o, b, r = self.tracker(occupied=(((0, 0, 0), STONE), ((1, 0, 0), STONE)))
        self.set_world(o, r, (0, 0, 0), AIR)
        self.prepare(o)
        o.submit()
        b.projection_occupancy = object()
        r.timers.pop()()
        o.tick()
        self.assertFalse(r.attached)
        self.assertIsNone(o.pending_model)

    def test_empty_then_restored_projection_keeps_both_buffers_and_world_offset(self):
        o, b, r = self.tracker()
        anchor = (27., 72., 9.)
        b.projection_mesh = (o.entity, o.model, o.origin, anchor)
        for pos in ((0, 0, 0), (1, 0, 0)):
            self.set_world(o, r, pos, STONE)
        self.prepare(o)
        o.submit()
        self.commit_pending(o)
        self.assertTrue(o.shader.empty)
        self.assertEqual(set(o.shader.names), r.models[o.entity])
        self.assertEqual(anchor, o.anchor)
        self.set_world(o, r, (1, 0, 0), AIR)
        self.prepare(o)
        o.submit()
        self.commit_pending(o)
        self.assertFalse(o.shader.empty)
        o.shader.follow(anchor, (26., 73., 8.))
        for name in o.shader.names:
            self.assertEqual((16.5, -8., -11.5), r.offsets[name])
        self.assertEqual({4}, set(r.uniforms))
        self.assertEqual(1, len(r.created))
        self.assertEqual(anchor, b.projection_mesh[3])
        self.assertFalse(r.attached or r.removed)

    def test_many_changes_rebuild_inactive_geometry_and_keep_current_visible(self):
        doc = Document((12, 1, 1), dict(((x, 0, 0), STONE) for x in range(12)))
        o, b, r = self.tracker(document=doc)
        for x in range(10):
            self.set_world(o, r, (x, 0, 0), STONE)
        current = o.model
        o.tick()
        self.assertEqual(10, len(o.changed))
        self.assertEqual(current, o.model)
        self.assertEqual(o.shader.names[1], r.geometry_calls[-1][0])
        self.assertIsNotNone(o.pending_model)
        self.commit_pending(o)
        self.assertEqual(o.shader.names[1], o.model)
        self.assertEqual(2., r.uniforms[4][2])
        self.assertFalse(o.changed)
        self.assertFalse(r.attached or r.removed)

    def test_uniform_failure_does_not_commit_cached_state(self):
        o, b, r = self.tracker()
        old = dict(o.shader.uniforms)
        r.SetEntityExtraUniforms = lambda *args: False
        self.set_world(o, r, (0, 0, 0), STONE)
        with self.assertRaises(ValueError):
            o.shader.write(4, (19487., 1., 2., .5))
        self.assertEqual(old, o.shader.uniforms)

    def test_failed_buffer_switch_keeps_committed_model_and_snapshot(self):
        o, b, r = self.tracker()
        self.set_world(o, r, (0, 0, 0), STONE)
        self.prepare(o); o.submit()
        previous = (o.model, o.rendered, o.shader.bank, o.shader.empty)
        r.SetEntityExtraUniforms = lambda *args: False
        with self.assertRaises(ValueError):
            self.commit_pending(o)
        self.assertEqual(previous, (o.model, o.rendered, o.shader.bank, o.shader.empty))

    def test_unknown_world_state_preserves_last_known_visibility(self):
        o, b, r = self.tracker(occupied=(((0, 0, 0), STONE),))
        for value in (None, ('minecraft:unknown', 0), (b'minecraft:unknown', 0)):
            self.set_world(o, r, (0, 0, 0), value)
            self.set_world(o, r, (1, 0, 0), value)
            self.assertEqual([2, 1], list(o.state))
            self.assertFalse(o.changed)

    def test_incremental_cache_reads_only_changed_document_cells(self):
        doc = Document((16, 16, 16), {(x, y, z): STONE
            for x in range(16) for y in range(16) for z in range(16)})
        o, b, r = self.tracker(document=doc)
        self.set_world(o, r, (7, 8, 9), STONE)
        lookup, calls = o.document.blocks.__class__.__getitem__, []
        def counted(store, pos):
            calls.append(pos)
            return lookup(store, pos)
        with patch.object(o.document.blocks.__class__, '__getitem__', counted):
            self.prepare(o)
        self.assertEqual([(7, 8, 9)], calls)
        self.assertEqual(4095, o.output.count)
        self.assertEqual(4095, len(set(o.output.common[STONE])))

    def test_reverted_preparation_keeps_cache_reversal_for_next_batch(self):
        o, b, r = self.tracker()
        self.set_world(o, r, (0, 0, 0), STONE)
        self.prepare(o)
        self.set_world(o, r, (0, 0, 0), AIR)
        o.submit()
        self.set_world(o, r, (1, 0, 0), STONE)
        self.prepare(o)
        self.assertEqual([0], o.output.common[STONE])

    def test_bulk_unknown_and_omitted_multiblock_entries_use_exact_reads(self):
        from modern_projection.projection.occupancy_scan import OccupancyScan
        doc = Document((32, 1, 1), {(x, 0, 0): STONE for x in range(32)})
        o, b, r = self.tracker(document=doc)
        o.bulk = OccupancyScan(o)
        data = {'volume': (1, 16, 1), 'common': {AIR: list(range(1, 16))}}
        r.GetBlockPaletteBetweenPos = lambda lo, hi, eliminate: types.SimpleNamespace(
            SerializeBlockPalette=lambda: data)
        r.world[o.origin] = ('minecraft:wooden_door', 8)
        for unused in o.bulk.scan():
            pass
        self.assertEqual(2, o.state[0])
        self.assertEqual({0}, o.changed)
        r.world[o.origin] = None
        o.bulk.cursor = 0
        for unused in o.bulk.scan():
            pass
        self.assertEqual(2, o.state[0], 'unloaded bulk air must not reveal old occupancy')

    def test_unloaded_native_air_cannot_override_last_known_occupancy(self):
        o, b, r = self.tracker(occupied=(((0, 0, 0), STONE),))
        o.loaded_chunks, o.dimension = set(), 0
        r.world[o.origin] = AIR
        reads = o.reads
        self.assertFalse(o.read((0, 0, 0)))
        self.assertEqual(reads, o.reads)
        self.assertEqual(2, o.state[0])
        o.loaded_chunks.add((0, o.origin[0] >> 4, o.origin[2] >> 4))
        self.assertTrue(o.read((0, 0, 0)))
        self.assertEqual({0}, o.changed)

    def test_full_volume_warmup_keeps_old_buffer_longer_than_small_model(self):
        o, b, r = self.tracker()
        self.set_world(o, r, (0, 0, 0), STONE)
        self.prepare(o); o.submit()
        self.assertEqual(.15, o.resource_wait)
        self.commit_pending(o)
        o.state.extend(bytearray(524286))
        self.set_world(o, r, (0, 0, 0), AIR)
        self.prepare(o); o.submit()
        self.assertGreaterEqual(o.resource_wait, 1.25)

    def test_poll_and_prepare_do_not_rescan_hidden_document_blocks(self):
        document = Document((64, 128, 64), {(0, 0, 0): STONE, (63, 127, 63): STONE})
        for hidden, layer, expected in ((tuple(range(128)), None, []),
                                         ((), 127, [(63, 127, 63)])):
            with self.subTest(layer=layer):
                o, b, r = self.tracker(document=document, hidden=hidden, layer=layer)
                o.document.blocks.items = lambda: self.fail('hidden document rescan')
                self.assertEqual(expected, list(o.positions()))
                with patch('modern_projection.projection.occupancy.time.time', return_value=100.):
                    before = o.reads
                    o.poll(100.)
                self.assertLessEqual(o.reads-before, POLL_LIMIT)
                self.prepare(o)
                self.assertEqual(len(expected), o.output.count)

    def test_empty_nearby_cells_yield_work_units_and_obey_query_limit(self):
        document = Document((16, 16, 16), {(15, 15, 15): STONE})
        o, b, r = self.tracker(document=document)
        r.camera = tuple(o.origin[i]+5. for i in range(3))
        calls = []
        class EmptyTargets:
            def __contains__(self, pos):
                calls.append(pos)
                return False
            def __iter__(self):
                return iter([(15, 15, 15)] * 1000)
        o.targets = EmptyTargets()
        with patch('modern_projection.projection.occupancy.time.time', return_value=100.):
            before = o.reads
            o.poll(100.)
        self.assertLessEqual(len(calls), POLL_LIMIT)
        self.assertLessEqual(o.reads-before, POLL_LIMIT)
        self.assertGreater(o.reads-before, 0)

    def test_no_visible_targets_skip_camera_and_block_queries(self):
        o, b, r = self.tracker(hidden=(0,))
        r.GetPosition = lambda: self.fail('hidden projection must not query the camera')
        r.GetBlock = lambda pos: self.fail('hidden projection must not query blocks')
        o.next_poll = 0.
        o.tick()
        self.assertFalse(r.geometry_calls)

    def test_hints_deduplicate_bound_queue_and_preserve_far_cursor(self):
        document = Document((16, 2, 16), {(x, y, z): STONE
            for x in range(16) for y in range(2) for z in range(16)})
        o, b, r = self.tracker(document=document)
        expected = iter(o.targets)
        o.scan = iter(o.targets)
        self.assertEqual(next(expected), next(o.scan))
        cursor = o.scan
        with patch('modern_projection.projection.occupancy.time.time', return_value=100.):
            for unused in range(3):
                for pos in o.targets:
                    o.hint(tuple(o.origin[i]+pos[i] for i in range(3)))
        self.assertEqual(MAX_HINTS, len(o.hints))
        self.assertEqual(MAX_HINTS, len(o.hint_queue))
        self.assertEqual(MAX_HINTS, len(set(o.hint_queue)))
        self.assertIs(cursor, o.scan)
        self.assertEqual(next(expected), next(o.scan))
        self.assertFalse(r.sent)

    def test_client_hint_covers_only_target_self_and_six_neighbours(self):
        document = Document((3, 3, 3), {(x, y, z): STONE
            for x in range(3) for y in range(3) for z in range(3)})
        o, b, r = self.tracker(document=document)
        reads = o.reads
        with patch('modern_projection.projection.occupancy.time.time', return_value=100.):
            o.hint(tuple(o.origin[i]+1 for i in range(3)))
        self.assertEqual({(1, 1, 1), (0, 1, 1), (2, 1, 1), (1, 0, 1),
                          (1, 2, 1), (1, 1, 0), (1, 1, 2)}, set(o.hints))
        self.assertEqual(reads, o.reads)
        self.assertFalse(r.sent)
        with patch('modern_projection.projection.occupancy.time.time', return_value=101.):
            o.poll(101.)
        self.assertFalse(o.hints)
        self.assertFalse(o.hint_queue)

    def test_hint_membership_outside_boundaries_does_not_alias_edge_cells(self):
        document = Document((64, 128, 64), {(0, 0, 0): STONE, (63, 127, 63): STONE})
        o, b, r = self.tracker(document=document)
        for local in ((-17, 0, 0), (-2, 0, 0), (65, 127, 63),
                      (0, -17, 0), (63, 129, 63), (0, 0, -17), (63, 127, 65)):
            o.hint(tuple(o.origin[i]+local[i] for i in range(3)))
        self.assertFalse(o.hints)
        o.hint((o.origin[0]-1, o.origin[1], o.origin[2]))
        self.assertEqual({(0, 0, 0)}, set(o.hints))

    def test_far_poll_progresses_even_when_hints_consume_time_budget(self):
        document = Document((16, 2, 16), {(x, y, z): STONE
            for x in range(16) for y in range(2) for z in range(16)})
        o, b, r = self.tracker(document=document)
        far = (15, 1, 15)
        o.scan = iter([far] * 100)
        clock, queries = [100.], []
        def slow_get(pos):
            queries.append(pos)
            clock[0] += .0003
            return AIR
        r.GetBlock = slow_get
        with patch('modern_projection.projection.occupancy.time.time', side_effect=lambda: clock[0]):
            for unused in range(3):
                o.hint(o.origin)
                queries[:] = []
                o.poll(clock[0])
                self.assertIn(tuple(o.origin[i]+far[i] for i in range(3)), queries)
                self.assertLessEqual(len(queries), POLL_LIMIT)
                clock[0] += .1

    def test_disabled_or_replaced_tracker_performs_no_queries_or_native_work(self):
        for reason in ('stopped', 'destroyed', 'replaced', 'failed'):
            with self.subTest(reason=reason):
                o, b, r = self.tracker()
                self.set_world(o, r, (0, 0, 0), STONE)
                o.next_poll = 0.
                if reason == 'stopped':
                    b.session.projection_active = False
                elif reason == 'destroyed':
                    b.alive = False
                elif reason == 'replaced':
                    b.projection_occupancy = None
                else:
                    o.failed = True
                reads = o.reads
                o.tick()
                self.assertEqual(reads, o.reads)
                self.assertFalse(r.geometry_calls)
                self.assertFalse(r.sent)

    def test_change_during_first_actor_delay_is_reconciled_without_new_actor(self):
        o, b, r = self.tracker(occupied=(((0, 0, 0), STONE), ((1, 0, 0), STONE)))
        self.set_world(o, r, (0, 0, 0), AIR)
        self.prepare(o)
        o.submit()
        self.set_world(o, r, (0, 0, 0), STONE)
        r.timers.pop()()
        o.tick()
        self.assertEqual({0}, o.changed)
        self.prepare(o)
        o.submit()
        self.commit_pending(o)
        self.assertFalse(o.changed)
        self.assertTrue(o.shader.empty)
        self.assertEqual(1, len(r.created))
        self.assertEqual(2, len(r.models[o.entity]))
        self.assertFalse(r.sent)


if __name__ == '__main__':
    unittest.main()
