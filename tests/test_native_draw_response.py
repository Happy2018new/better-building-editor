"""A compositor receipt alone must never pass native visibility controls."""
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from native_draw_response import (INSTALL, REMOVE, changed_pixels, native_clock,
                                  capture_response, frame_count, backdrop_pixel_coverage)
from mcdk import MCDKError
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

    def test_backdrop_preflight_uses_exact_native_zxy_volume_before_writes(self):
        for width, height in ((25, 25), (7, 13), (31, 2)):
            for order in ('zxy', 'xyz'):
                with self.subTest(width=width, height=height, order=order):
                    writes = []
                    class Palette:
                        def SerializeBlockPalette(self):
                            return {'volume': (1, width, height) if order=='zxy' else (width, height, 1),
                                    'common': {('minecraft:air', 0): list(range(width*height))},
                                    'extra': {}, 'actor': {}}
                    class PaletteBlock:
                        def GetBlockPaletteBetweenPos(self, *unused): return Palette()
                    class Adapter:
                        dimension = 0
                        palette_block = PaletteBlock()
                        def __init__(self, unused): pass
                        def write(self, pos, value):
                            writes.append((pos, value))
                            return True
                    api = types.ModuleType('mod.server.extraServerApi')
                    api.GetPlayerList = lambda: ['owned_player']
                    server = types.ModuleType('mod.server')
                    server.extraServerApi = api
                    mod = types.ModuleType('mod')
                    mod.server = server
                    module = types.ModuleType('modern_projection.server_system')
                    module.WorldAdapter = Adapter
                    source = (SETUP % ((0, 20, 0),)).replace(
                        'hi=(target[0]+22,target[1]+24,target[2]+12)',
                        'hi=(target[0]-2+%d,target[1]-16+%d,target[2]+12)' % (width-1,height-1))
                    imports = {'mod': mod, 'mod.server': server, 'mod.server.extraServerApi': api,
                               'modern_projection': types.ModuleType('modern_projection'),
                               'modern_projection.server_system': module}
                    with patch.dict(sys.modules, imports):
                        try:
                            if order=='xyz':
                                with self.assertRaises(AssertionError): exec(source, {})
                                self.assertEqual([], writes)
                                self.assertFalse(hasattr(sys, '_snow_contrast_backdrop'))
                            else:
                                result = {}
                                exec(source, result)
                                self.assertEqual(width*height, len(writes))
                                self.assertEqual(width*height, json.loads(result['_result'])['cells'])
                                restored = {}
                                exec(RESTORE, restored)
                                self.assertTrue(json.loads(restored['_result'])['restored'])
                                self.assertEqual(width*height*2, len(writes))
                        finally:
                            if hasattr(sys, '_snow_contrast_backdrop'):
                                del sys._snow_contrast_backdrop

    def test_only_fixed_read_timeout_retries_and_restores_transport_timeout(self):
        class Check:
            client = types.SimpleNamespace(timeout=30.)
            reads = []
            def run(self, source):
                self.reads.append((source, self.client.timeout))
                if len(self.reads) == 1:
                    raise MCDKError('Code execution failed: IPC JSON request timed out')
                return 42
        check = Check()
        with patch('native_draw_response.time.sleep'):
            self.assertEqual(42, frame_count(check))
        self.assertEqual(2, len(check.reads))
        self.assertTrue(all(source == '_result=sys._snow_product_render_frames.count' and timeout == 5.
                            for source, timeout in check.reads))
        self.assertEqual(30., check.client.timeout)
        self.assertFalse(check.native_frame_read_retries[0]['mutation_replayed'])

    def test_identity_rejection_and_repeated_timeouts_are_not_unbounded_retries(self):
        for message, attempts in (('Assigned instance identity changed', 1),
                                  ('IPC JSON request timed out', 2)):
            calls = []
            class Check:
                client = types.SimpleNamespace(timeout=30.)
                def run(self, source):
                    calls.append(source)
                    raise MCDKError(message)
            check = Check()
            with self.subTest(message=message), patch('native_draw_response.time.sleep'):
                with self.assertRaises(MCDKError):
                    frame_count(check)
            self.assertEqual(attempts, len(calls))
            self.assertEqual(30., check.client.timeout)

    def test_actual_background_must_cover_cell_even_when_geometry_would_fit(self):
        roi = Image.new('L', (200, 200))
        ImageDraw.Draw(roi).rectangle((50, 50, 150, 150), fill=255)
        dark = self.record('wall')
        self.assertTrue(backdrop_pixel_coverage(dark, (0, 0, 200, 200), roi)['passed'])
        image = Image.new('RGB', (200, 200))
        draw = ImageDraw.Draw(image)
        draw.rectangle((70, 50, 100, 60), fill=(80, 103, 53))
        path = self.root/'partial_wall.png'
        image.save(path)
        self.assertFalse(backdrop_pixel_coverage({'path': str(path)}, (0, 0, 200, 200), roi)['passed'])
        image = Image.new('RGB', (200, 200))
        ImageDraw.Draw(image).line((90, 100, 110, 100), fill='white')
        image.save(path)
        self.assertTrue(backdrop_pixel_coverage({'path': str(path)}, (0, 0, 200, 200), roi)['passed'])

    def test_native_response_waits_for_model_alpha_instead_of_placeholder_change(self):
        baseline = self.record('empty')
        pending = self.record('pending', body=True, clock=True)
        ready = self.record('ready', body=True, clock=True)
        class Check:
            output = self.root/'report.json'
            def run(self, unused): return 10
            def capture(self, unused): return next(captures)
        captures = iter((pending, ready))
        with patch('native_draw_response.time.sleep'), patch('native_draw_response.time.monotonic',
                                                              side_effect=[0, .1, .2, .3, .4]):
            record, response = capture_response(Check(), 'editor', baseline, (50, 50, 150, 150), 0,
                validate=lambda value: {'passed': value['path'] == ready['path']})
        self.assertEqual(ready, record)
        self.assertEqual(2, len(response['attempts']))
        self.assertFalse(response['attempts'][0]['validation']['passed'])


if __name__ == '__main__':
    unittest.main()
