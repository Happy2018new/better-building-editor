"""Independent shelf shape/UV/winding controls for the isolated resource tool."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

TOOLS = Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0, str(TOOLS))
import generate_shelf_skeleton_resources_r21 as generator
import probe_shelf_skeleton_world_r21 as probe
from verify_shelf_skeleton_r21 import verify_mesh


class ShelfSkeletonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = json.loads((TOOLS/'data/shelf_body_java_1.21.9_reference.json').read_bytes())

    def test_all_fronts_preserve_solid_bounds_and_outward_triangle_normals(self):
        for front in generator.FRONTS:
            report = verify_mesh(generator.mesh(self.reference, front, 'test'))
            self.assertTrue(report['passed'], (front, report))
            self.assertEqual((report['vertices'], report['triangles']), (352, 176))

    def test_each_front_selects_its_own_complete_reference_rectangle(self):
        for front in generator.FRONTS:
            vertices = generator.mesh(self.reference, front, 'test')['mesh'][0]['vertices']
            panel = [vertex for vertex in vertices if vertex['pos'][2] == 1.3125
                     and vertex['normal'] == [0, 0, -1] and .25 <= vertex['pos'][1] <= .75]
            self.assertEqual(len(panel), 4)
            expected = self.reference['models'][front]['elements'][0]['faces']['north']['uv']
            corners = ((expected[0], expected[1]), (expected[2], expected[1]),
                       (expected[2], expected[3]), (expected[0], expected[3]))
            self.assertEqual([row['uvcoord'] for row in panel], [[u/16., v/16.] for u, v in corners])

    def test_backing_side_uvs_are_continuous_across_three_slab_splits(self):
        vertices = generator.mesh(self.reference, 'unpowered', 'test')['mesh'][0]['vertices'][:88]
        for row in vertices:
            x, y, z = row['pos']
            normal = row['normal']
            if z < 1.3125 or normal[1] or normal == [0, 0, -1]:
                continue
            face = 'east' if normal[0] > 0 else 'west' if normal[0] < 0 else 'south'
            rect = self.reference['models']['body']['elements'][0]['faces'][face]['uv']
            self.assertAlmostEqual(row['uvcoord'][1], (rect[1]+(1.-y)*(rect[3]-rect[1]))/16.)

    def test_negative_uv_sizes_are_retained_on_bottom_and_top(self):
        vertices = generator.mesh(self.reference, 'unpowered', 'test')['mesh'][0]['vertices']
        low = next(index for index, row in enumerate(vertices) if row['normal'] == [0, -1, 0])
        self.assertGreater(vertices[low]['uvcoord'][0], vertices[low+1]['uvcoord'][0])

    def test_reversed_winding_is_rejected(self):
        data = generator.mesh(self.reference, 'unpowered', 'test')
        triangle = data['mesh'][0]['indices'][0]
        data['mesh'][0]['indices'][0] = tuple(reversed(triangle))
        self.assertFalse(verify_mesh(data)['passed'])

    def test_corrupted_normals_are_rejected(self):
        data = generator.mesh(self.reference, 'unpowered', 'test')
        data['mesh'][0]['vertices'][0]['normal'] = [0, 0, 0]
        self.assertFalse(verify_mesh(data)['passed'])

    def test_public_preview_depth_header_is_reused_exactly(self):
        vertex, _ = generator.shaders()
        header = (generator.ROOT/'resource_pack/shaders/glsl/modern_projection_liquid_preview_depth.h').read_text(encoding='ascii')
        self.assertIn(header, vertex)
        self.assertIn('liquidUniformPreviewDepth(', vertex)
        self.assertNotIn('GetBoneMatForNetease(int(BONEID_0))*entityNormal', vertex)

    def test_world_normals_share_position_bone_and_instance_transforms(self):
        vertex, _ = generator.shaders(True)
        for name in ('entityPoint', 'entityNormal'):
            self.assertIn(name+'.z=-'+name+'.z;', vertex)
            self.assertIn('GetBoneMatForNetease(int(BONEID_0))*'+name, vertex)
            self.assertIn('GetInstanceWorldMatForNetease()*'+name, vertex)
        self.assertIn('shelfAxisIntensity(shelfWorldNormal,TILE_LIGHT_COLOR.w)', vertex)
        self.assertNotIn('void liquidApplyPreviewDepth', vertex)


class ShelfProbeAdmissionTests(unittest.TestCase):
    def test_selector_requires_pixels_inside_the_native_projected_cell(self):
        projection = [{'screen': {'screenX': x, 'screenY': y}} for x, y in ((40., 40.), (60., 60.))]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'selector.png'
            image = Image.new('RGB', (100, 100), 'white')
            image.paste((255, 0, 255), (0, 0, 20, 20))
            image.save(path)
            outside = probe.selector_pixels(path, projection)
            self.assertEqual(outside['magenta_pixels_in_frame'], 400)
            self.assertFalse(outside['passed'])
            image.paste((255, 0, 255), (45, 45, 55, 55))
            image.save(path)
            self.assertTrue(probe.selector_pixels(path, projection)['passed'])

    def test_offscreen_native_cell_cannot_pass_material_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'selector.png'
            Image.new('RGB', (100, 100), (255, 0, 255)).save(path)
            projection = [{'screen': {'screenX': 150., 'screenY': 150.}}]
            self.assertFalse(probe.selector_pixels(path, projection)['passed'])

    def test_probe_templates_compile_and_selection_stops_before_other_modes(self):
        for code in (probe.CREATE % probe.MODEL, probe.SUBMIT % ((5, 128), probe.MODEL),
                     probe.STATUS, probe.CLEAN):
            compile(code, '<shelf-game-template>', 'exec')
        self.assertEqual(probe.PHASES['selection'], (('selector', 5),))
        self.assertEqual(len(probe.PHASES['details'])+2, 9)

    def test_review_is_bound_to_completed_restored_report_and_raw_image_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root/'selector.png'
            Image.new('RGB', (10, 10), (255, 0, 255)).save(image)
            report_path, review_path = root/'report.json', root/'review.json'
            report = {'completed': True, 'restored': True, 'source_unchanged': True,
                      'selector_readback': {'passed': True}, 'captures': {'selector': {'path': str(image)}}}
            report_path.write_text(json.dumps(report), encoding='ascii')
            review = {'root_visual_review_accepted': True, 'direction': 'south',
                'source_report': str(report_path),
                'source_report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
                'selector_sha256': hashlib.sha256(image.read_bytes()).hexdigest()}
            review_path.write_text(json.dumps(review), encoding='ascii')
            self.assertEqual(probe.validate_review(review_path, 'south'), review)
            with self.assertRaises(ValueError):
                probe.validate_review(review_path, 'west')
            Image.new('RGB', (10, 10), 'white').save(image)
            with self.assertRaises(ValueError):
                probe.validate_review(review_path, 'south')


if __name__ == '__main__':
    unittest.main()
