"""Moving-cover white fragments must survive the diagnostic's color filter."""
from pathlib import Path
from contextlib import redirect_stdout
import hashlib
import io
import json
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_book_motion_r20 import analyze, white_cover_fragments


class BookMotionAnalysisTests(unittest.TestCase):
    def make_burst(self, root, corrupt=False, stale=False):
        directory = root/'editor_active'
        directory.mkdir()
        frames, artifacts = [], []
        for index in range(80):
            image = Image.new('RGB', (500, 400), (129, 86, 37))
            image.putpixel((250, 200), (129+(0 if stale else index % 80), 86, 37))
            if corrupt and index == 40:
                for y in range(160, 200, 5):
                    for x in range(210, 250, 5):
                        image.putpixel((x, y), (220, 220, 210))
            path = directory/('frame_%06d.png' % index)
            image.save(path)
            artifacts.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            frames.append({'sequence': index, 'png': path.name, 'capture_valid': True,
                           'frame_qpc_100ns': 100000000+index*2200000})
        manifest = dict(frames=frames, valid_frames=80, planned_duration_ms=17600,
                        max_gap_ms=250, maximum_gap_100ns=2200000,
                        request_qpc_100ns=100000000, planned_end_qpc_100ns=276000000)
        path = directory/'manifest.json'
        path.write_text(json.dumps(manifest), encoding='ascii')
        capture = dict(capture_valid=True, temporal_complete=True, native_resolution=True,
                       activation_fallback=False, artifacts=artifacts,
                       native_manifest_file={'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        route = dict(capture=capture, frozen=False, fixed_camera=True,
                     trace={'rows': [[0, [0, 0, 0], 0, False, '', ['stable-owner']]], 'overflow': False})
        report = dict(schema_version=1, engine='3.10.0.420447', completed=True,
                      restored=True, cleanup_errors=[], source_unchanged=True,
                      source_before={'mesh': 'exact'}, source_after={'mesh': 'exact'},
                      routes={'editor_active': route})
        source = root/'report.json'
        source.write_text(json.dumps(report), encoding='ascii')
        return source, report

    def measure(self, source):
        with redirect_stdout(io.StringIO()):
            return analyze(source, source.parent/'analysis.json')

    def test_dense_motion_rejects_white_corruption_with_the_original_limit(self):
        for corrupt in (False, True):
            with tempfile.TemporaryDirectory() as folder:
                source, report = self.make_burst(Path(folder), corrupt=corrupt)
                measured = self.measure(source)
                self.assertTrue(measured['diagnostic_valid'])
                self.assertEqual(not corrupt, measured['dense_cover_motion_passed'])
                self.assertEqual(8, measured['maximum_allowed_isolated_pixels'])

    def test_stale_content_aliases_and_changed_pixels_cannot_admit_motion(self):
        with tempfile.TemporaryDirectory() as folder:
            source, report = self.make_burst(Path(folder), stale=True)
            measured = self.measure(source)
            self.assertFalse(measured['checks']['motion_content_changes'])
            self.assertFalse(measured['dense_cover_motion_passed'])
        with tempfile.TemporaryDirectory() as folder:
            source, report = self.make_burst(Path(folder))
            report['alias_sources'] = report['alias_sources_after'] = {'diagnostic': True}
            report['alias_source_unchanged'] = True
            source.write_text(json.dumps(report), encoding='ascii')
            self.assertFalse(self.measure(source)['dense_cover_motion_passed'])
            (source.parent/'editor_active/frame_000000.png').write_bytes(b'changed pixels')
            with self.assertRaisesRegex(ValueError, 'pixels differ'):
                self.measure(source)

    def test_claimed_temporal_completeness_cannot_hide_a_real_gap(self):
        with tempfile.TemporaryDirectory() as folder:
            source, report = self.make_burst(Path(folder))
            path = source.parent/'editor_active/manifest.json'
            manifest = json.loads(path.read_bytes())
            manifest['frames'][40]['frame_qpc_100ns'] += 1000000
            path.write_text(json.dumps(manifest), encoding='ascii')
            report['routes']['editor_active']['capture']['native_manifest_file']['sha256'] = (
                hashlib.sha256(path.read_bytes()).hexdigest())
            source.write_text(json.dumps(report), encoding='ascii')
            measured = self.measure(source)
            self.assertGreater(measured['maximum_measured_gap_ms'], 250)
            self.assertFalse(measured['dense_cover_motion_passed'])

    def test_white_internal_fragments_are_detected(self):
        image = np.full((60, 80, 3), (129, 86, 37), dtype=np.int16)
        image[25, 35] = (220, 220, 210)
        image[35, 45] = (180, 180, 180)
        image[36, 46] = (180, 180, 180)
        self.assertEqual(3, white_cover_fragments(image).sum())

    def test_page_silhouette_and_white_background_are_excluded(self):
        image = np.full((60, 80, 3), (245, 245, 245), dtype=np.int16)
        image[10:50, 10:70] = (129, 86, 37)
        image[10:12, 10:70] = (220, 220, 210)
        image[30:50, 50:70] = (220, 220, 210)
        self.assertEqual(0, white_cover_fragments(image).sum())

    def test_artwork_and_foliage_are_excluded(self):
        image = np.full((60, 80, 3), (18, 65, 12), dtype=np.int16)
        image[10:50, 10:70] = (129, 86, 37)
        image[20:40, 20:60] = (78, 51, 22)
        self.assertEqual(0, white_cover_fragments(image).sum())

    def test_long_page_edge_is_not_counted_as_detached_fragments(self):
        image = np.full((60, 80, 3), (129, 86, 37), dtype=np.int16)
        image[15, 15:65] = (220, 220, 210)
        image[35, 35] = (220, 220, 210)
        self.assertEqual(1, white_cover_fragments(image).sum())


if __name__ == '__main__':
    unittest.main()
