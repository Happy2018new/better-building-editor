"""Native pose comparison must reject bad controls and incomplete routes."""
import copy
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_item_sprite_closeup import native_body_measurement
from analyze_visible_items_r16 import native_body_gate,native_edge_gate
from item_sprite_edge_pixels import native_edge_measurement


class ItemPoseAcceptanceTests(unittest.TestCase):
    def comparisons(self,offset=0):
        native=np.zeros((96,96),dtype=bool)
        native[20:72,20:72]=True
        body=native_body_measurement(np.roll(native,offset,axis=1),native)
        body['negative_controls']={
            'blank_rejected':not native_body_measurement(np.zeros_like(native),native)['passed'],
            'shifted_rejected':not native_body_measurement(np.roll(native,8,axis=1),native)['passed']}
        return [{'native_body_comparison':{'full':body,'missing':copy.deepcopy(body)}}]

    def test_actual_native_body_with_rejected_blank_and_shifted_controls_passes(self):
        self.assertTrue(native_body_gate(self.comparisons()))

    def test_displaced_body_rejects_even_when_declared_geometry_could_pass(self):
        self.assertFalse(native_body_gate(self.comparisons(offset=8)))

    def test_missing_route_or_native_reference_cannot_pass(self):
        self.assertFalse(native_body_gate([]))
        self.assertFalse(native_body_gate([{}]))
        cases=self.comparisons()
        del cases[0]['native_body_comparison']['missing']
        self.assertFalse(native_body_gate(cases))

    def test_unrejected_or_missing_negative_control_rejects(self):
        for name in ('blank_rejected','shifted_rejected'):
            cases=self.comparisons()
            cases[0]['native_body_comparison']['missing']['negative_controls'][name]=False
            self.assertFalse(native_body_gate(cases))
            del cases[0]['native_body_comparison']['missing']['negative_controls'][name]
            self.assertFalse(native_body_gate(cases))

    def test_later_failed_pose_cannot_be_hidden_by_an_earlier_success(self):
        self.assertFalse(native_body_gate(self.comparisons()+self.comparisons(offset=8)))

    def test_local_clipped_tip_rejects_even_when_global_native_body_passes(self):
        native=np.zeros((240,320),dtype=bool)
        native[50:190,40:240]=True
        native[112:128,240:256]=True
        clipped=native.copy()
        clipped[112:128,252:256]=False
        self.assertTrue(native_body_measurement(clipped,native)['passed'])
        edge=native_edge_measurement(clipped,native)
        self.assertFalse(edge['passed'])
        self.assertTrue(any(row['label']=='terminal_right' and not row['passed'] for row in edge['regions']))

    def test_local_gate_preserves_two_pixel_tolerance_and_rejects_blank(self):
        native=np.zeros((180,180),dtype=bool)
        native[40:140,30:150]=True
        self.assertTrue(native_edge_measurement(np.roll(native,2,axis=1),native)['passed'])
        self.assertFalse(native_edge_measurement(np.zeros_like(native),native)['passed'])
        self.assertFalse(native_edge_measurement(native,np.zeros_like(native))['passed'])

    def test_every_pose_needs_both_local_native_routes_and_a_rejected_blank(self):
        native=np.zeros((180,180),dtype=bool)
        native[40:140,30:150]=True
        edge=native_edge_measurement(native,native)
        edge['negative_controls']={'blank_rejected':True}
        cases=[{'native_edge_comparison':{'full':edge,'missing':copy.deepcopy(edge)}}]
        self.assertTrue(native_edge_gate(cases))
        self.assertFalse(native_edge_gate([]))
        self.assertFalse(native_edge_gate([{}]))
        cases[0]['native_edge_comparison']['missing']['negative_controls']['blank_rejected']=False
        self.assertFalse(native_edge_gate(cases))

    def test_two_pixel_tolerance_does_not_mask_thicker_lost_perimeter(self):
        native=np.zeros((180,180),dtype=bool)
        native[40:140,30:150]=True
        body=np.roll(native,3,axis=1)
        self.assertFalse(native_edge_measurement(body,native)['passed'])


if __name__=='__main__':
    unittest.main()
