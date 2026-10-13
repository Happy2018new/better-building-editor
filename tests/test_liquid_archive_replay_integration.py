"""Cold-replay real committed liquid evidence without launching a game.

The archives are expected in docs/evidence after the owning agent's commits
are integrated. BBE_LIQUID_REPLAY_EVIDENCE_ROOT can select a staging archive
root; that root supplies bytes only, never imports or live runtime access.
"""
import importlib.util
import hashlib
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


@unittest.skipUnless((EVIDENCE / 'liquid-native-write-r13-v4b/archive-index.json').is_file(),
                     'Exact mixed V4b archive is not integrated in this checkout')
class MixedColdReplay(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='bbe-liquid-v4b-cold-test-')
        self.addCleanup(self.directory.cleanup)
        self.cold = Path(self.directory.name)
        self.archive = self.cold / 'archive'
        shutil.copytree(EVIDENCE / 'liquid-native-write-r13-v4b', self.archive)
        helper_path = self.cold / 'replay.py'
        shutil.copyfile(ROOT / 'tools/replay_liquid_native_archive.py', helper_path)
        spec = importlib.util.spec_from_file_location('mixed_cold_replay_helper', helper_path)
        self.helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.helper)
        self.index_path = self.archive / 'archive-index.json'
        self.original_index = self.index_path.read_bytes()

    def execute(self):
        return self.helper.replay(self.archive, 'archive-index.json', self.cold / 'replay.json',
                                  expected_name='native-write-analysis.json')

    def rewrite_index(self, index):
        self.index_path.write_text(json.dumps(index), encoding='ascii')

    def test_single_mixed_archive_reproduces_exact_observation_and_alias_manifest(self):
        report = self.execute()
        expected = json.loads((self.archive / 'native-write-analysis.json').read_bytes())
        self.assertTrue(report['reproduced'])
        self.assertEqual(report['schema'], 2)
        self.assertEqual(replay.semantic_result(report['recomputed']), replay.semantic_result(expected))
        self.assertEqual(report['recomputed']['status'], 'OBSERVED')
        self.assertTrue(report['recomputed']['native_visibility_observed'])
        for name in ('side_uv_qualified', 'transparency_qualified', 'animation_qualified', 'production_qualified'):
            self.assertFalse(report['recomputed'][name])
        self.assertEqual(len(report['imported_source_sha256']), 46)
        self.assertEqual(len(report['source_alias_manifests']), 1)
        manifest = report['source_alias_manifests'][0]
        self.assertEqual(manifest['schema'], 1)
        self.assertEqual(len(manifest['sources']), 117)
        self.assertEqual(manifest['archive_index_sha256'], hashlib.sha256(self.original_index).hexdigest())
        self.assertEqual(report['new_launches'], 0)
        self.assertEqual(report['sdk_or_network_calls'], 0)
        self.assertEqual(self.index_path.read_bytes(), self.original_index)

    def test_non_source_bytes_are_verified_even_when_excluded_from_imports(self):
        index = json.loads(self.original_index)
        row = next(row for row in index['files'] if row['archive_path'].endswith('.png'))
        path = self.archive / row['archive_path']
        path.write_bytes(path.read_bytes() + b'tampered')
        with self.assertRaisesRegex(ValueError, 'Archived original bytes changed'):
            self.execute()
        self.assertFalse((self.cold / 'replay.json').exists())

    def test_source_newlines_still_refuse_through_project_alias(self):
        path = self.archive / 'sources/tools/analyze_liquid_native_write.py'
        raw = path.read_bytes()
        self.assertIn(b'\n', raw)
        changed = raw.replace(b'\r\n', b'\n') if b'\r\n' in raw else raw.replace(b'\n', b'\r\n')
        self.assertNotEqual(raw, changed)
        path.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, 'Archived original bytes changed'):
            self.execute()
        self.assertFalse((self.cold / 'replay.json').exists())

    def test_modified_geometry_plan_and_reindexed_hash_do_not_replace_original_binding(self):
        path = self.archive / 'original-priority_geometry_plan.json'
        plan = json.loads(path.read_bytes())
        plan['source_bindings']['tools/analyze_liquid_sides.py']['sha256'] = '0' * 64
        path.write_text(json.dumps(plan), encoding='ascii')
        index = json.loads(self.original_index)
        row = next(row for row in index['files'] if row['archive_path'] == path.name)
        row.update(sha256=replay.digest(path), bytes=path.stat().st_size)
        self.rewrite_index(index)
        with self.assertRaisesRegex(ValueError, 'Original reference is missing or changed'):
            self.execute()
        self.assertFalse((self.cold / 'replay.json').exists())

    def test_missing_mixed_source_cannot_import_current_checkout(self):
        index = json.loads(self.original_index)
        relative = 'behavior_pack/modern_projection/projection/block_traits.py'
        row = next(row for row in index['files'] if row.get('project_relative_path') == relative)
        (self.archive / row['archive_path']).unlink()
        index['files'].remove(row)
        self.rewrite_index(index)
        with self.assertRaisesRegex(ValueError, "No module named 'projection.block_traits'"):
            self.execute()
        self.assertFalse((self.cold / 'replay.json').exists())


if __name__ == '__main__':
    unittest.main()
