"""Culling experiments must not reset unrelated inherited render states."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_book_raster_controls_r17 import raster_material


class BookRasterControlTests(unittest.TestCase):
    def test_culling_controls_preserve_native_state_inheritance(self):
        original={'+states':['Blending','DisableCulling'],'-states':['DisableDepthWrite'],
                  'blendSrc':'SourceAlpha','blendDst':'OneMinusSrcAlpha'}
        for mode in ('double','back','front'):
            candidate=raster_material(original,mode)
            self.assertNotIn('states',candidate)
            self.assertIn('Blending',candidate['+states'])
            self.assertIn('DisableDepthWrite',candidate['-states'])
            self.assertEqual('SourceAlpha',candidate['blendSrc'])
            self.assertEqual('OneMinusSrcAlpha',candidate['blendDst'])
        self.assertEqual(['Blending','DisableCulling'],original['+states'])

    def test_existing_explicit_states_keep_unrelated_depth_test_policy(self):
        result=raster_material({'states':['DisableDepthTest','DisableCulling']},'back')
        self.assertEqual(['DisableDepthTest'],result['states'])
        self.assertIn('DisableCulling',result['-states'])
