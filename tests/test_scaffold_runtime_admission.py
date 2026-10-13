"""World admission keeps air None, but never admits missing nonair states."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import run_scaffold_runtime_lifecycle as runner


class RuntimeAdmissionTests(unittest.TestCase):
    def sample(self):
        client = {'runtime': runner.world.RUNTIME, 'ui_initialized': True, 'render_ticks': 2,
                  'player': 'player', 'foot': [.5, -60., .5]}
        server = {'runtime': runner.world.RUNTIME, 'player': 'player', 'foot': [.5, -60., .5],
                  'dimension': 0, 'ground': {'front': {'name': 'minecraft:grass_block', 'aux': 0}, 'states': {}},
                  'reserve': [{'offset': offset, 'front': {'name': 'minecraft:air', 'aux': 0},
                               'states': None, 'liquid': None} for offset in runner.world.OFFSETS]}
        return client, server

    def test_air_none_is_admitted_but_never_changed(self):
        client, server = self.sample()
        before = copy.deepcopy(server)
        self.assertTrue(runner.physical_ready(client, server))
        self.assertEqual(before, server)
        self.assertTrue(all(row['states'] is None for row in server['reserve']))

    def test_ui_loading_identity_and_nonair_state_failures_are_rejected(self):
        for change in ('ui', 'ticks', 'height', 'dimension', 'player', 'ground', 'nonair', 'wet'):
            client, server = self.sample()
            if change == 'ui':
                client['ui_initialized'] = False
            elif change == 'ticks':
                client['render_ticks'] = 1
            elif change == 'height':
                server['foot'][1] = client['foot'][1] = 32769.6
            elif change == 'dimension':
                server['dimension'] = False
            elif change == 'player':
                server['player'] = 'another-player'
            elif change == 'ground':
                server['ground']['states'] = None
            elif change == 'nonair':
                server['reserve'][0]['front']['name'] = 'minecraft:stone'
            else:
                server['reserve'][0]['liquid'] = {'name': 'minecraft:water', 'aux': 0}
            with self.subTest(change=change):
                self.assertFalse(runner.physical_ready(client, server))


if __name__ == '__main__':
    unittest.main()
