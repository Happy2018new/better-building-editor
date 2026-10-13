"""Reject misleading visibility, raw state drift and changed frozen native scope."""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import run_native_plant_positions as runner
import verify_native_plant_positions_phase as phase


class NativeCoordinateControlTests(unittest.TestCase):
    def snapshot(self, name='minecraft:poppy', box=None):
        if box is None:
            box = {'min': [6.2,-48.,6.2], 'max': [6.75,-47.4,6.75]}
        return {'server': {'pos': [6,-48,6], 'front': {'name': name,'aux':0},
                           'clip': box,'collision':box},
                'client': {'pos': [6,-48,6], 'front': [name,0], 'clip': box,'collision':box,
                           'palette': {'common': [[name,0,[0]]], 'extra': []}}}

    def test_matching_native_boxes_pass_without_mesh_authority(self):
        value = self.snapshot()
        self.assertTrue(phase.boxes_consistent(value, copy.deepcopy(value), (6,-48,6), 'minecraft:poppy'))
        self.assertFalse(phase.CONTRACT['selection_boxes_are_mesh_pivots'])
        self.assertFalse(phase.CONTRACT['production_acceptance'])

    def test_client_server_aux_disagreement_fails(self):
        value=self.snapshot();value['client']['front'][1]=1
        self.assertFalse(phase.boxes_consistent(value,value,(6,-48,6),'minecraft:poppy'))

    def test_box_changes_across_capture_fail(self):
        before=self.snapshot();after=copy.deepcopy(before)
        for side in ('server','client'):after[side]['clip']['min'][0]+=.01
        self.assertFalse(phase.boxes_consistent(before,after,(6,-48,6),'minecraft:poppy'))

    def test_position_disagreement_fails(self):
        value=self.snapshot();value['client']['pos'][0]=7
        self.assertFalse(phase.boxes_consistent(value,value,(6,-48,6),'minecraft:poppy'))

    def test_matching_absent_air_boxes_are_recorded(self):
        value=self.snapshot('minecraft:air')
        for side in ('server','client'):
            value[side]['clip']=None;value[side]['collision']=None
        self.assertTrue(phase.boxes_consistent(value,value,(6,-48,6),'minecraft:air'))

    def test_absent_plant_clip_is_rejected(self):
        value=self.snapshot()
        for side in ('server','client'):value[side]['clip']=None
        self.assertFalse(phase.boxes_consistent(value,value,(6,-48,6),'minecraft:poppy'))

    def mask(self, rect):
        image=Image.new('L',(997,552));ImageDraw.Draw(image).rectangle(rect,fill=255)
        return image

    def test_complete_stone_footprint_passes_existing_thresholds(self):
        reference=self.mask((306,115,683,455))
        value=phase.stone_coverage(reference,reference)
        self.assertTrue(value['passed']);self.assertEqual(value['recall_3px'],1.)

    def test_small_moving_actor_cannot_qualify_stone(self):
        reference=self.mask((306,115,683,455));actual=self.mask((500,300,540,350))
        self.assertGreater(actual.histogram()[255],1000)
        self.assertFalse(phase.stone_coverage(actual,reference)['passed'])

    def test_large_wrong_region_cannot_qualify_stone(self):
        reference=self.mask((306,115,683,455));actual=self.mask((0,0,377,340))
        self.assertFalse(phase.stone_coverage(actual,reference)['passed'])

    def plan(self):
        return {'native_coordinate_control': copy.deepcopy(phase.CONTRACT),
                'texture_condition': 'native_original',
                'files': {'native_coordinate_runner': {'path':str(runner.ROOT/'tools/run_native_plant_positions.py')},
                          'native_coordinate_phase': {'path':str(runner.ROOT/'tools/verify_native_plant_positions_phase.py')},
                          'native_stone_reference_roi': {'sha256':phase.CONTRACT['stone_reference_roi_sha256']}}}

    def validate(self, value):
        with mock.patch.object(runner.startup,'validate_plan',return_value=value):
            return runner.validate_plan('not-launched.json','unused')

    def test_original_frozen_contract_validates_without_launch(self):
        self.assertEqual(self.validate(self.plan())['native_coordinate_control'],phase.CONTRACT)

    def test_texture_override_rejected(self):
        value=self.plan();value['texture_condition']='native_alpha_preserved'
        with self.assertRaises(ValueError):self.validate(value)

    def test_candidate_profile_rejected(self):
        value=self.plan();value['plant_candidate']={'identifier':'diagnostic'}
        with self.assertRaises(ValueError):self.validate(value)

    def test_target_or_reference_changes_rejected(self):
        value=self.plan();value['native_coordinate_control']['targets'][0][0]=9
        with self.assertRaises(ValueError):self.validate(value)
        value=self.plan();value['files']['native_stone_reference_roi']['sha256']='0'*64
        with self.assertRaises(ValueError):self.validate(value)


if __name__ == '__main__':unittest.main()
