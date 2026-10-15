"""Attribute diagnostics must reject ordinary starfields and recover real stripes."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_portal_attributes_r20 import decode
from generate_portal_attribute_diagnostics_r20 import generate, install


class PortalAttributeTests(unittest.TestCase):
    def setUp(self):
        self.camera = {'face_points': [('north', [
            {'screenX': x, 'screenY': y, 'isInScreen': True}
            for x, y in ((0, 0), (383, 0), (383, 159), (0, 159))])]}

    def test_known_depth_stripes_decode_uv_and_reject_unrendered_layers(self):
        values = np.zeros((160, 384, 3), dtype=np.uint8)
        for x in range(384):
            layer = (x // 4) % 32
            if 8 <= layer < 24:
                values[:, x] = np.rint((np.array([.125, .875, layer / 32.]) * .75 + .25) * 255.)
        result = decode(Image.fromarray(values), self.camera)
        self.assertTrue(result['control_observed'])
        self.assertEqual(list(range(8, 24)), result['observed_layers'])
        self.assertAlmostEqual(.125, result['layers'][8]['color_uv'][0], delta=.003)
        self.assertAlmostEqual(.875, result['layers'][8]['color_uv'][1], delta=.003)
        self.assertFalse(result['pixel_acceptance'])

    def test_ordinary_star_noise_cannot_prove_attribute_control(self):
        values = np.random.default_rng(731).integers(0, 96, (160, 384, 3), dtype=np.uint8)
        result = decode(Image.fromarray(values), self.camera)
        self.assertFalse(result['control_observed'])
        self.assertEqual([], result['observed_layers'])

    def test_solid_marker_cannot_be_decoded_as_native_attributes(self):
        result = decode(Image.new('RGB', (384, 160), (191, 0, 191)), self.camera)
        self.assertFalse(result['control_observed'])
        self.assertEqual([], result['observed_layers'])

    def test_clone_generator_preserves_native_inputs_and_blend_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            native, output = base / 'native', base / 'output'
            original = {'vertexShader': 'shaders/end_portal.vertex',
                        'fragmentShader': 'shaders/end_portal.fragment',
                        'blendSrc': 'One', 'blendDst': 'SourceAlpha',
                        'depthFunc': 'LessEqual', '+states': ['Blending']}
            sources = {'shaders/glsl/end_portal.vertex': b'vertex sentinel\n',
                       'shaders/glsl/end_portal.fragment': b'fragment sentinel\n',
                       'resource_packs/vanilla/materials/portal.material': json.dumps(
                           {'materials': {'version': '1.0.0', 'portal_base': original}}).encode('ascii')}
            for name in ('common.json', 'fancy.json', 'sad.json'):
                sources['resource_packs/vanilla/materials/' + name] = b'[{"path":"materials/portal.material"}]\n'
            for relative, value in sources.items():
                path = native / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(value)
            contract = generate(native, output)
            self.assertTrue(contract['requires_observed_sentinel'])
            self.assertFalse(contract['production_qualified'])
            shader = output / 'resource_pack/shaders/glsl'
            self.assertEqual(b'vertex sentinel\n', (shader / 'r20_portal_attribute.vertex').read_bytes())
            self.assertEqual(b'fragment sentinel\n', (shader / 'r20_portal_attribute_native.h').read_bytes())
            self.assertIn('precision highp float;', (shader / 'r20_portal_attribute.fragment').read_text())
            material = json.loads((output / 'resource_pack/materials/portal.material').read_bytes())['materials']['portal_base']
            for key in ('blendSrc', 'blendDst', 'depthFunc', '+states'):
                self.assertEqual(original[key], material[key])
            repo = base / 'protected-project'
            (repo / '.git').mkdir(parents=True)
            with self.assertRaises(ValueError):
                install(output, repo)


if __name__ == '__main__':
    unittest.main()
