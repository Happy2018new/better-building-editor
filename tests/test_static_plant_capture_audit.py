"""Background plant acceptance permits normal application use, never game focus."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from audit_static_plant_matrix import audit, capture_status
from verify_fungus_remaining_matrix import record, source_errors


class StaticPlantCaptureAuditTests(unittest.TestCase):
    def test_legacy_matrix_audit_uses_the_background_capture_contract(self):
        from verify_fungus_remaining_matrix import audit
        matrix, output = Path('matrix.json'), Path('audit.json')
        expected = {'integrity_passed': True}
        with patch('audit_static_plant_matrix.audit', return_value=expected) as delegated:
            self.assertIs(expected, audit(matrix, output))
        delegated.assert_called_once_with(matrix, output)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        path = Path(self.directory.name)/'native.png'
        image = Image.new('RGB', (8, 8), 'red')
        ImageDraw.Draw(image).rectangle((0, 0, 3, 7), fill='blue')
        image.save(path)
        self.matrix = {'game_pid': 100, 'owner': 'owned-plant-test'}
        self.capture = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'capture': {'ok': True, 'reliable': True, 'background_only': True,
                                    'native_resolution': True, 'background_safe': True,
                                    'foreground_unchanged': False,
                                    'game_pid': 100, 'owner': 'owned-plant-test',
                                    'foreground_before': {'hwnd': 2, 'pid': 200},
                                    'foreground_after': {'hwnd': 3, 'pid': 300},
                                    'frame': {'frame_qpc_100ns': 11, 'request_qpc_100ns': 10,
                                              'width': 8, 'height': 8}}}

    def test_other_application_switch_is_preserved_without_failing_safe_capture(self):
        errors, switch = capture_status(self.capture, self.matrix)
        self.assertEqual([], errors)
        self.assertEqual(self.capture['capture']['foreground_before'], switch['foreground_before'])
        self.assertEqual(self.capture['capture']['foreground_after'], switch['foreground_after'])
        self.assertIn('Allowed ordinary switching', switch['classification'])

    def test_owned_game_foreground_is_rejected_before_or_after_capture(self):
        for field in ('foreground_before', 'foreground_after'):
            with self.subTest(field=field):
                capture = deepcopy(self.capture)
                capture['capture'][field]['pid'] = 100
                errors, switch = capture_status(capture, self.matrix)
                self.assertTrue(any('owned game was foreground' in error for error in errors))
                self.assertIn('Untrusted', switch['classification'])

    def test_stale_frame_or_wrong_owner_is_rejected(self):
        capture = deepcopy(self.capture)
        capture['capture']['frame']['frame_qpc_100ns'] = 10
        capture['capture']['owner'] = 'different-task'
        errors, unused = capture_status(capture, self.matrix)
        self.assertTrue(any('frame predates' in error for error in errors))
        self.assertTrue(any('ownership differs' in error for error in errors))

    def test_unreliable_metadata_and_changed_native_png_are_rejected(self):
        capture = deepcopy(self.capture)
        capture['capture']['reliable'] = False
        capture['sha256'] = '0'*64
        errors, unused = capture_status(capture, self.matrix)
        self.assertTrue(any('background capture gate' in error for error in errors))
        self.assertTrue(any('original PNG changed' in error for error in errors))

    def test_actual_blank_png_is_rejected_even_when_metadata_claims_reliability(self):
        path = Path(self.capture['path'])
        Image.new('RGB', (8, 8), 'black').save(path)
        self.capture['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        errors, unused = capture_status(self.capture, self.matrix)
        self.assertTrue(any('native PNG is blank' in error for error in errors))

    def test_repeated_audit_keeps_original_sheets_and_pngs_unchanged(self):
        directory = Path(self.directory.name)
        original_sheet = directory/'report_inspect.png'
        original_sheet.write_bytes(b'previous immutable inspection')
        report = directory/'report.json'
        image_row = {'screenshot': self.capture}
        value = {'cleanup_errors': [], 'native_cleanup': [{'clean': True}],
                 'limits': {'native_recall': .75, 'native_precision': .75,
                            'native_edge_tolerance_pixels': 3},
                 'rows': [{'kind': 'plant', 'plant': 'poppy', 'height': 0, 'masks': {},
                           'crop': [0, 0, 8, 8], 'editor_crop': [0, 0, 8, 8],
                           'native': image_row, 'world': {'full': image_row, 'missing': image_row},
                           'editor': self.capture}], 'view': 'public'}
        report.write_text(json.dumps(value), encoding='utf8')
        source_file = directory/'original-source.py'
        source_file.write_bytes(b'captured original code')
        frozen = directory/'frozen.json'
        frozen.write_text(json.dumps({'hashes_sha256': {source_file.name: record(source_file)['sha256']}}))
        matrix_path = directory/'matrix.json'
        matrix = dict(self.matrix, rows=[record(report)], frozen_source=record(frozen),
                      completed=True, restored=True, passed=False)
        matrix_path.write_text(json.dumps(matrix), encoding='utf8')
        originals = {path: path.read_bytes() for path in
                     (original_sheet, report, source_file, frozen, matrix_path, Path(self.capture['path']))}
        for attempt in ('first', 'second'):
            output = directory/(attempt+'.json')
            sheets = directory/attempt
            result = audit(matrix_path, output, inspection_dir=sheets, source_root=directory)
            self.assertTrue(result['integrity_passed'])
            self.assertFalse(result['matrix_passed'])
            self.assertEqual(1, result['unique_native_pngs_audited'])
            self.assertEqual((sheets/'report_inspect.png').resolve(),
                             Path(result['inspection_sheets'][0]['path']))
        self.assertEqual(originals, {path: path.read_bytes() for path in originals})
        with self.assertRaisesRegex(ValueError, 'Inspection PNG must be fresh'):
            audit(matrix_path, directory/'collision.json', directory/'first', directory)

    def test_restored_sources_use_exact_archive_bytes_and_reject_corrupt_overrides(self):
        directory = Path(self.directory.name)
        project, archive = directory/'project', directory/'archive'
        project.mkdir()
        archive.mkdir()
        for name in ('candidate.json', 'shared.py'):
            (project/name).write_bytes(b'original '+name.encode('ascii'))
        frozen = {'hashes_sha256': {name: record(project/name)['sha256']
                                    for name in ('candidate.json', 'shared.py')}}
        self.assertEqual([], source_errors(frozen, root=project))
        (archive/'candidate.json').write_bytes((project/'candidate.json').read_bytes())
        (project/'candidate.json').unlink()
        self.assertEqual(['candidate.json'], source_errors(frozen, root=project))
        self.assertEqual([], source_errors(frozen, root=project, archive=archive))
        (archive/'shared.py').write_bytes(b'changed archive must not fall back to live code')
        self.assertEqual(['shared.py'], source_errors(frozen, root=project, archive=archive))


if __name__ == '__main__':
    unittest.main()
