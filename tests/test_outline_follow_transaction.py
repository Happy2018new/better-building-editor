"""Actual rainbow outline recovery under mutating native setter failures."""
import types
import unittest
from unittest.mock import patch

from test_projection_follow_transaction import NativeTransforms, bridge_fixture, OLD, TARGET, CORRUPT
from modern_projection.projection.projection_outline import ProjectionOutline


BOUNDS = ((20, 50, -10), (6, 8, 10))
CENTRE = (23., 54., -5.)
OUTLINE_OLD = (1., 66., 6.)
OUTLINE_TARGET = (8., 70., -2.)
BAD_UNIFORM = CORRUPT + (1.,)


def correction(position):
    return tuple(CENTRE[i]-position[i] for i in range(3)) + (1.,)


def outline_fixture(current=OUTLINE_OLD):
    runtime = NativeTransforms()
    bridge = types.SimpleNamespace(factory=runtime, system=types.SimpleNamespace(
        DestroyClientEntity=lambda entity: runtime.positions.pop(entity, None)))
    outline = ProjectionOutline(bridge)
    outline.entity = 'outline'
    outline.style = 'rainbow'
    outline.bounds = BOUNDS
    outline.render_position = current
    outline._follow_uniform = correction(current) if current is not None else (1., 1., 1., 1.)
    runtime.positions['outline'] = current if current is not None else CENTRE
    runtime.uniforms['outline', 2] = outline._follow_uniform
    runtime.observer = lambda: outline.render_position
    return outline, runtime


def actual_outline_bridge_fixture():
    bridge, runtime = bridge_fixture()
    outline = ProjectionOutline(bridge)
    outline.entity = 'outline'
    outline.style = 'rainbow'
    outline.bounds = BOUNDS
    outline.render_position = OUTLINE_OLD
    outline._follow_uniform = correction(OUTLINE_OLD)
    runtime.positions['outline'] = OUTLINE_OLD
    runtime.uniforms['outline', 2] = outline._follow_uniform
    bridge.projection_outline = outline
    runtime.observer = lambda: (bridge.projection_mesh[3], bridge.projection_shader.anchor,
                               outline.render_position)
    return bridge, runtime


