"""Cold-replay real committed liquid evidence without launching a game.

The archives are expected in docs/evidence after the owning agent's commits
are integrated. BBE_LIQUID_REPLAY_EVIDENCE_ROOT can select a staging archive
root; that root supplies bytes only, never imports or live runtime access.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
NAMES = ('liquid-native-write-r13-v2', 'liquid-native-write-r13-v2-source-closure',
         'liquid-native-write-r13-v2-source-closure-extra')
EVIDENCE = Path(os.environ.get('BBE_LIQUID_REPLAY_EVIDENCE_ROOT', ROOT / 'docs/evidence'))
spec = importlib.util.spec_from_file_location('cold_liquid_replay', ROOT / 'tools/replay_liquid_native_archive.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


@unittest.skipUnless(all((EVIDENCE / name / 'archive-index.json').is_file() for name in NAMES),
                     'Exact liquid archives are not integrated in this checkout')
class RealColdReplay(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='bbe-liquid-cold-test-')
        self.addCleanup(self.directory.cleanup)
        self.cold = Path(self.directory.name)
        for name in NAMES:
            shutil.copytree(EVIDENCE / name, self.cold / name)
        self.sources = [self.cold / name for name in NAMES[1:]]
        self.indexes = {name: replay.digest(self.cold / name / 'archive-index.json') for name in NAMES}

    def execute(self):
        return replay.replay(self.cold / NAMES[0], 'archive-index.json', self.cold / 'replay.json',
                             source_archives=self.sources)

    def test_exact_cold_replay_preserves_failed_pixels_and_all_source_gates(self):
        report = self.execute()
        self.assertTrue(report['reproduced'])
        self.assertEqual(report['recomputed']['status'], 'FAIL')
        self.assertFalse(report['recomputed']['production_qualified'])
        self.assertEqual(len(report['imported_source_sha256']), 46)
        self.assertEqual(report['new_launches'], 0)
        self.assertEqual(report['sdk_or_network_calls'], 0)
        expected = json.loads((self.cold / NAMES[0] / 'native-visibility-analysis.json').read_bytes())
        self.assertEqual(replay.semantic_result(report['recomputed']), replay.semantic_result(expected))
        for name in NAMES:
            self.assertEqual(self.indexes[name], replay.digest(self.cold / name / 'archive-index.json'))

    def test_changed_source_newlines_refuse_before_scoring(self):
        source = self.cold / NAMES[1] / 'sources/tools/analyze_liquid_sides.py'
        raw = source.read_bytes()
        self.assertIn(b'\r\n', raw)
        source.write_bytes(raw.replace(b'\r\n', b'\n'))
        with self.assertRaisesRegex(ValueError, 'Archived original bytes changed'):
            self.execute()
        self.assertFalse((self.cold / 'replay.json').exists())

    def test_changed_capture_byte_refuses_before_scoring(self):
        images = list((self.cold / NAMES[0]).glob('*native_palette_h_vnw*.png'))
        self.assertEqual(len(images), 1)
        raw = images[0].read_bytes()
        images[0].write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, 'Archived original bytes changed'):
            self.execute()
        self.assertFalse((self.cold / 'replay.json').exists())

    def test_missing_closure_module_has_no_current_checkout_fallback(self):
        # Only this disposable index changes. The module still exists in the
        # developer checkout, so import must fail rather than loading live code.
        index_path = self.cold / NAMES[2] / 'archive-index.json'
        index = json.loads(index_path.read_bytes())
        relative = 'behavior_pack/modern_projection/projection/block_traits.py'
        matches = [row for row in index['files'] if row['project_relative_path'] == relative]
        self.assertEqual(len(matches), 1)
        (index_path.parent / matches[0]['archive_path']).unlink()
        index['files'] = [row for row in index['files'] if row not in matches]
        index_path.write_text(json.dumps(index), encoding='ascii')
        with self.assertRaisesRegex(ValueError, "No module named 'projection.block_traits'"):
            self.execute()
        self.assertFalse((self.cold / 'replay.json').exists())


if __name__ == '__main__':
    unittest.main()
