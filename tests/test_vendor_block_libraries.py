"""Pinned vendoring rejects source drift and produces independently importable bytes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('vendor_block_libraries', ROOT / 'tools/vendor_block_libraries.py')
vendor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vendor)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root)] + list(args), stderr=subprocess.PIPE)


def pin(root, package):
    return {'package': package, 'branch': 'main',
            'commit': git(root, 'rev-parse', 'HEAD').decode('ascii').strip(),
            'manifest_sha256': vendor.digest((root / 'snapshot_manifest.json').read_bytes()),
            'license_sha256': vendor.digest((root / 'LICENSE').read_bytes()),
            'runtime_files': {path.relative_to(root).as_posix(): vendor.digest(path.read_bytes())
                              for path in sorted((root / package).glob('*.py'))}}


class VendorBlockLibrariesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix='block-library-fixture-')
        cls.fixture_root = Path(cls.fixture.name)
        for name, package in vendor.PACKAGES.items():
            root = cls.fixture_root / name
            (root / package).mkdir(parents=True)
            git(root, 'init', '--initial-branch=main')
            (root / package / '__init__.py').write_bytes(b'')
            if name == 'nemc-block-states':
                (root / package / 'values.py').write_bytes(b'VALUE = 17\n')
                (root / package / 'relative.py').write_bytes(b'from .values import VALUE\n')
            else:
                (root / package / 'layout.py').write_bytes(b'from math import floor\nVALUE = floor(3.8)\n')
            manifest = {'modules': [{'destination': path.relative_to(root).as_posix(),
                                     'sha256': vendor.digest(path.read_bytes())}
                                    for path in sorted((root / package).glob('*.py'))]}
            if name == 'nemc-block-renderer':
                manifest['states_binding'] = {'snapshot_manifest_sha256': vendor.digest(
                    (cls.fixture_root / 'nemc-block-states/snapshot_manifest.json').read_bytes())}
            (root / 'snapshot_manifest.json').write_bytes(vendor.encoded(manifest))
            (root / 'LICENSE').write_bytes(b'fixture license\n')
            git(root, 'add', '.')
            git(root, '-c', 'user.name=Vendor Test', '-c', 'user.email=vendor@example.invalid',
                '-c', 'commit.gpgsign=false', 'commit', '-m', 'fixture')

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='block-library-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.sources = {}
        for name in vendor.PACKAGES:
            target = self.root / name
            shutil.copytree(self.fixture_root / name, target)
            self.sources[name] = target
        self.lock = {'schema_version': 1, 'libraries': {
            name: pin(root, vendor.PACKAGES[name]) for name, root in self.sources.items()}}
        self.lock_path = self.root / 'lock.json'
        self.output = self.root / 'private_vendor'

    def build(self, output=None):
        self.lock_path.write_bytes(vendor.encoded(self.lock))
        return vendor.build(self.sources['nemc-block-states'], self.sources['nemc-block-renderer'],
                            output or self.output, self.lock_path)

    def test_exact_bytes_and_nested_import_without_sources_or_site_packages(self):
        receipt = self.build()
        self.assertEqual(5, receipt['runtime_python_files'])
        for row in self.lock['libraries'].values():
            for path, expected in row['runtime_files'].items():
                self.assertEqual(expected, hashlib.sha256((self.output / path).read_bytes()).hexdigest())
        self.assertEqual(vendor.digest(self.lock_path.read_bytes()), receipt['lock_sha256'])
        # Remove access to the fixture checkouts before importing the output.
        for name, root in self.sources.items():
            root.rename(self.root / (name + '-unavailable'))
        script = ('import sys; sys.path.insert(0,sys.argv[1]); '
                  'from private_vendor.nemc_block_states.relative import VALUE as state; '
                  'from private_vendor.nemc_block_renderer.layout import VALUE as layout; '
                  'assert (state,layout)==(17,3); print("independent nested imports passed")')
        result = subprocess.check_output([sys.executable, '-I', '-S', '-B', '-c', script, str(self.root)],
                                         cwd=self.root, text=True)
        self.assertIn('independent nested imports passed', result)
        actual = {path.relative_to(self.output).as_posix() for path in self.output.rglob('*') if path.is_file()}
        self.assertEqual(set(receipt['files_sha256']) | {'vendor_manifest.json'}, actual)

    def test_missing_runtime_file_is_rejected_before_output(self):
        (self.sources['nemc-block-states'] / 'nemc_block_states/values.py').unlink()
        with self.assertRaisesRegex(ValueError, 'inventory mismatch'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_changed_runtime_bytes_are_rejected_before_output(self):
        (self.sources['nemc-block-states'] / 'nemc_block_states/values.py').write_bytes(b'VALUE = 99\n')
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_rehashing_dirty_runtime_cannot_bypass_pinned_git_blob(self):
        path = self.sources['nemc-block-states'] / 'nemc_block_states/values.py'
        path.write_bytes(b'VALUE = 99\n')
        self.lock['libraries']['nemc-block-states']['runtime_files']['nemc_block_states/values.py'] = vendor.digest(path.read_bytes())
        with self.assertRaisesRegex(ValueError, 'pinned Git blob'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_wrong_commit_and_non_main_checkout_are_rejected(self):
        row = self.lock['libraries']['nemc-block-states']
        commit = row['commit']
        row['commit'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'commit mismatch'):
            self.build()
        row['commit'] = commit
        git(self.sources['nemc-block-states'], 'checkout', '-b', 'other')
        with self.assertRaisesRegex(ValueError, 'must be on main'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_cross_directory_and_windows_paths_are_rejected(self):
        files = self.lock['libraries']['nemc-block-states']['runtime_files']
        for path in ('../outside.py', 'nemc_block_states/../outside.py',
                     'nemc_block_states/sub/file.py', 'nemc_block_states\\outside.py',
                     'D:/outside.py', '/outside.py', 'nemc_block_states/values.py:stream'):
            with self.subTest(path=path):
                files[path] = 'a' * 64
                with self.assertRaisesRegex(ValueError, 'Unsafe runtime package path'):
                    self.build()
                files.pop(path)
        self.assertFalse(self.output.exists())

    def test_unlocked_python_module_is_rejected(self):
        (self.sources['nemc-block-states'] / 'nemc_block_states/extra.py').write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'inventory mismatch'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_manifest_drift_and_wrong_cross_library_binding_are_rejected(self):
        root = self.sources['nemc-block-renderer']
        path = root / 'snapshot_manifest.json'
        manifest = json.loads(path.read_bytes())
        manifest['states_binding']['snapshot_manifest_sha256'] = 'a' * 64
        path.write_bytes(vendor.encoded(manifest))
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            self.build()
        git(root, 'add', 'snapshot_manifest.json')
        git(root, '-c', 'user.name=Vendor Test', '-c', 'user.email=vendor@example.invalid',
            '-c', 'commit.gpgsign=false', 'commit', '-m', 'bad binding')
        self.lock['libraries']['nemc-block-renderer'] = pin(root, 'nemc_block_renderer')
        with self.assertRaisesRegex(ValueError, 'Renderer binding'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_existing_output_and_source_directory_are_preserved(self):
        self.output.mkdir()
        marker = self.output / 'keep.txt'
        marker.write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.build()
        self.assertEqual(b'keep', marker.read_bytes())
        with self.assertRaisesRegex(ValueError, 'separate from both source'):
            self.build(self.sources['nemc-block-states'] / 'new-output')


if __name__ == '__main__':
    unittest.main()
