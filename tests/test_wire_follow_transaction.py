"""Golden/starry delegated transforms commit and recover as one owned set."""
import types
import unittest
from unittest.mock import patch

from test_projection_follow_transaction import NativeTransforms, bridge_fixture, OLD, TARGET, CORRUPT
from modern_projection.projection.projection_outline import ProjectionOutline
from modern_projection.projection.survey_effects import WireEffects, SurveyEffects


WIRE_OLD = (1., 66., 6.)
WIRE_TARGET = (8., 70., -2.)
CENTRE = (23., 54., -5.)
BAD_UNIFORM = CORRUPT + (1.,)


def correction(position, centre=CENTRE):
    return tuple(centre[i]-position[i] for i in range(3)) + (1.,)


def wire_fixture(style='golden', survey=False, point=False):
    runtime = NativeTransforms()
    bridge = types.SimpleNamespace(factory=runtime, system=types.SimpleNamespace(
        DestroyClientEntity=lambda entity: runtime.positions.pop(entity, None)))
    effect = SurveyEffects(bridge) if survey else WireEffects(bridge)
    effect.style = style
    effect.anchor, effect.camera = WIRE_OLD, (1., 66., 2.)
    kinds = ('guide', 'wire', 'stars', 'strike') if point else ('guide', 'wire', 'stars')
    for index, kind in enumerate(kinds):
        entity = 'wire_%d' % index
        centre = tuple(CENTRE[i]+index for i in range(3))
        record = {'id': entity, 'centre': centre, 'size': (6., 8., 10.), 'kind': kind,
                  'face': 4, 'started': 0., 'anchor': WIRE_OLD,
                  'uniforms': {2: correction(WIRE_OLD, centre)}, 'glow': None}
        runtime.positions[entity] = WIRE_OLD
        runtime.uniforms[entity, 2] = record['uniforms'][2]
        if kind == 'strike':
            effect.points[0] = record
        else:
            effect.layers.append(record)
    runtime.observer = lambda: (effect.anchor, tuple(record['anchor'] for record in effect._records()))
    return effect, runtime


def transforms(runtime):
    return [call for call in runtime.calls if call[0] == 'position' or (call[0] == 'uniform' and call[2] == 2)]


