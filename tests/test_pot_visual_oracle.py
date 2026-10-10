"""Pot acceptance rejects missing models, displaced bodies and wrong artwork."""
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from verify_copper_chest_render import object_frame, world_alignment
from shulker_pixels import _prepared_pair
from verify_pot_visuals import reflected_reference


class PotVisualOracleTests(unittest.TestCase):
    def test_mirrored_native_reference_tracks_world_front_and_exchanges_side_artwork(self):
        names=('north','west','east','south')
        for operation,directions in (('mirror_x',(0,3,2,1)),('mirror_z',(2,1,0,3))):
            for direction in range(4):
                with self.subTest(operation=operation,direction=direction):
                    self.assertEqual((directions[direction],('north','east','west','south')),
                                     reflected_reference(direction,operation,names))

    def fixture(self,path,pattern=None,offset=0):
        image=Image.new('RGB',(400,300),(140,190,245))
        draw=ImageDraw.Draw(image)
        draw.rectangle((170,225,230,245),fill=(115,115,115))
        if pattern is not None:
            draw.rectangle((165+offset,95,235+offset,215),fill=(160,78,46))
            for index in range(8):
                if pattern=='horizontal':
                    draw.rectangle((173+offset,108+index*12,227+offset,111+index*12),fill=(225,170,110))
                else:
                    draw.rectangle((171+offset+index*7,108,173+offset+index*7,202),fill=(225,170,110))
        image.save(path)

    def test_empty_model_cannot_pass_using_unchanged_support(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.fixture(root/'empty.png')
            with self.assertRaisesRegex(AssertionError,'central'):
                object_frame(root/'empty.png',root/'empty.png',root/'signal.png')

    def test_same_body_and_artwork_pass_but_wrong_pattern_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.fixture(root/'empty.png')
            self.fixture(root/'native.png','horizontal')
            self.fixture(root/'wrong.png','vertical')
            first=object_frame(root/'native.png',root/'empty.png',root/'native_signal.png')
            second=object_frame(root/'wrong.png',root/'empty.png',root/'wrong_signal.png')
            self.assertGreater(_prepared_pair(first,first)['texture_cosine'],.99)
            self.assertLess(_prepared_pair(first,second)['texture_cosine'],.45)
            self.assertGreater(_prepared_pair(first,second)['shape_iou'],.99)

    def test_displaced_model_fails_absolute_alignment(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.fixture(root/'empty.png')
            self.fixture(root/'native.png','horizontal')
            self.fixture(root/'shifted.png','horizontal',offset=12)
            first=object_frame(root/'native.png',root/'empty.png',root/'native_signal.png')
            second=object_frame(root/'shifted.png',root/'empty.png',root/'shifted_signal.png')
            self.assertFalse(world_alignment(first[2],second[2])['passed'])


if __name__=='__main__':
    unittest.main()
