import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from pack_chest_occupied_evidence_r10 import original_gates, state_matches


class OccupiedEvidenceGateTests(unittest.TestCase):
    def test_report_pass_flag_cannot_override_original_gates(self):
        value = {'passed': True, 'shape_iou': .9, 'texture_cosine': .6, 'scale_relative_error': .1,
                 'alignment': {'center_distance_pixels': 1, 'boundary_rms_pixels': 1}}
        self.assertTrue(original_gates(value, 1000))
        self.assertFalse(original_gates(value, 999))
        for key, bad in (('shape_iou', .81), ('texture_cosine', .44), ('texture_cosine', None),
                         ('scale_relative_error', .21)):
            with self.subTest(key=key, value=bad):
                self.assertFalse(original_gates(dict(value, **{key: bad}), 1000))
        for key, bad in (('center_distance_pixels', 3.5), ('boundary_rms_pixels', 4.1)):
            drifted = copy.deepcopy(value)
            drifted['alignment'][key] = bad
            self.assertFalse(original_gates(drifted, 1000))

    def test_occupied_half_requires_eviction_and_unchanged_document_history(self):
        row = {'active': True, 'ready': True, 'has_occupancy': True, 'tracked': True,
               'state': 2, 'rendered': 2, 'cache_slot': -1, 'error': None, 'failed': False,
               'preparing': False, 'building': False, 'pending': False, 'changed': 0,
               'document_preserved': True, 'history_preserved': True}
        self.assertTrue(state_matches(row, 2))
        self.assertFalse(state_matches(row, 1))
        for key, bad in (('cache_slot', 0), ('rendered', 1), ('document_preserved', False),
                         ('history_preserved', False), ('pending', True)):
            with self.subTest(key=key):
                self.assertFalse(state_matches(dict(row, **{key: bad}), 2))


if __name__ == '__main__':
    unittest.main()
