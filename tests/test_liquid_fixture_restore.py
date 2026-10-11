"""Host-only protection against overwriting resources during fixture cleanup."""
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from generate_liquid_visibility_fixture import restore


class LiquidFixtureRestoreTests(unittest.TestCase):
    def fixture(self, root):
        project, backup = root / 'project', root / 'backup'
        original = b'{"original": true}\r\n'
        installed = {
            'resource_pack/blocks.json': b'{"experiment": true}\n',
            'resource_pack/models/netease_block/fixture.json': b'{"fixture": true}\n',
        }
        for relative, content in installed.items():
            target = project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        source = backup / 'resource_pack/blocks.json'
        source.parent.mkdir(parents=True)
        source.write_bytes(original)
        (backup / 'installation.json').write_text(json.dumps({
            'project': str(project),
            'installed_sha256': {name: hashlib.sha256(content).hexdigest()
                                 for name, content in installed.items()},
        }), encoding='ascii')
        unrelated = project / 'unrelated.txt'
        unrelated.write_bytes(b'leave this file alone')
        return project, backup, original, installed

    def test_restores_original_bytes_and_removes_only_installed_new_file(self):
        with TemporaryDirectory() as folder:
            project, backup, original, _ = self.fixture(Path(folder))
            self.assertEqual(restore(project, backup), {'restored': True, 'files': 2})
            self.assertEqual((project / 'resource_pack/blocks.json').read_bytes(), original)
            self.assertFalse((project / 'resource_pack/models/netease_block/fixture.json').exists())
            self.assertEqual((project / 'unrelated.txt').read_bytes(), b'leave this file alone')

    def test_changed_resource_rejects_before_any_original_is_restored(self):
        with TemporaryDirectory() as folder:
            project, backup, _, installed = self.fixture(Path(folder))
            changed = project / 'resource_pack/models/netease_block/fixture.json'
            changed.write_bytes(b'new user change')
            with self.assertRaisesRegex(ValueError, 'changed; refusing restoration'):
                restore(project, backup)
            self.assertEqual((project / 'resource_pack/blocks.json').read_bytes(),
                             installed['resource_pack/blocks.json'])
            self.assertEqual(changed.read_bytes(), b'new user change')

    def test_other_project_is_rejected_without_mutation(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            project, backup, _, installed = self.fixture(root)
            with self.assertRaisesRegex(ValueError, 'different project'):
                restore(root / 'other', backup)
            for relative, content in installed.items():
                self.assertEqual((project / relative).read_bytes(), content)


if __name__ == '__main__':
    unittest.main()
