"""Terrain readback must retain native alpha/discard and distinguish data slots."""
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_shelf_terrain_inputs_r21 import FLAG_CHANNELS, fragment
from probe_shelf_terrain_inputs_r21 import pixel_observations
from verify_shelf_terrain_inputs_r21 import flag_bytes, RENDER


class ShelfTerrainInputTests(unittest.TestCase):
    def source(self):
        return ('// __multiversion__\n#ifdef BYPASS_PIXEL_SHADER\n'
                'gl_FragColor=vec4(0.);return;\n#else\n'
                'if(diffuse.a<0.5)discard;gl_FragColor = diffuse;\n#endif\n')

    def test_only_output_and_precision_change(self):
        original = self.source()
        candidate = fragment(original)
        self.assertIn('if(diffuse.a<0.5)discard;', candidate)
        self.assertIn('gl_FragColor=vec4(0.);return;', candidate)
        self.assertIn('gl_FragColor=vec4(shelfTerrainRgb,diffuse.a);', candidate)
        self.assertNotIn('TILE_LIGHT_COLOR', candidate)
        self.assertNotIn('uniform ', candidate)
        self.assertNotIn('varying ', candidate)

    def test_four_marker_data_pairs(self):
        candidate = fragment(self.source())
        for value in ('mod(floor(gl_FragCoord.x/16.0),8.0)', 'shelfTerrainRgb=color.rgb;',
                      'texture2D(TEXTURE_1,uv1).rgb', '#if !defined(ALWAYS_LIT)',
                      'shelfTerrainRgb=shelfTerrainFlags;', 'shelfTerrainRgb=diffuse.rgb;',
                      'vec3(1.0,1.0,0.0)', 'vec3(1.0,0.0,1.0)', 'vec3(0.0,1.0,1.0)', 'vec3(1.0)'):
            self.assertIn(value, candidate)

    def test_all_flags_have_distinct_channel_bits(self):
        candidate = fragment(self.source())
        for channel, names in enumerate(FLAG_CHANNELS):
            for bit, name in enumerate(names):
                expected = [0, 0, 0]
                expected[channel] = (1 << bit)*17
                self.assertEqual(flag_bytes((name,)), expected)
                self.assertIn('#ifdef '+name+'\nshelfTerrainFlags.'+'rgb'[channel]+
                              '+='+str(1 << bit)+'.0/15.0;', candidate)

    def test_changed_anchor_is_rejected(self):
        with self.assertRaises(ValueError):
            fragment(self.source().replace('gl_FragColor = diffuse;', 'gl_FragColor=diffuse;'))

    def test_renderer_checks_all_eight_slots_and_native_alpha(self):
        self.assertEqual(RENDER.count('strip<8;'), 2)
        self.assertIn('canvas.width=128;', RENDER)
        self.assertIn('[...slots[strip],baseline[3]]', RENDER)
        self.assertIn('bypass||discard?baseline:', RENDER)

    def test_background_data_cannot_qualify_input_readback(self):
        projection = [{'screen': {'screenX': x, 'screenY': y}} for x, y in ((1., 1.), (128., 3.))]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('native', 'empty'):
                Image.new('RGB', (132, 8), (255, 255, 0)).save(root/(name+'.png'))
            result = pixel_observations(root/'native.png', root/'empty.png', projection)
        self.assertEqual(len(result['slots']), 8)
        self.assertTrue(all(row['pixels'] > 0 for row in result['slots']))
        self.assertTrue(all(row['changed_pixels_gt_24'] == 0 for row in result['slots']))
        self.assertFalse(result['native_input_readback_qualified'])


if __name__ == '__main__':
    unittest.main()
