"""Observe independent EXTRA_VECTOR payloads in two native PaperDolls."""
# pylint: disable=unexpected-keyword-arg,E1123
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import probe_liquid_pose_channel as base
import probe_liquid_uniform_transport as transport
from generate_liquid_skeleton_fixture import MODEL
from _session import load_session


def extended_phases():
    original=transport.uniforms(5)
    reverse=transport.uniforms(5,heights=tuple(reversed(transport.HEIGHT_CODES)))
    badtag=original[:3]+[(4,(0.,1.,16777215.,5.))]
    left_tint=original[:3]+[(4,(39686.,1.,float(0x123456),6.))]
    right_tint=reverse[:3]+[(4,(39686.,.5,float(0xABCDEF),6.))]
    left_opacity=original[:3]+[(4,(39686.,.5,float(0x123456),7.))]
    right_opacity=reverse[:3]+[(4,(39686.,.25,16777215.,7.))]
    return [('left_fourth',[(0,original)]),('right_fourth',[(1,reverse)]),
            ('left_badtag',[(0,badtag)]),('left_tint',[(0,left_tint)]),
            ('right_tint',[(1,right_tint)]),('left_opacity_code',[(0,left_opacity)]),
            ('right_opacity_code',[(1,right_opacity)])]


OPEN_UI='''from modern_projection.pyreact import Component,Panel,Image,Color,Position,PaperDollRenderType,use_ref,navigator
from modern_projection.pyreact.hooks import use_animation_frame
from modern_projection.projection.widgets import Doll,S
assert not navigator.is_transitioning
assert navigator.top is None or navigator.top.key=='modern_projection_workspace'
assert not hasattr(sys,'_liquid_skeleton_ui')
sys._liquid_skeleton_ui={'refs':None,'ids':None}
@Component
def LiquidSkeletonUI():
 left,right=use_ref(None),use_ref(None)
 def ready(unused):
  saved=getattr(sys,'_liquid_skeleton_ui',None)
  if saved is not None:saved['refs']=(left,right)
 use_animation_frame(ready)
 width,height=factory.CreateGame(level).GetScreenSize()
 return Panel(style=S(width=width,height=height),children=[
  Image(color=Color(0xF0F0F0FF),style=S(position=Position.absolute,left=0,top=0,width=width,height=height,zIndex=0)),
  Doll(ref=left,managed=True,renderType=PaperDollRenderType.skeleton,
   style=S(position=Position.absolute,left=width*.03,top=height*.08,width=width*.44,height=height*.84,zIndex=1)),
  Doll(ref=right,managed=True,renderType=PaperDollRenderType.skeleton,
   style=S(position=Position.absolute,left=width*.53,top=height*.08,width=width*.44,height=height*.84,zIndex=1))])
assert navigator.push(LiquidSkeletonUI(),key='liquid_skeleton_ui_probe')
_result=json.dumps({'opened':True,'screen_size':factory.CreateGame(level).GetScreenSize()})
'''
READY='''from modern_projection.pyreact import navigator
saved=sys._liquid_skeleton_ui
refs=saved['refs']
_result=json.dumps({'ready':bool(refs and all(ref and ref.current for ref in refs) and navigator.top and navigator.top.key=='liquid_skeleton_ui_probe' and not navigator.is_transitioning)})
'''
DRAW='''params={'skeleton_model_name':%r,'scale':.15,'render_depth':-50,'init_rot_x':-55.,'init_rot_y':0.,'init_rot_z':0.}
rows=[]
for ref in sys._liquid_skeleton_ui['refs']:
 control=ref.current
 returned=control.asNeteasePaperDoll().RenderSkeletonModel(params)
 rows.append({'returned':returned,'position':control.GetPosition(),'size':control.GetSize()})
_result=json.dumps({'params':params,'controls':rows})
'''
MODEL_IDS='''ids=[ref.current.asNeteasePaperDoll().GetModelId() for ref in sys._liquid_skeleton_ui['refs']]
sys._liquid_skeleton_ui['ids']=ids
_result=json.dumps({'ids':ids,'ready':all(value!=-1 for value in ids) and len(set(ids))==2})
'''
SET_UNIFORMS='''values=%r
model=factory.CreateModel(None)
ids=sys._liquid_skeleton_ui['ids']
rows=[]
for index,payload in values:
 for group,value in payload:
  returned=model.SetExtraUniformValue(ids[index],group,tuple(value))
  assert returned,(ids[index],group,value)
  rows.append({'model_id':ids[index],'group':group,'value':value,'returned':returned})
_result=json.dumps({'ids':[ref.current.asNeteasePaperDoll().GetModelId() for ref in sys._liquid_skeleton_ui['refs']],'uniform_calls':rows})
'''
CLEAN='''from modern_projection.pyreact import navigator
saved=getattr(sys,'_liquid_skeleton_ui',None)
if saved is not None:
 if navigator.top and navigator.top.key=='liquid_skeleton_ui_probe':assert navigator.pop()
 del sys._liquid_skeleton_ui
_result=True
'''
CLEAN_READY='''from modern_projection.pyreact import navigator
_result=json.dumps({'restored':not hasattr(sys,'_liquid_skeleton_ui') and not navigator.is_transitioning and (navigator.top is None or navigator.top.key=='modern_projection_workspace')})
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True)
    parser.add_argument('--owner',required=True)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--capture-exe',required=True,type=Path)
    parser.add_argument('--extended',action='store_true')
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)),MCDEV_OWNER=args.owner)
    session=load_session(args.session,args.owner,live=True)
    if Path(session['project']).resolve()!=base.ROOT:
        parser.error('The session belongs to another project')
    report={'schema':1,'completed':False,'restored':False,'captures':{},'observations':{},'metrics':[],
            'extended_uniforms':args.extended,
            'scope':'Two native skeleton model IDs sharing one static four-plane definition',
            'editor_uniforms_accepted':False,'native_geometry_accepted':False,
            'animated_sampling_accepted':False,'production_memory_accepted':False,
            'source_sha256':{Path(path).name:hashlib.sha256(Path(path).read_bytes()).hexdigest()
                             for path in (__file__,base.__file__,transport.__file__)}}

    def record():
        base.write(args.output,report)

    def frame(label):
        report['captures'][label]=base.capture(args.session,args.owner,
            args.output.with_name(args.output.stem+'_'+label+'.png'),args.capture_exe)
        record()

    def wait_ready(code,key):
        deadline=time.monotonic()+10.
        while True:
            result=base.run(client,code)
            if result[key]:
                return result
            if time.monotonic()>=deadline:
                raise RuntimeError('Native model/UI did not become ready: '+repr(result))
            time.sleep(.1)

    original=transport.uniforms(2)
    reverse=transport.uniforms(2,heights=tuple(reversed(transport.HEIGHT_CODES)))
    zero=[(group,(0.,0.,0.,0.)) for group in range(1,5)]
    with base.Client(timeout=45) as client:
        try:
            report['metrics'].append(dict(transport.metrics(args.session,args.owner),label='before_setup'))
            report['ui_setup']=base.run(client,OPEN_UI)
            wait_ready(READY,'ready')
            report['render']=base.run(client,DRAW % MODEL)
            record()
            time.sleep(.3)
            report['model_ids']=wait_ready(MODEL_IDS,'ready')
            frame('default_zero')
            phases=[
                    ('independent',[(0,original),(1,reverse)]),
                    ('left_reversed',[(0,reverse)]),
                    ('left_zero',[(0,zero)]),
                    ('right_original',[(1,original)]),
                    ('repeat_independent',[(0,original),(1,reverse)])]
            if args.extended:
                phases.extend(extended_phases())
            for label,values in phases:
                report['observations'][label]=base.run(client,SET_UNIFORMS % values)
                record()
                time.sleep(.3)
                frame(label)
            report['metrics'].append(dict(transport.metrics(args.session,args.owner),label='after_frames'))
            report['completed']=True
        except Exception as error:
            report['error']='%s: %s' % (type(error).__name__,error)
            raise
        finally:
            try:
                report['ui_cleanup']=base.run(client,CLEAN)
                report['cleanup_state']=wait_ready(CLEAN_READY,'restored')
                report['restored']=bool(report['ui_cleanup'] and report['cleanup_state']['restored'])
                report['metrics'].append(dict(transport.metrics(args.session,args.owner),label='after_cleanup'))
            except Exception as error:
                report['cleanup_error']='%s: %s' % (type(error).__name__,error)
                raise
            finally:
                record()
    print(json.dumps({'completed':report['completed'],'restored':report['restored'],'output':str(args.output.resolve())}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__=='__main__':
    raise SystemExit(main())