class OutlineFollowTransactionTests(unittest.TestCase):
    def setUp(self):
        self.log = patch('traceback.print_exc')
        self.log.start()
        self.addCleanup(self.log.stop)

    def test_position_refusal_or_exception_after_mutation_restores_before_uniform_write(self):
        for failure in (False, ValueError('outline position failure')):
            with self.subTest(failure=failure):
                outline, runtime = outline_fixture()
                runtime.outcomes['position', 'outline', None] = [failure]
                self.assertFalse(outline.follow(OUTLINE_TARGET))
                self.assertEqual(OUTLINE_OLD, runtime.positions['outline'])
                self.assertEqual(correction(OUTLINE_OLD), runtime.uniforms['outline', 2])
                self.assertEqual(OUTLINE_OLD, outline.render_position)
                self.assertEqual(['position', 'position'], [call[0] for call in runtime.calls])
                self.assertIsNone(outline._follow_restore)
                self.assertTrue(outline.follow(OUTLINE_TARGET))
                self.assertEqual(OUTLINE_TARGET, outline.render_position)

    def test_uniform_refusal_or_exception_after_mutation_rolls_back_uniform_and_position(self):
        for failure in (False, RuntimeError('outline uniform failure')):
            with self.subTest(failure=failure):
                outline, runtime = outline_fixture()
                runtime.outcomes['uniform', 'outline', 2] = [failure]
                self.assertFalse(outline.follow(OUTLINE_TARGET))
                self.assertEqual(OUTLINE_OLD, runtime.positions['outline'])
                self.assertEqual(correction(OUTLINE_OLD), runtime.uniforms['outline', 2])
                self.assertEqual(OUTLINE_OLD, outline.render_position)
                self.assertEqual(correction(OUTLINE_OLD), outline._follow_uniform)
                self.assertEqual(['position', 'uniform', 'uniform', 'position'],
                                 [call[0] for call in runtime.calls])
                self.assertTrue(all(call[4] == OUTLINE_OLD for call in runtime.calls))
                self.assertIsNone(outline._follow_restore)

    def test_first_follow_failure_restores_creation_centre_and_documented_default_uniform(self):
        for kind in ('position', 'uniform'):
            with self.subTest(kind=kind):
                outline, runtime = outline_fixture(current=None)
                runtime.outcomes[kind, 'outline', None if kind == 'position' else 2] = [False]
                self.assertFalse(outline.follow(OUTLINE_TARGET))
                self.assertEqual(CENTRE, runtime.positions['outline'])
                self.assertEqual((1., 1., 1., 1.), runtime.uniforms['outline', 2])
                self.assertIsNone(outline.render_position)
                self.assertIsNone(outline._follow_restore)
                self.assertTrue(outline.follow(OUTLINE_TARGET))

    def test_hot_reload_instance_without_new_fields_recovers_its_committed_correction(self):
        outline, runtime = outline_fixture()
        del outline._follow_restore
        del outline._follow_uniform
        runtime.outcomes['uniform', 'outline', 2] = [False]
        self.assertFalse(outline.follow(OUTLINE_TARGET))
        self.assertEqual(OUTLINE_OLD, runtime.positions['outline'])
        self.assertEqual(correction(OUTLINE_OLD), runtime.uniforms['outline', 2])
        self.assertEqual(OUTLINE_OLD, outline.render_position)
        self.assertIsNone(outline._follow_restore)

    def test_failed_uniform_and_position_rollbacks_are_retained_and_stationary_follow_repairs_both(self):
        outline, runtime = outline_fixture()
        runtime.outcomes['position', 'outline', None] = [True, (RuntimeError('position rollback'), CORRUPT)]
        runtime.outcomes['uniform', 'outline', 2] = [False, (False, BAD_UNIFORM)]
        self.assertFalse(outline.follow(OUTLINE_TARGET))
        self.assertEqual(OUTLINE_OLD, outline.render_position)
        self.assertEqual(OUTLINE_OLD, outline._follow_restore['position'])
        self.assertEqual(correction(OUTLINE_OLD), outline._follow_restore['uniform'])
        runtime.calls[:] = []
        self.assertTrue(outline.follow(OUTLINE_OLD))
        self.assertEqual(['uniform', 'position'], [call[0] for call in runtime.calls])
        self.assertEqual(OUTLINE_OLD, runtime.positions['outline'])
        self.assertEqual(correction(OUTLINE_OLD), runtime.uniforms['outline', 2])
        self.assertIsNone(outline._follow_restore)
        runtime.calls[:] = []
        self.assertTrue(outline.follow(OUTLINE_OLD))
        self.assertEqual([], runtime.calls)

    def test_unresolved_rollback_blocks_new_move_and_configuration_until_next_retry(self):
        outline, runtime = outline_fixture()
        runtime.outcomes['uniform', 'outline', 2] = [False, (False, BAD_UNIFORM),
                                                   (False, BAD_UNIFORM), (False, BAD_UNIFORM)]
        self.assertFalse(outline.follow(OUTLINE_TARGET))
        self.assertIsNone(outline._follow_restore['position'])
        runtime.calls[:] = []
        self.assertFalse(outline.follow(OUTLINE_TARGET))
        self.assertFalse(outline.configure('outline'))
        self.assertEqual(['uniform', 'uniform'], [call[0] for call in runtime.calls])
        self.assertEqual(OUTLINE_OLD, runtime.positions['outline'])
        self.assertEqual(OUTLINE_OLD, outline.render_position)
        self.assertTrue(outline.follow(OUTLINE_TARGET))
        self.assertEqual(OUTLINE_TARGET, runtime.positions['outline'])
        self.assertEqual(correction(OUTLINE_TARGET), runtime.uniforms['outline', 2])

    def test_initial_configuration_establishes_disabled_correction_for_exact_first_rollback(self):
        outline, runtime = outline_fixture(current=None)
        outline.bridge.session = types.SimpleNamespace(reduced_motion=False,
            outline_options={'rainbow': {'speed': 1., 'brightness': 1., 'width': 1.}})
        runtime.CreateModel = lambda entity: types.SimpleNamespace(SetEntityShadowShow=lambda value: True)
        self.assertTrue(outline.configure('outline'))
        self.assertEqual((0., 0., 0., 0.), outline._follow_uniform)
        runtime.outcomes['uniform', 'outline', 2] = [False]
        self.assertFalse(outline.follow(OUTLINE_TARGET))
        self.assertEqual(CENTRE, runtime.positions['outline'])
        self.assertEqual((0., 0., 0., 0.), runtime.uniforms['outline', 2])
        self.assertIsNone(outline.render_position)

    def test_initial_configuration_mutating_refusal_or_exception_restores_uniform_before_follow(self):
        for failure in (False, RuntimeError('configure correction failure')):
            with self.subTest(failure=failure):
                outline, runtime = outline_fixture(current=None)
                outline.bridge.session = types.SimpleNamespace(reduced_motion=False,
                    outline_options={'rainbow': {'speed': 1., 'brightness': 1., 'width': 1.}})
                runtime.CreateModel = lambda entity: types.SimpleNamespace(SetEntityShadowShow=lambda value: True)
                runtime.outcomes['uniform', 'outline', 2] = [failure]
                self.assertFalse(outline.configure('outline'))
                self.assertEqual((1., 1., 1., 1.), outline._follow_uniform)
                self.assertEqual(outline._follow_uniform, runtime.uniforms['outline', 2])
                self.assertIsNone(outline._follow_restore)
                runtime.outcomes['uniform', 'outline', 2] = [False]
                self.assertFalse(outline.follow(OUTLINE_TARGET))
                self.assertEqual(CENTRE, runtime.positions['outline'])
                self.assertEqual(outline._follow_uniform, runtime.uniforms['outline', 2])

    def test_initial_configuration_failed_rollback_is_retained_and_blocks_follow_until_recovery(self):
        outline, runtime = outline_fixture(current=None)
        outline.bridge.session = types.SimpleNamespace(reduced_motion=False,
            outline_options={'rainbow': {'speed': 1., 'brightness': 1., 'width': 1.}})
        runtime.CreateModel = lambda entity: types.SimpleNamespace(SetEntityShadowShow=lambda value: True)
        runtime.outcomes['uniform', 'outline', 2] = [False, (False, BAD_UNIFORM), (False, BAD_UNIFORM)]
        self.assertFalse(outline.configure('outline'))
        self.assertIsNotNone(outline._follow_restore)
        runtime.calls[:] = []
        self.assertFalse(outline.follow(OUTLINE_TARGET))
        self.assertEqual(['uniform'], [call[0] for call in runtime.calls])
        self.assertEqual(CENTRE, runtime.positions['outline'])
        self.assertIsNone(outline.render_position)
        self.assertTrue(outline.follow(OUTLINE_TARGET))
        self.assertIsNone(outline._follow_restore)
        self.assertEqual(OUTLINE_TARGET, outline.render_position)

    def test_failed_hide_preserves_recovery_and_successful_hide_clears_owned_state(self):
        outline, runtime = outline_fixture()
        runtime.outcomes['position', 'outline', None] = [False, (False, CORRUPT)]
        self.assertFalse(outline.follow(OUTLINE_TARGET))
        with patch.object(outline.bridge.system, 'DestroyClientEntity', side_effect=RuntimeError('destroy refusal')):
            with self.assertRaisesRegex(RuntimeError, 'destroy refusal'):
                outline.hide()
        self.assertEqual('outline', outline.entity)
        self.assertEqual(OUTLINE_OLD, outline.render_position)
        self.assertIsNotNone(outline._follow_restore)
        outline.hide()
        self.assertIsNone(outline.entity)
        self.assertIsNone(outline.render_position)
        self.assertIsNone(outline._follow_restore)
        self.assertNotIn('outline', runtime.positions)

    def test_changed_entity_never_receives_old_owner_recovery(self):
        outline, runtime = outline_fixture()
        runtime.outcomes['position', 'outline', None] = [False, (False, CORRUPT)]
        self.assertFalse(outline.follow(OUTLINE_TARGET))
        outline.entity = 'replacement'
        runtime.positions['replacement'] = OUTLINE_OLD
        runtime.uniforms['replacement', 2] = correction(OUTLINE_OLD)
        runtime.calls[:] = []
        self.assertTrue(outline.follow(OUTLINE_OLD))
        self.assertEqual([], runtime.calls)
        self.assertIsNone(outline._follow_restore)
        self.assertEqual(OUTLINE_OLD, runtime.positions['replacement'])


