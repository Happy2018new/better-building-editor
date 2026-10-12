"""The sampled native PNG must be the exact file bound by both capture records."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import analyze_liquid_coordinate_markers as primary
import diagnose_liquid_coordinate_background as background
import diagnose_liquid_coordinate_centers as centers
from analyze_liquid_workspace import capture_failures
from liquid_coordinate_markers import checked_capture_image,fingerprint


class NativePNGProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name)
        self.binding={'owner':'fixture','game_pid':1,'game_identity':'identity','session_file':'fixture-session.json'}
        self.positive=self.capture('positive.png',20);self.negative=self.capture('negative.png',160)

    def capture(self,name,offset):
        path=self.base/name
        pixels=np.arange(48,dtype=np.uint8).reshape(4,4,3)+offset
        Image.fromarray(pixels).save(path);payload=path.read_bytes()
        receipt=dict(self.binding,path=str(path),sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),
                     width=4,height=4,ok=True,reliable=True,background_only=True,background_safe=True,
                     native_resolution=True,backend='Windows.Graphics.Capture',variance=[20.,20.,20.],
                     frame={'backend':'Windows.Graphics.Capture','request_qpc_100ns':1,'frame_qpc_100ns':2,
                            'width':4,'height':4})
        return {'path':str(path),'sha256':receipt['sha256'],'bytes':len(payload),'mime':'image/png',
                'size':[4,4],'capture':receipt}

    def write(self,name,value):
        path=self.base/name;path.write_text(json.dumps(value),encoding='ascii');return path

    def fixture(self,control):
        swapped=copy.deepcopy(self.positive if control=='supported_positive' else self.negative)
        swapped['path']=self.negative['path'] if control=='supported_positive' else self.positive['path']
        cases=[];geometry=[];sequences=[]
        for depth,role in (('0','training'),('1','holdout')):
            case='fixture_depth_'+depth+'_pool';controls={name:{} for name in (
                'supported_positive','supported_negative','liquid_only','empty')}
            geometry.append({'case':case,'controls':controls,'surfaces':[]})
            captures={name:{'completed':True,'capture':copy.deepcopy(self.positive),
                            'native_before_capture':{},'native_after_capture':{}} for name in controls}
            captures['supported_negative']['capture']=copy.deepcopy(self.negative)
            captures[control]['capture']=copy.deepcopy(swapped)
            cases.append({'case':case,'completed':True,'controls':captures,'source':{'controls':controls}})
            sequences.append({'id':depth+'/north','role':role,'case':case,'observed':[[20.,30.,40.]],
                              'native_sample_points':[[1.,1.]],'grid':{'world_points':[[0.,0.,1.]]}})
        original=self.write('original.json',{'frozen_sources':{},'geometry_sequences':geometry,
            'geometry_roles':{'0':'training','1':'holdout'},'controls':list(controls),'sample_control':'supported_positive'})
        calibration=self.write('calibration.json',{'completed':True,'passed':True,'restored':True,
            'cleanup_errors':[],'session_file':'fixture-session.json','vertical_fov':60.})
        raw=self.write('native.json',{'coordinate_plan':fingerprint(original),'calibration':fingerprint(calibration),
            'session_file':'fixture-session.json','completed':True,'restored':True,'cleanup_errors':[],
            'background_only':True,'session_binding':self.binding,'cases':cases,
            'camera':{'stable':{'screen':[4,4]},'position':[0,0,0],'target':[0,0,1]}})
        baseline=self.write('baseline.json',{'plan':fingerprint(original),'source':fingerprint(raw),
            'capture_failures':[],'sampled_sequences':sequences})
        diagnostic=self.write('diagnostic.json',{'input':fingerprint(baseline),'original_plan':fingerprint(original),
            'independent_contrast':fingerprint(calibration),'sources':{},'background_control':'supported_negative',
            'transmission':.33,'sequences':sequences})
        return raw,diagnostic

    def test_exact_payload_is_decoded_and_records_are_all_checked(self):
        with checked_capture_image(self.positive) as image:
            np.testing.assert_array_equal(np.asarray(image),np.arange(48,dtype=np.uint8).reshape(4,4,3)+20)
        for location,key,value in (('wrapper','sha256','0'*64),('receipt','sha256','0'*64),
                                   ('wrapper','bytes',1),('receipt','bytes',1),('wrapper','size',[8,8]),
                                   ('frame','width',8)):
            changed=copy.deepcopy(self.positive)
            row=changed if location=='wrapper' else changed['capture']
            if location=='frame':row=row['frame']
            row[key]=value
            with self.subTest(location=location,key=key),self.assertRaises(ValueError):checked_capture_image(changed)

    def test_swapped_wrapper_still_passes_inner_receipt_but_cannot_be_sampled(self):
        swapped=copy.deepcopy(self.positive);swapped['path']=self.negative['path']
        self.assertEqual([],capture_failures({'positive':swapped['capture']},self.binding))
        with self.assertRaisesRegex(ValueError,'wrapper path'):checked_capture_image(swapped)

    def test_path_replacement_after_verification_does_not_replace_decoded_pixels(self):
        original_open=Image.open
        def replace_then_decode(source):
            Path(self.positive['path']).write_bytes(Path(self.negative['path']).read_bytes())
            return original_open(source)
        with patch('liquid_coordinate_markers.Image.open',side_effect=replace_then_decode):
            with checked_capture_image(self.positive) as image:
                np.testing.assert_array_equal(np.asarray(image),np.arange(48,dtype=np.uint8).reshape(4,4,3)+20)

    def test_all_native_analyzers_reject_swapped_wrapper_before_scoring(self):
        for analyzer,control in ((primary,'supported_positive'),(background,'supported_negative'),
                                 (centers,'supported_positive')):
            raw,plan=self.fixture(control)
            with self.subTest(analyzer=analyzer.__name__),patch.object(primary,'fixed_viewport'), \
                 patch.object(primary,'native_gate',return_value={'public_snapshot_unchanged':True}), \
                 patch.object(centers,'project_points',return_value=[{'isInScreen':True,'depth':1.,'screenX':1.,'screenY':1.}]), \
                 patch.object(analyzer,'measure' if analyzer is primary else 'diagnose',
                              side_effect=AssertionError('Scored a substituted PNG')):
                with self.assertRaisesRegex(ValueError,'wrapper path'):
                    if analyzer is primary:analyzer.analyze(raw)
                    else:analyzer.analyze(plan,self.base/'unused-output.json')


if __name__=='__main__':unittest.main()
