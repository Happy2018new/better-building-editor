"""Native alpha and uncertain background observations must survive route probes."""
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_shelf_native_routes_r21 import selector_fragment
from probe_shelf_native_routes_r21 import pixel_observations


class ShelfNativeRouteTests(unittest.TestCase):
    def test_final_output_is_the_only_native_body_change(self):
        original = '// __multiversion__\nvoid main(){if(tex.a<0.5)discard;gl_FragColor = color;}\n'
        candidate = selector_fragment(original, 'color', (0., 1., 1.))
        self.assertIn('if(tex.a<0.5)discard;', candidate)
        self.assertIn('vec3 shelfRouteRgb=color.rgb;', candidate)
        self.assertIn('gl_FragColor=vec4(shelfRouteRgb,color.a);', candidate)
        self.assertIn('floor(gl_FragCoord.x/16.0),2.0)', candidate)

    def test_terrain_bypass_is_preserved(self):
        original = '// __multiversion__\n#ifdef BYPASS_PIXEL_SHADER\n'
        original += 'gl_FragColor=vec4(0.);return;\n#else\ngl_FragColor = diffuse;\n#endif\n'
        candidate = selector_fragment(original, 'diffuse', (1., 1., 0.))
        self.assertIn('gl_FragColor=vec4(0.);return;', candidate)
        self.assertIn('gl_FragColor=vec4(shelfRouteRgb,diffuse.a);', candidate)

    def test_changed_native_output_anchor_is_rejected(self):
        for source in ('// __multiversion__\nvoid main(){}',
                       '// __multiversion__\ngl_FragColor = color;gl_FragColor = color;'):
            with self.assertRaises(ValueError):
                selector_fragment(source, 'color', (0., 1., 1.))

    def test_background_marker_does_not_qualify_native_route(self):
        projection = [{'screen': {'screenX': x, 'screenY': y}} for x, y in ((20., 20.), (40., 40.))]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('native', 'empty'):
                Image.new('RGB', (60, 60), (255, 255, 0)).save(root/(name+'.png'))
            result = pixel_observations(root/'native.png', root/'empty.png', projection)
            self.assertFalse(result['native_route_qualified'])
            self.assertGreater(result['marker_counts']['terrain_base']['world'], 0)
            self.assertEqual(result['marker_counts']['terrain_base']['world_changed'], 0)

    def test_changed_marker_pixels_are_observations_only(self):
        projection = [{'screen': {'screenX': x, 'screenY': y}} for x, y in ((20., 20.), (40., 40.))]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGB', (60, 60), (0, 255, 255)).save(root/'native.png')
            Image.new('RGB', (60, 60), (255, 255, 0)).save(root/'empty.png')
            result = pixel_observations(root/'native.png', root/'empty.png', projection)
            self.assertGreater(result['marker_counts']['entity_static_netease']['world_changed'], 0)
            self.assertFalse(result['native_route_qualified'])


if __name__ == '__main__':
    unittest.main()
