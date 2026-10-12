"""Complement coding survives spatial photometry only with independent pure phases."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import liquid_coordinate_bitplanes as code
from liquid_coordinate_markers import fingerprint
from measure_native_liquid_side_uv import Hypothesis


def exact_phases():
    return [{'kind':'synthetic_exact_frame','frame':index,'interpolation_fraction':0.} for index in range(20)]


def independent_edge_samples(frames,u,height):
    x=np.clip(np.floor(np.asarray(u)*16).astype(int),0,31)
    y=np.clip(np.floor((1-np.asarray(height))*16).astype(int),0,31)
    return frames[:20,y,x,:3].astype(float)


class CoordinateBitplaneTests(unittest.TestCase):
    def sequences(self):
        frames,_=code.marker_frames();u,fraction=np.meshgrid(code.GRID,code.GRID)
        u,fraction=u.ravel(),fraction.ravel();rows=[]
        for depth,top in ((0,.82),(1,.64),(3,.46)):
            height=fraction*top;expected=independent_edge_samples(frames,u,height)
            gain=np.column_stack((.02+.01*u,.15+.08*fraction,.3+.2*u))
            background=np.column_stack((220-180*fraction,40+120*u,170-100*fraction))
            observed=expected*gain[None,:,:]+background[None,:,:]
            rows.append({'id':str(depth),'role':'training' if depth==0 else 'holdout',
                         'grid':{'u':u,'height':height,'top':np.full_like(u,top)},
                         'observed_frames':observed,'phase_records':exact_phases()})
        return frames,rows

    def test_marker_is_grayscale_opaque_and_complements_all_ten_address_bits(self):
        frames,schedule=code.marker_frames()
        self.assertEqual((32,32,32,4),frames.shape);self.assertEqual(32,len(schedule))
        np.testing.assert_array_equal(frames[:,:,:,0],frames[:,:,:,1])
        np.testing.assert_array_equal(frames[:,:,:,0],frames[:,:,:,2])
        self.assertTrue(np.all(frames[:,:,:,3]==255))
        np.testing.assert_array_equal(frames[:20:2,:,:,:3].astype(int)+frames[1:20:2,:,:,:3],
                                      np.full((10,32,32,3),code.LOW+code.HIGH))
        signatures=np.transpose(frames[:20:2,:,:,0]>128,(1,2,0)).reshape(1024,10)
        self.assertEqual(1024,len(np.unique(signatures,axis=0)))

    def test_spatial_gain_and_nonuniform_backdrop_cancel_without_fitting(self):
        frames,rows=self.sequences();result=code.measure(frames,rows,'synthetic_exact_frames')
        self.assertTrue(result['synthetic_contract_passed'],result)
        self.assertEqual('nw',result['selected']['region'])
        self.assertEqual('bottom',result['selected']['side_v'])
        self.assertEqual('edges',result['selected']['pixel_mapping'])
        self.assertTrue(all(row['identified'] for row in result['identification'].values()))
        self.assertFalse(result['native_uv_accepted'])

    def test_wrong_holdout_bit_is_not_hidden_by_spatial_photometry(self):
        frames,rows=self.sequences()
        rows[1]['observed_frames'][0,0,1:3],rows[1]['observed_frames'][1,0,1:3]=(
            rows[1]['observed_frames'][1,0,1:3].copy(),rows[1]['observed_frames'][0,0,1:3].copy())
        result=code.measure(frames,rows,'synthetic_exact_frames')
        self.assertGreater(result['sequences']['1']['contradictions'],0)
        self.assertFalse(result['synthetic_contract_passed'])

    def test_timing_only_phase_and_swapped_exact_frame_proofs_reject_before_scoring(self):
        frames,rows=self.sequences()
        with patch.object(code,'expected_frames',side_effect=AssertionError('Scored unproven phases')):
            with self.assertRaisesRegex(ValueError,'native frame/mixture'):code.measure(frames,rows,'native_timing')
            rows[0]['phase_records'][0],rows[0]['phase_records'][2]=rows[0]['phase_records'][2],rows[0]['phase_records'][0]
            with self.assertRaisesRegex(ValueError,'exact frame order'):code.measure(frames,rows,'synthetic_exact_frames')

    def test_unobserved_axis_frame_permutation_can_masquerade_as_transposed_uv(self):
        frames,rows=self.sequences();order=np.r_[np.arange(10,20),np.arange(10)]
        for row in rows:row['observed_frames']=row['observed_frames'][order]
        result=code.measure(frames,rows,'synthetic_exact_frames')
        self.assertTrue(result['synthetic_contract_passed'])
        self.assertEqual('transpose',result['selected']['orientation'])
        self.assertFalse(result['native_uv_accepted'])
        with self.assertRaisesRegex(ValueError,'native frame/mixture'):code.measure(frames,rows,'native_timing')

    def test_half_interpolation_erases_complement_and_nonzero_mixture_is_rejected(self):
        frames,rows=self.sequences();values=rows[0]['observed_frames']
        midpoint=(values[0]+values[1])/2.;values[0]=midpoint;values[1]=midpoint
        with self.assertRaisesRegex(ValueError,'sufficient agreeing signal'):code.measure(frames,rows,'synthetic_exact_frames')
        rows[0]['phase_records'][0]['interpolation_fraction']=.5
        with self.assertRaisesRegex(ValueError,'zero interpolation'):code.measure(frames,rows,'synthetic_exact_frames')

    def test_background_drift_channel_disagreement_and_duplicate_ids_reject(self):
        frames,rows=self.sequences();changed=copy.deepcopy(rows)
        changed[0]['observed_frames'][0,0,1]+=500.
        changed[0]['observed_frames'][1,0,2]+=500.
        with self.assertRaisesRegex(ValueError,'agreeing signal'):code.measure(frames,changed,'synthetic_exact_frames')
        rows[1]['id']=rows[0]['id']
        with self.assertRaisesRegex(ValueError,'unique nonempty'):code.measure(frames,rows,'synthetic_exact_frames')

    def test_center_only_samples_do_not_identify_pixel_mapping(self):
        frames,_=code.marker_frames();u=(np.arange(2,14)+.5)/16
        height=1-(np.arange(2,14)+.5)/16
        grid={'u':u,'height':height,'top':np.ones_like(u)}
        edge=Hypothesis('nw','bottom','identity',1.,False,0.,'edges')
        center=Hypothesis('nw','bottom','identity',1.,False,0.,'centers')
        np.testing.assert_array_equal(code.expected_frames(frames,grid,edge,'nearest'),
                                      code.expected_frames(frames,grid,center,'nearest'))

    def test_entrypoint_rejects_changed_frozen_geometry_before_scoring(self):
        frames,rows=self.sequences()
        for row in rows:row.update(case='fixture_depth_'+row['id'],controls={'supported_positive':{'cells':[]}})
        serial=json.loads(json.dumps(rows,default=lambda array:array.tolist()))
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);marker=base/'flow.png';Image.fromarray(frames.reshape(1024,32,4)).save(marker)
            plan_path=base/'plan.json';input_path=base/'input.json'
            plan={'frozen_sources':{},'marker':fingerprint(marker),'schedule':code.marker_frames()[1],
                  'sequences':[{key:row[key] for key in ('id','role','case','grid','controls')} for row in serial]}
            plan_path.write_text(json.dumps(plan),encoding='ascii')
            source={'plan':fingerprint(plan_path),'sequences':serial,'evidence_kind':'synthetic_exact_frames'}
            source['sequences'][0]['grid']['u'][0]+=.01
            input_path.write_text(json.dumps(source),encoding='ascii')
            with patch.object(code,'measure',side_effect=AssertionError('Scored changed geometry')):
                with self.assertRaisesRegex(ValueError,'geometry samples changed'):code.analyze_synthetic(input_path)


if __name__=='__main__':unittest.main()