class WireFollowTransactionTests(unittest.TestCase):
    def setUp(self):
        self.log = patch('traceback.print_exc')
        self.log.start()
        self.addCleanup(self.log.stop)

    def assert_restored(self, effect, runtime):
        self.assertEqual(WIRE_OLD, effect.anchor)
        self.assertEqual((1., 66., 2.), effect.camera)
        for record in effect._records():
            self.assertEqual(WIRE_OLD, record['anchor'])
            self.assertEqual(WIRE_OLD, runtime.positions[record['id']])
            self.assertEqual(correction(WIRE_OLD, record['centre']), record['uniforms'][2])
            self.assertEqual(record['uniforms'][2], runtime.uniforms[record['id'], 2])
            self.assertNotIn('move_restore', record)

    def test_first_middle_last_mutating_refusal_or_exception_rolls_back_every_touched_layer(self):
        for style in ('golden', 'starry'):
            for entity in ('wire_0', 'wire_1', 'wire_2'):
                for kind in ('position', 'uniform'):
                    for failure in (False, RuntimeError('wire transform failure')):
                        with self.subTest(style=style, entity=entity, kind=kind, failure=failure):
                            effect, runtime = wire_fixture(style)
                            runtime.outcomes[kind, entity, None if kind == 'position' else 2] = [failure]
                            self.assertFalse(effect.follow(WIRE_TARGET, (8., 70., -6.)))
                            self.assert_restored(effect, runtime)
                            self.assertTrue(all(call[4] == (WIRE_OLD, (WIRE_OLD,)*3)
                                                for call in transforms(runtime)))
                            self.assertTrue(effect.follow(WIRE_TARGET, (8., 70., -6.)))
                            self.assertEqual(WIRE_TARGET, effect.anchor)
                            self.assertTrue(all(record['anchor'] == WIRE_TARGET for record in effect.layers))

    def test_failed_uniform_and_position_rollbacks_retry_before_stationary_layer_shortcuts(self):
        effect, runtime = wire_fixture()
        runtime.outcomes['position', 'wire_1', None] = [True, (RuntimeError('position rollback'), CORRUPT)]
        runtime.outcomes['uniform', 'wire_1', 2] = [False, (False, BAD_UNIFORM)]
        self.assertFalse(effect.follow(WIRE_TARGET))
        pending = effect.layers[1]['move_restore']
        self.assertEqual(WIRE_OLD, pending['position'])
        self.assertEqual(effect.layers[1]['uniforms'][2], pending['uniform'])
        self.assertEqual(WIRE_OLD, effect.anchor)
        runtime.calls[:] = []
        self.assertTrue(effect.follow(WIRE_OLD))
        self.assertEqual([('uniform', 'wire_1', 2), ('position', 'wire_1', None)],
                         [call[:3] for call in transforms(runtime)])
        self.assert_restored(effect, runtime)
        runtime.calls[:] = []
        self.assertTrue(effect.follow(WIRE_OLD))
        self.assertEqual([], transforms(runtime))

    def test_unresolved_record_recovery_blocks_new_moves_and_configuration(self):
        effect, runtime = wire_fixture('starry')
        runtime.outcomes['position', 'wire_1', None] = [(False, CORRUPT), (False, CORRUPT),
                                                      (False, CORRUPT), (False, CORRUPT)]
        self.assertFalse(effect.follow(WIRE_TARGET))
        runtime.calls[:] = []
        self.assertFalse(effect.follow(WIRE_TARGET))
        effect._configure(effect.layers[1])
        self.assertEqual([('position', 'wire_1', None, WIRE_OLD)]*2,
                         [call[:4] for call in runtime.calls])
        self.assertEqual(WIRE_OLD, effect.anchor)
        self.assertTrue(effect.follow(WIRE_TARGET))
        self.assertTrue(all(record['anchor'] == WIRE_TARGET for record in effect.layers))

    def test_direct_move_recovers_initial_centre_default_uniform_and_cleared_cache(self):
        for initial in (True, False):
            with self.subTest(initial=initial):
                effect, runtime = wire_fixture()
                record = effect.layers[0]
                record['uniforms'].clear()
                if initial:
                    record['anchor'] = None
                    runtime.positions[record['id']] = record['centre']
                    runtime.uniforms[record['id'], 2] = (1., 1., 1., 1.)
                runtime.outcomes['uniform', record['id'], 2] = [ValueError('uniform failure')]
                self.assertFalse(effect._move(record, WIRE_TARGET))
                expected_position = record['centre'] if initial else WIRE_OLD
                expected_uniform = (1., 1., 1., 1.) if initial else correction(WIRE_OLD)
                self.assertEqual(expected_position, runtime.positions[record['id']])
                self.assertEqual(expected_uniform, runtime.uniforms[record['id'], 2])
                self.assertNotIn('move_restore', record)
                self.assertEqual(None if initial else WIRE_OLD, record['anchor'])
                self.assertTrue(effect._move(record, WIRE_TARGET))
                self.assertEqual(WIRE_TARGET, record['anchor'])
                self.assertEqual(correction(WIRE_TARGET), record['uniforms'][2])

    def test_survey_point_failure_rolls_back_owned_layers_and_keeps_fixed_style(self):
        effect, runtime = wire_fixture(survey=True, point=True)
        runtime.outcomes['uniform', 'wire_3', 2] = [False]
        self.assertFalse(effect.follow(WIRE_TARGET))
        self.assert_restored(effect, runtime)
        self.assertEqual('golden', effect.style)
        self.assertEqual(3, len(effect.layers))
        self.assertEqual('wire_3', effect.points[0]['id'])

    def test_failed_release_keeps_journal_and_successful_release_clears_it(self):
        effect, runtime = wire_fixture()
        record = effect.layers[0]
        runtime.outcomes['position', record['id'], None] = [False, (False, CORRUPT)]
        self.assertFalse(effect._move(record, WIRE_TARGET))
        with patch.object(effect.bridge.system, 'DestroyClientEntity', side_effect=RuntimeError('destroy failure')):
            with self.assertRaisesRegex(RuntimeError, 'destroy failure'):
                effect._release(record)
        self.assertIn('move_restore', record)
        self.assertIn(record['id'], runtime.positions)
        effect._release(record)
        self.assertNotIn('move_restore', record)
        self.assertNotIn(record['id'], runtime.positions)


