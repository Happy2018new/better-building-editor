"""Capture provenance and independent pixel masks must fail closed."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from analyze_liquid_workspace import capture_failures, compare_masks, difference_mask, opacity_row, select_roi, transparency_control


class LiquidWorkspaceAnalysisTests(unittest.TestCase):
    def capture(self, directory):
        path = Path(directory)/'frame.png'
        image = Image.new('RGB',(8,8),(30,40,50))
        image.putpixel((0,0),(200,200,200))
        image.save(path)
        binding = {'owner':'owned', 'game_pid':9, 'game_identity':'123', 'session_file':'session.json'}
        row = dict(binding,ok=True,reliable=True,background_only=True,background_safe=True,native_resolution=True,
                   backend='Windows.Graphics.Capture',variance=[30.,30.,30.],width=8,height=8,path=str(path),
                   sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   frame={'backend':'Windows.Graphics.Capture','request_qpc_100ns':100,'frame_qpc_100ns':101})
        return binding,row

    def test_capture_binding_freshness_and_nonblank_are_independent_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            binding,row = self.capture(directory)
            self.assertEqual([],capture_failures({'frame':row},binding))
            for key,value in (('owner','other'),('game_pid',10),('game_identity','124'),
                              ('background_safe',False),('variance',[0.,0.,0.])):
                changed = dict(row,**{key:value})
                with self.subTest(key=key):
                    self.assertTrue(capture_failures({'frame':changed},binding))
            changed = deepcopy(row)
            changed['frame']['frame_qpc_100ns'] = 99
            self.assertTrue(capture_failures({'frame':changed},binding))

    def test_changed_capture_bytes_and_empty_report_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            binding,row = self.capture(directory)
            Path(row['path']).write_bytes(b'changed')
            self.assertIn('sha256',capture_failures({'frame':row},binding)[0]['failures'])
            self.assertTrue(capture_failures({},binding))

    def test_difference_mask_excludes_context_and_preserves_threshold(self):
        background = np.zeros((100,100,3),dtype=np.int16)
        image = background.copy()
        image[1,1] = 255
        image[25,25] = 12
        image[26,26] = 13
        image[50,50] = 255
        selected = select_roi(image.shape,(20,20,80,80),crosshair=True)
        mask = difference_mask(image,background,selected)
        self.assertEqual(1,int(mask.sum()))
        self.assertTrue(mask[26,26])
        self.assertFalse(mask[1,1])
        self.assertFalse(mask[50,50])

    def test_masks_keep_empty_or_shifted_silhouettes_visible(self):
        first = np.zeros((20,20),dtype=bool)
        second = first.copy()
        self.assertIsNone(compare_masks(first,second)['iou'])
        first[5:10,5:10] = True
        second[5:10,6:11] = True
        row = compare_masks(first,second)
        self.assertEqual(2./3.,row['iou'])
        self.assertEqual(1,row['max_edge_error'])

    def test_body_and_liquid_opacity_and_id_retention_are_separate(self):
        def state(opacity,body,identity):
            return {'body_uniforms':{'4':[19487.,1.,1.,body]},
                    'liquid_groups':[{'id':identity,'group':[None,None,None,[[],[],[],[39686.,-1.,0.,opacity]]]}]}
        low,high = state(.4,.8,1),state(.8,.8,1)
        row = opacity_row(low,high)
        self.assertFalse(row['body_updated'])
        self.assertTrue(row['liquid_updated'])
        self.assertTrue(row['ids_retained'])
        low['body_uniforms']['4'][3] = .4
        high['liquid_groups'][0]['id'] = 2
        row = opacity_row(low,high)
        self.assertTrue(row['body_updated'])
        self.assertFalse(row['ids_retained'])

    def transparency_frames(self):
        empty = np.zeros((20,20,3),dtype=np.int16)
        no_water,liquid_only = empty.copy(),empty.copy()
        rois = {'submerged_body':(2,5,6,10), 'behind_block':(12,5,16,10)}
        for roi in rois.values():
            selected = select_roi(empty.shape,roi)
            no_water[selected] = (150,100,50)
            liquid_only[selected] = (20,40,70)
        return empty,no_water,liquid_only,rois

    def test_opaque_water_fails_even_when_above_water_cap_is_visible(self):
        empty,no_water,liquid_only,rois = self.transparency_frames()
        positive = liquid_only.copy()
        positive[0:2,2:6] = (150,100,50)
        row = transparency_control(positive,no_water,liquid_only,empty,rois)
        self.assertEqual('FAIL',row['status'])
        self.assertTrue(all(value['body_contribution_pixels']==0 for value in row['controls'].values()))
        self.assertFalse(row['native_alpha_accepted'])

    def test_both_independent_regions_need_transmitted_body_contributions(self):
        empty,no_water,liquid_only,rois = self.transparency_frames()
        positive = liquid_only.copy()
        positive[select_roi(empty.shape,rois['submerged_body'])] = (80,60,60)
        self.assertEqual('FAIL',transparency_control(positive,no_water,liquid_only,empty,rois)['status'])
        positive[select_roi(empty.shape,rois['behind_block'])] = (80,60,60)
        row = transparency_control(positive,no_water,liquid_only,empty,rois)
        self.assertEqual('OBSERVED',row['status'])
        self.assertFalse(row['native_alpha_accepted'])

    def test_missing_underlying_or_water_control_is_not_tested(self):
        empty,no_water,liquid_only,rois = self.transparency_frames()
        row = transparency_control(liquid_only,empty,liquid_only,empty,rois)
        self.assertEqual('NOT_TESTED',row['status'])
        row = transparency_control(no_water,no_water,empty,empty,rois)
        self.assertEqual('NOT_TESTED',row['status'])


if __name__ == '__main__':
    unittest.main()
