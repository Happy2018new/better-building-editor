"""A repeated depth inspection must preserve every existing evidence artifact."""
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from measure_flat_frame_pose import output_paths


class FlatFramePoseOutputTests(unittest.TestCase):
    def test_existing_input_or_report_is_preserved(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'native.json'
            path.write_bytes(b'original native report')
            with self.assertRaisesRegex(ValueError, 'Preserve existing evidence'):
                output_paths(path, ['left', 'right'])
            self.assertEqual(b'original native report', path.read_bytes())
            self.assertEqual([path], list(path.parent.iterdir()))

    def test_existing_comparison_rejects_before_any_new_output(self):
        with TemporaryDirectory() as directory:
            report = Path(directory)/'inspection.json'
            occupied = report.with_name('inspection_right_comparison.png')
            occupied.write_bytes(b'original comparison')
            with self.assertRaisesRegex(ValueError, 'Preserve existing evidence'):
                output_paths(report, ['left', 'right'])
            self.assertEqual(b'original comparison', occupied.read_bytes())
            self.assertEqual([occupied], list(report.parent.iterdir()))

    def test_distinct_labels_are_safe_and_output_paths_are_stable(self):
        with TemporaryDirectory() as directory:
            report = Path(directory)/'inspection.json'
            expected = [report.resolve().with_name('inspection_'+view+'_comparison.png')
                        for view in ('left', 'right')]
            self.assertEqual(expected, output_paths(report, ['left', 'right']))
            for labels in (['left', 'left'], ['../left'], [''], ['left/right']):
                with self.subTest(labels=labels), self.assertRaises(ValueError):
                    output_paths(report, labels)
            self.assertEqual([], list(report.parent.iterdir()))


if __name__ == '__main__':
    unittest.main()
