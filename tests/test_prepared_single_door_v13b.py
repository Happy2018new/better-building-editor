"""Preserve the reviewed V13b freeze independently of its subsequent observation."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'tools/data/native_single_door_v13b_prepared'
MANIFEST_SHA = '0c95fdd3bbd25cebf682aa47a970e656232ce98364cef4a7f0dc6d36716ab154'
sys.path.insert(0, str(ROOT / 'tools'))
import probe_native_single_door as probe


def frozen_constants():
    module = ast.parse((DATA / 'runner.py').read_text(encoding='ascii'))
    return {node.targets[0].id: ast.literal_eval(node.value) for node in module.body
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, (ast.Constant, ast.Tuple))}


class PreparedSingleDoorV13bTests(unittest.TestCase):
    def test_frozen_inventory_matches_original_reviewed_source_pins(self):
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

    def test_original_v13_is_fixed_and_the_corrected_runner_is_distinct(self):
        manifest = json.loads((DATA / 'manifest.json').read_bytes())
        original = ROOT / 'tools/data/native_single_door_v13_prepared'
        self.assertEqual('c69f755f7aaf055e1bb56f847ea562833ae695dd27cd2941254365f8437e4876',
                         manifest['supersedes_manifest_sha256'])
        self.assertEqual(manifest['supersedes_manifest_sha256'],
                         hashlib.sha256((original / 'manifest.json').read_bytes()).hexdigest())
        self.assertNotEqual((original / 'runner.py').read_bytes(), (DATA / 'runner.py').read_bytes())
        for name in ('probe.py', 'load_preflight.py', 'shape_helpers.py', 'session_loader.py'):
            with self.subTest(name=name):
                self.assertEqual((original / name).read_bytes(), (DATA / name).read_bytes())

    def test_prepared_family_keeps_native_acceptance_false_and_shared_inputs_pinned(self):
        manifest = json.loads((DATA / 'manifest.json').read_bytes())
        for key in ('native_attempted', 'data_replication_verified', 'client_typed_pair_verified',
                    'physical_orientation_accepted', 'capture_reliable', 'production_mapping_changed'):
            self.assertFalse(manifest[key])
        self.assertTrue(manifest['root_review_required_before_native_attempt'])
        self.assertEqual([120, 30, 20, 20, 200, 240, 3], [manifest['limits'][key] for key in
                         ('readiness', 'load', 'fixture', 'cleanup', 'work', 'total', 'child_reap_reserve')])
        constants = frozen_constants()
        self.assertEqual(constants['CHILD_REAP_RESERVE_SECONDS'], manifest['limits']['child_reap_reserve'])
        self.assertEqual(72, constants['PROBE_WORK_SECONDS'])
        self.assertEqual(72, probe.MIN_WORK_SECONDS)
        self.assertEqual(5, manifest['maximum_live_games'])
        self.assertEqual(constants['MCDK_SHA'], manifest['approved_shared_inputs']['mcdk'])
        self.assertEqual(constants['GUARD_SHA'], manifest['approved_shared_inputs']['guard'])
        self.assertEqual(constants['COPY_HASHES'], tuple(manifest['approved_shared_inputs'][key] for key in
                         ('instances.py', 'mcdk.py', 'flat_config')))


if __name__ == '__main__':
    unittest.main()
