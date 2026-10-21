"""Run unchanged actual LiquidControls.update with an already-ready request."""
import ast
from collections import OrderedDict, namedtuple
import json
import os
import sys

WORK = os.path.dirname(os.path.abspath(__file__)).decode(sys.getfilesystemencoding())
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(WORK)))
PATH = os.path.join(ROOT, '.runtime/projects/water-r27-gui-offset-v1/behavior_pack/modern_projection/projection/liquid_viewport.py')


def main():
    output = sys.argv[1]
    assert not os.path.exists(output)
    source = open(PATH, 'rb').read()
    module = ast.parse(source)
    cls = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == 'LiquidControls')
    reduced = ast.Module(body=[cls])
    ast.fix_missing_locations(reduced)
    namespace = {'SkeletonLiquidRenderer': object, 'with_preview_distance': object(),
                 'integer_types': (int, long), 'RenderGroup': tuple, '_immutable': lambda value: True}
    exec compile(reduced, '<actual-LiquidControls>', 'exec') in namespace
    LiquidControls = namespace['LiquidControls']
    class Native(object):
        def __init__(self):self.calls=[]
        def SetPosition(self, value):self.calls.append(('position',value))
        def SetSize(self, value):self.calls.append(('size',value))
    class Ref(object):
        def __init__(self):self.current=Native()
    class Renderer(object):
        def __init__(self):self.error=None;self.updates=0
        def restore_publication(self):return True
        def update(self, *args):self.updates+=1;return True
        @staticmethod
        def validate(group,pose):return pose
    Group = namedtuple('Group','origin')
    View = namedtuple('View','position size distance clipped')
    group=Group((0,0,0));renderer=Renderer()
    dolls,surfaces=[Ref(),Ref()],[Ref(),Ref()]
    displayed=group;pose=(.1,-55.,0.,25.)
    entry={'dolls':dolls,'surfaces':surfaces,'renderer':renderer,'ready_request':(displayed,pose),
           'geometry':((20.,75.),(400.,300.)),'clip_offset':(0.,0.)}
    controls=LiquidControls(OrderedDict((('one',entry),)),None,renderer_factory=Renderer,
                            distance_adapter=lambda group,distance:group)
    current=View((20.,150.),(400.,300.),4.,False)
    assert controls.update({'one':group},lambda origin:current,lambda view:pose,(0.,0.),0.)
    assert renderer.updates==0,'An unchanged ready request must not resubmit the model'
    assert all(ref.current.calls==[('position',(20.,150.)),('size',(400.,300.))] for ref in dolls)
    assert entry['geometry']==((20.,150.),(400.,300.))
    before=[list(ref.current.calls) for ref in dolls]
    assert controls.update({'one':group},lambda origin:current,lambda view:pose,(0.,0.),1.)
    assert renderer.updates==0 and [ref.current.calls for ref in dolls]==before
    report={'schema':1,'passed':True,'python':sys.version,'MC_started':False,
            'scope':'Actual unchanged LiquidControls class; explicit fake native setters and renderer only',
            'controls':[{'name':'Geometry updates before identical ready_request early return','passed':True},
                        {'name':'Stable geometry does not duplicate native setters or model submission','passed':True}],
            'formal_A_accepted':False,'production_admission_performed':False}
    open(output,'wb').write(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'controls':2}))


if __name__=='__main__':main()
