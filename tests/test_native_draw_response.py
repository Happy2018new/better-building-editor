"""A compositor receipt alone must never pass native visibility controls."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from native_draw_response import INSTALL, REMOVE, changed_pixels, native_clock, capture_response
from snow_contrast_backdrop import SETUP, RESTORE


class DrawResponseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def record(self, name, body=False, clock=False):
        image = Image.new('RGB', (200, 200))
        draw = ImageDraw.Draw(image)
        if body:
            draw.rectangle((80, 80, 100, 100), fill='white')
        if clock:
            draw.rectangle((70, 14, 85, 16), fill='white')
        path = self.root/(name+'.png')
        image.save(path)
        return {'path': str(path), 'size': image.size}

    def test_background_pixels_and_clock_are_separate_controls(self):
        blank = self.record('blank')
        body = self.record('body', body=True)
        clock = self.record('clock', clock=True)
        self.assertEqual(changed_pixels(blank, body, (50, 50, 150, 150)), 441)
        self.assertEqual(changed_pixels(blank, clock, (50, 50, 150, 150)), 0)
        self.assertEqual(native_clock(blank), native_clock(body))
        self.assertNotEqual(native_clock(blank), native_clock(clock))

    def test_stale_native_pixels_fail_despite_advancing_render_events(self):
        shown = self.record('shown', body=True)
        class Check:
            output = self.root/'report.json'
            def run(self, unused): return 10
            def capture(self, unused): return shown
        with patch('native_draw_response.time.sleep'), patch('native_draw_response.time.monotonic',
                                                              side_effect=[0, .1, .2, 1.]):
            with self.assertRaisesRegex(RuntimeError, 'Native visible response failed'):
                capture_response(Check(), 'hidden', shown, (50, 50, 150, 150), 0, seconds=.5)
        retained = json.loads((self.root/'report_hidden_response_error.json').read_bytes())
        self.assertFalse(retained['passed'])
        self.assertEqual(retained['attempts'][0]['changed_pixels'], 0)
        self.assertFalse(retained['attempts'][0]['native_clock_advanced'])

    def test_fresh_clock_without_visibility_response_also_fails(self):
        shown = self.record('shown', body=True)
        stale_body = self.record('hidden', body=True, clock=True)
        class Check:
            output = self.root/'report.json'
            def run(self, unused): return 10
            def capture(self, unused): return stale_body
        with patch('native_draw_response.time.sleep'), patch('native_draw_response.time.monotonic',
                                                              side_effect=[0, .1, .2, 1.]):
            with self.assertRaisesRegex(RuntimeError, 'Native visible response failed'):
                capture_response(Check(), 'hidden', shown, (50, 50, 150, 150), 0, seconds=.5)

    def test_sdk_snippets_compile(self):
        for source in (INSTALL, REMOVE, SETUP % ((0, 20, 0),), RESTORE):
            compile(source, '<snow-native-response>', 'exec')


if __name__ == '__main__':
    unittest.main()
