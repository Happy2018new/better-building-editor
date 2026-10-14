"""Image gate rejects absent controls, moving poses and unselected backdrops."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image,ImageDraw

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_projection_occlusion_r17 import analyze


def fixture(folder,leak=True,unstable=False,selected=True):
    folder.mkdir()
    case='enchanting_table'
    report={'completed':True,'restored':True,'prepared':{'focus':[3,3,3]},
            'rows':{case:{'source':{'fixture':'synthetic_negative_controls'}}},'captures':{}}
    for mode in ('off','on'):
        for background in ('air','air_back_repeat','leaves','stone','glass'):
            suffix=background if background=='air_back_repeat' else background+'_back'
            label=case+'_'+mode+'_'+suffix
            image=Image.new('RGB',(140,140),(140,85,35))
            if ((mode=='off' and background in ('leaves','stone','glass') and leak) or
                    (unstable and background=='air_back_repeat')):
                ImageDraw.Draw(image).line((40,70,100,70),fill=(0,0,0),width=2)
            path=folder/(label+'.png');image.save(path)
            report['captures'][label]={
                'capture':{'ok':True,'reliable':True,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},
                'pointed_block':{'hit':{'type':'Block' if selected else 'None','x':5,'z':3},
                                 'material':['minecraft:'+('oak_leaves' if background=='leaves' else background),0]}}
    (folder/'report.json').write_text(json.dumps(report),encoding='utf8')
    return folder


class ProjectionOcclusionAnalysisTests(unittest.TestCase):
    def run_case(self,**kwargs):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            source=fixture(root/'source',**kwargs)
            return analyze(source,'enchanting_table',(10,10,130,130),root/'output')

    def test_known_leak_and_depth_on_control_are_distinguished(self):
        result=self.run_case()
        self.assertTrue(result['passed'])
        self.assertGreater(result['results']['off']['backdrops']['leaves']['pixels'],0)
        self.assertEqual(0,result['results']['on']['backdrops']['leaves']['pixels'])

    def test_no_reproduction_cannot_pass_as_a_fix(self):
        result=self.run_case(leak=False)
        self.assertFalse(result['passed'])
        self.assertTrue(any('negative control' in row for row in result['failures']))

    def test_moving_pose_invalidates_comparison(self):
        result=self.run_case(unstable=True)
        self.assertFalse(result['passed'])
        self.assertTrue(any('repeat is unstable' in row for row in result['failures']))

    def test_missed_selection_is_an_invalid_fixture(self):
        with self.assertRaisesRegex(ValueError,'not selected'):
            self.run_case(selected=False)


if __name__=='__main__':unittest.main()
