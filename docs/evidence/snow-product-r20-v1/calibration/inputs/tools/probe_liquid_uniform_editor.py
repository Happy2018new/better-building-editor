"""Observe entity-uniform liquid carriers in a temporary native PaperDoll."""
# pylint: disable=unexpected-keyword-arg,E1123
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

import probe_liquid_pose_channel as base
import probe_liquid_uniform_transport as transport
from generate_liquid_uniform_fixture import identifier, TAG, DIRECT_ENTITY
from _session import load_session


OPEN_UI = '''from modern_projection.pyreact import Component,Panel,Image,Color,Position,PaperDollRenderType,use_ref,navigator
from modern_projection.pyreact.hooks import use_animation_frame
from modern_projection.projection.widgets import Doll,S
assert not navigator.is_transitioning
assert navigator.top is None or navigator.top.key=='modern_projection_workspace'
assert not hasattr(sys,'_liquid_uniform_ui')
render=factory.CreateActorRender(None)
entity_identifier=%r
sys._liquid_uniform_ui={'ref':None,'identifier':entity_identifier,'uniforms':[(group,render.GetEntityUIExtraUniforms(entity_identifier,group)) for group in range(1,5)]}
@Component
def LiquidUniformUI():
 ref=use_ref(None)
 def ready(unused):
  saved=getattr(sys,'_liquid_uniform_ui',None)
  if saved is not None:saved['ref']=ref
 use_animation_frame(ready)
 width,height=factory.CreateGame(level).GetScreenSize()
 return Panel(style=S(width=width,height=height),children=[
  Image(color=Color(0xF0F0F0FF),style=S(position=Position.absolute,left=0,top=0,width=width,height=height,zIndex=0)),
  Doll(ref=ref,managed=True,renderType=PaperDollRenderType.block_geometry,
   style=S(position=Position.absolute,left=width*.05,top=height*.05,width=width*.9,height=height*.9,zIndex=1))])
assert navigator.push(LiquidUniformUI(),key='liquid_uniform_ui_probe')
_result=json.dumps({'opened':True,'uniforms_before':sys._liquid_uniform_ui['uniforms']})
'''

UI_READY = '''from modern_projection.pyreact import navigator
saved=sys._liquid_uniform_ui
ref=saved['ref']
_result=json.dumps({'ready':bool(ref and ref.current and navigator.top and navigator.top.key=='liquid_uniform_ui_probe' and not navigator.is_transitioning)})
'''

UI_UNIFORMS = '''values=%r
render=factory.CreateActorRender(None)
for group,value in values:
 assert render.SetEntityUIExtraUniforms(sys._liquid_uniform_ui['identifier'],group,value)
_result=json.dumps({'uniforms':[(group,render.GetEntityUIExtraUniforms(sys._liquid_uniform_ui['identifier'],group)) for group,value in values]})
'''

DRAW = '''mode=%r
saved=sys._liquid_pose_client
control=sys._liquid_uniform_ui['ref'].current
doll=control.asNeteasePaperDoll()
control.SetVisible(True,False)
params={'scale':2.,'init_rot_x':-55.,'init_rot_y':0.,'init_rot_z':0.}
if mode=='block_geometry':
 params['block_geometry_model_name']=saved['paths'][0]['returned']
 returned=doll.RenderBlockGeometryModel(params)
else:
 if mode=='identifier':params['entity_identifier']=sys._liquid_uniform_ui['identifier']
 elif mode=='cow':params['entity_identifier']='minecraft:cow'
 else:params['entity_id']=saved['entity']
 params['render_depth']=-50
 returned=doll.RenderEntity(params)
_result=json.dumps({'mode':mode,'returned':returned,'params':params,'position':control.GetPosition(),'size':control.GetSize()})
'''

