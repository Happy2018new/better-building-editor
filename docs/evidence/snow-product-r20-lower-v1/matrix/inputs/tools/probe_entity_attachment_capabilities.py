"""Test owner-bound native attachment pixels on an independent PaperDoll.

Uses public appearance blueprint payloads without editing them. Native API
return values and actual pixels are separate observations. Production editor,
world projection placement, and native-world block parity are not accepted.

--skeleton-model replaces only the owned anchor's client model. A rejected
SetModel result stops before mounting the UI or binding an item, and the raw
result is preserved for cleanup. A valid model ID is an SDK acknowledgement;
the visible body and attachment still require independent pixel controls.
See probe_entity_attachment_capabilities.md for the next ordinary-sword route.
"""
# pylint: disable=unexpected-keyword-arg,E1123
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from PIL import Image, ImageChops

import probe_liquid_pose_channel as base
from _session import load_session

SAVE = '''from modern_projection.pyreact import navigator
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
assert owner is not None and owner.session is not None
s,b=owner.session,owner.bridge
assert not s.busy and not s.projection_active and s.edit_job is None and s.io_job is None
assert not navigator.is_transitioning
assert navigator.top is None or navigator.top.key=='modern_projection_workspace'
assert not hasattr(sys,'_entity_attachment_capabilities')
cam=factory.CreateCamera(level)
foot=factory.CreatePos(api.GetLocalPlayerId()).GetFootPos()
saved={'entities':{},'items':{},'refs':None,'camera_pos':cam.GetPosition(),
 'camera_rot':cam.GetCameraRotation(),'pitch_lock':cam.IsModCameraLockPitch(),
 'yaw_lock':cam.IsModCameraLockYaw(),'position':(foot[0]+2.,foot[1]+1.,foot[2]+2.)}
sys._entity_attachment_capabilities=saved
for name,identifier in (('anchor','modern_projection:anchor'),('cow','minecraft:cow')):
 pos=saved['position'] if name=='anchor' else (foot[0]+10.,foot[1]+1.,foot[2]+2.)
 entity=b.system.CreateClientEntityByTypeStr(identifier,pos,(0.,0.))
 assert entity,(name,'Client entity creation failed')
 saved['entities'][name]=entity
 factory.CreateModel(entity).SetEntityShadowShow(False)
from modern_projection.projection import block_registry
from modern_projection.projection.debug_appearance_blueprints import observations
from modern_projection.projection.entity_overlays import actor_item
fixtures=[]
for row in observations():
 if row['case'] not in ('frame_filled','glow_frame_filled','banner_base1','banner_ominous'):continue
 material=(row['block']['name'],row['block']['aux'])
 item=actor_item(material,row['cell_nbt'][0]['nbt'])
 assert item,row['case']
 saved['items'][row['case']]=item
 fixtures.append({'case':row['case'],'material':material,'item':item})
_result=json.dumps({'saved':True,'position':saved['position'],'entities':saved['entities'],
 'fixtures':fixtures,'game_version':block_registry.source_version(),
 'palette_sha256':block_registry.fingerprint(),
 'camera':dict((key,saved[key]) for key in ('camera_pos','camera_rot','pitch_lock','yaw_lock'))})
'''

OPEN_UI = '''from modern_projection.pyreact import Component,Panel,Image,Color,Position,use_ref,navigator
from modern_projection.pyreact.hooks import use_animation_frame
from modern_projection.projection.widgets import Doll,S
@Component
def AttachmentCapabilitiesUI():
 ref=use_ref(None)
 def ready(unused):
  saved=getattr(sys,'_entity_attachment_capabilities',None)
  if saved is not None:saved['refs']=[ref]
 use_animation_frame(ready)
 width,height=factory.CreateGame(level).GetScreenSize()
 return Panel(style=S(width=width,height=height),children=[
  Image(color=Color(0xF0F0F0FF),style=S(position=Position.absolute,left=0,top=0,width=width,height=height,zIndex=0)),
  Doll(ref=ref,managed=True,style=S(position=Position.absolute,left=width*.2,top=height*.12,
   width=width*.6,height=height*.76,zIndex=1))])
assert navigator.push(AttachmentCapabilitiesUI(),key='entity_attachment_capabilities')
_result=True
'''

READY = '''from modern_projection.pyreact import navigator
saved=sys._entity_attachment_capabilities
refs=saved['refs']
_result=json.dumps({'ready':bool(refs and refs[0].current and navigator.top and
 navigator.top.key=='entity_attachment_capabilities' and not navigator.is_transitioning)})
'''

DRAW = '''saved=sys._entity_attachment_capabilities
control=saved['refs'][0].current
params=%r
control.SetVisible(bool(params))
returned=control.asNeteasePaperDoll().RenderEntity(params) if params else None
_result=json.dumps({'returned':returned,'params':params,'position':control.GetPosition(),
 'size':control.GetSize()})
'''

