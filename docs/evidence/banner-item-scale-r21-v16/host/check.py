"""Offline checks for one patterned item, immutable view, and one scale setter."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import prepare


def load_stubs():
    source = prepare.BASE / 'check.py'
    scope = {'__file__': str(source), '__name__': 'prior_banner_offline_stubs'}
    exec(compile(source.read_bytes(), str(source), 'exec'), scope)
    return SimpleNamespace(**scope)


class ScaleControl(unittest.TestCase):
    def setUp(self):
        self.prior = load_stubs()
        self.prior.Controls.setUp(self)
        self.current_dimension, self.scale_ok = 0, True
        self.scale_calls = []
        for side in ('client', 'server'):
            api = sys.modules['mod.' + side + '.extra' + side.title() + 'Api']
            api.GetEngineCompFactory = lambda side=side: self.factory(side)

    def factory(self, side):
        factory = self.engine.factory()
        factory.CreateGame = lambda entity: SimpleNamespace(GetScreenSize=lambda: (499., 277.),
            **({'GetCurrentDimension': lambda: self.current_dimension} if side == 'client' else {}))
        factory.CreateDimension = lambda entity: SimpleNamespace(
            **({'GetEntityDimensionId': lambda: 0} if side == 'server' else {}))
        def item(entity):
            component = self.prior.Component(self.engine, entity)
            def scale(actor, identity, value, is_client):
                assert actor in self.engine.bindings and identity == 0 and value == 1. and is_client is False
                self.scale_calls.append((actor, identity, value, is_client))
                return self.scale_ok
            component.SetBindItemScale = scale
            return component
        factory.CreateItem = item
        return factory

    def action(self, action, server=False, pose='yaw90'):
        return self.prior.Controls.action(self, action, server=server, pose=pose)

    def cleanup(self):
        self.prior.Controls.cleanup(self)

    def tearDown(self):
        for key in ('_banner_scale_client_r21', '_banner_scale_server_r21'):
            if hasattr(sys, key):
                delattr(sys, key)
        self.prior.Controls.tearDown(self)

    def setup_one(self):
        self.action('journal', True)
        self.action('setup')
        mounted = self.action('mount')
        self.assertEqual(mounted['layout'], [{'label': 'patterned', 'position': [8., 88.64],
                                             'size': [235.5, 177.28]}])
        self.assertFalse(self.engine.bindings)
        self.action('bind')

    def test_one_patterned_same_id_scale_only_once_and_fixed_view(self):
        self.setup_one()
        before = list(self.engine.bind_calls)
        result = self.action('scale')
        self.assertEqual(result['identity'], 0)
        self.assertEqual(result['scale'], 1.)
        self.assertFalse(result['rebound'])
        self.assertEqual(self.engine.bind_calls, before)
        self.assertEqual(len(before), 1)
        self.assertEqual(before[0][1], self.inputs['items']['patterned'])
        self.assertTrue(all(row['params']['scale'] == 1.4 and row['params']['init_rot_y'] == 90. and
            row['params']['init_rot_x'] == 0. for row in result['render']))
        with self.assertRaises(AssertionError):
            self.action('scale')
        self.assertEqual(len(self.scale_calls), 1)
        self.cleanup()

    def test_failed_scale_retains_binding_and_rejects_retry(self):
        self.setup_one()
        self.scale_ok = False
        with self.assertRaises(AssertionError):
            self.action('scale')
        self.assertEqual(len(self.engine.bindings), 1)
        with self.assertRaises(AssertionError):
            self.action('scale')
        self.assertEqual(len(self.scale_calls), 1)
        self.cleanup()

    def test_unsettled_dimension_rejected_before_model(self):
        self.current_dimension = -1
        self.action('journal', True)
        with self.assertRaises(AssertionError):
            self.action('setup')
        self.assertEqual(self.engine.model_calls, [])
        self.cleanup()

    def test_delayed_destroy_preserves_absence_gate(self):
        self.action('journal', True)
        self.engine.delay_destroy = True
        self.action('restore', True)
        self.assertFalse(self.action('absent', True)['actors_absent'])
        self.assertTrue(hasattr(sys, '_banner_scale_server_r21'))
        self.engine.actors.clear()
        self.assertTrue(self.action('absent', True)['journal_removed'])


if __name__ == '__main__':
    prepare.verify()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ScaleControl))
    prepare.save(prepare.OUTPUT / 'offline-check.json', {'offline_only': True,
        'tests_run': result.testsRun, 'passed': result.wasSuccessful(),
        'failures': len(result.failures), 'errors': len(result.errors),
        'runtime_started': False, 'production_qualified': False})
    raise SystemExit(0 if result.wasSuccessful() else 1)
