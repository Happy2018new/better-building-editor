"""Independent clock evidence must distinguish directions and reject aliases."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_liquid_engine_clock import direction


class NativeClockTests(unittest.TestCase):
    def samples(self, sign):
        return [{'red': (2 + sign * index * 2) % 256, 'qpc': index * 625000,
                 'support_pixels': 600} for index in range(20)]

    def test_wrap_distinguishes_positive_and_negative_clock(self):
        for sign in (-1, 1):
            with self.subTest(sign=sign):
                result = direction(self.samples(sign))
                self.assertTrue(result['passed'])
                self.assertEqual(sign, result['clock_direction'])

    def test_static_mixed_polarity_and_sparse_pixels_are_rejected(self):
        static = self.samples(0)
        mixed = self.samples(1)
        mixed[10]['red'] = 15
        sparse = self.samples(-1)
        sparse[10]['support_pixels'] = 2
        for samples in (static, mixed, sparse, self.samples(1)[:7]):
            self.assertFalse(direction(samples)['passed'])

    def test_local_time_reversal_repetition_and_temporal_alias_are_rejected(self):
        for replacement in (0, 9 * 625000, 20000000):
            samples = self.samples(1)
            samples[10]['qpc'] = replacement
            self.assertFalse(direction(samples)['passed'])


if __name__ == '__main__':
    unittest.main()
