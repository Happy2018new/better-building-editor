"""Animation evidence must distinguish a visible changing body from a frozen one."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_item_dense_motion_r17 import continuous_change_measurement
from analyze_item_sprite_closeup import glint_visibility_comparison


class GlintMotionTests(unittest.TestCase):
    def setUp(self):
        self.times=np.arange(0.,8.01,.1)
        self.mask=np.ones((8,8),dtype=bool)
        x=np.arange(8)[None,:,None]
        self.images=[np.broadcast_to(100.+35.*np.sin(x+t*2.),(8,8,3)).astype(np.float32) for t in self.times]

    def test_changing_pattern_passes_but_frozen_body_and_pause_fail(self):
        self.assertTrue(continuous_change_measurement(self.images,self.mask,self.times)['passed'])
        self.assertFalse(continuous_change_measurement([self.images[0]]*len(self.times),self.mask,self.times)['passed'])
        paused=list(self.images)
        paused[25:46]=[self.images[25]]*21
        self.assertFalse(continuous_change_measurement(paused,self.mask,self.times)['passed'])

    def test_gap_and_empty_body_fail(self):
        self.assertFalse(continuous_change_measurement(self.images,np.zeros_like(self.mask),self.times)['passed'])
        times=self.times.copy()
        times[40:]+=.3
        self.assertFalse(continuous_change_measurement(self.images,self.mask,times)['passed'])

    def test_absent_body_is_a_failed_measurement_not_an_exception(self):
        items={'enchanted':{'glint':{'status':'NO_OBSERVED_BODY'}}}
        row=glint_visibility_comparison(items,items,False,True,{})
        self.assertFalse(row['passed'])
        self.assertEqual('NO_OBSERVED_BODY',row['status'])

    def test_centroid_stationarity_cannot_reject_visible_contrast(self):
        glint={'status':'MEASURED','rgb_range_p50_p90_max':[20.,30.,40.],
               'luma_range_p50_p90_max':[20.,30.,40.],
               'visible_highlight_fraction_p10_p50_p90':[.5,.6,.8],
               'highlight_centroid_body_widths_per_second':[]}
        items={'enchanted':{'glint':glint,'extent_pixels':[200,200],'temporal':{'passed':True}},
               'plain':{'temporal':{'passed':True}},'empty':{'temporal':{'passed':True}}}
        limits={'minimum_body_extent_pixels':150,'minimum_native_rgb_range_ratio':.8,
                'minimum_native_luma_range_ratio':.8,'minimum_native_visible_coverage_ratio':.7}
        row=glint_visibility_comparison(items,items,True,True,limits)
        self.assertTrue(row['passed'])
        self.assertFalse(row['continuous_motion_accepted'])


if __name__=='__main__':unittest.main()