class ActualOutlineBridgeTransactionTests(unittest.TestCase):
    def setUp(self):
        self.log = patch('traceback.print_exc')
        self.log.start()
        self.addCleanup(self.log.stop)

    def test_real_outline_position_or_uniform_failure_rolls_back_body_and_outline_before_retry(self):
        for kind in ('position', 'uniform'):
            for failure in (False, TypeError('outline setter exception')):
                with self.subTest(kind=kind, failure=failure):
                    bridge, runtime = actual_outline_bridge_fixture()
                    offsets, signature = dict(runtime.offsets), bridge._projection_follow_position
                    runtime.target()
                    runtime.camera_position = (OUTLINE_TARGET[0], OUTLINE_TARGET[1], OUTLINE_TARGET[2]-4.)
                    runtime.outcomes[kind, 'outline', None if kind == 'position' else 2] = [failure]
                    bridge.follow_projection()
                    self.assertEqual(OLD, bridge.projection_mesh[3])
                    self.assertEqual(OLD, bridge.projection_shader.anchor)
                    self.assertEqual(OLD, runtime.positions['mesh'])
                    self.assertEqual(offsets, runtime.offsets)
                    self.assertEqual(OUTLINE_OLD, bridge.projection_outline.render_position)
                    self.assertEqual(OUTLINE_OLD, runtime.positions['outline'])
                    self.assertEqual(correction(OUTLINE_OLD), runtime.uniforms['outline', 2])
                    self.assertEqual(signature, bridge._projection_follow_position)
                    self.assertIsNone(bridge._projection_follow_restore)
                    self.assertIsNone(bridge.projection_outline._follow_restore)
                    self.assertTrue(all(call[4] == (OLD, OLD, OUTLINE_OLD) for call in runtime.calls))
                    bridge.follow_projection()
                    self.assertEqual(TARGET, bridge.projection_mesh[3])
                    self.assertEqual(TARGET, bridge.projection_shader.anchor)
                    self.assertEqual(OUTLINE_TARGET, bridge.projection_outline.render_position)
                    self.assertEqual(correction(OUTLINE_TARGET), runtime.uniforms['outline', 2])

    def test_real_outline_rollback_failure_recovers_even_when_bridge_signature_is_stationary(self):
        bridge, runtime = actual_outline_bridge_fixture()
        offsets, signature = dict(runtime.offsets), bridge._projection_follow_position
        runtime.target()
        runtime.camera_position = (OUTLINE_TARGET[0], OUTLINE_TARGET[1], OUTLINE_TARGET[2]-4.)
        runtime.outcomes['position', 'outline', None] = [True, (False, CORRUPT)]
        runtime.outcomes['uniform', 'outline', 2] = [RuntimeError('uniform refusal'),
                                                   (RuntimeError('uniform rollback refusal'), BAD_UNIFORM)]
        bridge.follow_projection()
        self.assertEqual(OLD, bridge.projection_mesh[3])
        self.assertEqual(OLD, runtime.positions['mesh'])
        self.assertEqual(offsets, runtime.offsets)
        self.assertEqual(signature, bridge._projection_follow_position)
        self.assertIsNotNone(bridge.projection_outline._follow_restore)
        runtime.target(OLD)
        runtime.camera_position = (OUTLINE_OLD[0], OUTLINE_OLD[1], OUTLINE_OLD[2]-4.)
        runtime.calls[:] = []
        bridge.follow_projection()
        self.assertEqual([('uniform', 'outline', 2), ('position', 'outline', None)],
                         [call[:3] for call in runtime.calls])
        self.assertEqual(OUTLINE_OLD, runtime.positions['outline'])
        self.assertEqual(correction(OUTLINE_OLD), runtime.uniforms['outline', 2])
        self.assertIsNone(bridge.projection_outline._follow_restore)
        self.assertEqual(signature, bridge._projection_follow_position)
        runtime.calls[:] = []
        bridge.follow_projection()
        self.assertEqual([], runtime.calls)


if __name__ == '__main__':
    unittest.main()