class DelegatedOutlineBridgeTransactionTests(unittest.TestCase):
    def setUp(self):
        self.log = patch('traceback.print_exc')
        self.log.start()
        self.addCleanup(self.log.stop)

    def test_actual_golden_and_starry_outline_failure_restores_body_then_stationary_recovery(self):
        for style in ('golden', 'starry'):
            with self.subTest(style=style):
                bridge, runtime = bridge_fixture()
                effect, wires = wire_fixture(style)
                effect.bridge = bridge
                runtime.positions.update(wires.positions)
                runtime.uniforms.update(wires.uniforms)
                outline = ProjectionOutline(bridge)
                outline.style, outline.entity = style, 'wire_1'
                outline.bounds, outline.effects = ((20, 50, -10), (6, 8, 10)), effect
                bridge.projection_outline = outline
                signature = ((1., 66., 6.), OLD, 'mesh', 'wire_1')
                bridge._projection_follow_position = signature
                offsets = dict(runtime.offsets)
                runtime.target()
                runtime.camera_position = (8., 70., -6.)
                runtime.outcomes['uniform', 'wire_1', 2] = [False, (RuntimeError('wire rollback failure'), BAD_UNIFORM)]
                runtime.outcomes['position', 'wire_1', None] = [True, (False, CORRUPT)]
                bridge.follow_projection()
                self.assertEqual(OLD, bridge.projection_mesh[3])
                self.assertEqual(OLD, bridge.projection_shader.anchor)
                self.assertEqual(OLD, runtime.positions['mesh'])
                self.assertEqual(offsets, runtime.offsets)
                self.assertEqual(signature, bridge._projection_follow_position)
                self.assertEqual(WIRE_OLD, effect.anchor)
                self.assertIn('move_restore', effect.layers[1])
                runtime.target(OLD)
                runtime.camera_position = (1., 66., 2.)
                runtime.calls[:] = []
                bridge.follow_projection()
                self.assertEqual([('uniform', 'wire_1', 2), ('position', 'wire_1', None)],
                                 [call[:3] for call in transforms(runtime)])
                self.assertEqual(signature, bridge._projection_follow_position)
                self.assertEqual(WIRE_OLD, runtime.positions['wire_1'])
                self.assertEqual(correction(WIRE_OLD, effect.layers[1]['centre']), runtime.uniforms['wire_1', 2])
                self.assertNotIn('move_restore', effect.layers[1])
                runtime.calls[:] = []
                bridge.follow_projection()
                self.assertEqual([], transforms(runtime))
                runtime.target()
                runtime.camera_position = (8., 70., -6.)
                bridge.follow_projection()
                self.assertEqual(TARGET, bridge.projection_mesh[3])
                self.assertEqual(WIRE_TARGET, effect.anchor)
                self.assertTrue(all(record['anchor'] == WIRE_TARGET for record in effect.layers))

    def test_appearance_uniform_or_glow_exception_before_commit_restores_body_and_all_wire_layers(self):
        for style in ('golden', 'starry'):
            for source in (3, 4, 'glow'):
                with self.subTest(style=style, source=source):
                    bridge, runtime = bridge_fixture()
                    effect, wires = wire_fixture(style)
                    effect.bridge = bridge
                    runtime.positions.update(wires.positions)
                    runtime.uniforms.update(wires.uniforms)
                    outline = ProjectionOutline(bridge)
                    outline.style, outline.entity = style, 'wire_1'
                    outline.bounds, outline.effects = ((20, 50, -10), (6, 8, 10)), effect
                    bridge.projection_outline = outline
                    signature = ((1., 66., 6.), OLD, 'mesh', 'wire_1')
                    bridge._projection_follow_position = signature
                    offsets = dict(runtime.offsets)
                    runtime.observer = lambda: (bridge.projection_mesh[3], bridge.projection_shader.anchor,
                                               effect.anchor, tuple(record['anchor'] for record in effect.layers))
                    for record in effect.layers:
                        effect._update(record, 0., effect.camera)
                    runtime.calls[:] = []
                    runtime.target()
                    runtime.camera_position = (8., 70., -6.)
                    if source == 'glow':
                        effect.layers[2]['glow'] = types.SimpleNamespace(update=lambda *args:
                            (_ for _ in ()).throw(ValueError('appearance glow failure')))
                    else:
                        runtime.outcomes['uniform', 'wire_1', source] = [TypeError('appearance uniform failure')]
                    runtime.outcomes['uniform', 'wire_2', 2] = [True, (False, BAD_UNIFORM)]
                    bridge.follow_projection()
                    self.assertEqual(OLD, bridge.projection_mesh[3])
                    self.assertEqual(OLD, bridge.projection_shader.anchor)
                    self.assertEqual(OLD, runtime.positions['mesh'])
                    self.assertEqual(offsets, runtime.offsets)
                    self.assertEqual(signature, bridge._projection_follow_position)
                    self.assertEqual(WIRE_OLD, effect.anchor)
                    self.assertEqual((1., 66., 2.), effect.camera)
                    self.assertTrue(all(record['anchor'] == WIRE_OLD for record in effect.layers))
                    self.assertTrue(all(call[4] == (OLD, OLD, WIRE_OLD, (WIRE_OLD,)*3) for call in runtime.calls))
                    self.assertIn('move_restore', effect.layers[2])
                    effect.layers[2]['glow'] = None
                    runtime.target(OLD)
                    runtime.camera_position = (1., 66., 2.)
                    runtime.calls[:] = []
                    bridge.follow_projection()
                    self.assertEqual([('uniform', 'wire_2', 2)], [call[:3] for call in transforms(runtime)])
                    self.assertEqual(WIRE_OLD, runtime.positions['wire_2'])
                    self.assertEqual(correction(WIRE_OLD, effect.layers[2]['centre']), runtime.uniforms['wire_2', 2])
                    self.assertNotIn('move_restore', effect.layers[2])
                    self.assertEqual(signature, bridge._projection_follow_position)
                    for record in effect.layers:
                        self.assertEqual(record['uniforms'][4], runtime.uniforms[record['id'], 4])
                        self.assertEqual(tuple(effect.camera[i]-record['centre'][i] for i in range(3)),
                                         runtime.uniforms[record['id'], 4][:3])


if __name__ == '__main__':
    unittest.main()
