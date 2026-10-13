"""Raw provenance survives relocation; tampering and checkout fallback refuse."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('liquid_archive_replay', ROOT / 'tools/replay_liquid_native_archive.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


class RawArchiveBindings(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.raw = b"VALUE = 17\r\n"
        self.original = 'Z:/retired-development-machine/tools/analyze_liquid_native_write.py'
        (self.root / 'raw').mkdir()
        (self.root / 'raw/scorer.py').write_bytes(self.raw)
        self.record = {'original_path': self.original, 'archive_path': 'raw/scorer.py',
                       'bytes': len(self.raw), 'sha256': hashlib.sha256(self.raw).hexdigest()}
        self.write_index([self.record])
        self.closure = {'schema': 1, 'analyzer': 'tools/analyze_liquid_native_write.py',
                        'files': {'tools/analyze_liquid_native_write.py': {
                            key: self.record[key] for key in ('original_path', 'archive_path', 'sha256')}}}
        (self.root / 'closure.json').write_text(json.dumps(self.closure), encoding='ascii')

    def write_index(self, records):
        (self.root / 'archive-index.json').write_text(json.dumps({'schema': 1, 'files': records}), encoding='ascii')

    def test_retired_absolute_path_resolves_exact_crlf_bytes_without_checkout(self):
        archive = replay.Archive(self.root)
        path = archive.resolve({'path': self.original, 'sha256': self.record['sha256']})
        self.assertEqual(path.read_bytes(), self.raw)
        _, files, _ = replay.verify_closure(archive, 'closure.json')
        self.assertEqual(files['tools/analyze_liquid_native_write.py'], path)

    def test_same_python_content_with_different_newlines_is_rejected(self):
        # The AST is identical, but byte provenance is deliberately different.
        (self.root / 'raw/scorer.py').write_bytes(self.raw.replace(b'\r\n', b'\n'))
        with self.assertRaisesRegex(ValueError, 'original bytes changed'):
            replay.Archive(self.root)

    def test_source_hash_cannot_fall_back_to_a_live_original_file(self):
        live = self.root / 'otherwise-correct-current-source.py'
        live.write_bytes(self.raw)
        archive = replay.Archive(self.root)
        with self.assertRaisesRegex(ValueError, 'missing or changed'):
            archive.resolve({'path': str(live.resolve()), 'sha256': self.record['sha256']})

    def test_unindexed_closure_and_duplicate_original_references_refuse(self):
        (self.root / 'raw/unindexed.py').write_bytes(self.raw)
        self.closure['files']['tools/analyze_liquid_native_write.py']['archive_path'] = 'raw/unindexed.py'
        (self.root / 'closure.json').write_text(json.dumps(self.closure), encoding='ascii')
        with self.assertRaisesRegex(ValueError, 'exact indexed bytes'):
            replay.verify_closure(replay.Archive(self.root), 'closure.json')
        self.write_index([self.record, self.record])
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            replay.Archive(self.root)

    def test_archive_and_closure_cannot_escape_declared_roots(self):
        bad = dict(self.record, archive_path='../outside.py')
        self.write_index([bad])
        with self.assertRaisesRegex(ValueError, 'contained relative'):
            replay.Archive(self.root)
        self.write_index([self.record])
        self.closure['files']['../tools/analyze_liquid_native_write.py'] = self.closure['files'].pop(
            'tools/analyze_liquid_native_write.py')
        (self.root / 'closure.json').write_text(json.dumps(self.closure), encoding='ascii')
        with self.assertRaisesRegex(ValueError, 'source closure path'):
            replay.verify_closure(replay.Archive(self.root), 'closure.json')

    def test_comparison_keeps_all_hash_pixel_and_acceptance_values(self):
        original = {'source': {'path': 'old', 'sha256': 'a'},
                    'geometry_plan': {'path': 'old', 'sha256': 'b'},
                    'analyzer': {'path': 'old', 'sha256': 'c'},
                    'cases': {'pixels': 0}, 'status': 'FAIL', 'production_qualified': False}
        relocated = json.loads(json.dumps(original))
        for key in ('source', 'geometry_plan', 'analyzer'):
            relocated[key]['path'] = 'relocated'
        self.assertEqual(replay.semantic_result(original), replay.semantic_result(relocated))
        relocated['cases']['pixels'] = 1
        self.assertNotEqual(replay.semantic_result(original), replay.semantic_result(relocated))
        relocated['cases']['pixels'] = 0
        relocated['source']['sha256'] = 'changed'
        self.assertNotEqual(replay.semantic_result(original), replay.semantic_result(relocated))

    def supplement(self, relative='tools/analyze_liquid_native_write.py', original=None, raw=None):
        root = self.root / 'supplement'
        root.mkdir()
        content = self.raw if raw is None else raw
        (root / 'source.py').write_bytes(content)
        row = {'project_relative_path': relative, 'original_path': original or self.original,
               'archive_path': 'source.py', 'bytes': len(content),
               'sha256': hashlib.sha256(content).hexdigest()}
        (root / 'archive-index.json').write_text(json.dumps({'schema': 1, 'files': [row]}), encoding='ascii')
        return replay.Archive(root)

    def test_immutable_supplements_may_repeat_only_exact_source_bindings(self):
        original_index = (self.root / 'archive-index.json').read_bytes()
        archive = replay.Archive(self.root)
        supplement = self.supplement()
        archive.extend(supplement)
        _, files, _ = replay.verify_closure(archive, 'closure.json', archive, [supplement])
        self.assertEqual(files['tools/analyze_liquid_native_write.py'].read_bytes(), self.raw)
        self.assertEqual((self.root / 'archive-index.json').read_bytes(), original_index)

    def test_supplement_cannot_change_raw_original_reference(self):
        archive = replay.Archive(self.root)
        supplement = self.supplement(raw=self.raw.replace(b'\r\n', b'\n'))
        with self.assertRaisesRegex(ValueError, 'changes an original archive binding'):
            archive.extend(supplement)

    def test_supplement_cannot_replace_project_source_with_different_origin(self):
        archive = replay.Archive(self.root)
        supplement = self.supplement(original='Z:/unrelated-source.py')
        archive.extend(supplement)
        with self.assertRaisesRegex(ValueError, 'changes a source closure binding'):
            replay.verify_closure(archive, 'closure.json', archive, [supplement])

    def test_worker_cwd_restores_even_when_frozen_import_refuses(self):
        previous = os.getcwd()
        with self.assertRaisesRegex(ValueError, 'frozen import refused'):
            with replay.isolated_cwd(self.root):
                self.assertEqual(Path.cwd(), self.root)
                raise ValueError('frozen import refused')
        self.assertEqual(os.getcwd(), previous)


if __name__ == '__main__':
    unittest.main()
