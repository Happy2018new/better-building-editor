"""Compare one supplied liquid cell with native stone in the same UI viewport."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import probe_liquid_pose_channel as base
import probe_liquid_skeleton_water as water
from _session import load_session

OPEN = '''from modern_projection.pyreact import Component,Panel,Image,Color,Position,PaperDollRenderType,use_ref,navigator
from modern_projection.pyreact.hooks import use_animation_frame
from modern_projection.projection.widgets import Doll,S
from modern_projection.projection.liquid_render import SkeletonLiquidRenderer
assert not navigator.is_transitioning
assert navigator.top is None or navigator.top.key=='modern_projection_workspace'
assert not hasattr(sys,'_liquid_water_ui')
sys._liquid_water_ui={'refs':None,'renderers':None,'groups':[None],
 'pose':(.18,-65.,0.,35.),'ready':[False],'frames':0,'closing':False,
 'stone':None,'seed':None,'stone_name':None,'stone_pose':None,'stone_visible':False}
@Component
def LiquidAlignmentUI():
 refs=[use_ref(None),use_ref(None)]
 stone,seed=use_ref(None),use_ref(None)
 def tick(now):
  saved=getattr(sys,'_liquid_water_ui',None)
  if saved is None or saved['closing']:return
  saved['refs'],saved['stone'],saved['seed']=refs,stone,seed
  if not all(ref.current for ref in refs+[stone,seed]):return
  if saved['renderers'] is None:
   def show(slot,visible):refs[slot].current.SetVisible(visible)
   saved['renderers']=[SkeletonLiquidRenderer([ref.current.asNeteasePaperDoll() for ref in refs],factory.CreateModel(None),show)]
  saved['ready']=[saved['renderers'][0].update(saved['groups'][0],saved['pose'],now)]
  stone.current.SetVisible(saved['stone_visible'])
  request=(saved['stone_name'],saved['stone_pose'])
  if saved['stone_visible'] and saved.get('stone_request')!=request:
   scale,x,y,z=saved['stone_pose']
   assert stone.current.asNeteasePaperDoll().RenderBlockGeometryModel({
    'block_geometry_model_name':saved['stone_name'],'scale':scale,
    'init_rot_x':x,'init_rot_y':y,'init_rot_z':z})
   saved['stone_request']=request
  saved['frames']+=1
 use_animation_frame(tick)
 width,height=factory.CreateGame(level).GetScreenSize()
 viewport_width=width
 skeleton_top=height*.08
 viewport=S(position=Position.absolute,left=0,top=height*.08,width=width,height=height*.84)
 children=[Image(color=Color(0xF0F0F0FF),style=S(position=Position.absolute,left=0,top=0,width=width,height=height,zIndex=0)),
  Image(ref=seed,src='textures/modern_projection/transparent',style=S(position=Position.absolute,width=1,height=1,zIndex=49)),
  Doll(ref=stone,managed=True,renderType=PaperDollRenderType.block_geometry,style=S(position=Position.absolute,left=0,top=height*.08,width=viewport_width,height=height*.84,zIndex=50))]
 for index,ref in enumerate(refs):
  children.append(Doll(key=str(index),ref=ref,managed=True,renderType=PaperDollRenderType.skeleton,
   style=S(position=Position.absolute,left=0,top=skeleton_top,width=viewport_width,height=height*.84,zIndex=306)))
 return Panel(style=S(width=width,height=height),children=children)
assert navigator.push(LiquidAlignmentUI(),key='liquid_water_ui_probe')
_result=json.dumps({'opened':True,'screen':factory.CreateGame(level).GetScreenSize(),'layers':(50,306)})
'''
CONFIGURE = '''from collections import namedtuple
from modern_projection.projection.model import Document
from modern_projection.projection.liquid_transport import RenderGroup,pack_group
from modern_projection.projection.preview_depth import depth_color
position,pose,liquid_scale,liquid_rotation,height,mode,model_name=%r
saved=sys._liquid_water_ui
bridge=api.GetSystem('ModernProjection','ModernProjectionClientSystem').bridge
document=Document(size=(4,4,4),blocks={position:('minecraft:stone',0)})
saved['stone_name']=bridge.geometry(document)
assert saved['stone_name']
saved['stone_pose']=pose
saved['pose']=(pose[0]*liquid_scale,)+tuple(liquid_rotation or pose[1:])
saved['stone_visible']=mode in ('stone','overlay')
saved['seed'].current.asImage().SetSpriteColor(depth_color(-4.,'plains',(4,4)))
Surface=namedtuple('AlignmentSurface','position layer heights faces texture_key flow_uv')
payload=pack_group((0,0,0),(Surface(position,0,(height,)*4,63,'still_water_grey',None),),
 (0,0,0),1.,.5 if mode=='overlay' else 1.)
saved['groups']=[RenderGroup(position,model_name,(0,0,0),payload) if mode in ('water','overlay') else None]
saved['ready']=[False]
_result=json.dumps({'position':position,'stone_pose':pose,'liquid_pose':saved['pose'],'height':height,
 'mode':mode,'stone_model':saved['stone_name'],'uniforms':payload})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--liquid-scale', type=float, default=1.)
    parser.add_argument('--liquid-rotation', type=float, nargs=3)
    parser.add_argument('--base-scale', type=float, default=2.)
    parser.add_argument('--liquid-top-offset', type=float, default=0., help='Fraction of actual viewport short side')
    parser.add_argument('--viewport-width', type=float, default=1., help='Fraction of logical screen width')
    parser.add_argument('--calibrated-scale', action='store_true')
    parser.add_argument('--model-name', default='modern_projection_liquid_still_water_grey_frozen')
    parser.add_argument('--quick', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != base.ROOT:
        parser.error('The session belongs to another project')
    report = {'schema': 1, 'completed': False, 'restored': False, 'captures': {}, 'observations': {},
              'native_ui_alignment_accepted': False, 'production_editor_accepted': False,
              'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}

    def record():
        base.write(args.output, report)

    def ready(code=water.STATUS, key='ready'):
        deadline = time.monotonic() + 10.
        while True:
            row = base.run(client, code)
            if row[key]:
                return row
            if time.monotonic() >= deadline:
                raise RuntimeError('Native alignment UI did not become ready: ' + repr(row))
            time.sleep(.1)

    with base.Client(timeout=45) as client:
        try:
            code = OPEN.replace('viewport_width=width','viewport_width=width*%r' % args.viewport_width)
            code = code.replace('skeleton_top=height*.08',
                'skeleton_top=height*.08+min(viewport_width,height*.84)*%r' % args.liquid_top_offset)
            report['ui_setup'] = base.run(client, code)
            report['liquid_top_offset'] = args.liquid_top_offset
            report['viewport_width'] = args.viewport_width
            if args.calibrated_scale:
                width,height = report['ui_setup']['screen']
                args.liquid_scale = 10./min(width*args.viewport_width,height*.84)
            report['liquid_scale_multiplier'] = args.liquid_scale
            ready()
            poses = ((args.base_scale, -65., 0., 35.), (args.base_scale, -90., 0., 0.),
                     (args.base_scale, 0., 0., 0.))
            positions = ((1, 1, 1), (2, 1, 1), (1, 2, 1), (1, 1, 2))
            cases = [('empty', positions[0], poses[0], 1., 'empty')]
            for index, pose in enumerate(poses):
                for mode in ('stone', 'water'):
                    cases.append(('pose%d_%s' % (index, mode), positions[0], pose, 1., mode))
            for axis, position in enumerate(positions[1:]):
                for mode in ('stone', 'water'):
                    cases.append(('axis%d_%s' % (axis, mode), position, poses[0], 1., mode))
            cases.extend((('height70', positions[0], poses[0], .7, 'water'),
                          ('overlay', positions[0], poses[0], .7, 'overlay')))
            if args.quick:
                cases = cases[:3]
            for label, position, pose, height, mode in cases:
                values = (position, pose, args.liquid_scale, args.liquid_rotation, height, mode, args.model_name)
                report['observations'][label] = base.run(client, CONFIGURE % (values,))
                ready()
                time.sleep(.25)
                report['captures'][label] = base.capture(args.session, args.owner,
                    args.output.with_name(args.output.stem + '_' + label + '.png'), args.capture_exe)
                record()
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            report['ui_cleanup'] = base.run(client, water.CLEAN)
            report['cleanup_state'] = ready(water.CLEAN_READY, 'restored')
            report['restored'] = bool(report['ui_cleanup'] and report['cleanup_state']['restored'])
            record()
    print(json.dumps({'completed': report['completed'], 'restored': report['restored']}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
