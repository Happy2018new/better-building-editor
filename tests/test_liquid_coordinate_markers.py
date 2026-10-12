"""Nonlinear cold markers discriminate spatial UVs without fitted photometry."""
import sys
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from liquid_coordinate_markers import check_frozen_sources,fingerprint,marker_frame,measure,ranks,score,validate_sequences


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

    def test_colliding_holdout_id_rejects_wrong_training_before_every_scorer(self):
        import diagnose_liquid_coordinate_background as background
        import diagnose_liquid_coordinate_centers as centers
        import diagnose_liquid_coordinate_sampling as sampling
        frame=marker_frame(32,271);rows=self.sequences(frame)
        rows[0]['observed']=np.flip(rows[0]['observed'],axis=0)
        rows[1]['id']=rows[0]['id']
        for scorer,module in ((measure,'liquid_coordinate_markers'),
                              (sampling.diagnose,'diagnose_liquid_coordinate_sampling'),
                              (background.diagnose,'diagnose_liquid_coordinate_background'),
                              (centers.diagnose,'diagnose_liquid_coordinate_background')):
            with self.subTest(scorer=scorer.__module__),patch(module+'.score',side_effect=AssertionError('Scored invalid sequences')):
                with self.assertRaisesRegex(ValueError,'unique nonempty string'):scorer(frame,rows)

    def test_sequence_ids_and_roles_are_exhaustive(self):
        valid=[{'id':'train','role':'training'},{'id':'test','role':'holdout'}]
        self.assertEqual(valid,validate_sequences(iter(valid)))
        for identifier in (None,0,'','  '):
            with self.subTest(identifier=identifier),self.assertRaises(ValueError):
                validate_sequences([dict(valid[0],id=identifier),valid[1]])
        for role in (None,'validation','TRAINING'):
            with self.subTest(role=role),self.assertRaises(ValueError):
                validate_sequences(valid+[{'id':'unexpected','role':role}])
        with self.assertRaises(ValueError):validate_sequences(valid[1:])

    def test_frozen_archive_fallback_is_explicit_and_strict(self):
        with tempfile.TemporaryDirectory() as directory:
            live=Path(directory)/'live.py';archive=Path(directory)/'archive.py'
            live.write_bytes(b'original\n');archive.write_bytes(live.read_bytes())
            plan={'frozen_sources':{'fixture':{'live':fingerprint(live),'archive':fingerprint(archive)}}}
            self.assertEqual([],check_frozen_sources(plan)['archive_fallbacks'])
            live.write_bytes(b'updated\n')
            with self.assertRaisesRegex(ValueError,'fixture/live'):check_frozen_sources(plan)
            result=check_frozen_sources(plan,allow_archive=True)
            self.assertEqual(fingerprint(live),result['archive_fallbacks'][0]['current_live'])
            self.assertEqual(plan['frozen_sources']['fixture']['archive'],result['archive_fallbacks'][0]['verified_archive'])
            archive.write_bytes(b'changed archive\n')
            with self.assertRaisesRegex(ValueError,'fixture/archive'):check_frozen_sources(plan,allow_archive=True)


if __name__=='__main__':unittest.main()
