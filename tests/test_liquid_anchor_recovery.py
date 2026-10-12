"""Attempted free-model moves restore before anchor caches can publish."""
import contextlib
import io
import unittest

from test_liquid_render import ANCHOR, Runtime, group
from projection.liquid_render import WorldLiquidRenderer


TARGET = (20., 74., 30.)
CORRUPT = (900., 900., 900.)


class PositionRuntime(Runtime):
    def __init__(self):
        super().__init__()
        self.outcomes, self.position_calls = {}, []
        self.observer = lambda: None

    def SetFreeModelPos(self, model, x, y, z):
        value = x, y, z
        outcomes = self.outcomes.get(model, [])
        result = outcomes.pop(0) if outcomes else True
        outcome, actual = result if isinstance(result, tuple) else (result, value)
        self.position_calls.append((model, value, self.observer()))
        self.positions[model] = actual
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class LiquidAnchorRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.runtime = PositionRuntime()
        self.renderer = WorldLiquidRenderer(self.runtime, 4, 0, (1.,) * 3, (0., 180., 0.))
        self.errors = io.StringIO()
        self.stderr = contextlib.redirect_stderr(self.errors)
        self.stderr.__enter__()
        self.addCleanup(self.stderr.__exit__, None, None, None)

    def settle(self, groups, now):
        self.assertTrue(self.renderer.begin(groups, ANCHOR, now))
        for delay in (.19, .21, .24, .27, .31):
            ready = self.renderer.advance(now + delay)
        self.assertTrue(ready)

    def records(self):
        return tuple(self.renderer.active.values()) + tuple(self.renderer.staging.values())

    def prepare(self):
        groups = tuple(group(key)._replace(origin=(key * 4, 0, key * 4)) for key in range(4))
        self.settle(groups[:3], 0.)
        self.assertTrue(self.renderer.begin(groups,
                                            ANCHOR, 1., deferred=True))
        self.assertFalse(self.renderer.advance(1.01))
        self.runtime.position_calls[:] = []
        self.runtime.observer = lambda: (self.renderer.anchor,
            tuple((record['model_id'], record['anchor']) for record in self.records()))
        return dict(self.runtime.positions)

    def test_first_middle_last_mutating_failure_restores_failed_record_and_all_caches(self):
        for index in (0, 1, 3):
            for failure in (False, RuntimeError('Native liquid position failure')):
                with self.subTest(index=index, failure=failure):
                    self.setUp()
                    previous = self.prepare()
                    records = self.records()
                    identity = records[index]['model_id']
                    old_ownership = (dict(self.renderer.active), dict(self.renderer.staging),
                                     dict(self.renderer.retired))
                    baseline = self.runtime.observer()
                    self.runtime.outcomes[identity] = [failure]
                    self.assertFalse(self.renderer.follow(TARGET))
                    self.assertEqual(previous, self.runtime.positions)
                    self.assertEqual(baseline, self.runtime.observer())
                    self.assertTrue(all(call[2] == baseline for call in self.runtime.position_calls))
                    self.assertEqual([], self.renderer.position_restore)
                    self.assertEqual(old_ownership, (self.renderer.active, self.renderer.staging,
                                                     self.renderer.retired))
                    identities = [call[0] for call in self.runtime.position_calls]
                    attempted = [record['model_id'] for record in records[:index + 1]]
                    self.assertEqual(attempted + list(reversed(attempted)), identities)
                    self.assertIn('position', self.errors.getvalue())
                    self.runtime.position_calls[:] = []
                    self.assertTrue(self.renderer.follow(TARGET))
                    self.assertTrue(all(call[2] == baseline for call in self.runtime.position_calls))
                    self.assertEqual(TARGET, self.renderer.anchor)
                    self.assertTrue(all(record['anchor'] == TARGET for record in records))

    def test_failed_restore_retains_attempts_and_stationary_follow_forces_recovery(self):
        previous = self.prepare()
        records = self.records()
        first, failed = records[0]['model_id'], records[2]['model_id']
        baseline = self.runtime.observer()
        self.runtime.outcomes[first] = [True, (RuntimeError('Native rollback failure'), CORRUPT)]
        self.runtime.outcomes[failed] = [False, (False, CORRUPT)]
        self.assertFalse(self.renderer.follow(TARGET))
        self.assertEqual(set((first, failed)),
                         set(record['model_id'] for record, anchor in self.renderer.position_restore))
        self.assertEqual(baseline, self.runtime.observer())
        self.runtime.outcomes[failed] = [(False, CORRUPT)]
        self.runtime.position_calls[:] = []
        self.assertFalse(self.renderer.follow(ANCHOR))
        self.assertEqual(set((first, failed)), set(call[0] for call in self.runtime.position_calls))
        self.assertEqual([failed], [record['model_id'] for record, anchor
                                    in self.renderer.position_restore])
        self.assertEqual(baseline, self.runtime.observer())
        self.runtime.position_calls[:] = []
        self.assertTrue(self.renderer.follow(ANCHOR))
        self.assertEqual([failed], [call[0] for call in self.runtime.position_calls])
        self.assertEqual(previous, self.runtime.positions)
        self.assertEqual([], self.renderer.position_restore)
        self.assertIsNone(self.renderer.error)
        self.assertIn('position', self.errors.getvalue())

    def test_pending_position_restore_gates_controls_publication_cancel_and_new_begin(self):
        for operation in ('visible', 'opacity', 'publication', 'cancel', 'advance', 'begin', 'shared'):
            with self.subTest(operation=operation):
                self.setUp()
                previous = self.prepare()
                self.assertFalse(self.renderer.advance(1.1))
                self.assertTrue(self.renderer.advance(1.11))
                failed = self.records()[1]['model_id']
                self.runtime.outcomes[failed] = [False, (False, CORRUPT)]
                self.assertFalse(self.renderer.follow(TARGET))
                baseline = self.runtime.observer()
                old_ownership = (dict(self.renderer.active), dict(self.renderer.staging),
                                 dict(self.renderer.retired))
                uniforms = list(self.runtime.uniform_calls)
                serial = self.runtime.serial
                self.runtime.outcomes[failed] = [(False, CORRUPT)]
                self.runtime.position_calls[:] = []
                operations = {'visible': lambda: self.renderer.set_visible(False),
                              'opacity': lambda: self.renderer.set_opacity(.25),
                              'publication': lambda: self.renderer.prepare_publication(),
                              'cancel': self.renderer.cancel_preparation,
                              'advance': lambda: self.renderer.advance(1.2),
                              'begin': lambda: self.renderer.begin((group(9),), TARGET, 1.2),
                              'shared': self.renderer.restore_publication}
                self.assertFalse(operations[operation]())
                self.assertEqual([failed], [call[0] for call in self.runtime.position_calls])
                self.assertEqual(old_ownership, (self.renderer.active, self.renderer.staging,
                                                 self.renderer.retired))
                self.assertEqual(uniforms, self.runtime.uniform_calls)
                self.assertEqual(serial, self.runtime.serial)
                self.assertEqual(baseline, self.runtime.observer())
                self.assertTrue(self.renderer.position_restore)
                self.assertTrue(self.renderer.restore_publication())
                self.assertEqual(previous, self.runtime.positions)
                self.assertFalse(self.renderer.position_restore)

    def test_stationary_advance_restores_position_before_ready_and_does_not_publish_anchor(self):
        previous = self.prepare()
        self.assertFalse(self.renderer.advance(1.1))
        self.assertTrue(self.renderer.advance(1.11))
        failed = self.records()[1]['model_id']
        self.runtime.outcomes[failed] = [False, (False, CORRUPT)]
        self.assertFalse(self.renderer.follow(TARGET))
        baseline = self.runtime.observer()
        self.runtime.position_calls[:] = []
        self.assertTrue(self.renderer.advance(1.2))
        self.assertEqual([failed], [call[0] for call in self.runtime.position_calls])
        self.assertEqual(previous, self.runtime.positions)
        self.assertEqual(baseline, self.runtime.observer())
        self.assertIsNone(self.renderer.error)
        self.assertFalse(self.renderer.position_restore)

    def test_shared_recovery_retries_visibility_and_position_independently(self):
        previous = self.prepare()
        failed = self.records()[1]
        self.runtime.outcomes[failed['model_id']] = [False, (False, CORRUPT)]
        self.assertFalse(self.renderer.follow(TARGET))
        payload = failed['group'].uniforms[3]
        self.renderer.publication_restore = [(failed, payload)]
        self.runtime.uniforms_ok = False
        self.runtime.position_calls[:] = []
        self.assertFalse(self.renderer.restore_publication())
        self.assertEqual(previous, self.runtime.positions)
        self.assertFalse(self.renderer.position_restore)
        self.assertTrue(self.renderer.publication_restore)
        self.runtime.uniforms_ok = True
        self.assertTrue(self.renderer.restore_publication())
        self.assertFalse(self.renderer.publication_restore)

    def test_close_retains_unconfirmed_removal_and_second_close_releases_without_position_replay(self):
        self.prepare()
        failed = self.records()[1]['model_id']
        self.runtime.outcomes[failed] = [False, (False, CORRUPT)]
        self.assertFalse(self.renderer.follow(TARGET))
        live = set(self.runtime.models)
        removed = self.runtime.RemoveFreeModel
        self.runtime.RemoveFreeModel = lambda identity: False if identity == failed else removed(identity)
        self.runtime.position_calls[:] = []
        self.assertFalse(self.renderer.close())
        self.assertEqual({failed}, set(self.runtime.models))
        self.assertEqual({failed}, set(self.renderer.retired))
        self.assertEqual(live - {failed}, set(self.runtime.removed))
        self.assertEqual([failed], [record['model_id'] for record, anchor
                                    in self.renderer.position_restore])
        self.assertEqual({}, self.renderer.active)
        self.assertEqual({}, self.renderer.staging)
        self.assertFalse(self.renderer.follow(ANCHOR))
        self.assertEqual([], self.runtime.position_calls)
        self.runtime.RemoveFreeModel = removed
        self.assertTrue(self.renderer.close())
        self.assertEqual({}, self.runtime.models)
        self.assertEqual({}, self.renderer.retired)
        self.assertFalse(self.renderer.position_restore)
        self.assertEqual([], self.runtime.position_calls)
        self.assertTrue(self.renderer.close())

    def test_retired_records_never_move_and_keep_existing_allocation_ownership(self):
        self.settle((group(0), group(1)), 0.)
        old = self.renderer.active[1]
        self.runtime.RemoveFreeModel = lambda identity: False
        self.settle((group(0), group(1, .3)), 1.)
        self.assertEqual({old['model_id']}, set(self.renderer.retired))
        self.runtime.position_calls[:] = []
        baseline = dict(self.renderer.retired)
        self.assertTrue(self.renderer.follow(TARGET))
        self.assertNotIn(old['model_id'], [call[0] for call in self.runtime.position_calls])
        self.assertEqual(ANCHOR, old['anchor'])
        self.assertEqual(baseline, self.renderer.retired)
