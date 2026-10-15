"""Extra delayed frames must strengthen, never replace, the public matrix."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from qualify_spawner_product_r16 import capture_matrix, validate_matrix
from analyze_spawner_product_r16 import retained_frame


class SpawnerQualificationMatrixTests(unittest.TestCase):
    def evidence(self, default=False, delayed=False):
        required, followups = capture_matrix(default)
        captures = required | followups if delayed else required
        analysis = {
            'rows': {name: {'observed_badge_difference': True} for name in required
                     if name.endswith(('_badge', '_restored', '_full'))},
            'retained_support': {name: {'retained_support_observed': True}
                                 for name in captures if retained_frame(name)}}
        return captures, analysis

    def test_legacy_and_extended_matrices_preserve_every_declared_case(self):
        for default in (False, True):
            for delayed in (False, True):
                with self.subTest(default=default, delayed=delayed):
                    captures, analysis = self.evidence(default, delayed)
                    self.assertEqual((54 if default else 72) + (24 if delayed else 0), len(captures))
                    validate_matrix(captures, analysis, default)

    def test_same_count_with_wrong_or_missing_case_is_rejected(self):
        captures, analysis = self.evidence()
        captures.remove('full_trial_spawner_unknown_badge')
        captures.add('full_trial_spawner_unverified_badge')
        with self.assertRaisesRegex(ValueError, 'declared cases'):
            validate_matrix(captures, analysis, False)

    def test_delayed_blank_or_unanalyzed_frame_cannot_be_hidden_by_good_initial_frame(self):
        for missing in (False, True):
            captures, analysis = self.evidence(delayed=True)
            label = 'editor_trial_spawner_unknown_badge_section_later_1.5'
            if missing:
                del analysis['retained_support'][label]
            else:
                analysis['retained_support'][label]['retained_support_observed'] = False
            with self.assertRaisesRegex(ValueError, 'omits or fails'):
                validate_matrix(captures, analysis, False)


if __name__ == '__main__':
    unittest.main()
