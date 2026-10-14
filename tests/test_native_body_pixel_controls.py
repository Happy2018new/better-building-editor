"""Static world colors cannot substitute for a visible native body or support."""
from pathlib import Path
import sys
import unittest

from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_native_palette_body_r16 import colors


class NativeBodyPixelControls(unittest.TestCase):
    def test_same_colored_terrain_is_not_a_body_positive(self):
        terrain=Image.new('RGB',(20,20),(130,100,60))
        warm=lambda r,g,b:r>g and g>b
        self.assertEqual(0,colors(terrain,terrain,(0,0,1,1),warm))
        body=terrain.copy()
        body.paste((160,110,50),(5,5,15,15))
        self.assertEqual(100,colors(body,terrain,(0,0,1,1),warm))

    def test_cyan_sky_and_small_noise_do_not_count_as_support(self):
        sky=Image.new('RGB',(20,20),(60,170,190))
        cyan=lambda r,g,b:g>r*1.3 and b>r*1.2
        noise=Image.new('RGB',(20,20),(65,165,195))
        self.assertEqual(0,colors(noise,sky,(0,0,1,1),cyan))
        support=sky.copy()
        support.paste((10,100,110),(5,5,15,15))
        self.assertEqual(100,colors(support,sky,(0,0,1,1),cyan))


if __name__=='__main__':
    unittest.main()
