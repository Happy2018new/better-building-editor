"""An unrelated successful analysis cannot bless a different animation run."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_item_dense_motion_r17 import analyze


class DenseMotionEvidenceTests(unittest.TestCase):
    def test_mismatched_report_is_rejected_even_in_diagnostic_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            report=root/'report.json'; sparse=root/'sparse.json'
            report.write_text('{}',encoding='ascii')
            sparse.write_text(json.dumps({'source_sha256':'different', 'evidence_valid':True}),encoding='ascii')
            for diagnostic in (False,True):
                with self.assertRaisesRegex(ValueError,'does not belong'):
                    analyze(report,sparse,root/'out',diagnostic)
            self.assertFalse((root/'out').exists())

    def test_diagnostic_flag_never_bypasses_failed_capture_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            report=root/'report.json'; sparse=root/'sparse.json'
            report.write_text(json.dumps({'source_unchanged':True,'completed':True,
                                           'cleanup_errors':['fixture not restored']}),encoding='ascii')
            sparse.write_text(json.dumps({'source_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),
                                          'evidence_valid':False,'capture_failures':[],
                                          'native_closeup':{'reference_valid':True}}),encoding='ascii')
            with self.assertRaisesRegex(ValueError,'Base closeup evidence is invalid'):
                analyze(report,sparse,root/'out',True)
            self.assertFalse((root/'out').exists())


if __name__=='__main__':
    unittest.main()
