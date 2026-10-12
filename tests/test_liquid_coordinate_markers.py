"""Nonlinear cold markers discriminate spatial UVs without fitted photometry."""
import sys
import unittest
import json
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from liquid_coordinate_markers import marker_frame,measure,ranks,score


def independent_samples(frame,u,height):
    values=[]
    for x_fraction,y_height in zip(u,height):
        x,y=x_fraction*15,(1.-y_height)*15
        left,top=int(x),int(y)
        dx,dy=x-left,y-top
        values.append(frame[top,left,:3]*(1-dx)*(1-dy)
            +frame[top,left+1,:3]*dx*(1-dy)+frame[top+1,left,:3]*(1-dx)*dy
            +frame[top+1,left+1,:3]*dx*dy)
    return np.asarray(values)


class CoordinateMarkerTests(unittest.TestCase):
    def sequences(self,frame):
        u,fraction=np.meshgrid(np.linspace(.12,.88,16),np.linspace(.12,.88,16))
        u,fraction=u.ravel(),fraction.ravel()
        rows=[]
        for depth,top in ((0,.82),(1,.64),(3,.46)):
            heights=fraction*top
            expected=independent_samples(frame,u,heights)
            observed=10.+(expected/255.)**1.3*np.array([90.,130.,170.])
            rows.append({'id':str(depth),'role':'training' if depth==0 else 'holdout',
                         'grid':{'u':u,'height':heights,'top':np.full_like(u,top)},'observed':observed})
        return rows

    def test_equal_quadrant_histograms_do_not_repeat_spatial_codes(self):
        frame=marker_frame(32,271)
        for channel in range(3):
            np.testing.assert_array_equal(np.sort(frame[:16,:16,channel].ravel()),
                                          np.sort(frame[16:,16:,channel].ravel()))
        self.assertFalse(np.array_equal(frame[:16,:16],frame[16:,16:]))
        self.assertTrue(np.all(frame[:,:,3]==255))

    def test_fixed_spatial_hypotheses_survive_monotonic_photometry(self):
        frame=marker_frame(32,271)
        result=measure(frame,self.sequences(frame))
        self.assertTrue(result['passed'],result)
        self.assertEqual('nw',result['selected']['region'])
        self.assertEqual('centers',result['selected']['pixel_mapping'])
        self.assertTrue(all(row['identified'] for row in result['identification'].values()))

    def test_serialized_native_grid_uses_the_same_fixed_hypotheses(self):
        frame=marker_frame(32,271)
        sequences=self.sequences(frame)
        serial=json.loads(json.dumps(sequences,default=lambda array:array.tolist()))
        self.assertEqual(measure(frame,sequences),measure(frame,serial))

    def test_geometry_holdout_is_not_used_to_select_a_mapping(self):
        frame=marker_frame(32,271);rows=self.sequences(frame)
        baseline=measure(frame,rows)
        rows[1]['observed']=np.flip(rows[1]['observed'],axis=0)
        result=measure(frame,rows)
        self.assertEqual(baseline['selected'],result['selected'])
        self.assertFalse(result['passed'])

    def test_null_signal_and_no_geometry_holdout_are_rejected(self):
        frame=marker_frame(32,271);rows=self.sequences(frame)
        for row in rows:row['observed']=np.full_like(row['observed'],80.)
        self.assertFalse(measure(frame,rows)['passed'])
        with self.assertRaises(ValueError):measure(frame,rows[:1])

    def test_rank_ties_and_nonmonotonic_spatial_errors(self):
        values=np.array([[0,2,5],[0,1,4],[4,1,3]],float)
        np.testing.assert_array_equal(ranks(values)[:,0],[.25,.25,1.])
        self.assertEqual(0.,score(values,values*3+20)['rank_rmse'])
        self.assertGreater(score(values,values[::-1])['rank_rmse'],.2)


if __name__=='__main__':unittest.main()