CLEAN_UI = '''from modern_projection.pyreact import navigator
saved=getattr(sys,'_liquid_uniform_ui',None)
if saved is not None:
 if navigator.top and navigator.top.key=='liquid_uniform_ui_probe':
  assert navigator.pop()
 render=factory.CreateActorRender(None)
 for group,value in saved['uniforms']:
  if value is not None:assert render.SetEntityUIExtraUniforms(saved['identifier'],group,value)
 del sys._liquid_uniform_ui
_result=True
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--capture-exe', required=True, type=Path)
    parser.add_argument('--direct-entity', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != base.ROOT:
        parser.error('The session belongs to another project')
    report = {'schema': 1, 'completed': False, 'restored': False, 'captures': {},
              'observations': {}, 'metrics': [], 'height_codes': transport.HEIGHT_CODES,
              'direct_entity_diagnostic': args.direct_entity,
              'editor_uniforms_accepted': False, 'native_geometry_accepted': False,
              'production_memory_accepted': False,
              'scope': 'PaperDoll method capabilities with explicitly supplied diagnostic values only',
              'source_sha256': {Path(path).name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                                for path in (__file__, base.__file__, transport.__file__)}}

    def record():
        base.write(args.output, report)

    def frame(label):
        report['captures'][label] = base.capture(args.session, args.owner,
            args.output.with_name(args.output.stem + '_' + label + '.png'), args.capture_exe)
        record()

    def snapshot(label):
        report['metrics'].append(dict(transport.metrics(args.session, args.owner), label=label))
        record()

    with base.Client(timeout=45) as client:
        try:
            snapshot('before_fixture')
            report['environment'] = base.run(client, base.ENVIRONMENT, True)
            report['world_setup'] = base.run(client, base.PREPARE % identifier(), True)
            origin = tuple(report['world_setup']['origin'])
            report['near_player'] = base.run(client, base.NEAR_PLAYER, True)
            expected = report['near_player']['after']
            deadline = time.monotonic() + 10.
            while True:
                replica = base.run(client, base.REPLICATION % (origin,))
                ready = (replica['foot'] is not None and
                         all(abs(replica['foot'][i] - expected[i]) < .1 for i in range(3)) and
                         any(row['name'] == identifier() and row['indices'] == [0] for row in replica['materials']))
                if ready or time.monotonic() >= deadline:
                    break
                time.sleep(.2)
            report['replication'] = dict(replica, ready=ready)
            assert ready, replica
            base.run(client, base.SAVE % (origin,))
            report['geometry'] = base.run(client, 'import time\n' + transport.GENERATE % (
                'liquid_uniform_ui_' + uuid.uuid4().hex, [(slot, 0, 0) for slot in range(4)]))
            base.run(client, base.ATTACH % ('live', (-.5, 0., -.5), (TAG, 1., 16777215., 2.), transport.uniforms(2)[:3]))
            if args.direct_entity:
                base.run(client, "saved=sys._liquid_pose_client\napi.GetSystem('ModernProjection','ModernProjectionClientSystem').DestroyClientEntity(saved['entity'])\nsaved['attached']=None\nsaved['entity']=api.GetSystem('ModernProjection','ModernProjectionClientSystem').CreateClientEntityByTypeStr(%r,tuple(saved['origin']),(0.,0.))\nassert saved['entity']\n_result=True" % DIRECT_ENTITY)
                report['direct_entity_uniforms'] = base.run(client, transport.SET_UNIFORMS % transport.uniforms(2))
            base.run(client, base.CLEAR, True)
            if args.direct_entity:
                report['direct_camera'] = base.run(client, transport.CAMERA % ((1.5,0.,0.),(0.,4.,6.)))
                time.sleep(.3)
                frame('direct_world_uniforms')
            report['ui_setup'] = base.run(client, OPEN_UI % (DIRECT_ENTITY if args.direct_entity else 'modern_projection:anchor'))
            deadline = time.monotonic() + 10.
            while not base.run(client, UI_READY)['ready']:
                assert time.monotonic() < deadline, 'Native UI did not become ready'
                time.sleep(.1)
            snapshot('after_setup')
            for label, method, values in (
                    ('geometry_default', 'block_geometry', None),
                    ('entity_world_uniforms', 'entity', None),
                    ('entity_ui_uniforms', 'entity', transport.uniforms(2, heights=tuple(reversed(transport.HEIGHT_CODES)))),
                    ('identifier_ui_uniforms', 'identifier', None),
                    ('cow_positive_control', 'cow', None),
                    ('geometry_ui_uniforms', 'block_geometry', transport.uniforms(2))):
                if values is not None:
                    report['observations'][label + '_uniforms'] = base.run(client, UI_UNIFORMS % values)
                report['observations'][label] = base.run(client, DRAW % method)
                time.sleep(.4)
                frame(label)
            base.run(client, "sys._liquid_uniform_ui['ref'].current.SetVisible(False,False)\n_result=True")
            time.sleep(.2)
            frame('empty')
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            cleanup_errors = []
            restore_environment = ('import sys\nif hasattr(sys,"_context_environment_saved"):\n' +
                ''.join(' ' + line + '\n' for line in base.RESTORE_ENVIRONMENT.splitlines()) + 'else:\n _result=True\n')
            for key, code, server in (('ui_cleanup', CLEAN_UI, False), ('client_cleanup', base.CLEAN_CLIENT, False),
                                      ('world_cleanup', base.CLEAN_WORLD, True), ('environment_cleanup', restore_environment, True)):
                try:
                    report[key] = base.run(client, code, server)
                except Exception as error:
                    report[key] = False
                    cleanup_errors.append({'step': key, 'error': '%s: %s' % (type(error).__name__, error)})
            report['cleanup_errors'] = cleanup_errors
            report['restored'] = bool(report['ui_cleanup'] and report['client_cleanup'] and
                isinstance(report['world_cleanup'], dict) and report['world_cleanup'].get('restored') and report['environment_cleanup'])
            snapshot('after_cleanup')
            if cleanup_errors:
                raise RuntimeError('Native cleanup failed: ' + repr(cleanup_errors))
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'], 'output': str(args.output.resolve())}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