BIND = '''saved=sys._entity_attachment_capabilities
name=%r
item=factory.CreateItem(level)
if saved.get('binding') is not None:
 assert item.SetBindBoneForBindItem(saved['entities']['anchor'],saved['binding'],b'',True)
 saved['binding']=None
if name is not None:
 bind=item.BindItemToSkeletonModel if saved.get('skeleton_model') else item.BindItemToMinecraftModel
 identity=bind(saved['entities']['anchor'],saved['items'][name],
  b'root',True,(0.,0.,0.),(0.,0.,0.),1.)
 assert identity!=-1,'Native item bind failed'
 saved['binding']=identity
_result=json.dumps({'case':name,'item_model_id':saved.get('binding')})
'''

INSPECT = '''saved=sys._entity_attachment_capabilities
identity=saved['binding']
model=factory.CreateModel(saved['entities']['anchor'])
item=factory.CreateItem(level)
_result=json.dumps({'item_model_id':identity,
 'offset':item.GetBindItemOffset(saved['entities']['anchor'],identity,True),
 'rotation':item.GetBindItemRotation(saved['entities']['anchor'],identity,True),
 'scale':item.GetBindItemScale(saved['entities']['anchor'],identity,True),
 'model_material':model.GetModelMaterial(identity),
 'extra_uniform':model.SetExtraUniformValue(identity,4,(0.,0.,0.,0.)),
 'set_material':model.SetModelMaterial(identity,b'entity_alphatest'),
 'available_model_methods':[name for name in dir(model) if 'Opacity' in name or 'Item' in name]})
'''

WORLD = '''from modern_projection.pyreact import navigator
saved=sys._entity_attachment_capabilities
if navigator.top and navigator.top.key=='entity_attachment_capabilities':assert navigator.pop()
cam=factory.CreateCamera(level)
cam.DepartCamera()
cam.LockModCameraPitch(1)
cam.LockModCameraYaw(1)
x,y,z=saved['position']
pos=(x,y,z-2.5)
rot=api.GetRotFromDir((0.,0.,2.5))
assert cam.SetCameraPos(pos)
assert cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
_result=True
'''

OPACITY = '''saved=sys._entity_attachment_capabilities
factory.CreateModel(saved['entities']['anchor']).SetEntityOpacity(%r)
_result=json.dumps({'opacity_requested':%r})
'''

RESTORE = '''from modern_projection.pyreact import navigator
saved=getattr(sys,'_entity_attachment_capabilities',None)
if saved is not None:
 if navigator.top and navigator.top.key=='entity_attachment_capabilities':assert navigator.pop()
 if saved.get('binding') is not None:
  assert factory.CreateItem(level).SetBindBoneForBindItem(saved['entities']['anchor'],saved['binding'],b'',True)
  saved['binding']=None
 owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
 for name,entity in list(saved['entities'].items()):
  owner.bridge.system.DestroyClientEntity(entity)
  del saved['entities'][name]
 cam=factory.CreateCamera(level)
 cam.ResetCameraPos()
 cam.UnDepartCamera()
 cam.SetCameraRotation(tuple(saved['camera_rot']))
 cam.LockModCameraPitch(1 if saved['pitch_lock'] else 0)
 cam.LockModCameraYaw(1 if saved['yaw_lock'] else 0)
 baseline=dict((key,saved[key]) for key in ('camera_pos','camera_rot','pitch_lock','yaw_lock'))
 restored={'camera_pos':cam.GetPosition(),'camera_rot':cam.GetCameraRotation(),
  'pitch_lock':cam.IsModCameraLockPitch(),'yaw_lock':cam.IsModCameraLockYaw()}
 del sys._entity_attachment_capabilities
 _result=json.dumps({'cleanup_completed':True,'baseline':baseline,'restored':restored})
else:
 _result=json.dumps({'cleanup_completed':False})
'''


