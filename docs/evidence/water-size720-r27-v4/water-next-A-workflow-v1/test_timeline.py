"""Clock accounting controls; synthetic timestamps never claim capture acceptance."""
import copy
import unittest
from inspect_timeline import inspect


def frame(sequence, source, before, readback, valid=True):
    return {'sequence': sequence, 'capture_valid': valid, 'frame_qpc_100ns': source,
            'before': {'observed_qpc_100ns': before},
            'after_readback': {'observed_qpc_100ns': readback},
            'capture_last_window_state': {'observed_qpc_100ns': readback},
            'initial_timestamp_assessment': {'observed_qpc_100ns': before}}


def manifest(frames):
    return {'request_qpc_100ns': 10000000, 'planned_end_qpc_100ns': 42000000,
            'frames': frames, 'max_gap_ms': 150, 'capture_valid': True,
            'temporal_complete': False, 'ok': False}


class TimelineTests(unittest.TestCase):
    def test_stale_source_pair_and_worker_pair_are_distinct(self):
        raw = manifest([frame(1, 11000000, 11010000, 11020000),
                        frame(2, 11500000, 16500000, 16520000),
                        frame(3, 17000000, 17100000, 17120000)])
        value = inspect(raw)
        self.assertEqual((2, 3), tuple(value['largest_source_gap'][key] for key in
                                      ('first_sequence', 'second_sequence')))
        self.assertEqual((1, 2), tuple(value['largest_worker_unobserved_interval'][key] for key in
                                      ('first_sequence', 'second_sequence')))
        self.assertFalse(value['source_and_worker_maximum_same_pair'])
        self.assertEqual(550., value['largest_source_gap']['source_gap_ms'])

    def test_missing_zero_readback_stays_null(self):
        value = inspect(manifest([frame(1, 9999999, 10001000, 0, False),
                                  frame(2, 10001000, 10002000, 10003000)]))
        self.assertIsNone(value['per_attempt'][0]['readback_qpc_100ns'])
        self.assertIsNone(value['per_attempt'][0]['poll_through_readback_ms'])

    def test_invalid_attempt_does_not_hide_gap_between_valid_sources(self):
        value = inspect(manifest([frame(1, 11000000, 11010000, 11020000),
                                  frame(2, 12000000, 12010000, 0, False),
                                  frame(3, 14000000, 14010000, 14020000)]))
        self.assertEqual(300., value['source_gap_exceedances'][0]['source_gap_ms'])
        self.assertEqual(2, value['valid_frames'])

    def test_fixed_origin_boundaries_and_input_are_preserved(self):
        raw = manifest([frame(1, 10100000, 10110000, 10120000),
                        frame(2, 41900000, 41910000, 41920000)])
        before = copy.deepcopy(raw)
        value = inspect(raw)
        self.assertEqual(3200., value['fixed_measurement_ms'])
        self.assertEqual(10., value['start_source_gap_ms'])
        self.assertEqual(10., value['tail_source_gap_ms'])
        self.assertEqual(before, raw)
        self.assertFalse(value['formal_A_accepted'])

    def test_empty_attempt_has_no_fabricated_timestamps_or_maxima(self):
        value = inspect(manifest([]))
        self.assertIsNone(value['largest_source_gap'])
        self.assertIsNone(value['largest_worker_unobserved_interval'])
        self.assertIsNone(value['start_source_gap_ms'])
        self.assertEqual([], value['source_gap_exceedances'])


if __name__ == '__main__':
    unittest.main()
