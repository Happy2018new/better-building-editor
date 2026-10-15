"""Reject forged or missing shared controls before replaying a second plant."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_snow_product_r20 import reuse_snow_control


class SnowSharedControlR20Tests(unittest.TestCase):
    def setUp(self):
        self.source = {'editor': {'sha256': 'editor-hash'}, 'world': {
            mode: {'screenshot': {'sha256': mode + '-hash'}} for mode in ('full', 'missing')}}
        self.row = {'plant': 'fern', 'kind': 'snow', 'height': 4, 'shared_snow_control': {
            'plant': 'blue_orchid', 'height': 4, 'editor_sha256': 'editor-hash',
            'full_sha256': 'full-hash', 'missing_sha256': 'missing-hash'}}
        self.frames = {(mode, 'blue_orchid', 'snow', 4): object()
                       for mode in ('editor', 'full', 'missing')}

    def test_reuse_requires_same_preceding_source_and_all_three_capture_hashes(self):
        reuse_snow_control(self.row, {('blue_orchid', 4): self.source}, self.frames)
        for mode in ('editor', 'full', 'missing'):
            self.assertIs(self.frames[(mode, 'blue_orchid', 'snow', 4)],
                          self.frames[(mode, 'fern', 'snow', 4)])
        for changed in ('plant', 'height', 'editor_sha256', 'full_sha256', 'missing_sha256'):
            row = copy.deepcopy(self.row)
            row['shared_snow_control'][changed] = 7 if changed == 'height' else 'forged'
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                reuse_snow_control(row, {('blue_orchid', 4): self.source}, self.frames)
        with self.assertRaises(ValueError):
            reuse_snow_control(self.row, {}, self.frames)


if __name__ == '__main__':
    unittest.main()
