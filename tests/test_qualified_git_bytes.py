"""Use actual Git clean/smudge operations to guard qualified byte preservation."""
from pathlib import Path
import shutil
import tempfile
import unittest

from tools.verify_qualified_git_bytes import qualified_paths, verify_roundtrip

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('git'), 'Git is required for checkout filter checks')
class QualifiedGitBytesTests(unittest.TestCase):
    def test_current_qualified_sources_and_bundles_keep_exact_bytes(self):
        names = qualified_paths(ROOT)
        self.assertIn('behavior_pack/modern_projection/projection/block_registry_data.py', names)
        self.assertIn('docs/evidence/water-product-r24-v1/qualification.json', names)
        self.assertIn('docs/evidence/coral-r24-v1/verify.py', names)
        report = verify_roundtrip(ROOT, names)
        self.assertTrue(report['all_byte_identical'],
                        [row['path'] for row in report['files'] if not row['byte_identical']])

    def test_real_git_negative_control_changes_unprotected_line_endings(self):
        with tempfile.TemporaryDirectory(prefix='bbe-git-negative-') as temporary:
            root = Path(temporary).resolve()
            (root / '.gitattributes').write_bytes(b'crlf.py text eol=lf\n')
            (root / 'lf.py').write_bytes(b'first\nsecond\n')
            (root / 'crlf.py').write_bytes(b'first\r\nsecond\r\n')
            report = verify_roundtrip(root, ['lf.py', 'crlf.py'])
            self.assertFalse(report['all_byte_identical'])
            self.assertEqual([row['byte_identical'] for row in report['files']], [False, False])

    def test_explicit_byte_rules_preserve_both_line_endings(self):
        with tempfile.TemporaryDirectory(prefix='bbe-git-preserved-') as temporary:
            root = Path(temporary).resolve()
            (root / '.gitattributes').write_bytes(b'lf.py -text\ncrlf.py -text\n')
            (root / 'lf.py').write_bytes(b'first\nsecond\n')
            (root / 'crlf.py').write_bytes(b'first\r\nsecond\r\n')
            report = verify_roundtrip(root, ['lf.py', 'crlf.py'])
            self.assertTrue(report['all_byte_identical'])


if __name__ == '__main__':
    unittest.main()
