"""A body pixel gate must reject residue on every face and missing support."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_book_body_boundary_r19 import FACES, STATES, analyze, measure_view


def fixture():
    blank = Image.new('RGB', (80, 80), (120, 180, 220))
    control = blank.copy()
    ImageDraw.Draw(control).rectangle((5, 50, 74, 74), fill=(100, 100, 100))
    shown = control.copy()
    ImageDraw.Draw(shown).rectangle((20, 10, 59, 39), fill=(30, 20, 30))
    images = dict.fromkeys(STATES, control)
    images.update(shown=shown, restored=shown, blank=blank, legacy_negative=shown)
    face = Image.new('L', blank.size)
    ImageDraw.Draw(face).rectangle((20, 10, 59, 39), fill=255)
    support = Image.new('L', blank.size)
    ImageDraw.Draw(support).rectangle((5, 50, 74, 74), fill=255)
    return images, face, support


class BookBodyBoundaryPixelsTests(unittest.TestCase):
    def test_removal_restore_negative_and_support_are_all_required(self):
        for face in FACES:
            images, mask, support = fixture()
            self.assertTrue(measure_view(images, mask, support, face)['passed'])
            images['occupied'] = images['occupied'].copy()
            images['occupied'].putpixel((35, 25), (20, 10, 20))
            measured = measure_view(images, mask, support, face)
            self.assertFalse(measured['passed'])
            self.assertEqual(1, measured['occupied_changed_pixels'])

    def test_owner_counts_cannot_replace_a_pixel_negative(self):
        images, face, support = fixture()
        images['legacy_negative'] = images['support_control']
        self.assertFalse(measure_view(images, face, support, 'north')['passed'])

    def test_hidden_support_and_body_are_rejected_independently(self):
        images, face, support = fixture()
        images['occupied'] = images['blank']
        measured = measure_view(images, face, support, 'north')
        self.assertEqual(0, measured['occupied_changed_pixels'])
        self.assertFalse(measured['gates']['support_retained'])
        images, face, support = fixture()
        images['shown'] = images['restored'] = images['support_control']
        self.assertFalse(measure_view(images, face, support, 'north')['gates']['body_shown'])

    def test_a_single_edge_pixel_is_not_eroded_away(self):
        images, face, support = fixture()
        images['occupied'] = images['occupied'].copy()
        images['occupied'].putpixel((19, 25), (20, 10, 20))
        self.assertEqual(1, measure_view(images, face, support, 'west')['occupied_changed_pixels'])

    def test_native_report_requires_matching_camera_exact_files_and_five_real_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            images, unused_face, unused_support = fixture()
            captures = {}
            status = {'camera': [1., 2., 3.], 'rotation': [4., 5., 0.],
                      'screen': [80, 80], 'engine': '3.10.0.420447'}
            for state, image in images.items():
                path = root/(state+'.png')
                image.save(path)
                captures[state] = {'before': deepcopy(status), 'after': deepcopy(status),
                    'capture': {'path': str(path), 'reliable': True,
                                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}}
            def points(box):
                x0, y0, x1, y1 = box
                return [dict(screenX=x, screenY=y, isInScreen=True)
                        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
            row = {'occupied_world_retained_for_controls': True,
                   'visibility': {'shown': [1, 1], 'occupied': [0, 0], 'restored': [1, 1]},
                   'captures': captures,
                   'projection': {'face': points((20, 10, 59, 39)),
                                  'target': points((20, 10, 59, 39)),
                                  'supports': [points((5, 50, 74, 74))]}}
            report = {'schema_version': 1, 'stage': 'body_boundary_pixels',
                      'engine': status['engine'], 'completed': True, 'restored': True,
                      'source_unchanged': True, 'cleanup_errors': [],
                      'negative_route': 'legacy_neighbor_context',
                      'views': {face: deepcopy(row) for face in FACES}}
            path = root/'report.json'
            path.write_text(json.dumps(report), encoding='ascii')
            self.assertTrue(analyze(path)['body_boundary_pixels_passed'])
            bad = deepcopy(report)
            bad['views']['down']['captures']['occupied']['before']['rotation'][0] += 1
            path.write_text(json.dumps(bad), encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'camera'):
                analyze(path)
            bad = deepcopy(report)
            del bad['views']['west']
            path.write_text(json.dumps(bad), encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                analyze(path)
            path.write_text(json.dumps(report), encoding='ascii')
            (root/'occupied.png').write_bytes(b'changed native capture')
            with self.assertRaisesRegex(ValueError, 'changed'):
                analyze(path)


if __name__ == '__main__':
    unittest.main()
