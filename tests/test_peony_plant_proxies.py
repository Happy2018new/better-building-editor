"""Native-half texture binding and signed-UV guards; no GPU qualification."""
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import generate_ordinary_plant_proxies as generator
from plant_alpha_geometry import planar_alpha_spans


class PeonyPlantProxyTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads(generator.PROFILE.read_bytes())

    def test_independent_native_halves_keep_exact_texture_alpha_and_existing_cross_template(self):
        files = generator.outputs(self.profile)
        atlas = files[ROOT / 'resource_pack/textures/terrain_texture.json']['texture_data']
        for half in ('bottom', 'top'):
            name = 'ordinary_peony_' + half
            identifier = 'modern_projection:' + name
            key = 'modern_projection_' + name
            model = files[ROOT / ('resource_pack/models/netease_block/' + name + '.json')]
            self.assertEqual(generator.centered_cross_model(
                {'template': json.loads(generator.TEMPLATE.read_bytes())}, identifier, key), model)
            geometry = model['netease:block_geometry']
            self.assertFalse(geometry['description']['use_ao'])
            self.assertEqual('textures/blocks/double_plant_paeonia_' + half, atlas[key]['textures'])
            row = next(part for part in self.profile['plants']['peony']['halves'] if part['half'] == half)
            path = generator.TEXTURES / ('peony_' + half + '.png')
            self.assertEqual(row['native_texture_sha256'], generator.digest(path.read_bytes()))
            with Image.open(path) as image:
                texture = image.convert('RGBA')
                alpha_pixels = sum(pixel[3] > 127 for pixel in texture.getdata())
                self.assertGreater(alpha_pixels, 0)
                for bone in geometry['bones']:
                    cube, = bone['cubes']
                    self.assertEqual(alpha_pixels, len(planar_alpha_spans(cube, texture)))
                    for missing in ('north', 'south'):
                        broken = deepcopy(cube)
                        broken['uv'].pop(missing)
                        with self.assertRaisesRegex(ValueError, 'explicit north/south'):
                            planar_alpha_spans(broken, texture)
            # No cardinal camera is edge-on to either diagonal plane. This is
            # a CPU topology guard, not proof of GPU pixels or native shape.
            for direction in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                for bone in geometry['bones']:
                    yaw = math.radians(bone['rotation'][1])
                    self.assertGreater(abs(math.sin(yaw) * direction[0] +
                                           math.cos(yaw) * direction[1]), .7)

    def test_misbound_halves_state_types_missing_half_and_alpha_drift_are_rejected(self):
        for change in ('order', 'coverage', 'integer', 'state_order', 'texture', 'alpha', 'slots'):
            profile = deepcopy(self.profile)
            row = profile['plants']['peony']
            if change == 'order': row['halves'].reverse()
            elif change == 'coverage': row['halves'].pop()
            elif change == 'integer': row['native_states'][0]['states']['upper_block_bit'] = 0
            elif change == 'state_order': row['native_states'].reverse()
            elif change == 'texture': row['halves'][0]['native_texture_key'] = 'peony_top'
            elif change == 'alpha': row['halves'][1]['alpha_bounds'][1] = 0
            else: row['native_definition']['textures']['side'] = 'peony_carried'
            with self.subTest(change=change), self.assertRaises(ValueError):
                generator.validate(profile)


if __name__ == '__main__':
    unittest.main()
