"""Retired actors keep exclusive geometry ownership until destruction succeeds."""
import contextlib
import io
import types
import unittest

from test_bridge import Runtime, boundary
from projection.large_preview import SurfacePalette
from projection.model import Document, Editor
from projection.session import Session


class RetirementRuntime(Runtime):
    def __init__(self):
        super().__init__()
        self.destroy_failures = set()
        self.hide_uniform_failure = None
        self.hide_part_failure = None
        self.attach_failure = None
        self.visibility = {}
        self.visibility_calls = []
        self.uniform_calls = []
        self.destroy_attempts = []
        self.geometry_calls = []

    def DestroyClientEntity(self, entity):
        self.destroy_attempts.append(entity)
        if entity in self.destroy_failures:
            raise RuntimeError('injected entity destruction failure')
        return super().DestroyClientEntity(entity)

    def reject(self, failure):
        if failure == 'exception':
            raise RuntimeError('injected retirement setter exception')
        return False

    def SetEntityExtraUniforms(self, slot, values):
        self.uniform_calls.append((self.rendering, slot, values))
        failure = self.hide_uniform_failure
        if failure is not None and failure[0] == self.rendering and slot == 4 and values[2] < 0:
            return self.reject(failure[1])
        return super().SetEntityExtraUniforms(slot, values)

    def SetActorBlockGeometryVisible(self, name, visible):
        self.visibility_calls.append((self.rendering, name, visible))
        failure = self.hide_part_failure
        if failure is not None and failure[:2] == (self.rendering, name) and not visible:
            return self.reject(failure[2])
        self.visibility[self.rendering, name] = visible
        return True

    def AddActorBlockGeometry(self, name, offset=(0, 0, 0), rotation=(0, 0, 0)):
        result = super().AddActorBlockGeometry(name, offset, rotation)
        # Emulate an API that changes native state before it reports failure.
        self.visibility[self.rendering, name] = True
        if self.attach_failure == name:
            raise RuntimeError('injected attachment exception after native write')
        return result

    def geometry(self, bridge, document, name=None, **kwargs):
        self.geometry_calls.append(name)
        bridge.context_models[name] = ((name+'_context', (0, 0, 0), True),
                                       (name+'_overlay_a', (0, 0, 0), False),
                                       (name+'_overlay_b', (1, 0, 0), False))
        return name


