"""One occupancy snapshot publishes terrain and liquid only after both are ready."""
import contextlib
import io
import unittest
from unittest.mock import patch

import test_liquid_projection as fixtures
from test_liquid_projection import material, make_cell
from projection.model import Document, Editor


class ProjectionPairTests(unittest.TestCase):
    def setUp(self):
        fixtures.WorldLiquidIntegrationTests.setUp(self)
        b, r = self.bridge, self.runtime
        blocks = {}
        for x in (1, 2, 5, 6, 9, 10):
            blocks[x, 1, 1] = make_cell(material('oak_fence'), material('water'))
        b.session.editor = Editor(Document((12, 3, 4), blocks))
        b.session.projection_missing = True
        self.visibility = {}
        self.events = []
        self.failure = None
        self.rollback_failure = False
        self.failed_key = None
        self.failure_counts = {}
        self.baseline = None
        self.observed = []
        self.errors = io.StringIO()
        self.stderr = contextlib.redirect_stderr(self.errors)
        self.stderr.__enter__()

        def geometry(document, name=None, **kwargs):
            b.context_models[name] = ((name+'_context', (0, 0, 0), True),
                                     (name+'_overlay_a', (0, 0, 0), False),
                                     (name+'_overlay_b', (1, 0, 0), False))
            count = document.count if hasattr(document, 'count') else len(document.blocks)
            return name if count else None
        b.geometry = geometry

        uniform = r.SetEntityExtraUniforms
        def body_uniform(slot, value):
            result = uniform(slot, value)
            shader = b.projection_shader
            if slot == 4 and shader is not None:
                result = self.native('selector', (r.rendering, slot),
                                     shader._commit_candidate is not None, result)
            return result
        r.SetEntityExtraUniforms = body_uniform

        def body_visibility(name, value):
            self.visibility[r.rendering, name] = value
            shader = b.projection_shader
            return self.native('overlay', (r.rendering, name),
                               shader is not None and shader._commit_candidate is not None)
        r.SetActorBlockGeometryVisible = body_visibility

        models = r.liquid_models
        liquid_uniform = models.SetExtraUniformValue
        def liquid_visibility(model_id, slot, value):
            result = liquid_uniform(model_id, slot, value)
            liquid = b.projection_liquid
            if slot == 4 and liquid is not None:
                result = self.native('liquid', (model_id, slot),
                                     liquid.renderer.publication is not None, result)
            return result
        models.SetExtraUniformValue = liquid_visibility
        self.rebuild()

    def tearDown(self):
        self.failure = None
        self.rollback_failure = False
        self.bridge.stop_projection()
        self.stderr.__exit__(None, None, None)
        fixtures.WorldLiquidIntegrationTests.tearDown(self)

    def drain(self):
        fixtures.WorldLiquidIntegrationTests.drain(self)

    def rebuild(self):
        self.failure = None
        self.rollback_failure = False
        self.failed_key = None
        self.baseline = None
        self.bridge.project_large((10, 64, 20))
        self.drain()
        self.assertTrue(self.bridge.projection_work.ready)
        self.tracker = self.bridge.projection_occupancy
        self.water = self.bridge.projection_liquid
        if self.tracker is not None:
            self.tracker.next_poll = float('inf')
            self.tracker.next_bulk = float('inf')
            self.tracker.next_build = float('inf')

    def public(self):
        b, t, w = self.bridge, self.tracker, self.water
        return (b.projection_mesh, t.model, t.anchor, bytes(t.rendered), t.commits,
                t.shader.bank, t.shader.empty, dict(t.shader.uniforms),
                dict(t.shader.overlay_visibility),
                dict((key, (record['model_id'], record['group'], record['visible']))
                     for key, record in w.renderer.active.items()),
                bytes(w.occupied) if w.occupied is not None else None, w.targets)

    def native(self, kind, key, publishing, result=True):
        if publishing:
            self.events.append((kind, key))
            if self.baseline is not None:
                self.observed.append(self.public() == self.baseline)
            self.failure_counts[kind] = self.failure_counts.get(kind, 0)+1
        if self.failed_key == (kind, key) and self.rollback_failure:
            if self.rollback_failure == 'exception':
                raise RuntimeError('injected native rollback exception')
            return False
        if self.failure is not None and publishing:
            target, nth, mode = self.failure
            if kind == target and self.failure_counts[kind] == nth:
                self.failure = None
                self.failed_key = (kind, key)
                if mode == 'exception':
                    raise RuntimeError('injected failure after native mutation')
                return False
        return result

    def candidate(self, occupied=None, model=True):
        t = self.tracker
        state = t.state[:]
        if occupied is None:
            occupied = ((1, 1, 1), (5, 1, 1), (9, 1, 1))
        for pos in occupied:
            state[t.index(pos)] = 2
        t.state = state[:]
        t.snapshot = state
        selected = t.shader.names[1-t.shader.bank] if model else None
        self.bridge.geometry(t.document, name=selected or t.shader.names[1-t.shader.bank])
        t.pending_model = (selected, t.anchor, 0.)
        self.baseline = self.public()
        self.failure_counts = {}
        self.events = []
        self.observed = []
        return state

    def pump(self, limit=100):
        for unused in range(limit):
            self.bridge.update_projection_occupancy()
            if self.tracker.failed or self.tracker.pending_model is None:
                return
        self.fail('paired candidate did not complete')

    def assert_old_pair(self):
        self.assertEqual(self.baseline, self.public())
        self.assertTrue(all(self.observed))
        old_ids = {record['model_id'] for record in self.water.renderer.active.values()}
        self.assertTrue(all(not self.runtime.liquid_models.hidden(model_id) for model_id in old_ids))
        self.assertTrue(all(self.visibility[self.tracker.entity, name] == shown
                            for name, shown in self.tracker.shader.overlay_visibility.items()))
        self.assertEqual(self.tracker.shader.uniforms[4],
                         self.runtime.uniform_slots[self.tracker.entity, 4])

    def test_synchronous_provider_rejection_preserves_published_pair(self):
        self.candidate()
        with patch.object(self.water.profile, 'provider_factory',
                          side_effect=ValueError('provider rejected immutable source')):
            self.pump()
        self.assertTrue(self.tracker.failed)
        self.assert_old_pair()
        self.assertIsNone(self.tracker.pending_pair)

    def test_async_provider_model_map_and_native_preparation_failures_preserve_pair(self):
        failures = ('provider', 'models', 'create', 'bounds', 'scale', 'rotation', 'position', 'uniform')
        for failure in failures:
            with self.subTest(failure=failure):
                self.rebuild()
                self.candidate()
                models = self.runtime.liquid_models
                if failure == 'provider':
                    class Provider:
                        def surface(self, *args):
                            raise RuntimeError('asynchronous provider failure')
                    target, field, replacement = self.water.profile, 'provider_factory', lambda doc: Provider()
                elif failure == 'models':
                    target, field, replacement = self.water.profile, 'world_models', {}
                else:
                    names = {'create': 'CreateFreeModel', 'bounds': 'SetFreeModelBoundingBox',
                             'scale': 'SetFreeModelScale', 'rotation': 'SetFreeModelRot',
                             'position': 'SetFreeModelPos', 'uniform': 'SetExtraUniformValue'}
                    target, field = models, names[failure]
                    original = getattr(target, field)
                    def replacement(*args, _failure=failure, _original=original):
                        if _failure == 'create':
                            return None
                        result = _original(*args)
                        if _failure != 'uniform' or args[1] == 2:
                            raise RuntimeError('asynchronous native preparation failure')
                        return result
                with patch.object(target, field, replacement):
                    self.pump()
                self.assertTrue(self.tracker.failed)
                self.assert_old_pair()
                self.assertFalse(self.water.renderer.staging)
                self.assertFalse(self.tracker.pending_pair)

    def test_first_middle_last_switch_failures_restore_the_failed_write_too(self):
        for kind, positions in (('overlay', (1, 2, 4)), ('selector', (1,)), ('liquid', (1, 3, 6))):
            for nth in positions:
                for mode in ('false', 'exception'):
                    with self.subTest(kind=kind, nth=nth, mode=mode):
                        self.rebuild()
                        self.candidate()
                        self.failure = kind, nth, mode
                        self.pump()
                        self.assertTrue(self.tracker.failed)
                        self.assertIsNotNone(self.failed_key)
                        self.assert_old_pair()
                        self.assertFalse(self.tracker.shader.commit_restore)
                        self.assertFalse(self.water.renderer.publication_restore)
                        self.assertFalse(self.water.renderer.staging)

    def test_failed_rollback_retains_journal_and_blocks_follow_and_new_prepare(self):
        for kind in ('selector', 'overlay', 'liquid'):
            for mode in ('false', 'exception'):
                with self.subTest(kind=kind, mode=mode):
                    self.rebuild()
                    self.bridge.follow_projection()
                    self.candidate()
                    self.failure = kind, 1, mode
                    self.rollback_failure = mode
                    self.pump()
                    t, w, b = self.tracker, self.water, self.bridge
                    self.assertIsNotNone(t.pending_pair)
                    self.assertTrue(t.shader.commit_restore or w.renderer.publication_restore)
                    baseline, work = self.public(), b.projection_work
                    moves = len(self.runtime.moves)
                    b.follow_projection()
                    self.assertEqual(moves, len(self.runtime.moves))
                    b.project()
                    self.assertIs(work, b.projection_work)
                    self.assertEqual(baseline, self.public())
                    self.rollback_failure = False
                    t.tick()
                    self.assertFalse(t.pending_pair)
                    self.assertFalse(t.shader.commit_restore)
                    self.assertFalse(w.renderer.publication_restore)
                    self.assert_old_pair()
                    self.rebuild()

    def test_success_defers_all_caches_until_both_surfaces_accept_one_snapshot(self):
        state = self.candidate()
        self.tracker.after_build.add(self.tracker.index((2, 1, 1)))
        self.pump()
        t, w = self.tracker, self.water
        self.assertFalse(t.failed)
        self.assertTrue(all(self.observed))
        self.assertTrue(any(kind == 'selector' for kind, key in self.events))
        self.assertTrue(any(kind == 'liquid' for kind, key in self.events))
        self.assertEqual(bytes(state), bytes(t.rendered))
        self.assertEqual(bytes(state), bytes(w.occupied))
        state[:] = bytearray(len(state))
        self.assertNotEqual(bytes(state), bytes(w.occupied))
        self.assertEqual(1, t.commits)
        self.assertEqual({t.index((2, 1, 1))}, t.changed)
        self.assertFalse(t.after_build)
        self.assertFalse(t.pending_pair)
        self.assertFalse(w.renderer.staging)
        self.assertEqual(3, len(w.renderer.active))
        self.assertTrue(all(not self.runtime.liquid_models.hidden(record['model_id'])
                            for record in w.renderer.active.values()))

    def test_retired_budget_blocks_next_candidate_without_changing_committed_pair(self):
        self.water.renderer.max_groups = 3
        self.runtime.liquid_models.remove_ok = False
        self.candidate()
        self.pump()
        self.assertEqual(3, len(self.water.renderer.retired))
        self.assertEqual(6, len(self.runtime.liquid_models.models))
        self.tracker.state[:] = bytearray(len(self.tracker.state))
        self.candidate(occupied=((2, 1, 1), (6, 1, 1), (10, 1, 1)))
        self.pump()
        self.assertTrue(self.tracker.failed)
        self.assert_old_pair()
        self.assertEqual(6, len(self.runtime.liquid_models.models))
        self.assertIn('Retired', str(self.water.error))
        self.runtime.liquid_models.remove_ok = True

    def test_reused_and_empty_liquid_candidates_wait_for_explicit_pair_finalize(self):
        ids = set(self.runtime.liquid_models.models)
        self.candidate(occupied=())
        self.pump()
        self.assertEqual(ids, set(self.runtime.liquid_models.models))
        self.assertEqual(1, self.tracker.commits)
        self.candidate(occupied=tuple(self.tracker.document.blocks), model=False)
        self.pump()
        self.assertFalse(self.tracker.failed)
        self.assertTrue(self.tracker.shader.empty)
        self.assertFalse(self.water.renderer.active)
        self.assertFalse(self.runtime.liquid_models.models)
        self.assertEqual(bytes(self.tracker.rendered), bytes(self.water.occupied))

    def test_manual_rebuild_stop_and_stale_tracker_cancel_owned_preparations(self):
        for action in ('rebuild', 'stop', 'dimension'):
            with self.subTest(action=action):
                self.rebuild()
                self.candidate()
                old_tracker, old_water = self.tracker, self.water
                old_water.renderer.SETTLE_SECONDS = 60.
                self.bridge.update_projection_occupancy()
                self.assertTrue(old_water.renderer.staging)
                if action == 'rebuild':
                    self.rebuild()
                elif action == 'dimension':
                    self.bridge.dimension_changed(None)
                    self.drain()
                else:
                    self.bridge.stop_projection()
                    self.drain()
                self.assertTrue(old_water.closed)
                ids = set(self.runtime.liquid_models.models)
                self.assertFalse(old_tracker.replace(old_tracker.shader.names[1], old_tracker.anchor))
                self.assertEqual(ids, set(self.runtime.liquid_models.models))
                self.assertFalse(old_water.renderer.staging)
                if action != 'rebuild':
                    self.assertFalse(ids)

    def test_changes_during_settling_remain_after_build_without_mutating_source(self):
        state = self.candidate()
        self.water.renderer.SETTLE_SECONDS = 60.
        self.bridge.update_projection_occupancy()
        self.assertTrue(self.tracker.pending_pair)
        t = self.tracker
        reversal, added = t.index((1, 1, 1)), t.index((2, 1, 1))
        t.observe(reversal, 1)
        t.observe(added, 2)
        self.assertEqual({reversal, added}, t.after_build)
        self.water.renderer.SETTLE_SECONDS = 0.
        self.pump()
        self.assertEqual(bytes(state), bytes(t.rendered))
        self.assertEqual(bytes(state), bytes(self.water.occupied))
        self.assertEqual({reversal, added}, t.changed)
        self.assertEqual(1, t.state[reversal])
        self.assertEqual(2, t.state[added])
        self.assertEqual(material('water'), self.water.document.get_layer((1, 1, 1), 1))
        self.assertEqual(material('water'), self.sources[-1][0].get_layer((1, 1, 1), 1))

    def test_superseded_ready_liquid_candidate_never_publishes_stale_body_snapshot(self):
        self.candidate()
        self.water.renderer.SETTLE_SECONDS = 60.
        self.bridge.update_projection_occupancy()
        revision = self.tracker.pending_pair['revision']
        newer = bytearray(self.tracker.document.volume)
        self.water.request(occupied=newer, deferred=True)
        self.assertNotEqual(revision, self.water.revision)
        self.water.renderer.SETTLE_SECONDS = 0.
        self.pump()
        self.assertTrue(self.tracker.failed)
        self.assert_old_pair()
        for unused in range(10):
            self.bridge.update_projection_occupancy()
        self.assertEqual(self.baseline, self.public())
        self.assertTrue(self.water.deferred)
        self.assertTrue(self.water.ready)
        self.assertTrue(all(self.runtime.liquid_models.hidden(record['model_id'])
                            for record in self.water.renderer.staging.values()))

    def test_opacity_during_preparation_updates_pair_without_rebuilding_shapes(self):
        self.candidate()
        self.water.renderer.SETTLE_SECONDS = 60.
        self.bridge.update_projection_occupancy()
        requests = len(self.sources)
        models = set(self.runtime.liquid_models.models)
        self.bridge.session.opacity = .7
        self.bridge.update_projection_opacity()
        self.bridge.update_projection_occupancy()
        self.assertEqual(requests, len(self.sources))
        self.assertEqual(models, set(self.runtime.liquid_models.models))
        self.water.renderer.SETTLE_SECONDS = 0.
        self.baseline = None
        self.pump()
        self.assertFalse(self.tracker.failed)
        self.assertEqual(.7, self.tracker.shader.uniforms[4][3])
        self.assertTrue(all(record['group'].uniforms[3][3] == .7
                            for record in self.water.renderer.active.values()))
        self.assertEqual(bytes(self.tracker.rendered), bytes(self.water.occupied))

    def test_opacity_and_retirement_do_not_bypass_failed_pair_recovery(self):
        self.candidate()
        self.failure = 'liquid', 1, 'exception'
        self.rollback_failure = 'exception'
        self.pump()
        t, w, b, r = self.tracker, self.water, self.bridge, self.runtime
        self.assertTrue(t.pending_pair)
        self.assertTrue(w.renderer.publication_restore)
        uniforms = dict(t.shader.uniforms)
        b.session.opacity = .2
        b.update_projection_opacity()
        self.assertEqual(uniforms, t.shader.uniforms)
        r.liquid_models.remove_ok = False
        original = r.DestroyClientEntity
        def fail_destroy(entity):
            if entity == t.entity:
                raise RuntimeError('actor destruction remains unconfirmed')
            return original(entity)
        r.DestroyClientEntity = fail_destroy
        b.stop_projection()
        self.assertTrue(w.closed)
        self.assertFalse(w.renderer.publication_restore)
        self.assertFalse(t.shader.commit_restore)
        self.assertIn(t.entity, b.projection_retired_entities)
        self.assertIn(w, b.projection_retired_liquids)
        self.assertFalse(t.active())
        self.rollback_failure = False
        r.liquid_models.remove_ok = True
        r.DestroyClientEntity = original
        b.stop_projection()
        self.assertFalse(b.projection_retired_entities)
        self.assertFalse(b.projection_retired_liquids)
        self.assertFalse(r.liquid_models.models)

    def test_initially_empty_occupancy_late_actor_stays_hidden_until_paired_ready(self):
        b, r = self.bridge, self.runtime
        b.stop_projection()
        for pos, value in b.session.editor.document.blocks.items():
            r.world[tuple((10, 64, 20)[i]+pos[i] for i in range(3))] = value
        self.rebuild()
        t, w = self.tracker, self.water
        self.assertIsNone(t.entity)
        self.assertIsNone(t.shader.render)
        self.assertFalse(w.renderer.active)
        t.state[:] = bytearray(len(t.state))
        t.snapshot = t.state[:]
        t.changed.add(t.index((1, 1, 1)))
        from projection.large_preview import SurfacePalette
        t.output = SurfacePalette(t.size)
        for pos, value in t.document.blocks.items():
            t.output.add(pos, value)
        t.submit()
        self.assertIs(t.shader, b.projection_entity_shaders[t.entity])
        w.renderer.SETTLE_SECONDS = 60.
        self.drain()
        b.update_projection_occupancy()
        self.assertIsNone(t.model)
        self.assertIsNone(b.projection_mesh)
        self.assertTrue(all(r.liquid_models.hidden(record['model_id'])
                            for record in w.renderer.staging.values()))
        self.assertIsNone(t.shader.render)
        w.renderer.SETTLE_SECONDS = 0.
        self.baseline = None
        self.pump()
        self.assertFalse(t.failed)
        self.assertIsNotNone(t.model)
        self.assertIs(t.shader, b.projection_shader)
        self.assertGreater(t.shader.uniforms[4][2], 0.)
        self.assertEqual(bytes(t.rendered), bytes(w.occupied))

    def test_planning_cancellation_and_empty_place_remove_burst_do_not_publish(self):
        self.candidate()
        self.water.BUILD_SECONDS = 0.
        self.bridge.update_projection_occupancy()
        self.assertIsNotNone(self.water.iterator)
        self.assertFalse(self.water.renderer.staging)
        old_water = self.water
        self.bridge.stop_projection()
        self.assertTrue(old_water.closed)
        self.assertIsNone(old_water.iterator)
        self.assertFalse(self.runtime.liquid_models.models)
        self.runtime.world.clear()
        self.rebuild()
        t = self.tracker
        t.snapshot = t.state[:]
        t.after_build.add(t.index((1, 1, 1)))
        t.output = None
        before = self.public()
        t.submit()
        self.assertEqual(before, self.public())
        self.assertIsNone(t.snapshot)
        self.assertFalse(t.after_build)

    def test_new_overlay_attachment_is_hidden_even_when_attachment_mutates_then_raises(self):
        self.candidate()
        t, b, r = self.tracker, self.bridge, self.runtime
        name = t.shader.names[1-t.shader.bank]+'_new_overlay'
        b.context_models[t.shader.names[1-t.shader.bank]] = ((name, (2, 0, 0), False),)
        attach = r.AddActorBlockGeometry
        def partial(part, *args):
            result = attach(part, *args)
            self.visibility[t.entity, part] = True
            if part == name:
                raise RuntimeError('attachment mutated visibility before refusing')
            return result
        with patch.object(r, 'AddActorBlockGeometry', partial):
            self.pump()
        self.assertTrue(t.failed)
        self.assert_old_pair()
        self.assertFalse(self.visibility[t.entity, name])
        self.assertIn(name, t.shader.owned_parts)
        self.assertNotIn(name, t.shader.parts[1-t.shader.bank])

    def test_new_overlay_has_explicit_hidden_prepare_before_visible_pair_switch(self):
        self.candidate()
        t, b, r = self.tracker, self.bridge, self.runtime
        name = t.shader.names[1-t.shader.bank]+'_new_overlay'
        b.context_models[t.shader.names[1-t.shader.bank]] = ((name, (2, 0, 0), False),)
        attach = r.AddActorBlockGeometry
        calls = []
        visible = r.SetActorBlockGeometryVisible
        def native_visible(part, shown):
            if part == name:
                calls.append(shown)
            return visible(part, shown)
        def native_attach(part, *args):
            self.visibility[t.entity, part] = True
            return attach(part, *args)
        with patch.object(r, 'AddActorBlockGeometry', native_attach), patch.object(
                r, 'SetActorBlockGeometryVisible', native_visible):
            self.pump()
        self.assertFalse(t.failed)
        self.assertEqual([False, True], calls)
        self.assertTrue(self.visibility[t.entity, name])
        self.assertTrue(all(self.observed))

    def test_cancelled_late_actor_timer_cannot_revive_discarded_pending_snapshot(self):
        b, r = self.bridge, self.runtime
        b.stop_projection()
        for pos, value in b.session.editor.document.blocks.items():
            r.world[tuple((10, 64, 20)[i]+pos[i] for i in range(3))] = value
        self.rebuild()
        t = self.tracker
        t.changed.add(t.index((1, 1, 1)))
        t.snapshot = bytearray(t.document.volume)
        from projection.large_preview import SurfacePalette
        t.output = SurfacePalette(t.size)
        for pos, value in t.document.blocks.items():
            t.output.add(pos, value)
        t.submit()
        self.assertTrue(t.attaching)
        callbacks = list(r.timers)
        r.timers[:] = []
        self.assertTrue(t.cancel_pending())
        for callback in callbacks:
            callback()
        self.assertFalse(t.attaching)
        self.assertIsNone(t.pending_model)
        self.assertIsNone(t.snapshot)
        self.assertIsNone(t.shader.render)
        self.assertFalse(self.water.renderer.active)

    def test_manual_generation_liquid_publish_refusal_preserves_old_pair_and_owners(self):
        old = self.public()
        old_entity = self.bridge.entity
        old_liquid = self.water
        old_ids = set(self.runtime.liquid_models.models)
        models = self.runtime.liquid_models
        uniform = models.SetExtraUniformValue
        rejected = []
        def mutated(model_id, slot, value):
            result = uniform(model_id, slot, value)
            if model_id not in old_ids and slot == 4 and value[3] > 0. and not rejected:
                rejected.append(model_id)
                raise RuntimeError('manual staged publish mutated before exception')
            return result
        with patch.object(models, 'SetExtraUniformValue', mutated):
            self.bridge.project_large((30, 64, 20))
            self.drain()
        self.assertTrue(rejected)
        self.assertIsNotNone(self.bridge.projection_work.error)
        self.assertEqual(old, self.public())
        self.assertEqual(old_entity, self.bridge.entity)
        self.assertIs(old_liquid, self.bridge.projection_liquid)
        self.assertEqual(old_ids, set(models.models))
        self.assertTrue(all(not models.hidden(model_id) for model_id in old_ids))

    def test_manual_finalize_publishes_complete_new_descriptors_before_retirement_calls(self):
        old_entity = self.bridge.entity
        old_ids = set(self.runtime.liquid_models.models)
        observed = []
        destroy = self.runtime.DestroyClientEntity
        remove = self.runtime.liquid_models.RemoveFreeModel
        def observer():
            b = self.bridge
            observed.append(b.entity != old_entity and b.projection_work.ready and
                            b.projection_shader is b.projection_work.shader and
                            b.projection_occupancy is b.projection_work.occupancy and
                            b.projection_liquid is b.projection_work.liquid)
        def destroyed(entity):
            if entity == old_entity:
                observer()
            return destroy(entity)
        def removed(model_id):
            if model_id in old_ids:
                observer()
            return remove(model_id)
        with patch.object(self.runtime, 'DestroyClientEntity', destroyed), patch.object(
                self.runtime.liquid_models, 'RemoveFreeModel', removed):
            self.bridge.project_large((30, 64, 20))
            self.drain()
        self.assertTrue(observed)
        self.assertTrue(all(observed))
        self.assertTrue(self.bridge.projection_work.ready)

    def test_standalone_liquid_opacity_rollback_gates_controls_without_pending_pair(self):
        for missing in (True, False):
            for mode in ('false', 'exception'):
                with self.subTest(missing=missing, mode=mode):
                    self.bridge.session.projection_missing = missing
                    self.bridge.session.opacity = .4
                    self.rebuild()
                    b, r, w = self.bridge, self.runtime, self.water
                    b.follow_projection()
                    uniforms = dict(b.projection_shader.uniforms)
                    active = tuple(w.renderer.active.values())
                    before = dict((record['model_id'], record['group'].uniforms[3]) for record in active)
                    native = r.liquid_models.SetExtraUniformValue
                    refused = active[1]['model_id']
                    recovery = [False]
                    def mutated(model_id, slot, value):
                        result = native(model_id, slot, value)
                        if model_id == refused and slot == 4 and not recovery[0]:
                            if mode == 'exception':
                                raise RuntimeError('standalone opacity mutated before failure')
                            return False
                        return result
                    b.session.opacity = .2
                    with patch.object(r.liquid_models, 'SetExtraUniformValue', mutated):
                        w.advance()
                        self.assertIsNotNone(w.error)
                        self.assertTrue(w.renderer.publication_restore)
                        if b.projection_occupancy is not None:
                            self.assertIsNone(b.projection_occupancy.pending_pair)
                        moves = len(r.moves)
                        work = b.projection_work
                        b.follow_projection()
                        b.update_projection_opacity()
                        with self.assertRaisesRegex(ValueError, 'restore projection publication'):
                            b.update_biome_tint('swampland')
                        b.project()
                        self.assertEqual(moves, len(r.moves))
                        self.assertIs(work, b.projection_work)
                        self.assertEqual(uniforms, b.projection_shader.uniforms)
                        recovery[0] = True
                        b.update_projection_occupancy()
                        self.assertTrue(b.restore_projection_publication())
                    self.assertFalse(w.renderer.publication_restore)
                    self.assertTrue(all(r.liquid_models.models[model_id]['uniforms'][4] == value
                                        for model_id, value in before.items()))
                    self.rebuild()


if __name__ == '__main__':
    unittest.main()
