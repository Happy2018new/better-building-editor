"""Native atlas padding must never become visible book geometry."""
from pathlib import Path
import json
import sys
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from generate_book_resources_r16 import shape
from book_model_geometry import shape as diagnostic_shape


class BookResourceTests(unittest.TestCase):
    def test_default_geometry_remains_identical_to_installed_meshes(self):
        for family in ('enchanting_table', 'lectern'):
            installed = json.loads((ROOT/('resource_pack/models/modern_projection/book/'+
                                         family+'_mesh.json')).read_bytes())
            self.assertEqual(installed, json.loads(json.dumps(shape(family))))

    def test_page_clearance_controls_preserve_covers_uvs_and_topology(self):
        original = diagnostic_shape('enchanting_table', 'modern_projection/book/enchanting_table')['mesh'][0]
        candidate = diagnostic_shape('enchanting_table', 'modern_projection/book/enchanting_table', .125)['mesh'][0]
        self.assertEqual(original['indices'], candidate['indices'])
        self.assertEqual(original['vertices'][:288], candidate['vertices'][:288])
        self.assertNotEqual(original['vertices'][288:], candidate['vertices'][288:])
        self.assertEqual([v['uvcoord'] for v in original['vertices']],
                         [v['uvcoord'] for v in candidate['vertices']])

    def test_all_book_faces_have_consistent_exterior_winding(self):
        for family in ('enchanting_table','lectern'):
            mesh=shape(family)['mesh'][0]
            for indices in mesh['indices']:
                a,b,c=[mesh['vertices'][index] for index in indices]
                u=[b['pos'][i]-a['pos'][i] for i in range(3)]
                v=[c['pos'][i]-a['pos'][i] for i in range(3)]
                normal=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
                self.assertGreater(sum(normal[i]*a['normal'][i] for i in range(3)),0.,
                                   (family,indices))

    def test_every_face_samples_artwork_instead_of_opaque_black_padding(self):
        with Image.open(ROOT/'resource_pack/textures/models/modern_projection/book/native_book.png') as source:
            texture = source.convert('RGB')
        for family in ('enchanting_table', 'lectern'):
            vertices = shape(family)['mesh'][0]['vertices']
            for start in range(0, len(vertices), 4):
                face = vertices[start:start+4]
                xs = [vertex['uvcoord'][0]*texture.width for vertex in face]
                ys = [vertex['uvcoord'][1]*texture.height for vertex in face]
                # Validate the entire face's footprint, not merely its corners:
                # the old page UV included two opaque black rows at its bottom.
                for y in range(int(min(ys)), int(max(ys))+1):
                    for x in range(int(min(xs)), int(max(xs))+1):
                        self.assertNotEqual((0,0,0), texture.getpixel((x,y)),
                                            (family,start,x,y))
                for value in xs+ys:
                    self.assertAlmostEqual(.5, value % 1.)


if __name__ == '__main__':
    unittest.main()
