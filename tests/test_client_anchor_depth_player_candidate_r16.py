"""Existing-player positive submission with the same owned sword depth pair."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import prepare_client_anchor_depth_player_candidate_r16 as candidate
import execute_client_anchor_depth_candidate_r15 as runtime
import test_client_anchor_depth_candidate_r15 as prior


class PlayerPositive(unittest.TestCase):
    def fixture(self):
        helper = prior.CandidateStateTransitions()
        helper.nonce = 'c'*32
        helper.programs = candidate.snippets(helper.nonce)
        env, saved, native, submitted, bridge = helper.environment()
        saved['player'] = 'existing-local-player'
        return helper, env, saved, native, submitted, bridge

    def test_player_positive_retains_exact_shared_anchor_binding(self):
        helper, env, saved, native, submitted, bridge = self.fixture()
        for label in candidate.STATES:
            helper.execute(label, env, bridge)
        self.assertEqual(len(native.binds), 1)
        self.assertEqual(len(native.removes), 1)
        self.assertEqual(native.binds[0][0], saved['actor'])
        self.assertEqual(native.binds[0][2:], ('root', True, (0.,0.,0.), (0.,0.,0.), 1.))
        expected_positive = {'entity_id': saved['player'], 'scale': 1., 'render_depth': -50,
                             'init_rot_x': 0., 'init_rot_y': 60., 'init_rot_z': 0.}
        self.assertEqual(submitted[0], expected_positive)
        self.assertEqual(submitted[-1], expected_positive)
        self.assertTrue(all('entity_identifier' not in params for params in submitted))
        self.assertEqual([params['render_depth'] for params in submitted], [-50,-15,-15,-50,-15,-15,-50])
        for params in submitted[1:-1]:
            self.assertEqual(params['entity_id'], saved['actor'])
            self.assertEqual(params['scale'], .35)
            self.assertEqual(params['init_rot_y'], 0.)

    def test_actual_player_submission_validator_rejects_actorless_or_anchor_target(self):
        initial = {'actor': 'owned-anchor', 'player': 'existing-player',
                   'ui_params': dict(candidate.UI, entity_id='owned-anchor')}
        label = candidate.POSITIVE_STATES[0]
        native = {'control': label, 'actor': initial['actor'], 'attachments': [], 'native_item': None,
                  'journal': [{'operation': 'RenderEntity:'+label, 'state': 'returned', 'value': True}]}
        status = {'control': label, 'last_submission': dict(initial['ui_params'], entity_id=initial['player'],
                                                          render_depth=-50, scale=1., init_rot_y=60.),
                  'ui_params': initial['ui_params'], 'attachments': [], 'journal': native['journal']}
        with patch.object(runtime, 'candidate', candidate):
            self.assertIsNone(runtime.validate_state(label, status, initial, native, None))
            bad = deepcopy(status)
            bad['last_submission']['entity_id'] = initial['actor']
            with self.assertRaises(ValueError):
                runtime.validate_state(label, bad, initial, native, None)
            bad['last_submission'].pop('entity_id')
            bad['last_submission']['entity_identifier'] = 'minecraft:cow'
            with self.assertRaises(ValueError):
                runtime.validate_state(label, bad, initial, native, None)

    def test_frozen_candidate_rejects_positive_parameter_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)/'bundle'
            candidate.prepare(bundle)
            source = bundle/'ui_player_positive_client.py'
            source.write_bytes(source.read_bytes().replace(b"params['render_depth']=-50", b"params['render_depth']=-15"))
            with self.assertRaises(ValueError):
                candidate.verify(bundle)


if __name__ == '__main__':
    unittest.main()
