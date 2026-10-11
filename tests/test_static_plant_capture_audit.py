"""Background plant acceptance permits normal application use, never game focus."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from audit_static_plant_matrix import capture_status


class StaticPlantCaptureAuditTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        path = Path(self.directory.name)/'native.png'
        image = Image.new('RGB', (8, 8), 'red')
        ImageDraw.Draw(image).rectangle((0, 0, 3, 7), fill='blue')
        image.save(path)
        self.matrix = {'game_pid': 100, 'owner': 'owned-plant-test'}
        self.capture = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'capture': {'ok': True, 'reliable': True, 'background_only': True,
                                    'native_resolution': True, 'background_safe': True,
                                    'foreground_unchanged': False,
                                    'game_pid': 100, 'owner': 'owned-plant-test',
                                    'foreground_before': {'hwnd': 2, 'pid': 200},
                                    'foreground_after': {'hwnd': 3, 'pid': 300},
                                    'frame': {'frame_qpc_100ns': 11, 'request_qpc_100ns': 10,
                                              'width': 8, 'height': 8}}}

    def test_other_application_switch_is_preserved_without_failing_safe_capture(self):
        errors, switch = capture_status(self.capture, self.matrix)
        self.assertEqual([], errors)
        self.assertEqual(self.capture['capture']['foreground_before'], switch['foreground_before'])
        self.assertEqual(self.capture['capture']['foreground_after'], switch['foreground_after'])
        self.assertIn('Allowed ordinary switching', switch['classification'])

    def test_owned_game_foreground_is_rejected_before_or_after_capture(self):
        for field in ('foreground_before', 'foreground_after'):
            with self.subTest(field=field):
                capture = deepcopy(self.capture)
                capture['capture'][field]['pid'] = 100
                errors, switch = capture_status(capture, self.matrix)
                self.assertTrue(any('owned game was foreground' in error for error in errors))
                self.assertIn('Untrusted', switch['classification'])

    def test_stale_frame_or_wrong_owner_is_rejected(self):
        capture = deepcopy(self.capture)
        capture['capture']['frame']['frame_qpc_100ns'] = 10
        capture['capture']['owner'] = 'different-task'
        errors, unused = capture_status(capture, self.matrix)
        self.assertTrue(any('frame predates' in error for error in errors))
        self.assertTrue(any('ownership differs' in error for error in errors))

    def test_unreliable_metadata_and_changed_native_png_are_rejected(self):
        capture = deepcopy(self.capture)
        capture['capture']['reliable'] = False
        capture['sha256'] = '0'*64
        errors, unused = capture_status(capture, self.matrix)
        self.assertTrue(any('background capture gate' in error for error in errors))
        self.assertTrue(any('original PNG changed' in error for error in errors))

    def test_actual_blank_png_is_rejected_even_when_metadata_claims_reliability(self):
        path = Path(self.capture['path'])
        Image.new('RGB', (8, 8), 'black').save(path)
        self.capture['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        errors, unused = capture_status(self.capture, self.matrix)
        self.assertTrue(any('native PNG is blank' in error for error in errors))


if __name__ == '__main__':
    unittest.main()
