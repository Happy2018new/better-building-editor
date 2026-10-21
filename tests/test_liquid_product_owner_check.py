"""Read-only owner diagnostics preserve generation and expose the explicit scope."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
sys.path.insert(0, str(TOOLS))
import check_liquid_product_owner_contract as checker


def load_generator(root):
    path = root / 'tools/generate_liquid_product_owner_contract.py'
    spec = importlib.util.spec_from_file_location('temporary_water_owner_generator', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LiquidOwnerCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'tools').mkdir()
        for name in ('generate_liquid_product_owner_contract.py', 'check_liquid_product_owner_contract.py'):
            shutil.copyfile(TOOLS / name, self.root / 'tools' / name)
        self.generator = load_generator(self.root)
        for name in self.generator.SOURCES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('# bound input ' + name + '\r\n').encode('ascii'))
        contract, source = self.generator.generated()
        self.generator.CONTRACT.parent.mkdir(parents=True, exist_ok=True)
        self.generator.CONTRACT.write_bytes(contract)
        self.generator.OUTPUT.write_bytes(source)

    def check(self):
        with patch.object(checker, 'generator', self.generator):
            return checker.check()

    def snapshot(self):
        return {path.relative_to(self.root).as_posix(): path.read_bytes()
                for path in self.root.rglob('*') if path.is_file()}

    def test_success_preserves_all_bytes_and_generated_outputs(self):
        before, generated = self.snapshot(), self.generator.generated()
        result = self.check()
        self.assertTrue(result['passed'])
        self.assertEqual([], result['source_differences'])
        self.assertEqual(generated, self.generator.generated())
        self.assertEqual(before, self.snapshot())
        self.assertIn('not a transitive dependency closure', result['scope'])

    def test_added_removed_and_changed_sources_show_both_hashes(self):
        added, changed = self.generator.SOURCES[:2]
        removed = 'behavior_pack/modern_projection/projection/previously_bound.py'
        stored = json.loads(self.generator.CONTRACT.read_bytes())
        stored['source_sha256'].pop(added)
        stored['source_sha256'][removed] = 'e' * 64
        self.generator.CONTRACT.write_text(json.dumps(stored), encoding='ascii')
        changed_path = self.root / changed
        changed_path.write_bytes(changed_path.read_bytes() + b'# changed\n')
        before = self.snapshot()
        result = self.check()
        self.assertFalse(result['passed'])
        rows = {row['path']: row for row in result['source_differences']}
        self.assertEqual({'added', 'removed', 'changed'}, {row['status'] for row in rows.values()})
        self.assertEqual(None, rows[added]['expected_sha256'])
        self.assertEqual(self.generator.digest(checker.normalized(self.root / added)), rows[added]['actual_sha256'])
        self.assertEqual(('e' * 64, None), (rows[removed]['expected_sha256'], rows[removed]['actual_sha256']))
        self.assertEqual(stored['source_sha256'][changed], rows[changed]['expected_sha256'])
        self.assertEqual(self.generator.digest(checker.normalized(changed_path)), rows[changed]['actual_sha256'])
        self.assertEqual(before, self.snapshot())

    def test_unbound_helper_changes_remain_outside_scope_and_are_disclosed(self):
        helper = self.root / 'behavior_pack/modern_projection/projection/native_layers.py'
        self.assertNotIn(helper.relative_to(self.root).as_posix(), self.generator.SOURCES)
        helper.write_bytes(b'# original helper\n')
        before = self.generator.generated()
        helper.write_bytes(b'# changed helper, deliberately outside owner SOURCES\n')
        result = self.check()
        self.assertTrue(result['passed'])
        self.assertEqual(before, self.generator.generated())
        self.assertIn('Unlisted helper changes are not detected', result['scope'])
        self.assertIn('not a transitive dependency closure', result['scope'])

    def test_generator_self_fingerprint_is_still_checked(self):
        path = self.root / 'tools/generate_liquid_product_owner_contract.py'
        original = self.generator.source_contract()['generator_sha256']
        path.write_bytes(path.read_bytes() + b'\n# generator changed\n')
        result = self.check()
        self.assertFalse(result['passed'])
        self.assertEqual([], result['source_differences'])
        self.assertEqual(original, result['generator_difference']['expected_sha256'])
        self.assertEqual(self.generator.digest(checker.normalized(path)), result['generator_difference']['actual_sha256'])

    def test_missing_bound_source_is_reported_and_never_rewritten(self):
        name = self.generator.SOURCES[0]
        (self.root / name).unlink()
        before = self.snapshot()
        result = self.check()
        self.assertFalse(result['passed'])
        row = next(row for row in result['source_differences'] if row['path'] == name)
        self.assertEqual('removed', row['status'])
        self.assertIsNone(row['actual_sha256'])
        self.assertTrue(any(error.get('path') == name for error in result['errors']))
        self.assertEqual(before, self.snapshot())

    def test_invalid_contract_fails_without_writing_outputs(self):
        self.generator.CONTRACT.write_bytes(b'{not valid json')
        before = self.snapshot()
        result = self.check()
        self.assertFalse(result['passed'])
        self.assertTrue(result['errors'])
        self.assertEqual(before, self.snapshot())

    def test_cli_retains_zero_and_one_exit_codes(self):
        command = [sys.executable, '-B', str(self.root / 'tools/check_liquid_product_owner_contract.py'), '--check']
        for changed in (False, True):
            if changed:
                path = self.root / self.generator.SOURCES[0]
                path.write_bytes(path.read_bytes() + b'# drift\n')
            before = self.snapshot()
            process = subprocess.run(command, cwd=self.root, text=True, encoding='utf8', capture_output=True)
            self.assertEqual(1 if changed else 0, process.returncode, process.stderr)
            result = json.loads(process.stdout)
            self.assertEqual(not changed, result['passed'])
            self.assertEqual(before, self.snapshot())

    def test_real_old_contract_matches_original_check_result_without_refresh(self):
        generator = checker.generator
        protected = (TOOLS / 'generate_liquid_product_owner_contract.py', generator.CONTRACT,
                     generator.OUTPUT, ROOT / 'behavior_pack/modern_projection/projection/liquid_product_qualification_data.py')
        before = {path: path.read_bytes() for path in protected}
        generated = generator.generated()
        stored = json.loads(generator.CONTRACT.read_bytes())
        current = json.loads(generated[0])
        result = checker.check()
        self.assertEqual(checker.source_differences(stored['source_sha256'], current['source_sha256']),
                         result['source_differences'])
        original_passed = all(checker.normalized(path) == expected
                              for path, expected in ((generator.CONTRACT, generated[0]), (generator.OUTPUT, generated[1])))
        self.assertEqual(original_passed, result['passed'])
        self.assertEqual(generated, generator.generated())
        self.assertEqual(before, {path: path.read_bytes() for path in protected})


if __name__ == '__main__':
    unittest.main()
