"""Host fault injection for client-only projection transform transactions."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack'))
for module in ('mod', 'mod.client', 'mod.client.extraClientApi'):
    sys.modules.setdefault(module, types.ModuleType(module))
from modern_projection.projection.bridge import ClientBridge
from modern_projection.projection.occupancy_shader import OccupancyShader


OLD = (10., 65., 20.)
TARGET = (13., 67., 17.)
ORIGIN = (100, 64, -40)
CORRUPT = (900., 900., 900.)


class NativeTransforms:
    def __init__(self):
        self.positions = {'mesh': OLD}
        self.offsets = {}
        self.calls = []
        self.outcomes = {}
        self.foot = (OLD[0], OLD[1]-1., OLD[2])
        self.observer = lambda: None

    def write(self, kind, entity, name, value):
        key = (kind, entity, name)
        queue = self.outcomes.get(key, [])
        outcome = queue.pop(0) if queue else True
        result, actual = outcome if isinstance(outcome, tuple) else (outcome, value)
        self.calls.append((kind, entity, name, value, self.observer()))
        if kind == 'position':
            self.positions[entity] = actual
        else:
            self.offsets[entity, name] = actual
        if isinstance(result, Exception):
            raise result
        return result

    def CreateActorRender(self, entity):
        return types.SimpleNamespace(SetActorBlockGeometryOffset=lambda name, value:
                                     self.write('offset', entity, name, value))

    def CreatePos(self, entity):
        return types.SimpleNamespace(SetPosForClientEntity=lambda value:
                                     self.write('position', entity, None, value))

    def CreateCamera(self, level):
        return types.SimpleNamespace(GetPosition=lambda: (1., 66., 2.),
                                     GetForward=lambda: (0., 0., 1.))

    def GetFootPos(self):
        return self.foot

    def target(self, value=TARGET):
        self.foot = (value[0], value[1]-1., value[2])


class Outline:
    entity = 'outline'

    def __init__(self):
        self.outcomes = []
        self.calls = []
        self.observer = lambda: None

    def follow(self, position, camera):
        self.calls.append(self.observer())
        result = self.outcomes.pop(0) if self.outcomes else True
        if isinstance(result, Exception):
            raise result
        return result


def shader_fixture(runtime, entity='mesh'):
    tracker = types.SimpleNamespace(origin=ORIGIN,
        bridge=types.SimpleNamespace(projection_shader=None, projection_occupancy=None))
    shader = OccupancyShader(tracker)
    shader.render = runtime.CreateActorRender(entity)
    shader.anchor = OLD
    shader.parts = [{'a': ((0, 0, 0), True), 'b': ((16, 0, 0), False)},
                    {'c': ((0, 16, 0), True), 'd': ((0, 0, 16), False)}]
    shader.active_parts = [set(['a', 'b']), set(['c', 'd'])]
    shader.bank = 1
    shader.overlay_visibility = {'b': False, 'd': True}
    for parts in shader.parts:
        for name, value in parts.items():
            runtime.offsets[entity, name] = shader.offset(OLD, value[0])
    return shader


def bridge_fixture(shader=True):
    runtime = NativeTransforms()
    bridge = ClientBridge.__new__(ClientBridge)
    bridge.alive = True
    bridge.session = types.SimpleNamespace(projection_active=True)
    bridge.factory = runtime
    bridge.level = 'level'
    bridge.player_position = runtime
    bridge.survey_effects = types.SimpleNamespace(active=lambda: False, follow=lambda *args: True)
    bridge.entity = 'mesh'
    bridge.projection_mesh = ('mesh', 'a', ORIGIN, OLD)
    bridge.projection_shader = shader_fixture(runtime) if shader else None
    if not shader:
        runtime.offsets['mesh', 'a'] = (-90.5, -1., 59.5)
    bridge.projection_outline = Outline()
    bridge._projection_follow_position = None
    bridge._projection_follow_restore = None
    runtime.observer = lambda: (bridge.projection_mesh[3],
                               bridge.projection_shader.anchor if bridge.projection_shader else None)
    bridge.projection_outline.observer = runtime.observer
    bridge.follow_projection()
    runtime.calls[:] = []
    return bridge, runtime


class ShaderFollowTransactionTests(unittest.TestCase):
    def setUp(self):
        self.log = patch('traceback.print_exc')
        self.log.start()
        self.addCleanup(self.log.stop)

    def test_first_middle_last_refusal_or_exception_restores_every_touched_part(self):
        for name in ('a', 'b', 'd'):
            for failure in (False, RuntimeError('native offset failure')):
                with self.subTest(name=name, failure=failure):
                    runtime = NativeTransforms()
                    shader = shader_fixture(runtime)
                    previous = dict(runtime.offsets)
                    runtime.outcomes['offset', 'mesh', name] = [failure]
                    self.assertFalse(shader.follow(TARGET, (1., 66., 2.)))
                    self.assertEqual(previous, runtime.offsets)
                    self.assertEqual(OLD, shader.anchor)
                    self.assertEqual([], shader.offset_restore)
                    self.assertEqual(1, shader.bank)
                    self.assertEqual({'b': False, 'd': True}, shader.overlay_visibility)
                    writes = [call[2] for call in runtime.calls]
                    touched = writes[:len(writes)//2]
                    self.assertEqual(list(reversed(touched)), writes[len(writes)//2:])
                    self.assertTrue(shader.follow(TARGET, (1., 66., 2.)))
                    self.assertEqual(TARGET, shader.anchor)

    def test_rollback_failure_retains_only_failed_offsets_and_next_call_repairs_them(self):
        runtime = NativeTransforms()
        shader = shader_fixture(runtime)
        previous = dict(runtime.offsets)
        runtime.outcomes['offset', 'mesh', 'c'] = [False, (False, CORRUPT)]
        runtime.outcomes['offset', 'mesh', 'a'] = [True, (ValueError('rollback failure'), CORRUPT)]
        self.assertFalse(shader.follow(TARGET, (1., 66., 2.)))
        self.assertEqual(set(['a', 'c']), set(name for name, offset in shader.offset_restore))
        self.assertEqual(previous['mesh', 'b'], runtime.offsets['mesh', 'b'])
        self.assertEqual(OLD, shader.anchor)
        runtime.outcomes['offset', 'mesh', 'c'] = [(False, CORRUPT)]
        runtime.calls[:] = []
        self.assertFalse(shader.follow(TARGET, (1., 66., 2.)))
        self.assertEqual(set(['a', 'c']), set(call[2] for call in runtime.calls))
        self.assertEqual(['c'], [name for name, offset in shader.offset_restore])
        self.assertTrue(shader.follow(OLD, (1., 66., 2.)))
        self.assertEqual(previous, runtime.offsets)
        self.assertEqual([], shader.offset_restore)

    def test_prepare_delays_anchor_until_commit_and_commit_makes_no_native_calls(self):
        runtime = NativeTransforms()
        shader = shader_fixture(runtime)
        self.assertTrue(shader.prepare_follow(TARGET, (1., 66., 2.)))
        self.assertEqual(OLD, shader.anchor)
        self.assertEqual(4, len(shader.offset_restore))
        calls = list(runtime.calls)
        shader.commit_follow()
        self.assertEqual(TARGET, shader.anchor)
        self.assertEqual([], shader.offset_restore)
        self.assertEqual(calls, runtime.calls)

    def test_control_and_buffer_commit_wait_for_offset_recovery(self):
        for operation in ('control', 'commit'):
            with self.subTest(operation=operation):
                runtime = NativeTransforms()
                shader = shader_fixture(runtime)
                shader.offset_restore = [('b', runtime.offsets['mesh', 'b'])]
                runtime.outcomes['offset', 'mesh', 'b'] = [(False, CORRUPT)]
                with self.assertRaisesRegex(ValueError, 'restore projection geometry offsets'):
                    getattr(shader, operation)(*(() if operation == 'control' else (None,)))
                self.assertEqual(OLD, shader.anchor)
                self.assertEqual(1, shader.bank)
                self.assertEqual({'b': False, 'd': True}, shader.overlay_visibility)
                self.assertTrue(shader.offset_restore)


class BridgeFollowTransactionTests(unittest.TestCase):
    def setUp(self):
        self.log = patch('traceback.print_exc')
        self.log.start()
        self.addCleanup(self.log.stop)

    def assert_unchanged(self, bridge, runtime, offsets, signature):
        self.assertEqual(OLD, bridge.projection_mesh[3])
        self.assertEqual(OLD, runtime.positions['mesh'])
        self.assertEqual(offsets, runtime.offsets)
        self.assertEqual(signature, bridge._projection_follow_position)
        self.assertIsNone(bridge._projection_follow_restore)
        if bridge.projection_shader is not None:
            self.assertEqual(OLD, bridge.projection_shader.anchor)
            self.assertEqual(1, bridge.projection_shader.bank)
            self.assertEqual({'b': False, 'd': True}, bridge.projection_shader.overlay_visibility)
        self.assertTrue(all(call[4][0] == OLD for call in runtime.calls))

    def test_actor_refusal_or_exception_after_mutation_rolls_back_before_offsets(self):
        for failure in (False, ValueError('native position failure')):
            with self.subTest(failure=failure):
                bridge, runtime = bridge_fixture()
                offsets, signature = dict(runtime.offsets), bridge._projection_follow_position
                runtime.target()
                runtime.outcomes['position', 'mesh', None] = [failure]
                bridge.follow_projection()
                self.assertEqual(['position', 'position'], [call[0] for call in runtime.calls])
                self.assert_unchanged(bridge, runtime, offsets, signature)
                bridge.follow_projection()
                self.assertEqual(TARGET, bridge.projection_mesh[3])
                self.assertEqual(TARGET, bridge.projection_shader.anchor)

    def test_multipart_refusal_or_exception_rolls_back_actor_and_offsets(self):
        for name in ('a', 'b', 'd'):
            for failure in (False, RuntimeError('native offset failure')):
                with self.subTest(name=name, failure=failure):
                    bridge, runtime = bridge_fixture()
                    offsets, signature = dict(runtime.offsets), bridge._projection_follow_position
                    runtime.target()
                    runtime.outcomes['offset', 'mesh', name] = [failure]
                    bridge.follow_projection()
                    self.assert_unchanged(bridge, runtime, offsets, signature)
                    self.assertEqual(1, len(bridge.projection_outline.calls))

    def test_offset_and_actor_rollback_failure_repair_before_stationary_cache_hit(self):
        bridge, runtime = bridge_fixture()
        offsets, signature = dict(runtime.offsets), bridge._projection_follow_position
        runtime.target()
        runtime.outcomes['offset', 'mesh', 'c'] = [False, (False, CORRUPT)]
        runtime.outcomes['position', 'mesh', None] = [True, (RuntimeError('position rollback failure'), CORRUPT)]
        bridge.follow_projection()
        self.assertIsNotNone(bridge._projection_follow_restore)
        self.assertEqual(['c'], [name for name, offset in bridge.projection_shader.offset_restore])
        self.assertEqual(OLD, bridge.projection_shader.anchor)
        self.assertEqual(OLD, bridge.projection_mesh[3])
        self.assertEqual(signature, bridge._projection_follow_position)
        runtime.target(OLD)
        runtime.calls[:] = []
        bridge.follow_projection()
        self.assertEqual([('offset', 'c'), ('position', None)],
                         [(call[0], call[2]) for call in runtime.calls])
        self.assert_unchanged(bridge, runtime, offsets, signature)
        runtime.calls[:] = []
        bridge.follow_projection()
        self.assertEqual([], runtime.calls)

    def test_unresolved_position_rollback_blocks_new_follow_but_retries_next_call(self):
        bridge, runtime = bridge_fixture()
        runtime.target()
        runtime.outcomes['position', 'mesh', None] = [(False, CORRUPT), (False, CORRUPT), (False, CORRUPT)]
        bridge.follow_projection()
        self.assertIsNotNone(bridge._projection_follow_restore)
        runtime.calls[:] = []
        bridge.follow_projection()
        self.assertEqual([('position', 'mesh', None, OLD)], [call[:4] for call in runtime.calls])
        self.assertEqual(OLD, bridge.projection_mesh[3])
        runtime.calls[:] = []
        bridge.follow_projection()
        self.assertEqual(TARGET, bridge.projection_mesh[3])
        self.assertIsNone(bridge._projection_follow_restore)
        self.assertEqual(OLD, runtime.calls[0][3])

    def test_same_actor_buffer_refresh_preserves_pending_position_recovery(self):
        bridge, runtime = bridge_fixture()
        runtime.target()
        runtime.outcomes['position', 'mesh', None] = [(False, CORRUPT), (False, CORRUPT)]
        bridge.follow_projection()
        self.assertIsNotNone(bridge._projection_follow_restore)
        bridge.projection_mesh = ('mesh', 'c', ORIGIN, OLD)
        runtime.target(OLD)
        runtime.calls[:] = []
        bridge.follow_projection()
        self.assertEqual([('position', 'mesh', None, OLD)], [call[:4] for call in runtime.calls])
        self.assertEqual(OLD, runtime.positions['mesh'])
        self.assertEqual('c', bridge.projection_mesh[1])
        self.assertIsNone(bridge._projection_follow_restore)

    def test_plain_mesh_refusal_or_exception_restores_actor_and_single_offset(self):
        for failure in (False, TypeError('native offset failure')):
            with self.subTest(failure=failure):
                bridge, runtime = bridge_fixture(shader=False)
                offsets, signature = dict(runtime.offsets), bridge._projection_follow_position
                runtime.target()
                runtime.outcomes['offset', 'mesh', 'a'] = [failure]
                bridge.follow_projection()
                self.assert_unchanged(bridge, runtime, offsets, signature)

    def test_plain_mesh_rollback_failure_is_retained_and_stationary_follow_repairs_it(self):
        bridge, runtime = bridge_fixture(shader=False)
        offsets, signature = dict(runtime.offsets), bridge._projection_follow_position
        runtime.target()
        runtime.outcomes['offset', 'mesh', 'a'] = [False, (ValueError('offset rollback failure'), CORRUPT)]
        bridge.follow_projection()
        self.assertIsNotNone(bridge._projection_follow_restore)
        self.assertEqual(OLD, runtime.positions['mesh'])
        runtime.target(OLD)
        runtime.calls[:] = []
        bridge.follow_projection()
        self.assertEqual(['offset'], [call[0] for call in runtime.calls])
        self.assert_unchanged(bridge, runtime, offsets, signature)

    def test_outline_refusal_or_exception_rolls_back_staged_mesh_before_cache_commit(self):
        for failure in (False, RuntimeError('outline failure')):
            with self.subTest(failure=failure):
                bridge, runtime = bridge_fixture()
                offsets, signature = dict(runtime.offsets), bridge._projection_follow_position
                runtime.target()
                bridge.projection_outline.outcomes = [failure]
                bridge.follow_projection()
                self.assertEqual((OLD, OLD), bridge.projection_outline.calls[-1])
                self.assert_unchanged(bridge, runtime, offsets, signature)
                runtime.calls[:] = []
                bridge.follow_projection()
                self.assertEqual(TARGET, bridge.projection_mesh[3])
                self.assertEqual(TARGET, bridge.projection_shader.anchor)
                self.assertTrue(all(call[4] == (OLD, OLD) for call in runtime.calls))

    def test_replaced_owner_discards_stale_recovery_without_transforming_old_actor(self):
        bridge, runtime = bridge_fixture()
        runtime.target()
        runtime.outcomes['position', 'mesh', None] = [(False, CORRUPT), (False, CORRUPT)]
        bridge.follow_projection()
        self.assertIsNotNone(bridge._projection_follow_restore)
        bridge.entity = 'replacement'
        bridge.projection_mesh = ('replacement', 'a', ORIGIN, OLD)
        bridge.projection_shader = shader_fixture(runtime, 'replacement')
        runtime.positions['replacement'] = OLD
        runtime.target(OLD)
        runtime.calls[:] = []
        bridge.follow_projection()
        self.assertEqual([], runtime.calls)
        self.assertIsNone(bridge._projection_follow_restore)
        self.assertEqual(OLD, bridge.projection_mesh[3])


if __name__ == '__main__':
    unittest.main()
