"""Observe CURRENT_COLOR on skeletons after independently seeded UI images."""
import argparse
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
from modern_projection.projection.liquid_transport import RenderGroup
assert not navigator.is_transitioning
assert navigator.top is None or navigator.top.key=='modern_projection_workspace'
assert not hasattr(sys,'_liquid_water_ui')
payload=((85.,0.,0.,0.),(46003.,46003.,0.,0.),(0.,0.,0.,0.),(39686.,-1.,16777215.,1.))
name=%r
group=RenderGroup(0,name,(0,0,0),payload)
sys._liquid_water_ui={'refs':None,'renderers':None,'groups':[group,group],
 'ready':[False,False],'frames':0,'closing':False,'seeds':None}
def renderer(refs):
 def show(slot,visible):refs[slot].current.SetVisible(visible)
 return SkeletonLiquidRenderer([ref.current.asNeteasePaperDoll() for ref in refs],factory.CreateModel(None),show)
@Component
def LiquidPacketUI():
 refs=[use_ref(None),use_ref(None),use_ref(None),use_ref(None)]
 seeds=[use_ref(None),use_ref(None)]
 def tick(now):
  saved=getattr(sys,'_liquid_water_ui',None)
  if saved is None or saved['closing']:return
  saved['refs'],saved['seeds']=refs,seeds
  if not all(ref.current for ref in refs+seeds):return
  if saved['renderers'] is None:saved['renderers']=[renderer(refs[:2]),renderer(refs[2:])]
  saved['ready']=[item.update(group,(.18,-55.,35.,0.),now) for item,group in zip(saved['renderers'],saved['groups'])]
  saved['frames']+=1
 use_animation_frame(tick)
 width,height=factory.CreateGame(level).GetScreenSize()
 children=[Image(color=Color(0xF0F0F0FF),style=S(position=Position.absolute,left=0,top=0,width=width,height=height,zIndex=0))]
 for side in range(2):
  children.append(Image(key='seed'+str(side),ref=seeds[side],src='textures/modern_projection/transparent',
   style=S(position=Position.absolute,left=0,top=0,width=1,height=1,zIndex=side*2+1)))
  for slot in range(2):
   index=side*2+slot
   children.append(Doll(key=str(index),ref=refs[index],managed=True,renderType=PaperDollRenderType.skeleton,
    style=S(position=Position.absolute,left=width*(.03 if side==0 else .53),top=height*.08,
     width=width*.44,height=height*.84,zIndex=side*2+2)))
 return Panel(style=S(width=width,height=height),children=children)
assert navigator.push(LiquidPacketUI(),key='liquid_water_ui_probe')
_result=json.dumps({'opened':True,'screen_size':factory.CreateGame(level).GetScreenSize()})
'''
SEED = '''colors=%r
for ref,color in zip(sys._liquid_water_ui['seeds'],colors):ref.current.asImage().SetSpriteColor(tuple(color))
_result=json.dumps({'seed_colors':colors})
'''
DEPTH_SEED = '''from modern_projection.projection.preview_depth import depth_color
distances=%r
colors=[depth_color(distance,biome,(4,4)) for distance,biome in zip(distances,('plains','swampland'))]
for ref,color in zip(sys._liquid_water_ui['seeds'],colors):ref.current.asImage().SetSpriteColor(color)
_result=json.dumps({'seed_colors':colors})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model-name', default='modern_projection_liquid_still_water_grey_packet')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != base.ROOT:
        parser.error('The session belongs to another project')
    report = {'schema': 1, 'completed': False, 'restored': False, 'captures': {}, 'observations': {},
              'native_current_color_binding_accepted': False, 'native_shared_depth_accepted': False,
              'scope': 'Independent transparent-image CURRENT_COLOR seed binding on native skeletons'}

    def record():
        base.write(args.output, report)

    def ready(code=water.STATUS, key='ready'):
        deadline = time.monotonic() + 10.
        while True:
            row = base.run(client, code)
            if row[key]:
                return row
            if time.monotonic() >= deadline:
                raise RuntimeError('Native packet UI did not become ready: ' + repr(row))
            time.sleep(.1)

    with base.Client(timeout=45) as client:
        try:
            report['model_name'] = args.model_name
            report['ui_setup'] = base.run(client, OPEN % args.model_name)
            report['ready'] = ready()
            colors = [(18. / 255., 52. / 255., 86. / 255.), (171. / 255., 205. / 255., 239. / 255.)]
            for label, code in (('first', SEED % (colors,)), ('reversed', SEED % (list(reversed(colors)),)),
                                ('depth_packets', DEPTH_SEED % ((-4., -20.),)),
                                ('depth_positive', DEPTH_SEED % ((4., 4.),)),
                                ('depth_negative', DEPTH_SEED % ((-4., -4.),)),
                                ('depth_slice', DEPTH_SEED % ((0., 0.),))):
                report['observations'][label] = base.run(client, code)
                time.sleep(.3)
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
