"""Prepare a finite owned-client-actor plain-item and body-depth probe offline."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import uuid

import probe_native_item_paper_doll as base

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA256 = '7d4496ef5d616998d281a802c1dff3ef343808c1e6c1e9f4a26f49a7daf00e1a'
STATES = ('empty', 'plain', 'body_only_minus', 'combined_minus', 'body_only_plus',
          'combined_plus', 'plain_restored', 'empty_restored')
BODY = {'volume': (1, 3, 3), 'common': {('minecraft:stone', 0): list(range(9))},
        'extra': {}, 'states': {}, 'extraStates': {}, 'actor': {},
        'void': False, 'eliminateAir': True}
UI = {'scale': .35, 'render_depth': -50, 'init_rot_x': 0., 'init_rot_y': 0., 'init_rot_z': 0.}
RESOURCE_FILES = {'anchor.entity.json': 'resource_pack/entity/modern_projection_anchor.entity.json',
                  'anchor.geo.json': 'resource_pack/models/entity/modern_projection_anchor.geo.json',
                  'anchor.behavior.json': 'behavior_pack/entities/modern_projection_anchor.json',
                  'anchor.controller.json': 'resource_pack/render_controllers/modern_projection_anchor.json',
                  'transparent.png': 'resource_pack/textures/modern_projection/transparent.png'}

INSTALL = '''from copy import deepcopy
import math
from modern_projection.projection.bridge import _stable_palette
from modern_projection.projection import static_frame_item_data
assert not hasattr(sys,'_client_anchor_ui_probe')
assert navigator.is_ready and not navigator.is_transitioning
assert not s.busy and not s.projection_active and not b.preparing_entity
assert not any(profile['accepted'] for profile in static_frame_item_data.FRAME_ITEMS.values())
player=api.GetLocalPlayerId()
assert player and player!='-1'
foot=b.factory.CreatePos(player).GetFootPos()
assert foot is not None and len(foot)==3 and all(not math.isnan(value) and not math.isinf(value) for value in foot),foot
assert -1024.<foot[1]<4096.,('Player level is not physically loaded',foot)
screen=b.factory.CreateGame(b.level).GetScreenSize()
assert len(screen)==2 and all(value>32 for value in screen),screen
saved={'nonce':%r,'key':'client_anchor_ui_'+%r,'player':player,'foot':foot,
 'navigation':[entry.key for entry in navigator.get_entries()],
 'document':deepcopy(s.editor.document.to_data()),
 'profiles':repr(_stable_palette(static_frame_item_data.FRAME_ITEMS)),
 'camera':deepcopy(dict((key,getattr(s,key)) for key in ('camera_pose','camera_pivot','camera_pan','camera_depth_pose'))),
 'plain':json.loads(%r),'actor':None,'create':{'state':'pending','attempted':True},
 'journal':[],'attachments':[],'current':None,'body':None,'control':'empty',
 'push_attempted':False,'declared_size':min(240.,screen[0]-32.,screen[1]-32.),
 'size_inputs':screen,'markers':%r,'ui_params':%r}
sys._client_anchor_ui_probe=saved
saved['position']=(foot[0],foot[1]+1.,foot[2])
candidate=b.system.CreateClientEntityByTypeStr('modern_projection:anchor',saved['position'],(0.,0.))
saved['create']['value']=candidate
saved['create']['state']='returned'
if candidate is not None and candidate!='':
 saved['create']['state']='invalid_return'
 assert isinstance(candidate,basestring) and candidate not in ('-1',player),saved['create']
 saved['actor']=candidate
 saved['create']['state']='returned'
assert saved['actor'] is not None,saved['create']
saved['ui_params']['entity_id']=saved['actor']
_result=json.dumps(dict((key,saved[key]) for key in ('nonce','key','player','foot','position','actor','create','navigation','document','profiles','camera','declared_size','size_inputs','ui_params')))
'''

ACTOR_READY = '''saved=sys._client_anchor_ui_probe
assert saved['nonce']==%r
actor=saved['actor']
kind=b.factory.CreateEngineType(actor).GetEngineTypeStr()
if kind is not None:saved['observed_actor_kind']=kind
bone=b.factory.CreateActorRender(actor).GetQueryableBoneOrientation('root',True)
_result=json.dumps({'actor':actor,'kind':kind,'bone':bone,'ready':kind is not None and bone is not None and len(bone)==4,'clock':time.time()})
'''

OPEN_UI = '''from modern_projection.pyreact import Component,Image,Color,PaperDoll,Style,use_ref,AlignItems,JustifyContent,PaperDollRenderType,Position
saved=sys._client_anchor_ui_probe
assert saved['nonce']==%r and not saved['push_attempted']
screen=saved['size_inputs']
saved['markers']=[{'key':key,'rgb':rgb,'x':8. if index%%2==0 else screen[0]-14.,
 'y':8. if index<2 else screen[1]-14.,'size':6.} for index,(key,rgb) in enumerate(saved['markers'])]
@Component
def ClientAnchorPaperDollProbe():
 root_ref=use_ref(None)
 ref=use_ref(None)
 marker_refs=[use_ref(None),use_ref(None),use_ref(None),use_ref(None)]
 saved['root_ref'],saved['ref'],saved['marker_refs']=root_ref,ref,marker_refs
 children=[PaperDoll(key='native_item_probe_doll',ref=ref,renderType=PaperDollRenderType.entity,
  entityId=saved['actor'],scale=.35,renderDepth=-50,initRotX=0.,initRotY=0.,initRotZ=0.,
  style=Style(width=saved['declared_size'],height=saved['declared_size']))]
 for index,marker in enumerate(saved['markers']):
  rgb=marker['rgb']
  children.append(Image(key=marker['key'],ref=marker_refs[index],
   color=Color((rgb[0]<<24)|(rgb[1]<<16)|(rgb[2]<<8)|255),
   style=Style(position=Position.absolute,left=marker['x'],top=marker['y'],width=6.,height=6.)))
 return Image(key='native_item_probe_root',ref=root_ref,color=Color(0xF7F9FCFF),
  style=Style(width='100%%',height='100%%',alignItems=AlignItems.center,justifyContent=JustifyContent.center),children=children)
saved['push_attempted']=True
assert navigator.push(ClientAnchorPaperDollProbe(),key=saved['key'])
_result=True
'''

STATUS = base.STATUS.replace('_native_item_ui_probe', '_client_anchor_ui_probe').replace(
    "'version':api.GetMinecraftVersion(),", "'actor':saved['actor'],'journal':saved['journal'],'body':saved['body'],\n 'version':api.GetMinecraftVersion(),")

CONTROL = '''from copy import deepcopy
from modern_projection.projection.bridge import _stable_palette,_native_palette
saved=sys._client_anchor_ui_probe
assert saved['nonce']==%r and navigator.top.key==saved['key'] and not navigator.is_transitioning
actor=saved['actor']
label=%r
itemcomp=b.factory.CreateItem(b.level)
render=b.factory.CreateActorRender(actor)
def mutation(operation,call):
 row={'operation':operation,'state':'pending','attempted':True}
 saved['journal'].append(row)
 value=call()
 row.update(state='returned',value=value)
 assert value is True,row
 return value
def remove_item():
 for row in saved['attachments']:
  if row['state']=='bound':
   assert not row.get('remove_attempted'),row
   row['remove_attempted']=True
   row['remove_result']=itemcomp.SetBindBoneForBindItem(actor,row['id'],'',True)
   assert row['remove_result'] is True,row
   row['state']='removed'
 saved['current']=None
def bind_item():
 assert saved['current'] is None and all(row['state']=='removed' for row in saved['attachments'])
 item=deepcopy(saved['plain'])
 row={'control':label,'item':deepcopy(item),'canonical':repr(_stable_palette(item)),
  'state':'pending','attempted':True,'id':None,'offset':[0.,0.,0.],'rotation':[0.,0.,0.],'scale':1.}
 saved['attachments'].append(row)
 identity=itemcomp.BindItemToMinecraftModel(actor,item,'root',True,(0.,0.,0.),(0.,0.,0.),1.)
 row['id']=identity
 row['item_nonmutation']=repr(_stable_palette(item))==row['canonical']
 valid=isinstance(identity,(int,long)) and not isinstance(identity,bool) and identity>=0
 row['state']='rejected' if identity==-1 else 'bound' if valid else 'pending'
 assert valid and row['item_nonmutation'],row
 saved['current']=identity
if label in ('plain','combined_minus','combined_plus'):bind_item()
elif label in ('body_only_minus','body_only_plus','empty_restored'):remove_item()
if label=='body_only_minus':
 assert saved['body'] is None
 body=saved['body']={'name':'client_anchor_body_'+saved['nonce'],'state':'pending','combine_attempted':False,'add_attempted':False}
 data=_native_palette(%r)
 palette=b.factory.CreateBlock(b.level).GetBlankBlockPalette()
 assert palette is not None
 mutation('DeserializeBlockPalette',lambda:palette.DeserializeBlockPalette(data))
 body['palette_before']=repr(_stable_palette(palette.SerializeBlockPalette()))
 body['combine_attempted']=True
 body['model']=b.factory.CreateBlockGeometry(b.level).CombineBlockPaletteToGeometry(palette,body['name'],0)
 body['palette_nonmutation']=body['palette_before']==repr(_stable_palette(palette.SerializeBlockPalette()))
 assert body['model'] in (body['name'],body['name'].encode('utf8')) and body['palette_nonmutation'],body
 body['add_attempted']=True
 mutation('AddActorBlockGeometry',lambda:render.AddActorBlockGeometry(body['model'],(0.,0.,-2.),(0.,0.,0.)))
 body.update(state='attached',offset=[0.,0.,-2.],rotation=[0.,0.,0.],visible=True)
elif label=='body_only_plus':
 body=saved['body']
 assert body and body['state']=='attached'
 body['requested_offset']=[0.,0.,2.]
 mutation('SetActorBlockGeometryOffset',lambda:render.SetActorBlockGeometryOffset(body['model'],(0.,0.,2.)))
 body['offset']=[0.,0.,2.]
elif label=='plain_restored':
 body=saved['body']
 assert saved['current'] is not None and body and body['state']=='attached'
 body['requested_visible']=False
 mutation('SetActorBlockGeometryVisible',lambda:render.SetActorBlockGeometryVisible(body['model'],False))
 body['visible']=False
saved['control']=label
mutation('RenderEntity:'+label,lambda:saved['ref'].current.asNeteasePaperDoll().RenderEntity(saved['ui_params']))
saved['model_read_after']=time.time()+.15
native_item=None
if saved['current'] is not None:
 native_item={'offset':itemcomp.GetBindItemOffset(actor,saved['current'],True),
  'rotation':itemcomp.GetBindItemRotation(actor,saved['current'],True),
  'scale':itemcomp.GetBindItemScale(actor,saved['current'],True)}
 assert native_item=={'offset':(0.,0.,0.),'rotation':(0.,0.,0.),'scale':1.},native_item
_result=json.dumps({'control':label,'actor':actor,'attachments':saved['attachments'],'body':saved['body'],
 'journal':saved['journal'],'native_item':native_item,'clock':time.time(),'ui_params':saved['ui_params']})
'''

REMOVE = '''saved=getattr(sys,'_client_anchor_ui_probe',None)
_result=True
if saved is not None and saved['nonce']==%r:
 errors=[]
 if saved['actor'] is not None:
  item=b.factory.CreateItem(b.level)
  for row in saved['attachments']:
   if row['state']=='bound' and row['id'] is not None and not row.get('remove_attempted'):
    row['remove_attempted']=True
    try:
     row['remove_result']=item.SetBindBoneForBindItem(saved['actor'],row['id'],'',True)
     if row['remove_result'] is True:row['state']='removed'
     else:errors.append('Exact owned attachment removal rejected: '+repr(row['id']))
    except Exception as error:errors.append(repr(error))
 _result=json.dumps({'attachments':saved['attachments'],'errors':errors,'actor':saved['actor'],'create':saved['create']})
'''
NAVIGATION = base.NAVIGATION.replace('_native_item_ui_probe', '_client_anchor_ui_probe')
POP = base.POP.replace('_native_item_ui_probe', '_client_anchor_ui_probe')

DESTROY = '''saved=getattr(sys,'_client_anchor_ui_probe',None)
_result=True
if saved is not None and saved['nonce']==%r:
 actor=saved['actor']
 if actor is not None:
  assert actor!=saved['player'] and saved['create'].get('value')==actor
  assert not saved.get('destroy_attempted'),'Do not retry uncertain actor destruction'
  try:
   saved['pre_destroy_kind']=b.factory.CreateEngineType(actor).GetEngineTypeStr()
   if saved['pre_destroy_kind'] is not None:saved['observed_actor_kind']=saved['pre_destroy_kind']
  except Exception as error:saved['pre_destroy_kind_error']=repr(error)
  saved['destroy_attempted']=True
  saved['destroy_result']=b.system.DestroyClientEntity(actor)
  saved['destroy_returned']=True
 _result=json.dumps({'actor':actor,'create':saved['create'],'observed_actor_kind':saved.get('observed_actor_kind'),'pre_destroy_kind':saved.get('pre_destroy_kind'),'pre_destroy_kind_error':saved.get('pre_destroy_kind_error'),'destroy_attempted':saved.get('destroy_attempted',False),'destroy_returned':saved.get('destroy_returned',False)})
'''

ABSENT = '''saved=getattr(sys,'_client_anchor_ui_probe',None)
_result=json.dumps({'owned':False,'absent':True})
if saved is not None and saved['nonce']==%r:
 actor=saved['actor']
 kind=b.factory.CreateEngineType(actor).GetEngineTypeStr() if actor is not None else None
 absent=(actor is not None and saved.get('observed_actor_kind') is not None and saved.get('destroy_attempted') and kind is None) or (actor is None and saved['create']['state']=='returned')
 _result=json.dumps({'owned':True,'actor':actor,'kind':kind,'observed_actor_kind':saved.get('observed_actor_kind'),'absent':bool(absent),'create':saved['create']})
'''

VERIFY = '''from modern_projection.projection.bridge import _stable_palette
from modern_projection.projection import static_frame_item_data
saved=getattr(sys,'_client_anchor_ui_probe',None)
_result=json.dumps({'restored':True,'owned':False})
if saved is not None and saved['nonce']==%r:
 assert not navigator.is_transitioning and not navigator.contains(saved['key'])
 assert [entry.key for entry in navigator.get_entries()]==saved['navigation']
 assert s.editor.document.to_data()==saved['document']
 assert repr(_stable_palette(static_frame_item_data.FRAME_ITEMS))==saved['profiles']
 assert dict((key,getattr(s,key)) for key in ('camera_pose','camera_pivot','camera_pan','camera_depth_pose'))==saved['camera']
 actor=saved['actor']
 assert (actor is not None and saved.get('observed_actor_kind') is not None and saved.get('destroy_attempted') and b.factory.CreateEngineType(actor).GetEngineTypeStr() is None) or (actor is None and saved['create']['state']=='returned'),saved['create']
 for row in saved['attachments']:
  if row['state'] not in ('removed','rejected'):row['disposed_by_owned_actor_destruction']=True
 _result=json.dumps({'restored':True,'actor_absent':True,'observed_actor_kind':saved.get('observed_actor_kind'),'attachments':saved['attachments'],'body':saved['body'],'journal':saved['journal'],'create':saved['create']})
 del sys._client_anchor_ui_probe
'''


def snippets(nonce, plain):
    result = {'install_client.py': INSTALL % (nonce, nonce, json.dumps(plain, sort_keys=True), base.MARKERS, UI),
              'actor_ready_client.py': ACTOR_READY % nonce, 'open_ui_client.py': OPEN_UI % nonce,
              'status_client.py': STATUS % nonce, 'remove_client.py': REMOVE % nonce,
              'navigation_client.py': NAVIGATION % nonce, 'pop_client.py': POP % nonce,
              'destroy_client.py': DESTROY % nonce, 'absent_client.py': ABSENT % nonce,
              'verify_client.py': VERIFY % nonce}
    result.update({label + '_client.py': CONTROL % (nonce, label, BODY) for label in STATES})
    return result


def contract():
    return {'schema': 1, 'states': list(STATES), 'frames_per_state': 2, 'frame_interval_seconds': .4,
            'normal_budget_seconds': 90, 'cleanup_reserve_seconds': 30, 'outer_budget_seconds': 150,
            'rpc_timeout_seconds': 10, 'native_retries': 0, 'new_game_starts': 0,
            'actor_identifier': 'modern_projection:anchor', 'bone': 'root', 'is_client_entity': True,
            'item_offset': [0., 0., 0.], 'item_rotation_zyx': [0., 0., 0.], 'item_scale': 1.,
            'ui': UI, 'body': {'material': 'minecraft:stone', 'size_xyz': [3, 3, 1],
                'minus_offset': [0., 0., -2.], 'plus_offset': [0., 0., 2.], 'rotation': [0., 0., 0.]},
            'ordinary_minimum_stable_pixels': 80, 'difference_channel_threshold': 25,
            'score_roi': 'full physical width and lower 90 percent, fixed before capture; never calibration',
            'marker_contract': 'unchanged v4 four markers, TL/BR training, TR/BL holdouts, one-pixel gate',
            'body_dispatch_requires': 'ordinary visible candidate AND every prior marker gate passed',
            'geometry_resource_lifetime': 'inert nonce-owned resource until session exit; no documented delete API',
            'actor_absence_requires': 'recorded positive type getter before exact-owned destroy, then observed None',
            'runtime_executor_sha256': base.EXECUTOR_SHA256,
            'world_or_inventory_mutation': False, 'shader_or_material_mutation': False,
            'sdk_dispatch_authorized': False, 'production_rendering_accepted': False,
            'editor_frame_content_accepted': False, 'enchantment_glint_accepted': False}


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def prepare(raw_report, output):
    output = Path(output).absolute()
    if output.exists():
        raise ValueError('Preserve existing client anchor bundle')
    raw = Path(raw_report).read_bytes()
    controls, _ = base.item_controls(raw)
    nonce = uuid.uuid4().hex
    files = {'source.py': Path(__file__).read_bytes(),
             'tests.py': (ROOT / 'tests/test_client_anchor_paper_doll.py').read_bytes(),
             'diagnostic.md': (ROOT / 'docs/CLIENT_ANCHOR_PAPER_DOLL_DIAGNOSTIC_R13.md').read_bytes(),
             'native-original.json': raw, 'plain.json': (json.dumps(controls['plain'], sort_keys=True) + '\n').encode('ascii'),
             'v4-source.py': Path(base.__file__).read_bytes(),
             'v4-tests.py': (ROOT / 'tests/test_native_item_paper_doll.py').read_bytes(),
             'runtime-executor.py': Path(base.__file__).with_name('execute_frame_item_translation.py').read_bytes()}
    files.update({name: (ROOT / path).read_bytes() for name, path in RESOURCE_FILES.items()})
    files.update({name: code.encode('ascii') for name, code in snippets(nonce, controls['plain']).items()})
    output.mkdir(parents=True)
    for name, payload in files.items():
        (output / name).write_bytes(payload)
    plan = dict(contract(), nonce=nonce, base_source_sha256=BASE_SHA256,
                files=[{'path': name, 'bytes': len(payload), 'sha256': digest(payload)} for name, payload in files.items()])
    (output / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='ascii')
    return plan


def verify_bundle(bundle):
    bundle = Path(bundle).resolve(strict=True)
    plan = json.loads((bundle / 'plan.json').read_bytes())
    if any(plan.get(key) != value for key, value in contract().items()) or plan.get('base_source_sha256') != BASE_SHA256:
        raise ValueError('Prospective client anchor contract changed')
    nonce = plan['nonce']
    if len(nonce) != 32 or any(value not in '0123456789abcdef' for value in nonce):
        raise ValueError('Invalid anchor nonce')
    controls, _ = base.item_controls((bundle / 'native-original.json').read_bytes())
    programs = snippets(nonce, controls['plain'])
    expected = {'source.py', 'tests.py', 'diagnostic.md', 'native-original.json', 'plain.json',
                'v4-source.py', 'v4-tests.py', 'runtime-executor.py'} | set(programs) | set(RESOURCE_FILES)
    if {row['path'] for row in plan['files']} != expected or len(plan['files']) != len(expected):
        raise ValueError('Anchor frozen inventory changed')
    for row in plan['files']:
        payload = (bundle / row['path']).read_bytes()
        if len(payload) != row['bytes'] or digest(payload) != row['sha256']:
            raise ValueError('Anchor frozen file changed: ' + row['path'])
    for name, code in programs.items():
        if (bundle / name).read_bytes() != code.encode('ascii'):
            raise ValueError('Anchor client program differs from reviewed source: ' + name)
    if (digest((bundle / 'source.py').read_bytes()) != digest(Path(__file__).read_bytes()) or
            digest(Path(base.__file__).read_bytes()) != BASE_SHA256 or
            digest((bundle / 'v4-source.py').read_bytes()) != BASE_SHA256 or
            json.loads((bundle / 'plain.json').read_bytes()) != controls['plain']):
        raise ValueError('Anchor source or ordinary item input changed')
    import execute_frame_item_translation as executor
    if (digest(Path(executor.__file__).read_bytes()) != base.EXECUTOR_SHA256 or
            digest((bundle / 'runtime-executor.py').read_bytes()) != base.EXECUTOR_SHA256):
        raise ValueError('Actual imported anchor runtime executor differs from reviewed source')
    for name, path in RESOURCE_FILES.items():
        if (bundle / name).read_bytes() != (ROOT / path).read_bytes():
            raise ValueError('Anchor resource differs from reviewed bundle: ' + path)
    return bundle, plan


def preflight(bundle, output):
    bundle, plan = verify_bundle(bundle)
    output = Path(output).absolute()
    paths = [output, output.with_name(output.name + '.tmp')]
    for label in STATES:
        for index in range(plan['frames_per_state']):
            shot = base.capture_path(output, label, index)
            paths.extend((shot, shot.with_suffix('.capture.json'), shot.with_suffix('.capture_error.json')))
    if any(path.exists() for path in paths):
        raise ValueError('Preserve existing client anchor evidence')
    return bundle, plan, output


def layout_readback(tree, status, initial):
    nodes, pending = [], [tree]
    while pending:
        node = pending.pop()
        nodes.append(node)
        pending.extend(node.get('children', []))
    dolls = [node for node in nodes if node.get('key') == 'native_item_probe_doll']
    roots = [node for node in nodes if node.get('key') == 'native_item_probe_root']
    expected = {'entityId': initial['actor'], 'renderType': 'entity', 'scale': .35,
                'renderDepth': -50, 'initRotX': 0., 'initRotY': 0., 'initRotZ': 0.}
    if (len(dolls) != 1 or len(roots) != 1 or dolls[0].get('type') != 'PaperDoll' or
            dolls[0].get('opacity') != 1. or roots[0].get('opacity') != 1. or
            roots[0].get('props', {}).get('color') != {'r': 247 / 255., 'g': 249 / 255., 'b': 252 / 255., 'a': 1.} or
            any(dolls[0].get('props', {}).get(key) != value for key, value in expected.items())):
        raise ValueError('Owned anchor UI identity or frozen render props changed')
    native = status['native_layout']
    for name, node in (('paper_doll', dolls[0]), ('root', roots[0])):
        rect = native[name]
        if not rect.get('path') or any(type(rect.get(key)) not in (int, float) or not math.isfinite(rect[key]) or
                type(node.get('layout', {}).get(key)) not in (int, float) or not math.isfinite(node['layout'][key]) or
                abs(rect[key] - node['layout'][key]) > .01 for key in ('x', 'y', 'width', 'height')):
            raise ValueError('Anchor native bounds differ from snapshot')
    specs = base.marker_specs(initial['size_inputs'])
    if len(native.get('markers', [])) != 4:
        raise ValueError('Anchor markers are incomplete')
    for spec, row in zip(specs, native['markers']):
        found = [node for node in nodes if node.get('key') == spec['key']]
        expected_color = dict(zip(('r', 'g', 'b', 'a'), [v / 255. for v in spec['rgb']] + [1.]))
        if (len(found) != 1 or found[0].get('opacity') != 1. or
                found[0].get('props', {}).get('color') != expected_color or
                {key: row.get(key) for key in spec} != spec):
            raise ValueError('Anchor marker declaration changed')
        expected_rect = {'x': native['root']['x'] + spec['x'], 'y': native['root']['y'] + spec['y'],
                         'width': 6., 'height': 6.}
        if not row.get('rect', {}).get('path') or any(type(row['rect'].get(key)) not in (int, float) or
                not math.isfinite(row['rect'][key]) or type(found[0].get('layout', {}).get(key)) not in (int, float) or
                not math.isfinite(found[0]['layout'][key]) or abs(row['rect'][key] - value) > .01 or
                abs(row['rect'][key] - found[0]['layout'][key]) > .01 for key, value in expected_rect.items()):
            raise ValueError('Anchor marker native bounds changed')
    return {'native_readback': native, 'screen_to_ui_scale': 1.,
            'paper_doll': native['paper_doll'], 'root': native['root'], 'props': expected}


def images_for(report, labels):
    from PIL import Image
    from flat_frame_item_visual_checks import capture_payload
    result, size = {}, None
    for label in labels:
        result[label] = []
        for frame in report['states'][label]['frames']:
            with Image.open(capture_payload(frame['capture'])) as image:
                if size is None:
                    size = image.size
                if image.size != size:
                    raise ValueError('Anchor physical capture dimensions changed')
                result[label].append(image.convert('RGB').crop((0, math.ceil(size[1] * .1), size[0], size[1])))
        if len(result[label]) != 2:
            raise ValueError('Anchor state needs two independent frames')
    return result


def stable_difference(images, references):
    from itertools import combinations
    from PIL import Image, ImageChops, ImageFilter
    from verify_snow_plant_visibility import changed
    stable = Image.new('L', images[0].size, 255)
    for image in images:
        for reference in references:
            stable = ImageChops.multiply(stable, changed(image, reference, 25))
    motion = Image.new('L', images[0].size)
    for left, right in combinations(references, 2):
        motion = ImageChops.lighter(motion, changed(left, right, 25))
    motion = motion.filter(ImageFilter.MaxFilter(5))
    return ImageChops.subtract(stable, motion)


def ordinary_gate(report):
    from verify_snow_plant_visibility import count
    images = images_for(report, ('empty', 'plain'))
    pixels = count(stable_difference(images['plain'], images['empty']))
    marker_passed = all(frame.get('marker_mapping', {}).get('passed') is True
                        for label in ('empty', 'plain') for frame in report['states'][label]['frames'])
    return {'stable_plain_pixels': pixels, 'minimum_pixels': 80, 'ordinary_visible_candidate': pixels >= 80,
            'marker_gate_passed': marker_passed, 'body_dispatch_allowed': pixels >= 80 and marker_passed}


def execute_probe(bundle, output, check, owner_guard, deadline):
    from execute_frame_item_translation import BoundedRuntime, save_report
    bundle, plan, output = preflight(bundle, output)
    runtime = BoundedRuntime(check, owner_guard, deadline)
    runtime.capture_adapter()
    report = {'schema': 1, 'plan_sha256': digest((bundle / 'plan.json').read_bytes()),
              'completed': False, 'restored': False, 'production_rendering_accepted': False,
              'editor_frame_content_accepted': False, 'enchantment_glint_accepted': False,
              'sdk_dispatch_attempted': False, 'states': {}, 'errors': [], 'cleanup_errors': []}
    output.parent.mkdir(parents=True, exist_ok=True)
    save_report(output, report)
    original_run, original_wait = check.run, check.wait
    check.run, check.wait = runtime.run, runtime.wait

    def run(name):
        return check.run((bundle / name).read_text(encoding='ascii'))

    def preserve():
        try:
            save_report(output, report)
        except Exception as error:
            report['cleanup_errors'].append('report persistence: ' + repr(error))
            if not runtime.cleanup:
                raise

    try:
        report['sdk_dispatch_attempted'] = True
        report['attempted_operation'] = 'install_client.py'
        preserve()
        report['initial'] = run('install_client.py')
        report['actor_ready'] = runtime.wait('owned client root bone', lambda row: row['ready'],
                                             lambda: run('actor_ready_client.py'))
        report['attempted_operation'] = 'open_ui_client.py'
        preserve()
        report['ui_opened'] = run('open_ui_client.py')
        report['mounted'] = runtime.wait('owned anchor UI mounted', lambda row: row['ready'],
                                         lambda: run('status_client.py'))
        frozen_mapping, fixed_layout, last_clock = None, None, report['mounted']['clock']
        for label in STATES:
            if label == 'body_only_minus':
                report['ordinary_gate'] = ordinary_gate(report)
                preserve()
                if not report['ordinary_gate']['body_dispatch_allowed']:
                    raise ValueError('Body stage requires an ordinary visible item and preserved marker gate')
            row = report['states'][label] = {'state': 'pending', 'frames': [], 'native_dispatch_attempted': True}
            report['attempted_operation'] = label + '_client.py'
            preserve()
            row['native'] = run(label + '_client.py')
            time.sleep(min(.2, runtime.remaining()))
            for index in range(2):
                status = runtime.wait('anchor ' + label, lambda value: value['ready'], lambda: run('status_client.py'))
                if (status['actor'] != report['initial']['actor'] or status['control'] != label or
                        status['ui_params'] != report['initial']['ui_params'] or status['clock'] <= last_clock):
                    raise ValueError('Anchor identity, item control, UI pose or clock changed')
                last_clock = status['clock']
                tree = check.command('dump_tree')['tree']
                capture = runtime.capture(base.capture_path(output, label, index))
                frame = {'status': status, 'tree': tree, 'capture': capture}
                row['frames'].append(frame)
                preserve()
                try:
                    layout = layout_readback(tree, status, report['initial'])
                    if fixed_layout is None:
                        fixed_layout = layout
                    elif layout != fixed_layout:
                        raise ValueError('Anchor UI native layout changed between states')
                    frame['layout'] = layout
                    frame['marker_mapping'] = base.marker_mapping(capture, layout, frozen_mapping)
                    if frozen_mapping is None:
                        frozen_mapping = frame['marker_mapping']['calibration']
                        report['frozen_marker_calibration'] = frozen_mapping
                except Exception as error:
                    frame['marker_mapping'] = {'passed': False, 'error': repr(error)}
                preserve()
                if index == 0:
                    time.sleep(min(.4, runtime.remaining()))
            row['state'] = 'captured'
            preserve()
        report['completed'] = True
    except Exception as error:
        report['errors'].append(repr(error))
    finally:
        runtime.cleanup = True
        for name in ('remove_client.py',):
            try:
                report['cleanup_remove'] = run(name)
                if isinstance(report['cleanup_remove'], dict):
                    report['cleanup_errors'].extend(report['cleanup_remove']['errors'])
            except Exception as error:
                report['cleanup_errors'].append(name + ': ' + repr(error))
        try:
            report['navigation_before_pop'] = runtime.wait('owned transition settled',
                lambda row: not row['owned'] or not row['transition'], lambda: run('navigation_client.py'))
            report['pop_attempted'] = True
            preserve()
            report['cleanup_pop'] = run('pop_client.py')
            runtime.wait('owned page absent', lambda row: not row['transition'] and not row['contains_owned'],
                         lambda: run('navigation_client.py'))
        except Exception as error:
            report['cleanup_errors'].append('owned page: ' + repr(error))
        try:
            report['destroy_attempted'] = True
            preserve()
            report['cleanup_destroy'] = run('destroy_client.py')
        except Exception as error:
            report['cleanup_errors'].append('owned actor destroy: ' + repr(error))
        try:
            report['actor_absence'] = runtime.wait('owned actor absent', lambda row: row['absent'],
                                                  lambda: run('absent_client.py'))
            report['restore'] = run('verify_client.py')
            report['restored'] = isinstance(report['restore'], dict) and report['restore'].get('restored') is True and not report['cleanup_errors']
        except Exception as error:
            report['cleanup_errors'].append('verify restoration: ' + repr(error))
        check.run, check.wait = original_run, original_wait
        preserve()
    return report


def score_probe(report):
    from PIL import ImageChops
    from verify_snow_plant_visibility import count, changed
    result = {'production_rendering_accepted': False, 'editor_frame_content_accepted': False,
              'enchantment_glint_accepted': False, 'ordinary_item_on_client_actor_proven': False,
              'shared_body_depth_proven': False, 'interpretation': 'inconclusive'}
    if not report.get('completed') or not report.get('restored') or report['errors'] or report['cleanup_errors']:
        result['reason'] = 'Finite matrix or exact-owned restoration incomplete'
        return result
    images = images_for(report, STATES)
    frozen = None
    for label in STATES:
        for frame in report['states'][label]['frames']:
            if frame.get('marker_mapping', {}).get('passed') is not True:
                raise ValueError('Failed marker gate remains failed during offline scoring')
            mapping = base.marker_mapping(frame['capture'], frame['layout'], frozen)
            if frozen is None:
                frozen = mapping['calibration']
            if mapping != frame['marker_mapping']:
                raise ValueError('Anchor frozen calibration changed during offline scoring')
    references = images['empty'] + images['empty_restored']
    plain = stable_difference(images['plain'] + images['plain_restored'], references)
    plain_pixels = count(plain)
    body = {sign: stable_difference(images['body_only_' + sign], references) for sign in ('minus', 'plus')}
    intersection, union = ImageChops.multiply(body['minus'], body['plus']), ImageChops.lighter(body['minus'], body['plus'])
    body_overlap = count(intersection) / float(max(1, count(union)))
    controls = {}
    for sign in ('minus', 'plus'):
        item = stable_difference(images['combined_' + sign], images['body_only_' + sign])
        controls[sign] = {'stable_combined_vs_body_pixels': count(item),
                          'visible_pixels_on_plain_support': count(ImageChops.multiply(item, plain)),
                          'body_pixels': count(body[sign])}
    retained = [row['visible_pixels_on_plain_support'] for row in controls.values()]
    result.update(ordinary_gate=ordinary_gate(report), stable_plain_pixels=plain_pixels,
                  body_silhouette_intersection_over_union=body_overlap, depth_controls=controls,
                  ordinary_visible_candidate=plain_pixels >= 80,
                  depth_occlusion_candidate=plain_pixels >= 80 and body_overlap >= .99 and max(retained) >= 80 and
                      min(retained) <= max(2, plain_pixels * .01),
                  restored_plain_difference_pixels=count(changed(images['plain'][0], images['plain_restored'][0], 25)),
                  interpretation='Review owned client-item visibility and +/- body depth controls separately',
                  limitations=['Depth direction is observed, never inferred from sign.',
                               'Body movement must preserve its 2D silhouette before attributing occlusion.',
                               'No production pose, clipping, opacity, paging, facing matrix or glint acceptance.'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-report', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    plan = prepare(args.raw_report, args.output)
    print(json.dumps({'prepared': True, 'frames': len(STATES) * plan['frames_per_state'], 'sdk_dispatch_attempted': False}))


if __name__ == '__main__':
    main()
