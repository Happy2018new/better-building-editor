"""A mirrored UV and opposite face winding must not duplicate asymmetric alpha."""
import json
from pathlib import Path
import sys
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from plant_alpha_geometry import planar_alpha_spans
from verify_snow_plant_visibility import cross_assets
from projection.debug_snow_blueprints import NAMES
from projection.geometry_palette import PLANT_PROXIES


class PlanarAlphaTests(unittest.TestCase):
    def cube(self):
        return {'size': [16, 16, 0], 'uv': {
            'north': {'uv': [0, 0], 'uv_size': [16, 16]},
            'south': {'uv': [16, 0], 'uv_size': [-16, 16]}}}

    def texture(self):
        texture = Image.new('RGBA', (16, 16))
        texture.putpixel((2, 3), (255, 10, 30, 255))
        return texture

    def test_asymmetric_texel_is_not_duplicated_by_the_reverse_face(self):
        spans = planar_alpha_spans(self.cube(), self.texture())
        self.assertEqual(((.125, .1875, .75, .8125),), spans)
        self.assertNotIn((.8125, .875, .75, .8125), spans)

    def test_unmirrored_back_face_requires_camera_side_instead_of_union(self):
        cube = self.cube()
        cube['uv']['south'] = {'uv': [0, 0], 'uv_size': [16, 16]}
        with self.assertRaisesRegex(ValueError, 'camera-side'):
            planar_alpha_spans(cube, self.texture())

    def test_all_29_model_pairs_coincide_for_an_asymmetric_source(self):
        for plant in NAMES:
            name = PLANT_PROXIES[('minecraft:'+plant, 0)].split(':', 1)[1]
            model = json.loads((ROOT/'resource_pack/models/netease_block'/(name+'.json')).read_bytes())
            with self.subTest(plant=plant):
                for bone in model['netease:block_geometry']['bones']:
                    for cube in bone['cubes']:
                        self.assertEqual(((.125, .1875, .75, .8125),),
                                         planar_alpha_spans(cube, self.texture()))

    def test_available_pinned_native_sources_have_the_same_contract(self):
        native = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/Minecraft.Windows.exe')
        if not native.exists():
            self.skipTest('Pinned NEMC 3.9 source is not installed')
        for plant in NAMES:
            with self.subTest(plant=plant):
                model, texture, unused = cross_assets({'game_executable': str(native)}, plant)
                for bone in model['netease:block_geometry']['bones']:
                    for cube in bone['cubes']:
                        self.assertTrue(planar_alpha_spans(cube, texture))

    def test_partial_uv_crop_keeps_only_covered_texture_pixels(self):
        cube = self.cube()
        cube['uv'] = {'north': {'uv': [0, 0], 'uv_size': [8, 16]},
                      'south': {'uv': [8, 0], 'uv_size': [-8, 16]}}
        texture = self.texture()
        texture.putpixel((15, 3), (255, 255, 255, 255))
        self.assertEqual(((.25, .375, .75, .8125),), planar_alpha_spans(cube, texture))

    def test_unknown_faces_thickness_rotated_uv_and_invalid_sizes_are_rejected(self):
        for change in ('thick', 'extra', 'zero', 'rotation', 'outside'):
            cube = self.cube()
            if change == 'thick':
                cube['size'][2] = 1
            elif change == 'extra':
                cube['uv']['east'] = {'uv': [0, 0], 'uv_size': [16, 16]}
            elif change == 'zero':
                cube['uv']['north']['uv_size'][0] = 0
            elif change == 'rotation':
                cube['uv']['north']['uv_rotation'] = 90
            else:
                cube['uv']['north']['uv'][0] = -1
            with self.subTest(change=change), self.assertRaises(ValueError):
                planar_alpha_spans(cube, self.texture())


if __name__ == '__main__':
    unittest.main()
