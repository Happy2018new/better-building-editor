"""The native adapter must preserve source geometry and real sparse artwork."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from generate_portal_native_adapter_r19 import generate, layered_mesh, world_vertex


class PortalNativeAdapterTests(unittest.TestCase):
    def test_layer_encoding_preserves_non_depth_vertex_data_and_topology(self):
        source = json.loads((ROOT/'resource_pack/models/modern_projection/portal/end_gateway_mesh.json').read_bytes())
        before = deepcopy(source)
        output = layered_mesh(source, 12, 1)
        self.assertEqual(before, source)
        original = source['mesh'][0]
        result = output['mesh'][0]
        size = len(original['vertices'])
        self.assertEqual(size*13, len(result['vertices']))
        self.assertEqual(len(original['indices'])*13, len(result['indices']))
        for index, depth in enumerate((32,)+tuple(range(1, 13))):
            for old, new in zip(original['vertices'], result['vertices'][index*size:(index+1)*size]):
                restored = deepcopy(new)
                self.assertEqual(depth, restored['pos'][2])
                restored['pos'][2] = old['pos'][2]
                self.assertEqual(old, restored)
            self.assertEqual([[value+index*size for value in triangle] for triangle in original['indices']],
                             result['indices'][index*len(original['indices']):(index+1)*len(original['indices'])])

    def test_star_planes_cannot_overwrite_the_native_clear_plane(self):
        for count, first in ((0, 0), (32, 0), (16, -1), (16, 17)):
            with self.assertRaises(ValueError):
                layered_mesh({'mesh': []}, count, first)

    def test_measured_layout_uses_even_depth_bytes_and_reverse_color_indices(self):
        source = (ROOT/'resource_pack/shaders/glsl/modern_projection_portal_geometry_world.vertex').read_text(encoding='ascii')
        vertex = world_vertex(source, native_layout=True)
        self.assertIn('floor(layerIndex*(255.0/16.0))*(32.0/255.0)', vertex)
        self.assertIn('float colorIndex=15.0-layerIndex;', vertex)
        expected = [0, 15, 31, 47, 63, 79, 95, 111, 127, 143, 159, 175, 191, 207, 223, 239]
        self.assertEqual(expected, [int(index*255./16.) for index in range(16)])

    def test_actual_entity_star_texture_and_native_fragment_are_bundled_verbatim(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            native, output = base/'native', base/'output'
            fragment = b'// native sentinel\nvoid main() {}\n'
            starfield = b'actual sparse starfield sentinel'
            for relative, value in (
                ('shaders/glsl/end_portal.vertex', b'vertex sentinel'),
                ('shaders/glsl/end_portal.fragment', fragment),
                ('resource_packs/vanilla/materials/portal.material', b'material sentinel'),
                ('resource_packs/vanilla/textures/entity/end_portal.png', starfield),
                ('resource_packs/vanilla/textures/environment/end_sky.png', b'wrong gray noise')):
                path = native/relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(value)
            contract = generate(ROOT, native, output, 12, 1)
            self.assertEqual(fragment, (output/'resource_pack/shaders/glsl/r19_native_portal_original.h').read_bytes())
            self.assertEqual(starfield, (output/'resource_pack/textures/models/modern_projection/portal/r19_native_starfield.png').read_bytes())
            self.assertFalse(contract['production_qualified'])
            self.assertEqual((12, 1), (contract['layers'], contract['first_layer']))
            for model in contract['models'].values():
                self.assertEqual('modern_projection/portal/r19_native_starfield', model['texture']['tex0'])


if __name__ == '__main__':
    unittest.main()
