"""A sign glyph oracle separates tinted text from brown background changes."""
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from verify_sign_visuals import colored_text,shape_match,layout_match,panel_bounds


class SignVisualOracleTests(unittest.TestCase):
    def test_shifted_and_enlarged_text_are_rejected_even_when_glyph_shape_is_identical(self):
        tolerance={'center':.1,'size':.2}
        panel=(0,0,100,60)
        text=(20,10,80,30)
        self.assertTrue(layout_match(text,panel,(40,20,160,60),(0,0,200,120),tolerance)['passed'])
        self.assertFalse(layout_match(text,panel,(40,10,100,30),panel,tolerance)['passed'])
        self.assertFalse(layout_match(text,panel,(5,5,95,35),panel,tolerance)['passed'])

    def test_panel_detection_excludes_narrow_stem_and_separate_top_bar(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'board.png'
            image=Image.new('RGB',(120,120),(120,180,240))
            draw=ImageDraw.Draw(image)
            draw.rectangle((10,5,110,10),fill=(140,100,60))
            draw.rectangle((15,25,105,75),fill=(140,100,60))
            draw.rectangle((58,76,62,110),fill=(140,100,60))
            image.save(path)
            self.assertEqual((15,25,106,76),panel_bounds(path,(0,0,120,120)))

    def fixture(self,root):
        blank=Image.new('RGB',(120,80),(170,130,80))
        blank.save(root/'blank.png')
        return blank

    def test_semitransparent_red_on_wood_is_detected_and_unchanged_sign_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            shown=self.fixture(root)
            ImageDraw.Draw(shown).rectangle((30,20,70,35),fill=(145,65,25))
            shown.save(root/'shown.png')
            mask,result=colored_text(root/'shown.png',root/'blank.png',(0,0,120,80),'red',root/'mask.png')
            self.assertEqual((30,20,71,36),mask.getbbox())
            self.assertGreater(result['pixels'],500)
            empty,unused=colored_text(root/'blank.png',root/'blank.png',(0,0,120,80),'red',root/'empty.png')
            self.assertFalse(shape_match(mask,empty)['passed'])

    def test_neutral_lighting_and_wrong_text_color_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            shown=self.fixture(root)
            ImageDraw.Draw(shown).rectangle((10,10,30,30),fill=(190,150,100))
            ImageDraw.Draw(shown).rectangle((40,10,70,30),fill=(30,230,30))
            shown.save(root/'shown.png')
            mask,unused=colored_text(root/'shown.png',root/'blank.png',(0,0,120,80),'red',root/'mask.png')
            self.assertIsNone(mask.getbbox())

    def test_different_glyph_shape_stays_rejected(self):
        first,second=Image.new('L',(120,80)),Image.new('L',(120,80))
        ImageDraw.Draw(first).rectangle((20,20,90,26),fill=255)
        ImageDraw.Draw(first).rectangle((20,50,90,56),fill=255)
        ImageDraw.Draw(second).rectangle((20,20,26,56),fill=255)
        ImageDraw.Draw(second).rectangle((84,20,90,56),fill=255)
        self.assertFalse(shape_match(first,second)['passed'])