class ProjectionRetirementTests(unittest.TestCase):
    def setUp(self):
        self.runtime = RetirementRuntime()
        self.original_api = boundary.clientApi
        boundary.clientApi = types.SimpleNamespace(GetEngineCompFactory=lambda: self.runtime,
            GetLevelId=lambda: 'level', GetLocalPlayerId=lambda: 'player')
        self.bridge = boundary.ClientBridge(self.runtime)
        self.bridge.session = Session(self.bridge)
        self.bridge.session.editor = Editor(Document((1, 1, 1),
            {(0, 0, 0): ('minecraft:stone', 0)}))
        self.bridge.session.origin = (10, 64, 20)
        self.bridge.session.projection_missing = False
        self.bridge.geometry = lambda document, **kwargs: self.runtime.geometry(
            self.bridge, document, **kwargs)
        self.errors = io.StringIO()
        self.stderr = contextlib.redirect_stderr(self.errors)
        self.stderr.__enter__()

    def tearDown(self):
        self.stderr.__exit__(None, None, None)
        boundary.clientApi = self.original_api

    def drain(self):
        for unused in range(200):
            if not self.runtime.timers:
                return
            self.runtime.timers.pop(0)()
        self.fail('projection did not finish within the frame budget')

    def project(self):
        self.bridge.project()
        self.drain()
        self.assertTrue(self.bridge.projection_work.ready)
        return self.bridge.entity, self.bridge.projection_shader

    def committed(self):
        b = self.bridge
        return (b.entity, b.projection_mesh, b.projection_shader, b.projection_occupancy,
                b.projection_outline, b.projection_liquid)

    def assert_pool_blocked(self, committed):
        b, r = self.bridge, self.runtime
        generated, created = list(r.geometry_calls), list(r.created)
        b.project()
        self.drain()
        self.assertEqual(committed, self.committed())
        self.assertIsNone(b.projection_work)
        self.assertEqual(generated, r.geometry_calls)
        self.assertEqual(created, r.created)
        self.assertTrue(b.session.projection_active)

    def test_multiple_generations_quarantine_both_banks_until_destroy_returns(self):
        b, r = self.bridge, self.runtime
        old, old_shader = self.project()
        r.destroy_failures.add(old)
        current, current_shader = self.project()
        self.assertEqual((0, 1), (old_shader.pool, current_shader.pool))
        self.assertIs(old_shader, b.projection_entity_shaders[old])
        self.assertEqual({old}, b.projection_retired_entities)
        self.assertTrue(old_shader.retirement_uniform_hidden)
        self.assertFalse(old_shader.retirement_parts)
        self.assertTrue(all(not r.visibility[old, name] for name in old_shader.owned_parts))
        hidden_uniforms = [call for call in r.uniform_calls if call[0] == old and call[2][2] < 0]
        hidden_parts = [call for call in r.visibility_calls if call[0] == old and not call[2]]
        self.assert_pool_blocked(self.committed())
        self.assertEqual(hidden_uniforms,
                         [call for call in r.uniform_calls if call[0] == old and call[2][2] < 0])
        self.assertEqual(hidden_parts,
                         [call for call in r.visibility_calls if call[0] == old and not call[2]])
        self.assertNotIn(current, r.destroyed)
        self.assertGreater(r.uniform_slots[current, 4][2], 0)
        r.destroy_failures.clear()
        replacement, replacement_shader = self.project()
        self.assertEqual(old_shader.names, replacement_shader.names)
        self.assertNotEqual(current, replacement)
        self.assertIn(old, r.destroyed)
        self.assertNotIn(old, b.projection_entity_shaders)
        self.assertIn(current, r.destroyed)
        b.stop_projection()
        self.assertFalse(b.projection_retired_entities)
        self.assertFalse(b.projection_entity_shaders)

    def test_false_and_exception_hide_writes_retry_without_releasing_pool(self):
        for mode in ('false', 'exception'):
            with self.subTest(mode=mode):
                old, shader = self.project()
                overlay = shader.names[shader.bank]+'_overlay_a'
                original = dict(shader.uniforms)
                r, b = self.runtime, self.bridge
                r.destroy_failures.add(old)
                r.hide_uniform_failure = (old, mode)
                r.hide_part_failure = (old, overlay, mode)
                current, unused = self.project()
                self.assertEqual(original, shader.uniforms)
                self.assertFalse(shader.retirement_uniform_hidden)
                self.assertEqual({overlay}, shader.retirement_parts)
                self.assertTrue(shader.overlay_visibility[overlay])
                self.assertTrue(r.visibility[old, overlay])
                self.assertTrue(any('retirement' in message or 'hide retired' in message
                                    for message in b.projection_work.cleanup_errors))
                calls = len(r.visibility_calls)
                self.assert_pool_blocked(self.committed())
                self.assertGreater(len(r.visibility_calls), calls)
                r.hide_uniform_failure = r.hide_part_failure = None
                b.release_projection_resources()
                self.assertTrue(shader.retirement_uniform_hidden)
                self.assertFalse(shader.retirement_parts)
                self.assertFalse(r.visibility[old, overlay])
                self.assertIn(old, b.projection_retired_entities)
                self.assertIs(shader, b.projection_entity_shaders[old])
                self.assert_pool_blocked(self.committed())
                self.assertNotIn(current, r.destroyed)
                r.destroy_failures.clear()
                self.project()
                b.stop_projection()
                self.assertFalse(b.projection_entity_shaders)

    def test_failed_partial_bind_retains_attempted_overlay_and_shader_owner(self):
        b, r = self.bridge, self.runtime
        old, unused = self.project()
        committed = self.committed()
        r.attach_failure = 'modern_projection_buffer_1_0_overlay_a'
        b.project()
        while b.preparing_entity is None:
            r.timers.pop(0)()
        pending, shader = b.preparing_entity, b.projection_work.shader
        r.destroy_failures.add(pending)
        r.hide_part_failure = (pending, r.attach_failure, 'exception')
        self.drain()
        self.assertEqual(committed, self.committed())
        self.assertIs(shader, b.projection_entity_shaders[pending])
        self.assertIn(r.attach_failure, shader.owned_parts)
        self.assertNotIn(r.attach_failure, shader.parts[0])
        self.assertEqual({r.attach_failure}, shader.retirement_parts)
        self.assert_pool_blocked(committed)
        self.assertNotIn(old, r.destroyed)
        r.attach_failure = r.hide_part_failure = None
        r.destroy_failures.clear()
        self.project()
        self.assertIn(pending, r.destroyed)
        b.stop_projection()
        self.assertFalse(b.projection_entity_shaders)

    def test_cancelled_unbound_actor_keeps_pool_until_close_recovery(self):
        b, r = self.bridge, self.runtime
        b.project()
        while b.preparing_entity is None:
            r.timers.pop(0)()
        pending, shader = b.preparing_entity, b.projection_work.shader
        self.assertIsNone(shader.render)
        self.assertIs(shader, b.projection_entity_shaders[pending])
        r.destroy_failures.add(pending)
        current, current_shader = self.project()
        self.assertEqual(1, current_shader.pool)
        self.assertIs(shader, b.projection_entity_shaders[pending])
        self.assert_pool_blocked(self.committed())
        b.stop_projection()
        self.assertIn(pending, b.projection_retired_entities)
        self.assertNotIn(current, b.projection_entity_shaders)
        r.destroy_failures.clear()
        b.stop_projection()
        self.assertIn(pending, r.destroyed)
        self.assertFalse(b.projection_entity_shaders)
        self.assertFalse(b.projection_retired_entities)

    def test_successful_destroy_releases_owner_even_after_hide_failure(self):
        b, r = self.bridge, self.runtime
        old, shader = self.project()
        r.hide_uniform_failure = (old, 'false')
        r.hide_part_failure = (old, shader.names[0]+'_overlay_a', 'false')
        self.project()
        self.assertIn(old, r.destroyed)
        self.assertNotIn(old, b.projection_entity_shaders)
        self.assertFalse(b.projection_retired_entities)
        self.assertTrue(b.projection_work.cleanup_errors)
        r.hide_uniform_failure = r.hide_part_failure = None
        unused, replacement = self.project()
        self.assertEqual(shader.pool, replacement.pool)
        b.stop_projection()

    def test_initially_empty_occupancy_reserves_late_actor_before_binding(self):
        b, r = self.bridge, self.runtime
        b.session.projection_missing = True
        r.world[b.session.origin] = ('minecraft:stone', 0)
        geometry = b.geometry
        b.geometry = lambda document, **kwargs: (geometry(document, **kwargs)
                                                if document.count else None)
        b.project()
        self.drain()
        self.assertIsNone(b.entity)
        self.assertIsNone(b.projection_shader)
        tracker = b.projection_occupancy
        tracker.changed.add(0)
        tracker.state[0] = 1
        tracker.snapshot = tracker.state[:]
        tracker.output = SurfacePalette(tracker.size)
        tracker.output.add((0, 0, 0), ('minecraft:stone', 0))
        tracker.submit()
        pending, shader = b.entity, tracker.shader
        self.assertIsNone(shader.render)
        self.assertIs(shader, b.projection_entity_shaders[pending])
        r.destroy_failures.add(pending)
        b.stop_projection()
        self.drain()
        self.assertIs(shader, b.projection_entity_shaders[pending])
        self.assertIsNone(shader.render)
        b.session.projection_missing = False
        current, current_shader = self.project()
        self.assertNotEqual(shader.pool, current_shader.pool)
        self.assert_pool_blocked(self.committed())
        self.assertNotIn(current, r.destroyed)
        r.destroy_failures.clear()
        b.stop_projection()
        self.assertFalse(b.projection_entity_shaders)
        self.assertFalse(b.projection_retired_entities)

    def test_close_with_two_surviving_generations_blocks_reopen_until_recovery(self):
        b, r = self.bridge, self.runtime
        old, old_shader = self.project()
        r.destroy_failures.add(old)
        current, current_shader = self.project()
        r.destroy_failures.add(current)
        b.stop_projection()
        self.assertFalse(b.session.projection_active)
        self.assertIsNone(b.entity)
        self.assertEqual({old, current}, b.projection_retired_entities)
        self.assertIs(old_shader, b.projection_entity_shaders[old])
        self.assertIs(current_shader, b.projection_entity_shaders[current])
        created, generated = list(r.created), list(r.geometry_calls)
        b.project()
        self.drain()
        self.assertIsNone(b.projection_work)
        self.assertFalse(b.projection_requested)
        self.assertFalse(b.session.projection_active)
        self.assertEqual(created, r.created)
        self.assertEqual(generated, r.geometry_calls)
        self.assertEqual(72., r.render_distance)
        r.destroy_failures.clear()
        replacement, unused = self.project()
        self.assertNotIn(replacement, {old, current})
        self.assertFalse(b.projection_retired_entities)
        b.stop_projection()
        self.assertFalse(b.projection_entity_shaders)


if __name__ == '__main__':
    unittest.main()
