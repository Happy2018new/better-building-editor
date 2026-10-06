"""Projection actor pairs survive failed updates and asynchronous cancellation."""
import contextlib
import io
import unittest
import test_bridge as bridge_tests
from projection.model import Document, Editor, AIR
from projection.large_preview import SurfacePalette
from projection.biomes import shader_index


STONE = ('minecraft:stone', 0)


class BackdropLifecycleTests(unittest.TestCase):
    setUp = bridge_tests.ProjectionLifecycleTests.setUp
    tearDown = bridge_tests.ProjectionLifecycleTests.tearDown

    def drain(self):
        while self.runtime.timers:
            self.runtime.timers.pop(0)()

    def filtered(self, empty=False):
        b = self.bridge
        b.session.projection_missing = True
        b.session.origin = (10, 64, 20)
        b.session.editor = Editor(Document((2, 1, 1), {(0, 0, 0): STONE, (1, 0, 0): STONE}))
        if empty:
            self.runtime.world = {(10, 64, 20): STONE, (11, 64, 20): STONE}
        self.builds = []
        def geometry(document, visible=None, name=None):
            data = document.palette_data(visible)
            self.builds.append((name, data))
            return (name or 'model') if data['common'] else None
        b.geometry = geometry
        b.project()
        self.drain()
        return b.projection_occupancy

    def update(self, tracker, occupied):
        self.runtime.world = dict((tuple(tracker.origin[i] + pos[i] for i in range(3)), STONE)
                                  for pos in occupied)
        for pos in tracker.targets:
            tracker.read(pos)
        tracker.snapshot = tracker.state[:]
        tracker.after_build.clear()
        tracker.output = SurfacePalette(tracker.size)
        for unused in tracker.prepare():
            pass
        tracker.submit()

    def commit(self, tracker):
        model, anchor, unused = tracker.pending_model
        tracker.pending_model = None
        tracker.replace(model, anchor)

    def test_small_and_large_share_native_model_and_wait_as_a_pair(self):
        for large in (False, True):
            with self.subTest(large=large):
                b, r = self.bridge, self.runtime
                b.stop_projection()
                r.created[:], r.attached[:] = [], []
                built = []
                b.geometry = lambda doc, visible=None: built.append(doc) or 'shared_model'
                if large:
                    b.session.editor = Editor(Document((64, 128, 64), {(63, 127, 63): STONE}))
                    b.project_large((10, 20, 30))
                    while b.preparing_entity is None:
                        r.timers.pop(0)()
                else:
                    b.project()
                main, guard = b.preparing_entity, b.preparing_backdrop.entity
                self.assertFalse(r.attached)
                self.assertEqual(r.actor_positions[main][1], r.actor_positions[guard][1])
                self.drain()
                self.assertEqual(1, len(built))
                self.assertEqual({'shared_model'}, r.geometry_names[guard])
                self.assertEqual(r.geometry_names[main], r.geometry_names[guard])
                self.assertEqual((19488., float(shader_index(b.session.editor.document.biome)), 0., 0.),
                                 r.uniform_slots[guard, 4])
                self.assertFalse(r.transparent[guard, 'shared_model'])
                self.assertNotIn((guard, 'shared_model'), r.opacity)
                self.assertEqual(False, r.shadows[guard])

    def test_guard_attachment_failures_preserve_previous_pair(self):
        b, r = self.bridge, self.runtime
        b.project()
        self.drain()
        old_main, old_guard = b.entity, b.projection_backdrop
        for method in ('AddActorBlockGeometry', 'EnableActorBlockGeometryTransparent',
                       'SetEntityExtraUniforms', 'SetActorBlockGeometryVisible'):
            with self.subTest(method=method):
                b.project()
                pending = b.preparing_entity, b.preparing_backdrop.entity
                original = getattr(r, method)
                def fail_guard(*args):
                    return False if r.rendering == pending[1] else original(*args)
                setattr(r, method, fail_guard)
                with contextlib.redirect_stderr(io.StringIO()):
                    self.drain()
                setattr(r, method, original)
                self.assertEqual(old_main, b.entity)
                self.assertIs(old_guard, b.projection_backdrop)
                self.assertNotIn(old_main, r.destroyed)
                self.assertNotIn(old_guard.entity, r.destroyed)
                self.assertTrue(set(pending).issubset(r.destroyed))
                self.assertIsNone(b.preparing_backdrop)

    def test_guard_creation_failure_cleans_main_and_retains_current_pair(self):
        b, r = self.bridge, self.runtime
        b.project()
        self.drain()
        previous = b.entity, b.projection_backdrop
        create, attempted = r.CreateClientEntityByTypeStr, []
        def fail_second(*args):
            attempted.append(True)
            return create(*args) if len(attempted) == 1 else None
        r.CreateClientEntityByTypeStr = fail_second
        with self.assertRaises(ValueError):
            b.project()
        self.assertEqual(previous, (b.entity, b.projection_backdrop))
        self.assertIn(r.created[-1], r.destroyed)
        self.assertIsNone(b.preparing_entity)

    def test_stale_callbacks_and_destroy_release_current_and_pending_pairs(self):
        b, r = self.bridge, self.runtime
        b.project()
        self.drain()
        active = {b.entity, b.projection_backdrop.entity}
        b.project()
        superseded = {b.preparing_entity, b.preparing_backdrop.entity}
        b.project()
        pending = {b.preparing_entity, b.preparing_backdrop.entity}
        before = list(r.attached)
        b.destroy()
        self.drain()
        self.assertEqual(before, r.attached)
        for entity in active | superseded | pending:
            self.assertEqual(1, r.destroyed.count(entity))
        self.assertIsNone(b.entity)
        self.assertIsNone(b.projection_backdrop)
        self.assertIsNone(b.preparing_backdrop)

    def test_follow_moves_both_actors_with_same_world_origin_and_no_rebuild(self):
        b, r = self.bridge, self.runtime
        b.session.origin = (-30, 64, 5)
        b.project()
        self.drain()
        guard = b.projection_backdrop.entity
        b.geometry = lambda *a, **kw: self.fail('following must not regenerate geometry')
        for foot in ((8., 70., 9.), (-20., 65., 4.)):
            r.GetFootPos = lambda: foot
            b.follow_projection()
            for actor in (b.entity, guard):
                anchor = r.actor_positions[actor][1]
                offset = r.offsets[actor]
                self.assertEqual((-30, 64, 5),
                    (anchor[0]-offset[0]-.5, anchor[1]+offset[1], anchor[2]-offset[2]-.5))
        b.session.set_biome('desert')
        self.assertEqual(19488., r.uniform_slots[guard, 4][0])
        self.assertEqual(float(shader_index('desert')), r.uniform_slots[guard, 4][1])

    def test_bank_switch_empty_restore_and_failures_preserve_both_selectors(self):
        b, r = self.bridge, self.runtime
        tracker = self.filtered()
        guard = b.projection_backdrop.entity
        names = tracker.shader.names
        self.assertEqual(set(names), r.geometry_names[guard])
        self.assertEqual(2, len(self.builds), 'guard must reuse both native resources')
        def visible():
            return {name for name in names if r.visibility[guard, name]}
        self.assertEqual({names[0]}, visible())
        self.update(tracker, [(0, 0, 0)])
        self.assertEqual({names[0]}, visible(), 'preparing inactive bank must keep old guard')
        self.commit(tracker)
        self.assertEqual({names[1]}, visible())
        self.update(tracker, [(0, 0, 0), (1, 0, 0)])
        self.commit(tracker)
        self.assertFalse(visible())
        self.update(tracker, [])
        self.commit(tracker)
        self.assertEqual({names[0]}, visible())
        self.update(tracker, [(0, 0, 0)])
        previous = tracker.model, tracker.rendered, dict(tracker.shader.uniforms)
        setter = r.SetEntityExtraUniforms
        r.SetEntityExtraUniforms = lambda *a: False
        with self.assertRaises(ValueError):
            self.commit(tracker)
        r.SetEntityExtraUniforms = setter
        self.assertEqual({names[0]}, visible())
        self.assertEqual(previous, (tracker.model, tracker.rendered, tracker.shader.uniforms))
        setter = r.SetActorBlockGeometryVisible
        failures = [True]
        def fail_once(name, enabled):
            if name == names[1] and enabled and failures:
                failures.pop()
                return False
            return setter(name, enabled)
        r.SetActorBlockGeometryVisible = fail_once
        with self.assertRaises(ValueError):
            tracker.replace(names[1], tracker.anchor)
        self.assertEqual({names[0]}, visible())
        self.assertEqual(previous, (tracker.model, tracker.rendered, tracker.shader.uniforms))
        self.assertEqual(2, len(r.geometry_names[guard]))

    def test_initially_empty_pair_remains_staged_until_both_attachments_succeed(self):
        b, r = self.bridge, self.runtime
        tracker = self.filtered(empty=True)
        self.update(tracker, [(1, 0, 0)])
        pending = tracker.preparing_entity, tracker.preparing_backdrop.entity
        self.assertIsNone(b.entity)
        self.assertIsNone(b.projection_backdrop)
        self.drain()
        setter = r.AddActorBlockGeometry
        r.AddActorBlockGeometry = lambda *a: False if r.rendering == pending[1] else setter(*a)
        with contextlib.redirect_stderr(io.StringIO()):
            tracker.tick()
        self.assertTrue(tracker.failed)
        self.assertIsNone(b.entity)
        self.assertIsNone(b.projection_backdrop)
        self.assertTrue(set(pending).issubset(r.destroyed))
        self.assertTrue(b.session.projection_active)

    def test_initially_empty_pending_pair_is_cancelled_on_stop(self):
        b, r = self.bridge, self.runtime
        tracker = self.filtered(empty=True)
        self.update(tracker, [(1, 0, 0)])
        pending = tracker.preparing_entity, tracker.preparing_backdrop.entity
        b.stop_projection()
        self.drain()
        tracker.tick()
        self.assertTrue(set(pending).issubset(r.destroyed))
        self.assertFalse(r.attached)
        self.assertIsNone(b.entity)
        self.assertIsNone(tracker.preparing_entity)

    def test_zero_opacity_hides_guard_on_attachment_and_bank_commit(self):
        b, r = self.bridge, self.runtime
        b.session.opacity = 0.
        tracker = self.filtered()
        guard = b.projection_backdrop.entity
        self.assertFalse(any(r.visibility[guard, name] for name in tracker.shader.names))
        b.session.opacity = .5
        self.update(tracker, [(0, 0, 0)])
        self.commit(tracker)
        self.assertTrue(r.visibility[guard, tracker.model])
        b.session.opacity = 0.
        self.update(tracker, [])
        self.commit(tracker)
        self.assertFalse(any(r.visibility[guard, name] for name in tracker.shader.names))

    def test_failed_small_native_combine_keeps_committed_pair(self):
        b, r = self.bridge, self.runtime
        b.session.editor = Editor(Document((1, 1, 1), {(0, 0, 0): STONE}))
        b.project()
        self.drain()
        previous = b.entity, b.projection_backdrop
        b.geometry = lambda document, visible: (document.palette_data(visible), None)[1]
        with self.assertRaises(ValueError):
            b.project()
        self.assertEqual(previous, (b.entity, b.projection_backdrop))
        self.assertNotIn(previous[0], r.destroyed)
        self.assertNotIn(previous[1].entity, r.destroyed)

    def test_large_guard_failure_preserves_existing_projection_and_tracker(self):
        b, r = self.bridge, self.runtime
        tracker = self.filtered()
        previous = b.entity, b.projection_backdrop
        b.session.editor = Editor(Document((64, 128, 64), {(0, 0, 0): STONE}))
        b.project_large((30, 80, 40))
        while b.preparing_entity is None:
            r.timers.pop(0)()
        pending = b.preparing_entity, b.preparing_backdrop.entity
        setter = r.EnableActorBlockGeometryTransparent
        r.EnableActorBlockGeometryTransparent = lambda *a: False if r.rendering == pending[1] else setter(*a)
        self.drain()
        self.assertTrue(b.projection_work.error)
        self.assertEqual(previous, (b.entity, b.projection_backdrop))
        self.assertIs(tracker, b.projection_occupancy)
        self.assertTrue(set(pending).issubset(r.destroyed))

    def test_manual_replacement_cancels_empty_trackers_pending_pair(self):
        b, r = self.bridge, self.runtime
        tracker = self.filtered(empty=True)
        self.update(tracker, [(1, 0, 0)])
        staged = tracker.preparing_entity, tracker.preparing_backdrop.entity
        b.project()
        self.drain()
        tracker.tick()
        self.assertTrue(set(staged).issubset(r.destroyed))
        self.assertFalse(set(staged).intersection(r.attached))
        self.assertIsNot(tracker, b.projection_occupancy)
        self.assertIsNotNone(b.projection_backdrop)

    def test_pending_large_filtered_pair_uses_latest_biome(self):
        b, r = self.bridge, self.runtime
        self.filtered()
        b.session.editor = Editor(Document((64, 128, 64), {(0, 0, 0): STONE}))
        b.project_large((30, 80, 40))
        b.session.set_biome('jungle')
        self.drain()
        guard = b.projection_backdrop.entity
        self.assertEqual(float(shader_index('jungle')), r.uniform_slots[b.entity, 4][1])
        self.assertEqual(float(shader_index('jungle')), r.uniform_slots[guard, 4][1])

    def test_failed_follow_restores_guard_before_player_returns_to_cached_anchor(self):
        b, r = self.bridge, self.runtime
        b.session.origin = (0, 64, 0)
        b.project()
        self.drain()
        b.follow_projection()
        guard = b.projection_backdrop.entity
        previous = r.actor_positions[guard][1], r.offsets[guard]
        setter = r.SetActorBlockGeometryOffset
        r.GetFootPos = lambda: (10., 64., 0.)
        r.SetActorBlockGeometryOffset = lambda *a: False if r.rendering == guard else setter(*a)
        b.follow_projection()
        self.assertEqual(previous, (r.actor_positions[guard][1], r.offsets[guard]))
        r.SetActorBlockGeometryOffset = setter
        r.GetFootPos = lambda: (0., 64., 0.)
        b.follow_projection()
        anchor, offset = r.actor_positions[guard][1], r.offsets[guard]
        self.assertEqual((0, 64, 0),
            (anchor[0]-offset[0]-.5, anchor[1]+offset[1], anchor[2]-offset[2]-.5))

    def test_failed_second_bank_follow_restores_first_bank_offset(self):
        b, r = self.bridge, self.runtime
        tracker = self.filtered()
        guard, names = b.projection_backdrop.entity, tracker.shader.names
        offsets = {}
        setter = r.SetActorBlockGeometryOffset
        def record(name, offset):
            offsets[r.rendering, name] = offset
            return setter(name, offset)
        r.SetActorBlockGeometryOffset = record
        b.follow_projection()
        previous = r.actor_positions[guard][1], dict(offsets)
        new_foot = (10., 70., 25.)
        target_offset = b.projection_backdrop.offset((new_foot[0], new_foot[1]+1., new_foot[2]))
        def fail_second(name, offset):
            if r.rendering == guard and name == names[1] and offset == target_offset:
                return False
            return record(name, offset)
        r.GetFootPos = lambda: new_foot
        r.SetActorBlockGeometryOffset = fail_second
        b.follow_projection()
        self.assertEqual(previous[0], r.actor_positions[guard][1])
        for name in names:
            self.assertEqual(previous[1][guard, name], offsets[guard, name])

    def test_opacity_change_failure_restores_actual_old_guard_visibility(self):
        b, r = self.bridge, self.runtime
        tracker = self.filtered()
        guard = b.projection_backdrop.entity
        setter = r.SetEntityExtraUniforms
        for old_opacity, new_opacity in ((0., .5), (.5, 0.)):
            with self.subTest(old=old_opacity, new=new_opacity):
                b.session.opacity = old_opacity
                tracker.shader.control()
                previous = (dict(tracker.shader.backdrop.visible),
                            r.uniform_slots[b.entity, 4], tracker.shader.bank)
                b.session.opacity = new_opacity
                r.SetEntityExtraUniforms = lambda *args: False
                target = tracker.shader.names[1-tracker.shader.bank]
                with self.assertRaises(ValueError):
                    tracker.shader.commit(target)
                r.SetEntityExtraUniforms = setter
                self.assertEqual(previous[0], tracker.shader.backdrop.visible)
                self.assertEqual(previous[1], r.uniform_slots[b.entity, 4])
                self.assertEqual(previous[2], tracker.shader.bank)
                for name in tracker.shader.names:
                    self.assertEqual(previous[0][name], r.visibility[guard, name])

    def test_biome_control_synchronizes_zero_opacity_guard_and_rolls_back_on_failure(self):
        b, r = self.bridge, self.runtime
        tracker = self.filtered()
        guard, names = b.projection_backdrop.entity, tracker.shader.names
        b.session.opacity = 0.
        b.session.set_biome('desert')
        self.assertEqual(0., r.uniform_slots[b.entity, 4][3])
        self.assertFalse(any(r.visibility[guard, name] for name in names))
        b.session.opacity = .5
        setter = r.SetEntityExtraUniforms
        r.SetEntityExtraUniforms = lambda *a: False if r.rendering == b.entity else setter(*a)
        with self.assertRaises(ValueError):
            b.session.set_biome('jungle')
        self.assertEqual(0., r.uniform_slots[b.entity, 4][3])
        self.assertFalse(any(r.visibility[guard, name] for name in names))
        r.SetEntityExtraUniforms = setter
        tracker.shader.control()
        self.assertEqual(.5, r.uniform_slots[b.entity, 4][3])
        self.assertTrue(r.visibility[guard, tracker.model])
