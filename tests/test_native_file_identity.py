"""Real Windows file IDs and owner imports from normal and linked checkouts."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from native_file_identity import file_identity
from client_anchor_depth_owner_r15 import repository_root


@unittest.skipUnless(os.name == 'nt', 'Windows native file identity')
class FileIdentity(unittest.TestCase):
    def test_real_file_hardlink_and_rename_keep_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / 'original.txt'
            original.write_bytes(b'physical identity')
            alias = Path(directory) / 'alias.txt'
            os.link(original, alias)
            first, linked = file_identity(original), file_identity(alias)
            self.assertEqual((first['volume'], first['file_id']), (linked['volume'], linked['file_id']))
            self.assertEqual(first['bytes'], len(b'physical identity'))
            renamed = original.with_name('renamed.txt')
            original.rename(renamed)
            after = file_identity(renamed)
            self.assertEqual((first['volume'], first['file_id']), (after['volume'], after['file_id']))
            self.assertEqual(Path(after['final_path']).resolve(), renamed.resolve())
            folder = file_identity(directory, directory=True)
            self.assertEqual(Path(folder['final_path']).resolve(), Path(directory).resolve())
            with self.assertRaisesRegex(ValueError, 'Cannot open file identity'):
                file_identity(original)


class OwnerPortability(unittest.TestCase):
    def test_repository_discovery_for_external_worktree_and_main_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            main = Path(directory) / 'main'
            linked = Path(directory) / 'external-worktree'
            main.mkdir()
            subprocess.run(['git', 'init', '-q', str(main)], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(main), '-c', 'commit.gpgsign=false', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                            'commit', '-q', '--allow-empty', '-m', 'fixture'], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(main), 'worktree', 'add', '-q', '--detach', str(linked)],
                           check=True, capture_output=True)
            self.assertEqual(repository_root(main), main.resolve())
            self.assertEqual(repository_root(linked), main.resolve())

    def test_owner_import_does_not_load_ignored_staging_module_or_candidate(self):
        code = '''import importlib.abc,sys
from pathlib import Path
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname=='session_pack_stage':raise AssertionError('ignored staging module imported')
sys.meta_path.insert(0,Block())
sys.path.insert(0,sys.argv[1])
import client_anchor_depth_owner_r15 as owner
assert owner.file_identity.__module__=='native_file_identity'
assert owner.REPO==owner.repository_root(Path(sys.argv[2]))
import client_anchor_depth_owner_r16
assert not any('frame-baseline-plan-r11' in path for path in sys.path)
'''
        subprocess.run([sys.executable, '-I', '-c', code, str(ROOT / 'tools'), str(ROOT)],
                       cwd=ROOT, check=True, capture_output=True, timeout=15)
