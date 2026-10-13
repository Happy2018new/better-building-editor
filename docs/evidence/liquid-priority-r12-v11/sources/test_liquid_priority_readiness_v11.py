"""Finite cross-render camera declaration and failure journal replay."""
import ast
import copy
import math
from pathlib import Path
import unittest

source = Path(__file__).with_name('probe_liquid_original_sides_r12_v11.py').read_text(encoding='utf8')
tree = ast.parse(source)
names = {'camera_matches', 'forward_cosine', 'settle_camera'}
scope = {'math': math, 'workspace': type('Workspace', (), {'CAMERA': 'direction[1]+180.\n%r'})(),
         'CAMERA_STATE': 'state'}
exec(compile(ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef)
                             and node.name in names], type_ignores=[]), '<finite camera>', 'exec'), scope)


class FakeCheck:
    def __init__(self, values):self.values=values;self.cursor=0
    def run(self, code):
        if code != 'state':return {'position':[1.,2.,3.], 'render_events_at_request':10}
        value = self.values[min(self.cursor,len(self.values)-1)];self.cursor+=1;return copy.deepcopy(value)
    def wait(self, label, predicate, read):
        for unused in range(8):
            value=read()
            if predicate(value):return value
        raise TimeoutError('Finite actual-camera wait')


def camera(frames=12, rotation=0., forward=(0.,0.,-1.)):
    return {'position':[1.,2.,3.], 'rotation':[0.,rotation,0.], 'screen':[499.,277.],
            'fov':60., 'forward':forward, 'render_events':frames}


class CrossRenderCameraTests(unittest.TestCase):
    def test_delayed_setter_waits_for_render_and_stable_forward_before_declaration(self):
        journal=[]
        values=[camera(10,180.),camera(11,180.),camera(12),camera(13)]
        value=scope['settle_camera'](FakeCheck(values),(1.,2.,2.),(0.,0.,1.),journal,lambda:None)
        self.assertEqual(4,len(journal[0]['readbacks']))
        self.assertTrue(journal[0]['selected'])
        self.assertEqual(0.,value['rotation'][1])
        self.assertEqual([1.,2.,2.],value['target'])

    def test_never_render_ready_stops_after_fixed_read_count(self):
        journal=[]
        with self.assertRaises(TimeoutError):
            scope['settle_camera'](FakeCheck([camera(10)]),(1.,2.,2.),(0.,0.,1.),journal,lambda:None)
        self.assertEqual(8,len(journal[0]['readbacks']))
        self.assertNotIn('selected',journal[0])

    def test_wrong_forward_candidates_preserve_raw_readbacks_and_no_selection(self):
        journal=[]
        with self.assertRaises(RuntimeError):
            scope['settle_camera'](FakeCheck([camera(forward=(1.,0.,0.))]),(1.,2.,2.),(0.,0.,1.),journal,lambda:None)
        self.assertEqual([180.,0.],[row['yaw_adjustment'] for row in journal])
        self.assertTrue(all(row['readbacks'] and not row['selected'] for row in journal))
        main=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main')
        frame=next(node for node in ast.walk(main) if isinstance(node,ast.FunctionDef) and node.name=='frame')
        code=ast.unparse(frame)
        self.assertLess(code.index("report['states'][identity]"),code.index('validate_frame(identity, before)'))
        self.assertLess(code.index('save()'),code.index('validate_frame(identity, before)'))


if __name__=='__main__':unittest.main()
