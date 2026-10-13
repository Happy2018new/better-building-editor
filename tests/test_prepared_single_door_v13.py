"""Verify original V13 bytes independently of later corrected live runners."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'tools/data/native_single_door_v13_prepared'
sys.path.insert(0, str(ROOT / 'tools'))
import probe_native_single_door as probe
MANIFEST_SHA = 'c69f755f7aaf055e1bb56f847ea562833ae695dd27cd2941254365f8437e4876'


def frozen_constants():
    module = ast.parse((DATA / 'runner.py').read_text(encoding='ascii'))
    return {node.targets[0].id: ast.literal_eval(node.value) for node in module.body
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)}


class PreparedSingleDoorV13Tests(unittest.TestCase):
    def test_immutable_inventory_and_historical_source_pins_match_exactly(self):
        manifest = json.loads((DATA / 'manifest.json').read_bytes())
        self.assertEqual(MANIFEST_SHA, hashlib.sha256((DATA / 'manifest.json').read_bytes()).hexdigest())
        self.assertEqual(set(manifest['files']) | {'manifest.json'},
                         {path.name for path in DATA.iterdir() if path.is_file()})
        for name, row in manifest['files'].items():
            with self.subTest(name=name):
                frozen = (DATA / name).read_bytes()
                self.assertEqual(row['sha256'], hashlib.sha256(frozen).hexdigest())
        constants = frozen_constants()
        self.assertEqual(constants['PROBE_SHA'], manifest['files']['probe.py']['sha256'])
        self.assertEqual(constants['LOAD_PREFLIGHT_SHA'], manifest['files']['load_preflight.py']['sha256'])
        self.assertEqual(constants['SHAPE_HELPERS_SHA'], manifest['files']['shape_helpers.py']['sha256'])
        self.assertEqual(constants['SESSION_LOADER_SHA'], manifest['files']['session_loader.py']['sha256'])

    def test_prepared_gates_and_finite_budget_never_claim_native_acceptance(self):
        manifest = json.loads((DATA / 'manifest.json').read_bytes())
        for key in ('native_attempted', 'data_replication_verified', 'client_typed_pair_verified',
                    'physical_orientation_accepted', 'capture_reliable', 'production_mapping_changed'):
            self.assertFalse(manifest[key])
        self.assertTrue(manifest['root_review_required_before_native_attempt'])
        self.assertEqual([120, 30, 20, 20, 200, 240], [manifest['limits'][key] for key in
                         ('readiness', 'load', 'fixture', 'cleanup', 'work', 'total')])
        self.assertEqual(72, frozen_constants()['PROBE_WORK_SECONDS'])
        self.assertEqual(72, probe.MIN_WORK_SECONDS)
        self.assertEqual(5, manifest['maximum_live_games'])
        self.assertEqual(17, len(probe.single_pair((4, -48, 4))[2]))
        self.assertEqual('_native_single_door_saved', probe.MARKER)


if __name__ == '__main__':
    unittest.main()