def pixel_delta(first, second, threshold=12):
    with Image.open(first) as a, Image.open(second) as b:
        if a.size != b.size:
            raise ValueError('Native frame dimensions changed')
        box = (a.width // 4, a.height // 5, a.width * 3 // 4, a.height * 4 // 5)
        delta = ImageChops.difference(a.convert('RGB').crop(box), b.convert('RGB').crop(box))
        maximum = ImageChops.lighter(ImageChops.lighter(*delta.split()[:2]), delta.split()[2])
        return sum(maximum.histogram()[threshold + 1:])


def camera_restored(result):
    if not result.get('cleanup_completed'):
        return False
    before, after = result['baseline'], result['restored']
    return (all(abs(a - b) <= .01 for a, b in zip(before['camera_pos'], after['camera_pos'])) and
            all(abs((a - b + 180.) % 360. - 180.) <= .01
                for a, b in zip(before['camera_rot'], after['camera_rot'])) and
            all(before[key] == after[key] for key in ('pitch_lock', 'yaw_lock')))


def validate_skeleton_setup(result, model_name):
    identity = result.get('model_id') if isinstance(result, dict) else None
    if (not isinstance(result, dict) or result.get('model') != model_name or
            type(identity) is not int or identity < 0):
        raise ValueError('Owned anchor SetModel failed: %r' % result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--capture-exe', required=True, type=Path)
    parser.add_argument('--skeleton-model', help='Explicit installed 3.9 model for the separate skeleton binding control')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != base.ROOT:
        parser.error('Session belongs to another project')
    report = {'schema': 1, 'completed': False, 'restored': False, 'captures': {}, 'states': {},
              'production_rendering_accepted': False, 'world_blocks_changed': False,
              'public_blueprint': 'test.entities.appearances',
              'gates': {'minimum_attachment_pixels': 80, 'alpha0_maximum_residual_pixels': 2,
                        'alpha02_maximum_absolute_alpha_error': .05},
              'source_sha256': {str(Path(path).relative_to(base.ROOT)): hashlib.sha256(Path(path).read_bytes()).hexdigest()
                                for path in (__file__, base.__file__,
                                    base.ROOT / 'behavior_pack/modern_projection/projection/entity_overlays.py',
                                    base.ROOT / 'behavior_pack/modern_projection/projection/debug_appearance_blueprints.py',
                                    base.ROOT / 'behavior_pack/modern_projection/projection/appearance_defaults_data.py',
                                    base.ROOT / 'behavior_pack/modern_projection/projection/block_registry_data.py')}}

    def record():
        base.write(args.output, report)

    def frame(label):
        time.sleep(.45)
        report['captures'][label] = base.capture(args.session, args.owner,
            args.output.with_name(args.output.stem + '_' + label + '.png'), args.capture_exe)
        record()

    with base.Client(timeout=30) as client:
        try:
            report['saved'] = base.run(client, SAVE)
            if args.skeleton_model:
                report['skeleton_setup'] = base.run(client, '''saved=sys._entity_attachment_capabilities
saved['skeleton_model']=%r
saved['skeleton_id']=factory.CreateModel(saved['entities']['anchor']).SetModel(saved['skeleton_model'])
_result=json.dumps({'model':saved['skeleton_model'],'model_id':saved['skeleton_id']})
''' % args.skeleton_model)
                record()
                validate_skeleton_setup(report['skeleton_setup'], args.skeleton_model)
            record()
            report['ui_setup'] = base.run(client, OPEN_UI)
            deadline = time.monotonic() + 15.
            while not base.run(client, READY)['ready']:
                if time.monotonic() > deadline:
                    raise RuntimeError('Independent native PaperDoll did not mount')
                time.sleep(.15)
            anchor = report['saved']['entities']['anchor']
            cow = report['saved']['entities']['cow']
            params = {'scale': 1., 'render_depth': -50, 'init_rot_x': 0., 'init_rot_y': 0., 'init_rot_z': 0.}
            for label, source in (('ui_hidden', {}), ('ui_cow_identifier', {'entity_identifier': 'minecraft:cow'}),
                                  ('ui_cow_client', {'entity_id': cow}), ('ui_anchor_empty', {'entity_id': anchor})):
                report['states'][label] = base.run(client, DRAW % dict(params, **source) if source else DRAW % {})
                frame(label)
            for case in ('frame_filled', 'banner_base1', 'banner_ominous'):
                report['states']['ui_' + case] = base.run(client, BIND % case)
                report['states']['ui_' + case]['draw'] = base.run(client, DRAW % dict(params, entity_id=anchor, scale=4.))
                frame('ui_' + case)
            report['model_api'] = base.run(client, INSPECT)
            base.run(client, BIND % None)
            report['world_setup'] = base.run(client, WORLD)
            time.sleep(.5)
            frame('world_empty')
            base.run(client, BIND % 'frame_filled')
            frame('world_bound')
            for label, opacity in (('world_alpha02', .2), ('world_alpha0', 0.)):
                report['states'][label] = base.run(client, OPACITY % (opacity, opacity))
                frame(label)
            report['pixel_observations'] = {}
            for label, reference in (('ui_cow_identifier', 'ui_hidden'), ('ui_cow_client', 'ui_hidden'),
                                     ('ui_frame_filled', 'ui_anchor_empty'), ('ui_banner_base1', 'ui_anchor_empty'),
                                     ('ui_banner_ominous', 'ui_anchor_empty'), ('world_bound', 'world_empty'),
                                     ('world_alpha02', 'world_bound'), ('world_alpha0', 'world_empty')):
                report['pixel_observations'][label] = {'reference': reference, 'pixels_gt_12': pixel_delta(
                    report['captures'][reference]['path'], report['captures'][label]['path'])}
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            report['restoration'] = base.run(client, RESTORE)
            report['restored'] = camera_restored(report['restoration'])
            record()
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    main()
