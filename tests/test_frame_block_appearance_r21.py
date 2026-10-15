"""Pixel comparisons must expose lighting gain and texture rearrangement."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import analyze_frame_block_appearance_r21 as appearance
import prepare_frame_block_light_r21 as candidate
import archive_frame_block_appearance_r21 as archive


class FrameBlockAppearance(unittest.TestCase):
    def test_lighting_gain_is_not_normalized_out_of_the_pixel_errors(self):
        native = np.array([[20, 20, 20], [50, 50, 50], [80, 80, 80]], dtype=np.uint8)
        row = appearance.color_pair(native, native*2)
        self.assertEqual([50., 50., 50.], row['mean_absolute_rgb'])
        self.assertAlmostEqual(2., row['mean_luma_ratio'])
        self.assertAlmostEqual(1., row['texture_luma_correlation'])
        self.assertFalse(row['fitted_alignment_or_color_correction'])

    def test_identical_histograms_do_not_hide_a_wrong_uv_orientation(self):
        native = np.array([[10, 10, 10], [50, 50, 50], [90, 90, 90]], dtype=np.uint8)
        row = appearance.color_pair(native, native[::-1])
        self.assertEqual([0., 0., 0.], row['mean_signed_rgb'])
        self.assertGreater(row['mean_absolute_rgb'][0], 50.)
        self.assertAlmostEqual(-1., row['texture_luma_correlation'])
        self.assertAlmostEqual(1./3., row['identical_pixel_fraction'])

    def test_base_candidate_does_not_scale_independent_glint_or_alpha(self):
        original = (ROOT / candidate.FRAGMENT).read_text(encoding='ascii')
        for newline in ('\n', '\r\n'):
            with self.subTest(newline=repr(newline)):
                source = original.replace('\n', newline)
                changed = candidate.correct_base_light(source)
                self.assertIn('itemFrame>0.5 ? 0.93 : 1.0', changed)
                suffix = '    if(itemEnchanted>0.5)'
                self.assertEqual(source[source.index(suffix):], changed[changed.index(suffix):])
                self.assertEqual(source.count(newline) + 2, changed.count(newline))
                if newline == '\r\n':
                    self.assertNotIn('\n', changed.replace('\r\n', ''))
                with self.assertRaises(ValueError):
                    candidate.correct_base_light(changed)

    def test_candidate_archive_rejects_extra_glint_changes_even_with_updated_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'holdouts/sources' / candidate.FRAGMENT
            source.parent.mkdir(parents=True)
            source.write_text(candidate.ORIGINAL + '\n    glint=1.0;\n', encoding='ascii')
            changed = root / 'candidate' / candidate.FRAGMENT
            changed.parent.mkdir(parents=True)
            changed.write_text(candidate.correct_base_light(source.read_text(encoding='ascii')), encoding='ascii')
            metadata = {'production_qualified': False, 'native_pixels_accepted': False,
                'native_cause_established': False, 'base_light': .93,
                'files': {candidate.FRAGMENT: archive.digest(changed)},
                'source_file_sha256': {candidate.FRAGMENT: archive.digest(source)},
                'changed_paths': [candidate.FRAGMENT]}
            manifest = root / 'candidate/candidate.json'
            manifest.write_text(json.dumps(metadata), encoding='ascii')
            archive.candidate_differences(root / 'candidate', root / 'holdouts')
            changed.write_text(changed.read_text(encoding='ascii').replace('glint=1.0', 'glint=0.93'), encoding='ascii')
            metadata['files'][candidate.FRAGMENT] = archive.digest(changed)
            manifest.write_text(json.dumps(metadata), encoding='ascii')
            with self.assertRaises(AssertionError):
                archive.candidate_differences(root / 'candidate', root / 'holdouts')

    def test_archive_paths_cannot_escape_the_evidence_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                archive.contained(Path(directory), '../private-session.json')


if __name__ == '__main__':
    unittest.main()
