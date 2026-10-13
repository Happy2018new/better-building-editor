"""Freeze a finite same-binding world/UI discriminator without camera writes."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import uuid

import probe_client_anchor_paper_doll as anchor

ROOT = Path(__file__).resolve().parents[1]
ANCHOR_SHA256 = '2d93d4314e49dadc4bbe6e93b40c9b6c1e7e0ec5ab7b0c3304072f6ba8366a85'
STATES = ('world_empty', 'ui_empty', 'ui_plain', 'world_plain',
          'world_empty_restored', 'ui_empty_restored')
ATTRIBUTE = '_client_anchor_world_ui_probe'
PHYSICAL_SIZE = [1994, 1105]
FIXED_ROI = [0, 111, 1994, 1105]

CAMERA_READ = '''def native_camera_snapshot():
 cam=b.factory.CreateCamera(b.level)
 return {'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),'forward':cam.GetForward(),
  'pitch_lock':cam.IsModCameraLockPitch(),'yaw_lock':cam.IsModCameraLockYaw(),
  'motions':cam.GetCameraMotions()}
def native_camera_matches(actual,expected):
 return (all(abs(a-v)<=.01 for a,v in zip(actual['position'],expected['position'])) and
  all(abs((a-v+180.)%%360.-180.)<=.01 for a,v in zip(actual['rotation'],expected['rotation'])) and
  all(abs(a-v)<=.0001 for a,v in zip(actual['forward'],expected['forward'])) and
  all(actual[key]==expected[key] for key in ('pitch_lock','yaw_lock','motions')))
'''

PLACEMENT = '''cam_before=native_camera_snapshot()
assert not cam_before['motions'],('Camera has active motions',cam_before)
for key in ('position','rotation','forward'):
 values=cam_before[key]
 assert values is not None and len(values)==3 and all(not math.isnan(v) and not math.isinf(v) for v in values),(key,values)
forward=cam_before['forward']
length=math.sqrt(sum(v*v for v in forward))
assert length>.000001,('Camera forward is invalid',forward)
position=tuple(cam_before['position'][i]+forward[i]*3./length for i in range(3))
assert -1024.<position[1]<4096.,('Anchor placement is outside loaded height',position)
block=b.factory.CreateBlockInfo(b.level)
empty_cells=[]
for x in range(int(math.floor(position[0]-1.)),int(math.floor(position[0]+1.))+1):
 for y in range(int(math.floor(position[1]-1.)),int(math.floor(position[1]+1.))+1):
  for z in range(int(math.floor(position[2]-1.)),int(math.floor(position[2]+1.))+1):
   cell=(x,y,z)
   value=block.GetBlock(cell)
   assert value is not None and len(value)==2 and value[0]=='minecraft:air',('Placement is not verified loaded air',cell,value)
   empty_cells.append({'position':cell,'block':value})
saved['native_camera']=cam_before
saved['position']=position
saved['empty_cells']=empty_cells
saved['roi_receipt']={'physical_size':[1994,1105],'world':[0,111,1994,1105],'ui':[0,111,1994,1105],
 'declared_before_capture':True,'basis':'fixed native capture extent; top debug band excluded; anchor at camera forward ray distance 3; UI centered declared bounds'}
'''

CONTROL = '''from copy import deepcopy
from modern_projection.projection.bridge import _stable_palette
saved=sys._client_anchor_world_ui_probe
assert saved['nonce']==%r and not navigator.is_transitioning
label=%r
root=saved.get('root_ref')
if label!='world_empty':
 assert navigator.top is not None and navigator.top.key==saved['key'] and root and root.current
 visible=label.startswith('ui_')
 event={'operation':'owned_root_visibility:'+label,'state':'pending','attempted':True,'requested':visible}
 saved['journal'].append(event)
 event['return']=root.current.SetVisible(visible)
 event['readback']=root.current.GetVisible()
 event['state']='returned'
 assert event['readback'] is visible,event
itemcomp=b.factory.CreateItem(b.level)
if label=='ui_plain':
 assert not saved['attachments'] and saved['current'] is None
 item=deepcopy(saved['plain'])
 row={'control':label,'item':deepcopy(item),'canonical':repr(_stable_palette(item)),
  'state':'pending','attempted':True,'id':None,'offset':[0.,0.,0.],'rotation':[0.,0.,0.],'scale':1.}
 saved['attachments'].append(row)
 identity=itemcomp.BindItemToMinecraftModel(saved['actor'],item,'root',True,(0.,0.,0.),(0.,0.,0.),1.)
 row['id']=identity
 row['item_nonmutation']=repr(_stable_palette(item))==row['canonical']
 valid=isinstance(identity,(int,long)) and not isinstance(identity,bool) and identity>=0
 row['state']='rejected' if identity==-1 else 'bound' if valid else 'pending'
 assert valid and row['item_nonmutation'],row
 saved['current']=identity
elif label=='world_empty_restored':
 assert len(saved['attachments'])==1 and saved['attachments'][0]['state']=='bound'
 row=saved['attachments'][0]
 assert not row.get('remove_attempted'),row
 row['remove_attempted']=True
 row['remove_result']=itemcomp.SetBindBoneForBindItem(saved['actor'],row['id'],'',True)
 assert row['remove_result'] is True,row
 row['state']='removed'
 saved['current']=None
if label=='world_plain':
 assert len(saved['attachments'])==1 and saved['attachments'][0]['state']=='bound'
native_item=None
if saved['current'] is not None:
 native_item={'offset':itemcomp.GetBindItemOffset(saved['actor'],saved['current'],True),
  'rotation':itemcomp.GetBindItemRotation(saved['actor'],saved['current'],True),
  'scale':itemcomp.GetBindItemScale(saved['actor'],saved['current'],True),'id':saved['current']}
 assert native_item=={'offset':(0.,0.,0.),'rotation':(0.,0.,0.),'scale':1.,'id':saved['current']},native_item
if label.startswith('ui_'):
 event={'operation':'RenderEntity:'+label,'state':'pending','attempted':True}
 saved['journal'].append(event)
 event['value']=saved['ref'].current.asNeteasePaperDoll().RenderEntity(saved['ui_params'])
 event['state']='returned'
 assert event['value'] is True,event
 saved['model_read_after']=time.time()+.15
saved['control']=label
_result=json.dumps({'control':label,'actor':saved['actor'],'attachments':saved['attachments'],
 'native_item':native_item,'journal':saved['journal'],'clock':time.time()})
'''

STATUS_EXTRA = '''row=json.loads(_result)
root=saved.get('root_ref')
visible=root.current.GetVisible() if root and root.current else None
kind=b.factory.CreateEngineType(saved['actor']).GetEngineTypeStr()
if kind is not None:saved['observed_actor_kind']=kind
actual=native_camera_snapshot()
foot=b.factory.CreatePos(saved['player']).GetFootPos()
camera_matches=native_camera_matches(actual,saved['native_camera'])
foot_matches=foot is not None and len(foot)==3 and all(abs(v-a)<=.0001 for v,a in zip(foot,saved['foot']))
if saved['control'].startswith('world_'):
 row['ready']=kind=='modern_projection:anchor' and visible in (None,False) and not navigator.is_transitioning
else:row['ready']=row['ready'] and visible is True
row.update(root_visible=visible,actor_kind=kind,native_camera=actual,camera_matches=camera_matches,
 player_foot=foot,player_foot_matches=foot_matches,roi_receipt=saved['roi_receipt'])
_result=json.dumps(row)
'''

VERIFY_EXTRA = '''actual=native_camera_snapshot()
foot=b.factory.CreatePos(saved['player']).GetFootPos()
assert native_camera_matches(actual,saved['native_camera']),('Native camera changed',actual,saved['native_camera'])
assert foot is not None and len(foot)==3 and all(abs(v-a)<=.0001 for v,a in zip(foot,saved['foot'])),('Player foot changed',foot,saved['foot'])
'''


def inherited(code):
    return code.replace('_client_anchor_ui_probe', ATTRIBUTE)


def snippets(nonce, plain):
    # Keep the reviewed R13 exact-owned lifecycle, with a separate nonce attribute.
    install = inherited(anchor.INSTALL)
    install = install.replace("assert navigator.is_ready and not navigator.is_transitioning",
        "assert navigator.is_ready and not navigator.is_transitioning\nassert not navigator.get_entries(), 'World view requires no pre-existing pages'")
    install = install.replace("saved['position']=(foot[0],foot[1]+1.,foot[2])", PLACEMENT)
    install = install.replace('sys.' + ATTRIBUTE + '=saved\n', '')
    install = install.replace("candidate=b.system.CreateClientEntityByTypeStr", 'sys.' + ATTRIBUTE + '=saved\ncandidate=b.system.CreateClientEntityByTypeStr')
    install = install.replace("'control':'empty'", "'control':'world_empty'")
    install = install.replace("'ui_params')))", "'ui_params','native_camera','empty_cells','roi_receipt')))")
    camera = CAMERA_READ % ()
    verify = inherited(anchor.VERIFY).replace(" actor=saved['actor']", ''.join(' ' + line + '\n' for line in VERIFY_EXTRA.splitlines()) + " actor=saved['actor']")
    result = {'install_client.py': camera + install % (nonce, nonce, json.dumps(plain, sort_keys=True), anchor.base.MARKERS, anchor.UI),
              'actor_ready_client.py': inherited(anchor.ACTOR_READY) % nonce,
              'open_ui_client.py': (inherited(anchor.OPEN_UI) % nonce).replace(
                  "screen=saved['size_inputs']", "saved['control']='ui_empty'\nscreen=saved['size_inputs']"),
              'status_client.py': camera + inherited(anchor.STATUS) % nonce + STATUS_EXTRA,
              'remove_client.py': inherited(anchor.REMOVE) % nonce,
              'navigation_client.py': inherited(anchor.NAVIGATION) % nonce,
              'pop_client.py': inherited(anchor.POP) % nonce,
              'destroy_client.py': inherited(anchor.DESTROY) % nonce,
              'absent_client.py': inherited(anchor.ABSENT) % nonce,
              'verify_client.py': camera + verify % nonce}
    result.update({label + '_client.py': CONTROL % (nonce, label) for label in STATES})
    return result


def contract():
    return {'schema': 1, 'states': list(STATES), 'frames_per_state': 2,
            'normal_budget_seconds': 90, 'cleanup_reserve_seconds': 30, 'outer_budget_seconds': 150,
            'rpc_timeout_seconds': 10, 'native_retries': 0, 'new_game_starts': 0,
            'actor_identifier': 'modern_projection:anchor', 'bone': 'root', 'is_client_entity': True,
            'item_offset': [0., 0., 0.], 'item_rotation_zyx': [0., 0., 0.], 'item_scale': 1.,
            'binding_count': 1, 'ui': anchor.UI, 'world_ray_distance': 3.,
            'world_empty_box_half_extent': 1., 'physical_size': PHYSICAL_SIZE,
            'fixed_rois': {'world': FIXED_ROI, 'ui': FIXED_ROI},
            'roi_basis': 'fixed physical capture extent and debug exclusion; camera-forward anchor; centered UI bounds, all declared before first capture',
            'ordinary_minimum_stable_pixels': 80, 'difference_channel_threshold': 25,
            'marker_contract': 'unchanged V4; all UI markers must pass one physical pixel, including holdouts',
            'camera_mutation': False, 'player_movement': False, 'body_geometry_creation': False,
            'world_or_inventory_mutation': False, 'shader_or_material_mutation': False,
            'actor_absence_requires': 'recorded positive type before exact destroy, then observed None',
            'runtime_executor_sha256': anchor.base.EXECUTOR_SHA256,
            'anchor_source_sha256': ANCHOR_SHA256, 'base_source_sha256': anchor.BASE_SHA256,
            'sdk_dispatch_authorized': False, 'production_rendering_accepted': False,
            'editor_frame_content_accepted': False, 'enchantment_glint_accepted': False}


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def prepare(raw_report, output):
    output = Path(output).absolute()
    if output.exists():
        raise ValueError('Preserve existing paired anchor bundle')
    raw = Path(raw_report).read_bytes()
    controls, _ = anchor.base.item_controls(raw)
    nonce = uuid.uuid4().hex
    files = {'source.py': Path(__file__).read_bytes(),
             'tests.py': (ROOT / 'tests/test_client_anchor_world_ui.py').read_bytes(),
             'diagnostic.md': (ROOT / 'docs/CLIENT_ANCHOR_WORLD_UI_DIAGNOSTIC_R14.md').read_bytes(),
             'native-original.json': raw, 'plain.json': (json.dumps(controls['plain'], sort_keys=True) + '\n').encode('ascii'),
             'r13-source.py': Path(anchor.__file__).read_bytes(),
             'r13-tests.py': (ROOT / 'tests/test_client_anchor_paper_doll.py').read_bytes(),
             'v4-source.py': Path(anchor.base.__file__).read_bytes(),
             'v4-tests.py': (ROOT / 'tests/test_native_item_paper_doll.py').read_bytes(),
             'runtime-executor.py': Path(anchor.base.__file__).with_name('execute_frame_item_translation.py').read_bytes()}
    files.update({name: (ROOT / path).read_bytes() for name, path in anchor.RESOURCE_FILES.items()})
    files.update({name: code.encode('ascii') for name, code in snippets(nonce, controls['plain']).items()})
    output.mkdir(parents=True)
    for name, payload in files.items():
        (output / name).write_bytes(payload)
    plan = dict(contract(), nonce=nonce,
                files=[{'path': name, 'bytes': len(payload), 'sha256': digest(payload)} for name, payload in files.items()])
    (output / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='ascii')
    return plan


def verify_bundle(bundle):
    bundle = Path(bundle).resolve(strict=True)
    plan = json.loads((bundle / 'plan.json').read_bytes())
    if any(plan.get(key) != value for key, value in contract().items()):
        raise ValueError('Paired anchor prospective contract changed')
    nonce = plan['nonce']
    if len(nonce) != 32 or any(value not in '0123456789abcdef' for value in nonce):
        raise ValueError('Invalid paired anchor nonce')
    controls, _ = anchor.base.item_controls((bundle / 'native-original.json').read_bytes())
    programs = snippets(nonce, controls['plain'])
    expected = {'source.py', 'tests.py', 'diagnostic.md', 'native-original.json', 'plain.json',
                'r13-source.py', 'r13-tests.py', 'v4-source.py', 'v4-tests.py', 'runtime-executor.py'} | set(programs) | set(anchor.RESOURCE_FILES)
    if {row['path'] for row in plan['files']} != expected or len(plan['files']) != len(expected):
        raise ValueError('Paired anchor frozen inventory changed')
    for row in plan['files']:
        payload = (bundle / row['path']).read_bytes()
        if len(payload) != row['bytes'] or digest(payload) != row['sha256']:
            raise ValueError('Paired anchor frozen file changed: ' + row['path'])
    for name, code in programs.items():
        if (bundle / name).read_bytes() != code.encode('ascii'):
            raise ValueError('Paired anchor generated program differs from source: ' + name)
    import execute_frame_item_translation as executor
    for name, path, expected_hash in (
            ('r13-source.py', Path(anchor.__file__), ANCHOR_SHA256),
            ('v4-source.py', Path(anchor.base.__file__), anchor.BASE_SHA256),
            ('runtime-executor.py', Path(executor.__file__), anchor.base.EXECUTOR_SHA256)):
        if digest(path.read_bytes()) != expected_hash or digest((bundle / name).read_bytes()) != expected_hash:
            raise ValueError('Actual imported paired anchor dependency changed: ' + name)
    if ((bundle / 'source.py').read_bytes() != Path(__file__).read_bytes() or
            json.loads((bundle / 'plain.json').read_bytes()) != controls['plain']):
        raise ValueError('Paired anchor source or plain input changed')
    for name, path in anchor.RESOURCE_FILES.items():
        if (bundle / name).read_bytes() != (ROOT / path).read_bytes():
            raise ValueError('Paired anchor resource changed: ' + path)
    return bundle, plan


def preflight(bundle, output):
    bundle, plan = verify_bundle(bundle)
    output = Path(output).absolute()
    paths = [output, output.with_name(output.name + '.tmp')]
    for label in STATES:
        for index in range(2):
            shot = anchor.base.capture_path(output, label, index)
            paths.extend((shot, shot.with_suffix('.capture.json'), shot.with_suffix('.capture_error.json')))
    if any(path.exists() for path in paths):
        raise ValueError('Preserve existing paired anchor evidence')
    return bundle, plan, output


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
        if report['initial']['roi_receipt'] != {'physical_size': PHYSICAL_SIZE, 'world': FIXED_ROI, 'ui': FIXED_ROI,
                'declared_before_capture': True, 'basis': 'fixed native capture extent; top debug band excluded; anchor at camera forward ray distance 3; UI centered declared bounds'}:
            raise ValueError('Pre-capture ROI receipt differs from frozen contract')
        preserve()
        report['actor_ready'] = runtime.wait('paired anchor root', lambda row: row['ready'],
                                             lambda: run('actor_ready_client.py'))
        frozen_mapping, fixed_layout, last_clock = None, None, report['actor_ready']['clock']
        for label in STATES:
            if label == 'ui_empty':
                report['attempted_operation'] = 'open_ui_client.py'
                preserve()
                report['ui_opened'] = run('open_ui_client.py')
                runtime.wait('paired UI mounted', lambda row: row['ready'], lambda: run('status_client.py'))
            row = report['states'][label] = {'state': 'pending', 'frames': [], 'native_dispatch_attempted': True}
            report['attempted_operation'] = label + '_client.py'
            preserve()
            row['native'] = run(label + '_client.py')
            time.sleep(min(.2, runtime.remaining()))
            for index in range(2):
                status = runtime.wait(label, lambda value: value['ready'], lambda: run('status_client.py'))
                tree = check.command('dump_tree')['tree'] if label.startswith('ui_') else None
                capture = runtime.capture(anchor.base.capture_path(output, label, index))
                frame = {'status': status, 'tree': tree, 'capture': capture, 'fixed_roi': list(FIXED_ROI)}
                row['frames'].append(frame)
                preserve()
                if (status['actor'] != report['initial']['actor'] or status['control'] != label or
                        status['ui_params'] != report['initial']['ui_params'] or status['clock'] <= last_clock or
                        status['roi_receipt'] != report['initial']['roi_receipt'] or
                        not status['camera_matches'] or not status['player_foot_matches'] or
                        capture['size'] != PHYSICAL_SIZE):
                    raise ValueError('Paired actor, pose, ROI, camera, player foot or physical extent changed')
                last_clock = status['clock']
                if label.startswith('ui_'):
                    try:
                        layout = anchor.layout_readback(tree, status, report['initial'])
                        if fixed_layout is None:
                            fixed_layout = layout
                        elif layout != fixed_layout:
                            raise ValueError('Paired UI native layout changed')
                        frame['layout'] = layout
                        frame['marker_mapping'] = anchor.base.marker_mapping(capture, layout, frozen_mapping)
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
        try:
            report['cleanup_remove'] = run('remove_client.py')
            if isinstance(report['cleanup_remove'], dict):
                report['cleanup_errors'].extend(report['cleanup_remove']['errors'])
        except Exception as error:
            report['cleanup_errors'].append('remove: ' + repr(error))
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
    from PIL import Image
    from flat_frame_item_visual_checks import capture_payload
    from verify_snow_plant_visibility import count
    if not report.get('completed') or not report.get('restored'):
        raise ValueError('Complete restored paired report required for classification')
    if report['initial']['roi_receipt']['declared_before_capture'] is not True:
        raise ValueError('Prospective ROI receipt required')
    modes, marker_passed, frozen, layout = {}, True, None, None
    for mode in ('world', 'ui'):
        images = {}
        for suffix in ('empty', 'plain', 'empty_restored'):
            label = mode + '_' + suffix
            frames = report['states'][label]['frames']
            if len(frames) != 2:
                raise ValueError('Each paired state requires two frames')
            images[suffix] = []
            for frame in frames:
                status = frame['status']
                if (frame['fixed_roi'] != FIXED_ROI or report['initial']['roi_receipt'][mode] != FIXED_ROI or
                        not status['camera_matches'] or not status['player_foot_matches']):
                    raise ValueError('Paired fixed ROI or camera receipts changed')
                with Image.open(capture_payload(frame['capture'])) as source:
                    if list(source.size) != PHYSICAL_SIZE:
                        raise ValueError('Paired physical capture dimensions changed')
                    images[suffix].append(source.convert('RGB').crop(tuple(FIXED_ROI)))
                if mode == 'ui':
                    try:
                        current = anchor.layout_readback(frame['tree'], status, report['initial'])
                        if layout is None:
                            layout = current
                        elif layout != current:
                            raise ValueError('Paired native UI layout changed')
                        mapping = anchor.base.marker_mapping(frame['capture'], current, frozen)
                        if frozen is None:
                            frozen = mapping['calibration']
                        if (frame.get('marker_mapping', {}).get('passed') is not True or
                                mapping != frame['marker_mapping'] or frozen != report.get('frozen_marker_calibration')):
                            marker_passed = False
                    except Exception:
                        marker_passed = False
        pixels = count(anchor.stable_difference(images['plain'], images['empty'] + images['empty_restored']))
        restored_pixels = count(anchor.stable_difference(images['empty_restored'], images['empty']))
        modes[mode] = {'stable_plain_pixels': pixels, 'restored_difference_pixels': restored_pixels,
                       'ordinary_visible_candidate': pixels >= 80, 'empty_restored_candidate': restored_pixels < 80}
    ui_id = report['states']['ui_plain']['native']['native_item']['id']
    world_id = report['states']['world_plain']['native']['native_item']['id']
    if (ui_id != world_id or len(report['restore']['attachments']) != 1 or
            report['restore']['attachments'][0]['id'] != ui_id):
        raise ValueError('Paired modes did not retain one exact binding')
    valid = marker_passed and all(row['empty_restored_candidate'] for row in modes.values())
    if not valid:
        classification = 'invalid_controls'
    elif modes['world']['ordinary_visible_candidate'] and not modes['ui']['ordinary_visible_candidate']:
        classification = 'world_positive_ui_zero_on_this_anchor_and_pose'
    elif not modes['world']['ordinary_visible_candidate'] and not modes['ui']['ordinary_visible_candidate']:
        classification = 'both_zero_cause_unresolved'
    else:
        classification = 'paired_visibility_observation_requires_visual_review'
    return {'schema': 1, 'modes': modes, 'ui_marker_gate_passed': marker_passed,
            'same_binding_id': ui_id, 'classification': classification, 'visual_review_required': True,
            'production_rendering_accepted': False, 'editor_frame_content_accepted': False,
            'enchantment_glint_accepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'verify'))
    parser.add_argument('path')
    parser.add_argument('--raw-report')
    args = parser.parse_args()
    result = prepare(args.raw_report, args.path) if args.command == 'prepare' else verify_bundle(args.path)[1]
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
