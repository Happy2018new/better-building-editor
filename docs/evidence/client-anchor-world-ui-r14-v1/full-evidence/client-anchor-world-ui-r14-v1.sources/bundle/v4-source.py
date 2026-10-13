"""Prepare an isolated entity-ID item attachment probe; CLI never dispatches."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.entity_overlays import frame_item

RAW_SHA256 = 'a853a88604aa5dc05a4cf60d0f18a43db66eda8c7cb012e28db0322548bc86fc'
EXECUTOR_SHA256 = '7b3d7db8e5d25da97a7b8018a83f40eddc100e0d4c44977581ea98a0ce2a2662'
STATES = ('empty', 'plain', 'flag_enchanted', 'actual_enchanted', 'empty_restored')
MARKERS = (('native_item_marker_tl', [0, 255, 255]), ('native_item_marker_tr', [255, 0, 255]),
           ('native_item_marker_bl', [255, 255, 0]), ('native_item_marker_br', [0, 255, 0]))

INSTALL = '''# pylint: disable=unexpected-keyword-arg,E1123
from modern_projection.pyreact import Component,Image,Color,PaperDoll,Style,use_ref,AlignItems,JustifyContent,PaperDollRenderType,Position
from modern_projection.projection.bridge import _stable_palette
from modern_projection.projection import static_frame_item_data
from copy import deepcopy
assert not hasattr(sys,'_native_item_ui_probe')
assert not navigator.is_transitioning and navigator.is_ready
assert not s.busy and not s.projection_active and not b.preparing_entity
assert not any(profile['accepted'] for profile in static_frame_item_data.FRAME_ITEMS.values())
player=api.GetLocalPlayerId()
assert player and player!='-1'
native_screen=b.factory.CreateGame(b.level).GetScreenSize()
assert len(native_screen)==2 and all(value>32 for value in native_screen),native_screen
probe_size=min(240.,native_screen[0]-32.,native_screen[1]-32.)
assert probe_size>0,probe_size
markers=[{'key':'native_item_marker_tl','rgb':[0,255,255],'x':8.,'y':8.,'size':6.},
 {'key':'native_item_marker_tr','rgb':[255,0,255],'x':native_screen[0]-14.,'y':8.,'size':6.},
 {'key':'native_item_marker_bl','rgb':[255,255,0],'x':8.,'y':native_screen[1]-14.,'size':6.},
 {'key':'native_item_marker_br','rgb':[0,255,0],'x':native_screen[0]-14.,'y':native_screen[1]-14.,'size':6.}]
bone=b.factory.CreateActorRender(player).GetQueryableBoneOrientation('head',False)
assert bone is not None and len(bone)==4,bone
saved={'nonce':%r,'key':'native_item_ui_'+%r,'player':player,'bone':bone,
 'navigation':[entry.key for entry in navigator.get_entries()],
 'document':deepcopy(s.editor.document.to_data()),'profiles':repr(_stable_palette(static_frame_item_data.FRAME_ITEMS)),
 'camera':deepcopy(dict((key,getattr(s,key)) for key in ('camera_pose','camera_pivot','camera_pan','camera_depth_pose'))),
 'items':json.loads(%r),'attachments':[],'current':None,'control':'empty','push_attempted':False,
 'declared_size':probe_size,'size_inputs':native_screen,'markers':markers,
 'ui_params':{'entity_id':player,'scale':1.,'render_depth':-50,'init_rot_x':0.,'init_rot_y':60.,'init_rot_z':0.}}
sys._native_item_ui_probe=saved
@Component
def NativeItemPaperDollProbe():
 root_ref=use_ref(None)
 ref=use_ref(None)
 marker_refs=[use_ref(None),use_ref(None),use_ref(None),use_ref(None)]
 saved['root_ref']=root_ref
 saved['ref']=ref
 saved['marker_refs']=marker_refs
 children=[PaperDoll(key='native_item_probe_doll',ref=ref,renderType=PaperDollRenderType.entity,
  entityId=player,scale=1.,renderDepth=-50,initRotX=0.,initRotY=60.,initRotZ=0.,
  style=Style(width=probe_size,height=probe_size))]
 for index,marker in enumerate(markers):
  rgb=marker['rgb']
  children.append(Image(key=marker['key'],ref=marker_refs[index],
   color=Color((rgb[0]<<24)|(rgb[1]<<16)|(rgb[2]<<8)|255),
   style=Style(position=Position.absolute,left=marker['x'],top=marker['y'],width=6.,height=6.)))
 return Image(key='native_item_probe_root',ref=root_ref,color=Color(0xF7F9FCFF),style=Style(width='100%%',height='100%%',alignItems=AlignItems.center,
  justifyContent=JustifyContent.center),children=children)
saved['push_attempted']=True
assert navigator.push(NativeItemPaperDollProbe(),key=saved['key'])
_result=json.dumps(dict((key,saved[key]) for key in ('nonce','key','player','bone','navigation','document','profiles','camera','ui_params','declared_size','size_inputs','markers')))
'''

STATUS = '''saved=sys._native_item_ui_probe
assert saved['nonce']==%r
ref=saved.get('ref')
root_ref=saved.get('root_ref')
ready=bool(navigator.top and navigator.top.key==saved['key'] and not navigator.is_transitioning and ref and ref.current and root_ref and root_ref.current and len(saved.get('marker_refs',[]))==4 and all(marker.current for marker in saved['marker_refs']))
model=None
native_layout=None
now=time.time()
if ready:
 host=api.GetTopScreen()
 assert host is not None and host is navigator.top._host
 viewport=host.GetBaseUIControl(host._root_path)
 assert viewport is not None
 def native_rect(control):
  position=control.GetGlobalPosition()
  size=control.GetSize()
  return {'x':position[0],'y':position[1],'width':size[0],'height':size[1],'path':control.GetPath()}
 game=b.factory.CreateGame(b.level)
 native_layout={'paper_doll':native_rect(ref.current),'root':native_rect(root_ref.current),
  'viewport':native_rect(viewport),'screen_size_api_observed':game.GetScreenSize(),
  'screen_view_api_observed':game.GetScreenViewInfo(),
  'markers':[dict(marker,rect=native_rect(saved['marker_refs'][index].current)) for index,marker in enumerate(saved['markers'])],
  'declared_size':saved['declared_size'],'size_inputs':saved['size_inputs']}
 if saved.get('ready_first_seen') is None:saved['ready_first_seen']=now
 if now>=max(saved['ready_first_seen']+.15,saved.get('model_read_after',0.)):
  model=ref.current.asNeteasePaperDoll().GetModelId()
else:saved['ready_first_seen']=None
_result=json.dumps({'ready':ready,'control':saved['control'],'model_id':model,'clock':now,
 'native_layout':native_layout,
 'model_read_deferred':ready and model is None,
 'version':api.GetMinecraftVersion(),'attachments':saved['attachments'],'ui_params':saved['ui_params']})
'''

CONTROL = '''from modern_projection.projection.bridge import _stable_palette
from copy import deepcopy
saved=sys._native_item_ui_probe
assert saved['nonce']==%r and navigator.top.key==saved['key'] and not navigator.is_transitioning
itemcomp=b.factory.CreateItem(b.level)
for row in saved['attachments']:
 if row['state']=='bound':
  row['remove_attempted']=True
  row['remove_result']=itemcomp.SetBindBoneForBindItem(saved['player'],row['id'],'',False)
  assert row['remove_result'] is True,row
  row['state']='removed'
assert all(row['state'] in ('removed','rejected') for row in saved['attachments']),saved['attachments']
label=%r
saved['control']=label
saved['current']=None
if label not in ('empty','empty_restored'):
 item=deepcopy(saved['items'][label])
 row={'control':label,'item':deepcopy(item),'canonical':repr(_stable_palette(item)),
  'state':'pending','id':None,'remove_attempted':False}
 saved['attachments'].append(row)
 identity=itemcomp.BindItemToMinecraftModel(saved['player'],item,'head',False,(0.,0.,0.),(0.,0.,0.),1.)
 row['id']=identity
 row['item_nonmutation']=repr(_stable_palette(item))==row['canonical']
 valid=isinstance(identity,(int,long)) and not isinstance(identity,bool) and identity>=0
 row['state']='rejected' if identity==-1 else 'bound' if valid else 'pending'
 assert row['item_nonmutation'] and valid,row
 saved['current']=identity
assert saved['ref'].current.asNeteasePaperDoll().RenderEntity(saved['ui_params']) is True
saved['model_read_after']=time.time()+.15
_result=json.dumps({'control':label,'attachments':saved['attachments'],'clock':time.time(),'ui_params':saved['ui_params']})
'''

REMOVE = '''saved=getattr(sys,'_native_item_ui_probe',None)
_result=True
if saved is not None and saved['nonce']==%r:
 itemcomp=b.factory.CreateItem(b.level)
 errors=[]
 for row in saved['attachments']:
  if row['state']=='bound' and row['id'] is not None:
   row['remove_attempted']=True
   try:
    row['remove_result']=itemcomp.SetBindBoneForBindItem(saved['player'],row['id'],'',False)
    if row['remove_result'] is True:row['state']='removed'
    else:errors.append('remove rejected: '+repr(row['id']))
   except Exception as error:errors.append(repr(error))
  elif row['state']=='pending':errors.append('unresolved pending attachment: '+repr(row))
 _result=json.dumps({'attachments':saved['attachments'],'errors':errors})
'''

NAVIGATION = '''saved=getattr(sys,'_native_item_ui_probe',None)
owned=bool(saved is not None and saved['nonce']==%r)
_result=json.dumps({'owned':owned,'transition':bool(navigator.is_transitioning),
 'contains_owned':owned and navigator.contains(saved['key']),
 'top':navigator.top.key if navigator.top else None})
'''

POP = '''saved=getattr(sys,'_native_item_ui_probe',None)
_result=True
if saved is not None and saved['nonce']==%r and navigator.contains(saved['key']):
 assert not navigator.is_transitioning and navigator.top.key==saved['key'],'Owned probe is not top; refuse unrelated pop'
 assert navigator.pop()
_result=True
'''

VERIFY_RESTORE = '''from modern_projection.projection.bridge import _stable_palette
from modern_projection.projection import static_frame_item_data
saved=getattr(sys,'_native_item_ui_probe',None)
_result=True
if saved is not None and saved['nonce']==%r:
 assert not navigator.is_transitioning and not navigator.contains(saved['key'])
 assert [entry.key for entry in navigator.get_entries()]==saved['navigation']
 assert s.editor.document.to_data()==saved['document']
 assert repr(_stable_palette(static_frame_item_data.FRAME_ITEMS))==saved['profiles']
 assert dict((key,getattr(s,key)) for key in ('camera_pose','camera_pivot','camera_pan','camera_depth_pose'))==saved['camera']
 assert all(row['state'] in ('removed','rejected') for row in saved['attachments']),saved['attachments']
 assert not any(profile['accepted'] for profile in static_frame_item_data.FRAME_ITEMS.values())
 _result=json.dumps({'attachments':saved['attachments'],'navigation':saved['navigation'],'restored':True})
 del sys._native_item_ui_probe
'''


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def item_controls(raw):
    if digest(raw) != RAW_SHA256:
        raise ValueError('Use the exact preserved physical enchanted report')
    report = json.loads(raw)
    if not all(report[key] is True for key in ('completed', 'passed', 'restored', 'native_cleaned', 'client_cleaned')):
        raise ValueError('Physical source is not complete and restored')
    if report['production_rendering_accepted'] or report['enchantment_glint_accepted'] or report['cleanup_errors']:
        raise ValueError('Source acceptance or cleanup contract changed')
    row = next(row for row in report['client_palette']['rows'] if row['case'] == 'frame_filled')
    observed = next(row for row in report['native_readback']['results'] if row['case'] == 'frame_filled')
    actor = row['cell_nbt'][0]['nbt']
    if actor['Item'] != observed['actual_item'] or not observed['passed']:
        raise ValueError('Physical item source differs from native readback')
    actual = frame_item((row['block']['name'], row['block']['aux']), actor)
    if actual is None or not actual['isEnchanted'] or not actual['userData'].get('ench'):
        raise ValueError('Physical enchanted item dictionary is unavailable')
    plain = {'newItemName': actual['newItemName'], 'newAuxValue': actual['newAuxValue'],
             'isEnchanted': False, 'userData': {}}
    flagged = dict(plain, isEnchanted=True)
    return {'plain': plain, 'flag_enchanted': flagged, 'actual_enchanted': actual}, actor


def prepare(raw_report, output):
    output = Path(output).absolute()
    if output.exists():
        raise ValueError('Preserve existing probe bundle')
    raw = Path(raw_report).read_bytes()
    controls, actor = item_controls(raw)
    nonce = uuid.uuid4().hex
    serialized = json.dumps(controls, ensure_ascii=True, sort_keys=True)
    snippets = {'install_client.py': INSTALL % (nonce, nonce, serialized),
                'status_client.py': STATUS % nonce, 'remove_client.py': REMOVE % nonce,
                'cleanup_navigation_client.py': NAVIGATION % nonce,
                'pop_client.py': POP % nonce, 'verify_restore_client.py': VERIFY_RESTORE % nonce}
    snippets.update({name + '_client.py': CONTROL % (nonce, name) for name in STATES})
    files = {'native-original.json': raw, 'source.py': Path(__file__).read_bytes(),
             'tests.py': (ROOT / 'tests/test_native_item_paper_doll.py').read_bytes(),
             'diagnostic.md': (ROOT / 'docs/NATIVE_ITEM_PAPER_DOLL_DIAGNOSTIC_R12.md').read_bytes(),
             'items.json': (serialized + '\n').encode('ascii'),
             'actor.json': (json.dumps(actor, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('ascii')}
    files.update({name: code.encode('ascii') for name, code in snippets.items()})
    output.mkdir(parents=True)
    for name, payload in files.items():
        (output / name).write_bytes(payload)
    plan = {'schema': 4, 'scope': 'Native attached item inclusion in entity-ID UI rendering, independently of frame geometry',
            'supersedes_plan_sha256': '306a98496ccd50213bcf918704c1e4c024b876010688b6af04132186dd8d2e94',
            'nonce': nonce, 'states': STATES, 'frames_per_state': 3, 'frame_interval_seconds': .4,
            'native_budget_seconds': 150, 'cleanup_reserve_seconds': 30, 'rpc_timeout_seconds': 10,
            'native_retries': 0, 'new_game_starts': 0, 'world_or_inventory_mutation': False,
            'shader_or_material_mutation': False, 'target': {'kind': 'local native player', 'bone': 'head',
                'is_client_entity': False, 'offset': [0., 0., 0.], 'rotation_zyx_degrees': [0., 0., 0.], 'scale': 1.},
            'ui': {'render_type': 'entity', 'entity_id': 'resolved exact local player',
                   'size_rule': 'min(240, observed_GetScreenSize_width - 32, observed_GetScreenSize_height - 32)',
                   'maximum_square_side': 240, 'viewport_margin_total': 32, 'size_frozen_at': 'INSTALL',
                   'GetScreenSize_documented_units': 'pixels', 'GetScreenSize_observed_units': 'record without assuming physical pixels',
                   'scale': 1., 'render_depth': -50, 'init_rot_x': 0., 'init_rot_y': 60., 'init_rot_z': 0.,
                   'background_rgba': 'F7F9FCFF'},
            'marker_calibration': {'markers': MARKERS, 'logical_size': 6, 'logical_edge_inset': 8,
                'training_keys': [MARKERS[0][0], MARKERS[3][0]], 'holdout_keys': [MARKERS[1][0], MARKERS[2][0]],
                'rgb_channel_error': 16, 'minimum_component_pixels': 4, 'minimum_rectangle_fill': .95,
                'maximum_edge_or_center_error_physical_pixels': 1., 'fit': 'one positive scalar and x/y translation',
                'frozen_at': 'first empty frame; same parameters for all subsequent frames',
                'legacy_api_uniform_mapping_gate': 'preserved separately; never loosened or overwritten'},
            'runtime_executor_sha256': EXECUTOR_SHA256,
            'limitations': ['RenderEntity entity-ID selection is documented; inclusion of bound items is the hypothesis',
                           'This isolated surface does not establish block-geometry shared depth, clipping or alpha',
                           'Model ID must be read after UI readiness; -1 is preserved and is not an item-bind target',
                           'Native control rectangles and game pixel resolution must corroborate snapshots and uniform capture mapping',
                           'A timed-out bind can leave an unresolved pending ID; retain state and never blanket-clear native attachments'],
            'production_rendering_accepted': False, 'editor_frame_content_accepted': False,
            'enchantment_glint_accepted': False, 'sdk_dispatch_authorized': False,
            'files': [{'path': name, 'bytes': len(payload), 'sha256': digest(payload)} for name, payload in files.items()]}
    (output / 'plan.json').write_text(json.dumps(plan, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    return plan


def verify_bundle(bundle):
    bundle = Path(bundle).resolve(strict=True)
    plan = json.loads((bundle / 'plan.json').read_bytes())
    if plan['sdk_dispatch_authorized'] is not False or any(plan[key] for key in
            ('production_rendering_accepted', 'editor_frame_content_accepted', 'enchantment_glint_accepted')):
        raise ValueError('Diagnostic acceptance flags changed')
    if (plan['schema'] != 4 or tuple(plan['states']) != STATES or plan['frames_per_state'] != 3 or
            plan['frame_interval_seconds'] != .4 or plan['native_budget_seconds'] != 150 or
            plan['cleanup_reserve_seconds'] != 30 or plan['rpc_timeout_seconds'] != 10 or
            plan['native_retries'] != 0 or plan['new_game_starts'] != 0 or
            plan['world_or_inventory_mutation'] is not False or plan['shader_or_material_mutation'] is not False or
            plan['runtime_executor_sha256'] != EXECUTOR_SHA256):
        raise ValueError('Finite native item probe contract changed')
    names = {row['path'] for row in plan['files']}
    expected = {'native-original.json', 'source.py', 'tests.py', 'diagnostic.md', 'items.json', 'actor.json', 'install_client.py',
                'cleanup_navigation_client.py',
                'status_client.py', 'remove_client.py', 'pop_client.py', 'verify_restore_client.py'}
    expected.update(name + '_client.py' for name in STATES)
    if names != expected or len(names) != len(plan['files']):
        raise ValueError('Frozen file inventory changed')
    for row in plan['files']:
        payload = (bundle / row['path']).read_bytes()
        if len(payload) != row['bytes'] or digest(payload) != row['sha256']:
            raise ValueError('Frozen native item probe changed: ' + row['path'])
    controls, actor = item_controls((bundle / 'native-original.json').read_bytes())
    if (json.loads((bundle / 'items.json').read_bytes()) != controls or
            json.loads((bundle / 'actor.json').read_bytes()) != actor):
        raise ValueError('Frozen native item dictionaries changed')
    nonce = plan['nonce']
    if len(nonce) != 32 or any(character not in '0123456789abcdef' for character in nonce):
        raise ValueError('Invalid native item probe nonce')
    serialized = json.dumps(controls, ensure_ascii=True, sort_keys=True)
    snippets = {'install_client.py': INSTALL % (nonce, nonce, serialized), 'status_client.py': STATUS % nonce,
                'remove_client.py': REMOVE % nonce, 'pop_client.py': POP % nonce,
                'cleanup_navigation_client.py': NAVIGATION % nonce,
                'verify_restore_client.py': VERIFY_RESTORE % nonce}
    snippets.update({name + '_client.py': CONTROL % (nonce, name) for name in STATES})
    for name, code in snippets.items():
        if (bundle / name).read_bytes() != code.encode('ascii'):
            raise ValueError('Frozen native item client program differs from source: ' + name)
    if digest((bundle / 'source.py').read_bytes()) != digest(Path(__file__).read_bytes()):
        raise ValueError('Executing source differs from reviewed bundle')
    if digest(Path(__file__).with_name('execute_frame_item_translation.py').read_bytes()) != EXECUTOR_SHA256:
        raise ValueError('Reviewed runtime executor changed')
    return bundle, plan


def capture_path(output, label, index):
    return output.with_name(output.stem + '_' + label + '_' + str(index) + '_native.png')


def preflight(bundle, output):
    output = Path(output).absolute()
    if output.exists() or output.with_name(output.name + '.tmp').exists():
        raise ValueError('Preserve existing native item evidence')
    bundle, plan = verify_bundle(bundle)
    for label in plan['states']:
        for index in range(plan['frames_per_state']):
            shot = capture_path(output, label, index)
            if any(path.exists() for path in (shot, shot.with_suffix('.capture.json'),
                                             shot.with_suffix('.capture_error.json'))):
                raise ValueError('Preserve existing native capture: ' + str(shot))
    return bundle, plan, output


def marker_specs(size):
    return [{'key': key, 'rgb': rgb, 'x': 8. if index % 2 == 0 else size[0] - 14.,
             'y': 8. if index < 2 else size[1] - 14., 'size': 6.}
            for index, (key, rgb) in enumerate(MARKERS)]


def paper_doll_layout(tree, player, native, declared_size, size_inputs):
    nodes, pending = [], [tree]
    while pending:
        node = pending.pop()
        if not isinstance(node, dict):
            raise ValueError('Invalid UI tree node')
        nodes.append(node)
        pending.extend(reversed(node.get('children', [])))
    dolls = [node for node in nodes if node.get('key') == 'native_item_probe_doll']
    if len(dolls) != 1 or dolls[0].get('type') != 'PaperDoll':
        raise ValueError('Owned native paper doll is not unique')
    doll = dolls[0]
    props = doll.get('props', {})
    if (props.get('entityId') != player or props.get('renderType') != 'entity' or
            props.get('scale') != 1. or props.get('renderDepth') != -50 or
            [props.get('initRot' + axis) for axis in 'XYZ'] != [0., 60., 0.] or
            doll.get('opacity') != 1.):
        raise ValueError('Owned native paper doll props changed')
    roots = [node for node in nodes if node.get('key') == 'native_item_probe_root']
    if (len(roots) != 1 or roots[0].get('type') != 'Image' or roots[0].get('opacity') != 1. or
            roots[0].get('props', {}).get('color') != {'r': 247 / 255., 'g': 249 / 255., 'b': 252 / 255., 'a': 1.}):
        raise ValueError('Owned native paper doll root is not unique')
    root = roots[0].get('layout')
    box = doll.get('layout')
    if not root or not box:
        raise ValueError('Actual native paper doll layout is unavailable')
    for layout in (root, box):
        if not all(isinstance(layout.get(key), (int, float)) and math.isfinite(layout[key])
                   for key in ('x', 'y', 'width', 'height')):
            raise ValueError('Invalid native paper doll layout')
    if (not isinstance(size_inputs, (list, tuple)) or len(size_inputs) != 2 or
            not all(type(value) in (int, float) and math.isfinite(value) and value > 32 for value in size_inputs) or
            declared_size != min(240., size_inputs[0] - 32., size_inputs[1] - 32.)):
        raise ValueError('Native paper doll declared size differs from installation rule')
    if (box['width'] != declared_size or box['height'] != declared_size or root['width'] <= 0 or root['height'] <= 0 or
            box['x'] < root['x'] or box['y'] < root['y'] or
            box['x'] + box['width'] > root['x'] + root['width'] or
            box['y'] + box['height'] > root['y'] + root['height']):
        raise ValueError('Native paper doll is resized or outside the viewport')
    if not isinstance(native, dict):
        raise ValueError('Independent native layout readback is unavailable')
    for name, snapshot in (('root', root), ('paper_doll', box)):
        actual = native.get(name, {})
        if (not isinstance(actual.get('path'), str) or not actual['path'] or
                not all(type(actual.get(key)) in (int, float) and math.isfinite(actual[key]) and
                        abs(actual[key] - snapshot[key]) <= .01 for key in ('x', 'y', 'width', 'height'))):
            raise ValueError('Native ' + name + ' bounds differ from UI snapshot')
    viewport = native.get('viewport', {})
    pixels = native.get('screen_size_api_observed')
    if (not isinstance(viewport.get('path'), str) or not viewport['path'] or
            not all(type(viewport.get(key)) in (int, float) and math.isfinite(viewport[key])
                    for key in ('x', 'y', 'width', 'height')) or
            not isinstance(pixels, (list, tuple)) or len(pixels) != 2 or
            not all(type(value) in (int, float) and math.isfinite(value) and value > 0 for value in pixels) or
            not all(abs(viewport[key] - root[key]) <= .01 for key in ('x', 'y', 'width', 'height')) or
            abs(viewport['x']) > .01 or abs(viewport['y']) > .01):
        raise ValueError('Native full-screen viewport or game pixel metrics differ')
    if (list(pixels) != list(size_inputs) or native.get('declared_size') != declared_size or
            list(native.get('size_inputs', [])) != list(size_inputs) or
            abs(root['width'] - size_inputs[0]) > .01 or abs(root['height'] - size_inputs[1]) > .01 or
            abs((box['x'] - root['x']) - (root['width'] - declared_size) / 2.) > .01 or
            abs((box['y'] - root['y']) - (root['height'] - declared_size) / 2.) > .01):
        raise ValueError('Native viewport, frozen size or centered bounds changed since installation')
    scale = pixels[0] / viewport['width']
    if abs(scale * viewport['height'] - pixels[1]) > 1.:
        raise ValueError('Native screen mapping is not uniform; aspect or DPI changed')
    view = native.get('screen_view_api_observed')
    if (not isinstance(view, (list, tuple)) or len(view) != 4 or
            not all(type(value) in (int, float) and math.isfinite(value) for value in view) or
            view[0] <= 0 or view[1] <= 0):
        raise ValueError('Native screen view readback is unavailable')
    rows = native.get('markers')
    if not isinstance(rows, list) or len(rows) != 4:
        raise ValueError('Native marker readback is incomplete')
    for spec, actual in zip(marker_specs(size_inputs), rows):
        if {key: actual.get(key) for key in spec} != spec:
            raise ValueError('Native marker declarations changed')
        snapshots = [node for node in nodes if node.get('key') == spec['key']]
        if len(snapshots) != 1 or snapshots[0].get('type') != 'Image' or snapshots[0].get('opacity') != 1.:
            raise ValueError('Owned calibration marker is not unique and opaque')
        color = snapshots[0].get('props', {}).get('color', {})
        if color != dict(zip(('r', 'g', 'b', 'a'), [value / 255. for value in spec['rgb']] + [1.])):
            raise ValueError('Calibration marker color differs from fixed declaration')
        expected = {'x': root['x'] + spec['x'], 'y': root['y'] + spec['y'], 'width': 6., 'height': 6.}
        rect = actual.get('rect', {})
        snapshot = snapshots[0].get('layout', {})
        if (not isinstance(rect.get('path'), str) or not rect['path'] or
                not all(type(rect.get(key)) in (int, float) and math.isfinite(rect[key]) and
                        type(snapshot.get(key)) in (int, float) and math.isfinite(snapshot[key]) and
                        abs(rect[key] - expected[key]) <= .01 and abs(rect[key] - snapshot[key]) <= .01
                        for key in expected)):
            raise ValueError('Native calibration marker bounds differ from fixed declaration or snapshot')
        if (rect['x'] < root['x'] or rect['y'] < root['y'] or
                rect['x'] + 6. > root['x'] + root['width'] or rect['y'] + 6. > root['y'] + root['height'] or
                (rect['x'] < box['x'] + box['width'] and rect['x'] + 6. > box['x'] and
                 rect['y'] < box['y'] + box['height'] and rect['y'] + 6. > box['y'])):
            raise ValueError('Calibration marker is outside root or overlaps the paper doll')
    return {'native_path': doll['id'], 'root': root, 'paper_doll': box, 'props': props,
            'opacity': doll['opacity'], 'native_readback': native, 'screen_to_ui_scale': scale}


def physical_mapping(layout, size):
    native = layout['native_readback']
    if (not isinstance(size, (list, tuple)) or len(size) != 2 or
            not all(type(value) in (int, float) and math.isfinite(value) and value > 0 for value in size)):
        raise ValueError('Invalid physical capture dimensions')
    game = native['screen_size_api_observed']
    game_to_capture = size[0] / game[0]
    if abs(game_to_capture * game[1] - size[1]) > 1.:
        raise ValueError('Game pixel to physical capture mapping is not uniform; aspect or DPI changed')
    return {'screen_size_api_observed': game, 'GetScreenSize_documented_units': 'pixels',
            'GetScreenSize_observed_units': 'native viewport size; physical pixel equivalence unproved',
            'physical_pixels': list(size),
            'ui_to_game_scale': layout['screen_to_ui_scale'], 'game_to_physical_scale': game_to_capture,
            'ui_to_physical_scale': layout['screen_to_ui_scale'] * game_to_capture}


def legacy_api_mapping(layout, size):
    try:
        return {'passed': True, 'mapping': physical_mapping(layout, size), 'maximum_residual_pixels': 1.}
    except ValueError as error:
        return {'passed': False, 'reason': str(error), 'maximum_residual_pixels': 1.}


def marker_components(image, rgb):
    from PIL import ImageChops
    channels = image.split()
    mask = channels[0].point([255 if abs(value - rgb[0]) <= 16 else 0 for value in range(256)])
    for channel, target in zip(channels[1:], rgb[1:]):
        mask = ImageChops.multiply(mask, channel.point([255 if abs(value - target) <= 16 else 0
                                                       for value in range(256)]))
    payload, points = mask.tobytes(), set()
    index = payload.find(b'\xff')
    while index != -1:
        points.add(index)
        index = payload.find(b'\xff', index + 1)
    components = []
    while points:
        seed = points.pop()
        pending, component = [seed], [seed]
        while pending:
            index = pending.pop()
            x, y = index % image.width, index // image.width
            neighbors = []
            if x: neighbors.append(index - 1)
            if x + 1 < image.width: neighbors.append(index + 1)
            if y: neighbors.append(index - image.width)
            if y + 1 < image.height: neighbors.append(index + image.width)
            for neighbor in neighbors:
                if neighbor in points:
                    points.remove(neighbor)
                    pending.append(neighbor)
                    component.append(neighbor)
        if len(component) >= 4:
            xs, ys = [index % image.width for index in component], [index // image.width for index in component]
            bounds = [min(xs), min(ys), max(xs) + 1, max(ys) + 1]
            components.append({'bounds': bounds, 'pixels': len(component),
                               'rectangle_fill': len(component) / float((bounds[2] - bounds[0]) * (bounds[3] - bounds[1]))})
    return components


def marker_mapping(capture, layout, frozen=None):
    from PIL import Image
    from flat_frame_item_visual_checks import capture_payload
    source = capture_payload(capture)
    with Image.open(source) as image:
        image = image.convert('RGB')
    observed, logical = [], []
    for marker in layout['native_readback']['markers']:
        components = marker_components(image, marker['rgb'])
        if len(components) != 1 or components[0]['rectangle_fill'] < .95:
            raise ValueError('Calibration color is missing, ambiguous or not a solid rectangle: ' +
                             marker['key'] + '; components=' + str(len(components)))
        row = dict(components[0], key=marker['key'])
        bounds, rect = row['bounds'], marker['rect']
        row['center'] = [(bounds[0] + bounds[2]) / 2., (bounds[1] + bounds[3]) / 2.]
        observed.append(row)
        logical.append([rect['x'] + rect['width'] / 2., rect['y'] + rect['height'] / 2.])
    if frozen is None:
        delta = [logical[3][axis] - logical[0][axis] for axis in (0, 1)]
        physical_delta = [observed[3]['center'][axis] - observed[0]['center'][axis] for axis in (0, 1)]
        energy = sum(value * value for value in delta)
        if energy <= 0:
            raise ValueError('Calibration training marker positions are degenerate')
        scale = sum(left * right for left, right in zip(delta, physical_delta)) / energy
        translation = [(observed[0]['center'][axis] + observed[3]['center'][axis] -
                        scale * (logical[0][axis] + logical[3][axis])) / 2. for axis in (0, 1)]
        frozen = {'scale': scale, 'translation': translation, 'training_keys': [MARKERS[0][0], MARKERS[3][0]],
                  'holdout_keys': [MARKERS[1][0], MARKERS[2][0]], 'maximum_error_pixels': 1.,
                  'physical_size': list(image.size)}
    if (frozen['physical_size'] != list(image.size) or not math.isfinite(frozen['scale']) or frozen['scale'] <= 0 or
            not all(math.isfinite(value) for value in frozen['translation'])):
        raise ValueError('Frozen calibration is invalid or physical dimensions changed')
    for marker, row, center in zip(layout['native_readback']['markers'], observed, logical):
        rect = marker['rect']
        expected_center = [frozen['scale'] * center[axis] + frozen['translation'][axis] for axis in (0, 1)]
        expected_bounds = [frozen['scale'] * rect['x'] + frozen['translation'][0],
                           frozen['scale'] * rect['y'] + frozen['translation'][1],
                           frozen['scale'] * (rect['x'] + rect['width']) + frozen['translation'][0],
                           frozen['scale'] * (rect['y'] + rect['height']) + frozen['translation'][1]]
        row['center_errors'] = [abs(left - right) for left, right in zip(row['center'], expected_center)]
        row['edge_errors'] = [abs(left - right) for left, right in zip(row['bounds'], expected_bounds)]
        row['holdout'] = marker['key'] in frozen['holdout_keys']
        if max(row['center_errors'] + row['edge_errors']) > 1.:
            raise ValueError('Fixed calibration marker prediction exceeds one physical pixel: ' + marker['key'] +
                             '; center=' + repr(row['center_errors']) + '; edges=' + repr(row['edge_errors']))
    return {'calibration': frozen, 'markers': observed, 'passed': True,
            'legacy_api_uniform_mapping': legacy_api_mapping(layout, list(image.size))}


def frame_crop(layout, size, mapping):
    native = layout['native_readback']
    if not mapping['passed'] or list(size) != mapping['calibration']['physical_size']:
        raise ValueError('A matching positive marker calibration is required for the crop')
    box, scale, translation = native['paper_doll'], mapping['calibration']['scale'], mapping['calibration']['translation']
    crop = [math.floor(box['x'] * scale + translation[0]), math.floor(box['y'] * scale + translation[1]),
            math.ceil((box['x'] + box['width']) * scale + translation[0]),
            math.ceil((box['y'] + box['height']) * scale + translation[1])]
    if not (0 <= crop[0] < crop[2] <= size[0] and 0 <= crop[1] < crop[3] <= size[1]):
        raise ValueError('Native paper doll crop is outside the physical capture')
    return crop


def execute_probe(bundle, output, check, owner_guard, deadline):
    """Owner orchestrator only; importing and the CLI do not invoke this."""
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

    try:
        report['sdk_dispatch_attempted'] = True
        preserve()
        report['initial'] = run('install_client.py')
        mounted = report['mounted'] = runtime.wait('isolated paper doll mounted', lambda row: row['ready'],
                                                 lambda: run('status_client.py'))
        last_clock = mounted['clock']
        fixed_layout = None
        frozen_mapping = None
        for label in plan['states']:
            row = report['states'][label] = {'control': label, 'state': 'pending', 'frames': []}
            preserve()
            row['native'] = run(label + '_client.py')
            time.sleep(min(.15, runtime.remaining()))
            for index in range(plan['frames_per_state']):
                status = runtime.wait('paper doll ' + label, lambda value: value['ready'],
                                      lambda: run('status_client.py'))
                if (status['control'] != label or status['ui_params'] != mounted['ui_params'] or
                        status['version'] != mounted['version']):
                    raise ValueError('Native UI target, control or runtime version changed')
                if status['clock'] <= last_clock:
                    raise ValueError('Native client clock did not advance')
                last_clock = status['clock']
                layout = paper_doll_layout(check.command('dump_tree')['tree'], report['initial']['player'],
                                          status['native_layout'], report['initial']['declared_size'],
                                          report['initial']['size_inputs'])
                if fixed_layout is None:
                    fixed_layout = layout
                elif layout != fixed_layout:
                    raise ValueError('Native paper doll layout changed between controls')
                shot = capture_path(output, label, index)
                if any(path.exists() for path in (shot, shot.with_suffix('.capture.json'),
                                                 shot.with_suffix('.capture_error.json'))):
                    raise ValueError('Preserve existing native capture')
                capture = runtime.capture(shot)
                frame = {'status': status, 'layout': layout, 'capture': capture}
                row['frames'].append(frame)
                frame['marker_mapping'] = marker_mapping(capture, layout, frozen_mapping)
                if frozen_mapping is None:
                    frozen_mapping = frame['marker_mapping']['calibration']
                    report['frozen_marker_calibration'] = frozen_mapping
                frame['crop'] = frame_crop(layout, capture['size'], frame['marker_mapping'])
                preserve()
                if index + 1 < plan['frames_per_state']:
                    time.sleep(min(plan['frame_interval_seconds'], runtime.remaining()))
            row['state'] = 'captured'
            preserve()
        report['completed'] = True
    except Exception as error:
        report['errors'].append(repr(error))
    finally:
        runtime.cleanup = True
        try:
            result = report['owned attachments'] = run('remove_client.py')
            if isinstance(result, dict) and result.get('errors'):
                report['cleanup_errors'].extend(result['errors'])
        except Exception as error:
            report['cleanup_errors'].append('owned attachments: ' + repr(error))
        preserve()
        pop_dispatched = False
        try:
            report['navigation_before_pop'] = runtime.wait(
                'owned navigation transition settled', lambda nav: not nav['owned'] or not nav['transition'],
                lambda: run('cleanup_navigation_client.py'))
            pop_dispatched = True
            report['owned page'] = run('pop_client.py')
        except Exception as error:
            report['cleanup_errors'].append('owned page: ' + repr(error))
        preserve()
        try:
            if pop_dispatched:
                runtime.wait('owned page removed', lambda nav: not nav['transition'] and not nav['contains_owned'],
                             lambda: run('cleanup_navigation_client.py'))
            report['restore'] = run('verify_restore_client.py')
            report['restored'] = isinstance(report['restore'], dict) and report['restore'].get('restored') is True and not report['cleanup_errors']
        except Exception as error:
            report['cleanup_errors'].append('verify restore: ' + repr(error))
        check.run, check.wait = original_run, original_wait
        preserve()
    return report


def score_probe(report):
    """Offline differences only; material identity and glint remain unproved."""
    from itertools import combinations
    from PIL import Image, ImageChops, ImageFilter
    from flat_frame_item_visual_checks import capture_payload
    from verify_snow_plant_visibility import changed, count
    result = {'production_rendering_accepted': False, 'editor_frame_content_accepted': False,
              'enchantment_glint_accepted': False, 'native_bound_item_ui_inclusion_proven': False,
              'interpretation': 'inconclusive', 'channel_threshold': 25,
              'minimum_stable_item_pixels': 80, 'controls': {}}
    if not report['completed'] or not report['restored'] or report['errors'] or report['cleanup_errors']:
        result['reason'] = 'The finite native matrix or restoration did not complete'
        return result
    frames, fixed_crop, fixed_layout, frozen_mapping = {}, None, None, None
    for label in STATES:
        row = report['states'].get(label, {})
        if row.get('state') != 'captured' or len(row.get('frames', [])) != 3:
            raise ValueError('Incomplete native item frame inventory')
        frames[label] = []
        for frame in row['frames']:
            crop, layout = frame['crop'], frame['layout']
            if fixed_crop is None:
                fixed_crop, fixed_layout = crop, layout
            if crop != fixed_crop or layout != fixed_layout:
                raise ValueError('Native item evidence crop or layout changed')
            mapping = marker_mapping(frame['capture'], layout, frozen_mapping)
            if frozen_mapping is None:
                frozen_mapping = mapping['calibration']
            if (frame.get('marker_mapping') != mapping or
                    crop != frame_crop(layout, frame['capture']['size'], mapping)):
                raise ValueError('Native item crop differs from independent physical mapping')
            source = capture_payload(frame['capture'])
            with Image.open(source) as image:
                if (not isinstance(crop, list) or len(crop) != 4 or
                        any(type(value) is not int for value in crop) or
                        not (0 <= crop[0] < crop[2] <= image.width and 0 <= crop[1] < crop[3] <= image.height)):
                    raise ValueError('Native item evidence crop is invalid')
                frames[label].append(image.convert('RGB').crop(crop))
    size = frames['empty'][0].size
    if any(image.size != size for rows in frames.values() for image in rows):
        raise ValueError('Native item evidence dimensions changed')

    def temporal(images):
        mask = Image.new('L', size)
        for first, second in combinations(images, 2):
            mask = ImageChops.lighter(mask, changed(first, second, 25))
        return mask

    references = frames['empty'] + frames['empty_restored']
    baseline_motion = temporal(references)
    excluded = baseline_motion.filter(ImageFilter.MaxFilter(5))
    masks = {}
    for label in ('plain', 'flag_enchanted', 'actual_enchanted'):
        stable = Image.new('L', size, 255)
        for attached in frames[label]:
            for empty in references:
                stable = ImageChops.multiply(stable, changed(attached, empty, 25))
        stable = masks[label] = ImageChops.subtract(stable, excluded)
        result['controls'][label] = {'stable_pixels_outside_baseline_motion': count(stable),
                                     'bbox_in_paper_doll_crop': stable.getbbox(),
                                     'within_state_temporal_pixels': count(temporal(frames[label]))}
    interior = masks['plain']
    for label in ('flag_enchanted', 'actual_enchanted'):
        interior = ImageChops.multiply(interior, masks[label])
    interior = interior.filter(ImageFilter.MinFilter(3))
    plain_motion = temporal(frames['plain']).filter(ImageFilter.MaxFilter(5))
    interior = ImageChops.subtract(interior, plain_motion)
    for label in ('flag_enchanted', 'actual_enchanted'):
        result['controls'][label]['temporal_pixels_in_shared_item_interior_excluding_plain_motion'] = count(
            ImageChops.multiply(temporal(frames[label]), interior))
    result.update(crop=fixed_crop, baseline_temporal_pixels=count(baseline_motion),
                  shared_stable_item_interior_pixels=count(interior),
                  stable_plain_difference_candidate=count(masks['plain']) >= 80)
    if result['stable_plain_difference_candidate']:
        result['interpretation'] = 'Stable attachment-correlated pixels warrant visual review for native item inclusion'
    else:
        result['reason'] = 'No stable plain attachment difference above the minimum outside baseline motion'
    result['limitations'] = [
        'Player animation or attachment-driven body changes can still create stable differences; inspect the native frames',
        'Temporal changes do not establish GLINT defines, material identity, texture inputs or shader time',
        'This probe provides no block-geometry depth, clipping or composite-alpha evidence']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-report', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    plan = prepare(args.raw_report, args.output)
    print(json.dumps({'prepared': True, 'frames': len(plan['states']) * plan['frames_per_state'],
                      'sdk_dispatch_attempted': False, 'production_rendering_accepted': False}))


if __name__ == '__main__':
    main()
