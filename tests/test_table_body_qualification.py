"""Only the reviewed table metadata flag may differ during default admission."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from qualify_table_body_r20 import qualified_data, check_report, ENGINE_VERSION
from probe_book_native_r16 import BODY_SOURCES, OWNER_SOURCES


class TableBodyQualificationTests(unittest.TestCase):
    def test_flag_write_preserves_all_other_bytes_and_is_idempotent(self):
        raw = b'# Generated\r\nSCHEMA_VERSION = 1\r\nPRODUCT_QUALIFIED = False\r\nPROXY = "table"\r\n'
        expected = raw.replace(b'= False', b'= True')
        self.assertEqual(expected, qualified_data(raw))
        self.assertEqual(expected, qualified_data(expected))

    def test_missing_duplicate_and_computed_flags_are_rejected(self):
        for raw in (b'OTHER = False\n', b'PRODUCT_QUALIFIED = bool(1)\n',
                    b'PRODUCT_QUALIFIED = False\nPRODUCT_QUALIFIED = True\n'):
            with self.subTest(source=raw), self.assertRaises(ValueError):
                qualified_data(raw)

    def test_default_body_requires_exact_sources_and_no_candidate_assignment(self):
        sources = {'owner_files': dict.fromkeys(OWNER_SOURCES, 'a'*64),
                   'body_files': dict.fromkeys(BODY_SOURCES, 'b'*64),
                   'contract_present': True, 'contract_sha256': 'c'*64,
                   'files': {'mesh': 'd'*64}, 'models': {'book': {}}, 'materials': {'book': {}}}
        for key in ('resource_pack/blocks.json', 'resource_pack/textures/terrain_texture.json'):
            sources[key] = {'body': 'registered'}
        report = {'engine': ENGINE_VERSION, 'installed_sources': sources,
                  'production_default_requested': True, 'profile_assignment_performed': False,
                  'default_profile': {'body_candidate_override': False}}
        with tempfile.TemporaryDirectory() as folder, patch('qualify_table_body_r20.analyze',
                return_value={'body_boundary_pixels_passed': True}):
            source = Path(folder)/'report.json'
            source.write_text(json.dumps(report), encoding='ascii')
            check_report(source, sources, Path(folder)/'analysis.json', default=True)
            report['profile_assignment_performed'] = True
            source.write_text(json.dumps(report), encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'candidate'):
                check_report(source, sources, Path(folder)/'analysis.json', default=True)
            report['profile_assignment_performed'] = False
            report['installed_sources'] = dict(sources, body_files=dict(sources['body_files']))
            report['installed_sources']['body_files'][BODY_SOURCES[0]] = 'e'*64
            source.write_text(json.dumps(report), encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'changed'):
                check_report(source, sources, Path(folder)/'analysis.json', default=True)


if __name__ == '__main__':
    unittest.main()
