"""Native animated/frozen water artwork controls through the owned UI adapter."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import probe_liquid_pose_channel as base
import probe_liquid_uniform_transport as transport
from _session import load_session


OPEN_UI = '''from modern_projection.pyreact import Component,Panel,Image,Color,Position,PaperDollRenderType,use_ref,navigator
from modern_projection.pyreact.hooks import use_animation_frame
from modern_projection.projection.widgets import Doll,S
from modern_projection.projection.liquid_render import SkeletonLiquidRenderer
assert not navigator.is_transitioning
assert navigator.top is None or navigator.top.key=='modern_projection_workspace'
assert not hasattr(sys,'_liquid_water_ui')
sys._liquid_water_ui={'refs':None,'renderers':None,'groups':[None,None],
 'poses':[(.18,-55.,35.,0.)]*2,'ready':[False,False],'frames':0,'closing':False}
def water_renderer(refs):
 def show(slot,visible):refs[slot].current.SetVisible(visible)
 return SkeletonLiquidRenderer([ref.current.asNeteasePaperDoll() for ref in refs],factory.CreateModel(None),show)
@Component
def LiquidWaterUI():
 refs=[use_ref(None),use_ref(None),use_ref(None),use_ref(None)]
 def tick(now):
  saved=getattr(sys,'_liquid_water_ui',None)
  if saved is None or saved['closing']:return
  saved['refs']=refs
  if not all(ref.current for ref in refs):return
  if saved['renderers'] is None:
   saved['renderers']=[water_renderer(refs[:2]),water_renderer(refs[2:])]
  saved['ready']=[renderer.update(group,pose,now)
   for renderer,group,pose in zip(saved['renderers'],saved['groups'],saved['poses'])]
  motion=saved.get('motion')
  if motion is not None and len(motion)<16:
   renderer=saved['renderers'][0]
   doll=renderer.dolls[renderer.front]
   before=doll.GetModelId()
   pose=(.18,-55.,35.+3.*(len(motion)+1),0.)
   saved['poses'][0]=pose
   returned=renderer.update(saved['groups'][0],pose,now)
   after=doll.GetModelId()
   motion.append({'before':before,'after':after,'submitted':returned,'payload_ready':returned,'pose':pose,
    'pending':renderer.pending is not None,'front':renderer.front})
  saved['frames']+=1
 use_animation_frame(tick)
 width,height=factory.CreateGame(level).GetScreenSize()
 children=[Image(color=Color(0xF0F0F0FF),style=S(position=Position.absolute,
  left=0,top=0,width=width,height=height,zIndex=0))]
 for index,ref in enumerate(refs):
  children.append(Doll(key=str(index),ref=ref,managed=True,renderType=PaperDollRenderType.skeleton,
   style=S(position=Position.absolute,left=width*(.03 if index<2 else .53),
    top=height*.08,width=width*.44,height=height*.84,zIndex=1)))
 return Panel(style=S(width=width,height=height),children=children)
assert navigator.push(LiquidWaterUI(),key='liquid_water_ui_probe')
_result=json.dumps({'opened':True,'screen_size':factory.CreateGame(level).GetScreenSize()})
'''

STATUS = '''from modern_projection.pyreact import navigator
saved=sys._liquid_water_ui
renderers=saved['renderers']
rows=[]
if renderers is not None:
 for renderer in renderers:
  rows.append({'front':renderer.front,'ids':renderer.ids,'visible':renderer.visible,
   'pending':renderer.pending is not None,'error':renderer.error,'closed':renderer.closed,
   'native_ids':[doll.GetModelId() for doll in renderer.dolls]})
ready=bool(renderers is not None and all(saved['ready']) and navigator.top
 and navigator.top.key=='liquid_water_ui_probe' and not navigator.is_transitioning)
active_ids=[row['ids'][row['front']] for row in rows if row['visible'][row['front']]]
assert len(set(active_ids))==len(active_ids),active_ids
_result=json.dumps({'ready':ready,'frames':saved['frames'],'renderers':rows,'active_ids':active_ids})
'''

MOTION = '''saved=sys._liquid_water_ui
saved['motion']=[]
_result=True
'''
MOTION_READY = '''saved=sys._liquid_water_ui
_result=json.dumps({'ready':len(saved.get('motion',[]))==16,'rows':saved.get('motion',[])})
'''

SET_GROUPS = '''from collections import namedtuple
from modern_projection.projection import biomes
from modern_projection.projection.model import Document
from modern_projection.projection.liquid_transport import RenderGroup,pack_group
Surface=namedtuple('WaterProbeSurface','position layer heights faces texture_key flow_uv')
config=%r
saved=sys._liquid_water_ui
rows=[]
for index,(biome,projection,faces,sloped) in enumerate(config):
 document=Document(size=(4,4,4),biome=biome)
 color,opacity=biomes.water_appearance(document.biome)
 positions=((0,1,0),(3,1,0),(0,1,3),(3,1,3))
 shapes=((.25,.45,.65,.85),(.85,.65,.45,.25),(.35,.75,.55,.95),(.95,.55,.75,.35)) if sloped else ((.70,)*4,)*4
 surfaces=tuple(Surface(position,0,shape,faces,'still_water_grey',None)
  for position,shape in zip(positions,shapes))
 payload=pack_group((0,0,0),surfaces,color,opacity,projection)
 model='modern_projection_liquid_still_water_grey'+('_frozen' if index else '')
 saved['groups'][index]=RenderGroup((model,tuple(config[index])),model,(0,0,0),payload)
 rows.append({'document_biome':document.biome,'color':color,'native_opacity':opacity,
  'projection_opacity':projection,'supplied_shapes':shapes,'faces':faces,'uniforms':payload,'model':model})
saved['ready']=[False,False]
_result=json.dumps(rows)
'''

HIDE = '''saved=sys._liquid_water_ui
saved['groups']=[None,None]
saved['ready']=[False,False]
_result=True
'''

CLEAN = '''from modern_projection.pyreact import navigator
saved=getattr(sys,'_liquid_water_ui',None)
if saved is not None:
 saved['closing']=True
 if saved['renderers'] is not None:
  for renderer in saved['renderers']:renderer.close()
 assert all(renderer.closed and not any(renderer.visible) for renderer in saved['renderers'] or [])
 if navigator.top and navigator.top.key=='liquid_water_ui_probe':assert navigator.pop()
 del sys._liquid_water_ui
_result=True
'''

CLEAN_READY = '''from modern_projection.pyreact import navigator
_result=json.dumps({'restored':not hasattr(sys,'_liquid_water_ui') and not navigator.is_transitioning
 and (navigator.top is None or navigator.top.key=='modern_projection_workspace')})
'''


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--reload-adapter', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != base.ROOT:
        parser.error('The session belongs to another project')
    contract = json.loads(args.contract.read_bytes())
    project_files = ['behavior_pack/modern_projection/projection/' + name for name in (
        'liquid_render.py', 'liquid_transport.py', 'biomes.py', 'biome_water_data.py')]
    report = {'schema': 1, 'completed': False, 'restored': False, 'captures': {}, 'observations': {},
              'metrics': [], 'scope': 'Supplied-shape native still-water artwork and animation candidate',
              'native_shape_accepted': False, 'native_uv_accepted': False, 'native_alpha_accepted': False,
              'native_animation_accepted': False, 'production_editor_accepted': False,
              'production_memory_accepted': False, 'contract_sha256': sha256(args.contract),
              'source_sha256': {name: sha256(base.ROOT / name) for name in project_files},
              'probe_sha256': sha256(__file__), 'contract': contract}

    def record():
        base.write(args.output, report)

    def wait_ready(code=STATUS, key='ready'):
        deadline = time.monotonic() + 10.
        while True:
            result = base.run(client, code)
            if result[key]:
                return result
            if time.monotonic() >= deadline:
                raise RuntimeError('Native water UI did not become ready: ' + repr(result))
            time.sleep(.1)

    def frame(label):
        report['captures'][label] = base.capture(args.session, args.owner,
            args.output.with_name(args.output.stem + '_' + label + '.png'), args.capture_exe)
        report['observations'][label + '_state'] = base.run(client, STATUS)
        record()

    def groups(label, config):
        report['observations'][label] = base.run(client, SET_GROUPS % (config,))
        report['observations'][label + '_ready'] = wait_ready()
        time.sleep(.2)
        record()

    with base.Client(timeout=45) as client:
        try:
            report['metrics'].append(dict(transport.metrics(args.session, args.owner), label='before_setup'))
            if args.reload_adapter:
                report['adapter_reloaded'] = base.run(client,
                    'import modern_projection.projection.liquid_render as liquid_render\n'
                    'reload(liquid_render)\n_result=True')
            report['ui_setup'] = base.run(client, OPEN_UI)
            report['ui_ready'] = wait_ready()
            frame('empty')
            config = [('plains', 1., 63, False), ('plains', 1., 63, False)]
            groups('same_plains', config)
            for index in range(6):
                if index:
                    time.sleep(.31)
                frame('animated_' + str(index))
            groups('same_swamp', [('swampland', 1., 63, False)] * 2)
            frame('swamp')
            groups('same_mangrove', [('mangrove_swamp', 1., 63, False)] * 2)
            frame('mangrove')
            groups('projection_half', [('plains', .5, 63, False)] * 2)
            frame('half')
            groups('top_only', [('plains', 1., 1, False)] * 2)
            frame('top')
            groups('top_half', [('plains', .5, 1, False)] * 2)
            frame('top_half')
            groups('top_swamp', [('swampland', 1., 1, False)] * 2)
            frame('top_swamp')
            groups('explicit_slopes', [('plains', 1., 63, True)] * 2)
            frame('slopes')
            report['observations']['hide'] = base.run(client, HIDE)
            report['observations']['hide_ready'] = wait_ready()
            time.sleep(.2)
            frame('hidden')
            groups('restore_plains', config)
            frame('restored_plains')
            report['observations']['motion_start'] = base.run(client, MOTION)
            report['observations']['motion_ready'] = wait_ready(MOTION_READY)
            time.sleep(.2)
            frame('motion_end')
            report['metrics'].append(dict(transport.metrics(args.session, args.owner), label='after_frames'))
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            try:
                report['ui_cleanup'] = base.run(client, CLEAN)
                report['cleanup_state'] = wait_ready(CLEAN_READY, 'restored')
                report['restored'] = bool(report['ui_cleanup'] and report['cleanup_state']['restored'])
                report['metrics'].append(dict(transport.metrics(args.session, args.owner), label='after_cleanup'))
            except Exception as error:
                report['cleanup_error'] = '%s: %s' % (type(error).__name__, error)
                raise
            finally:
                record()
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'captures': len(report['captures']), 'output': str(args.output.resolve())}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
