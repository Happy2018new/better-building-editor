"""Finite original-art H/L four-direction and C/F side holdouts, with native controls."""
import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'tools'))
import probe_liquid_pose_channel as base
import probe_liquid_workspace as workspace
import probe_liquid_scene as scene
import verify_debug_blueprints as blueprints
import verify_debug_visuals as visuals
import capture_pure_liquid_native_controls as native
import capture_frozen_liquid_controls as frozen
import analyze_liquid_sides as oracle
from _session import load_session
from camera_projection import project_points

SCHEDULE = (
    ('h_vnw', 'water_depth_0_foreground', -135., 25., 18., (-1., .6, -1.2)),
    ('l_vnw', 'water_depth_3_foreground', -135., 25., 18., (-1., .6, -1.2)),
    ('h_vse', 'water_depth_0_foreground', 45., 25., 18., (1., .6, 1.2)),
    ('l_vse', 'water_depth_3_foreground', 45., 25., 18., (1., .6, 1.2)),
    ('c_vnw', 'water_flow_corner_foreground', -135., 25., 7., (-4., 2., -5.)),
    ('f_vnw', 'water_falling_column_foreground', -135., 25., 6., (-3., 2., -4.)))
PROFILE = '''from modern_projection.projection.liquid_deployment import candidate_profile
assert not hasattr(sys,'_liquid_scene_saved_profile')
sys._liquid_scene_saved_profile=(hasattr(s,'liquid_profile'),getattr(s,'liquid_profile',None))
s.liquid_profile=candidate_profile(frozen=True)
_result=True
'''
LOAD = '''from modern_projection.projection.debug_liquid_blueprints import source_document
from modern_projection.projection.cell import encode
identity,yaw,pitch,zoom=%r
document=source_document(identity,isolated=True,control='supported_positive')
sys._blueprint_qa_identity='original_side_'+identity
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':document.name,'size':document.size,'blocks':len(document.blocks)},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(document);s.progress=None;s.view='3d';s.page='workspace'
s.camera_focus_request=(3.5,3.5,3.5)
s.camera_view(yaw,pitch,zoom);s.camera_pan=(0.,0.);s.emit()
_result=json.dumps({'source_id':identity,'source_cells':[(pos,encode(value)) for pos,value in sorted(document.blocks.items())]})
'''
SCENE_STATE = workspace.STATE + '''row=json.loads(_result)
from modern_projection.projection.camera import OrbitCamera
camera=OrbitCamera(s.camera_pose[0]%360.,s.camera_pose[1],s.camera_pose[2]);camera.pan=s.camera_pan;camera.pivot=s.camera_pivot
row['basis']=camera.basis();row['pivot']=s.camera_pivot
row['groups']=[]
for key,entry in sorted(s.liquid_controls.registry.items(),key=lambda item:repr(item[0])):
 renderer=entry.get('renderer')
 if renderer is not None and any(renderer.visible):
  slot=renderer.visible.index(True)
  uniforms=renderer.uniforms[slot]
  group=s.liquid_preview.groups[key]
  row['groups'].append({'origin':group.origin,'uniforms':[uniforms[i] for i in (1,2,3,4)],
   'layer':0,'texture':key[1][0],'template':key[1][1],'visible':True})
_result=json.dumps(row)
'''
WORLD_STATE = workspace.WORLD_STATE + '''row=json.loads(_result)
row['groups']=[{'origin':record['group'].origin,'uniforms':record['group'].uniforms,'layer':0,
 'texture':record['group'].key[1][0],'template':record['group'].key[1][1],'visible':record['visible']}
 for record in renderer.active.values()] if renderer is not None else []
_result=json.dumps(row)
'''
DIRECT_WRITE = '''from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR,decode,encode,foreground,background,actor_data
saved=sys._liquid_pose_world
adapter=WorldAdapter(saved['player'])
cells=json.loads(%r)
decoded=[(tuple(pos),decode(value)) for pos,value in cells]
assert all(pos in saved['region'] and foreground(value)[0] in ('minecraft:stone','minecraft:water')
 and background(value)==AIR and actor_data(value) is None for pos,value in decoded)
cleared=[]
for pos in saved['workspace_cells']:
 pos=tuple(pos)
 before=encode(adapter.read(pos))
 changed=adapter.info.SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
 assert adapter.read(pos)==AIR,(pos,before,changed)
 cleared.append({'position':pos,'before':before,'changed':changed})
saved['workspace_cells']=[]
rows=[]
for pos,value in decoded:
 saved['workspace_cells'].append(pos)
 front=foreground(value)
 changed=adapter.info.SetBlockNew(pos,{'name':front[0],'aux':front[1]},0,saved['dimension'],True,False)
 actual=adapter.read(pos)
 assert changed and actual==value,(pos,encode(value),encode(actual),changed)
 rows.append({'position':pos,'actual':encode(actual),'changed':changed})
_result=json.dumps({'route':'SetBlockNew','isLegacy':True,'updateNeighbors':False,'cleared':cleared,'rows':rows})
'''
CAMERA_STATE = '''camera=b.factory.CreateCamera(b.level)
_result=json.dumps({'position':camera.GetPosition(),'rotation':camera.GetCameraRotation(),
 'screen':b.factory.CreateGame(b.level).GetScreenSize(),'fov':camera.GetFov(),
 'forward':camera.GetForward(),'render_events':sys._liquid_side_frames.count})
'''
FRAME_INSTALL = '''assert not hasattr(sys,'_liquid_side_frames')
class LiquidSideFrames(object):
 def __init__(self):self.count=0
 def tick(self,unused):self.count+=1
sys._liquid_side_frames=LiquidSideFrames()
probe=sys._liquid_side_frames
owner.ListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'GameRenderTickEvent',probe,probe.tick)
_result=True
'''
FRAME_REMOVE = '''if hasattr(sys,'_liquid_side_frames'):
 probe=sys._liquid_side_frames
 owner.UnListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'GameRenderTickEvent',probe,probe.tick)
 del sys._liquid_side_frames
_result=True
'''


def forward_cosine(camera, target):
    direction = [b - a for a, b in zip(camera['position'], target)]
    forward = camera['forward']
    if not all(math.isfinite(value) for vector in (direction, forward) for value in vector):
        return -1.
    length = math.sqrt(sum(value * value for value in direction) * sum(value * value for value in forward))
    return sum(a * b for a, b in zip(direction, forward)) / length if length else -1.


def settle_camera(check, target, offset, journal, save):
    for adjustment in (180., 0.):
        row = {'yaw_adjustment': adjustment, 'readbacks': []}
        journal.append(row)
        code = workspace.CAMERA.replace('direction[1]+180.', 'direction[1]+%r' % adjustment)
        code = code.replace("'target':target", "'render_events_at_request':sys._liquid_side_frames.count,'target':target")
        row['request'] = check.run(code % ((target, offset),)); save()
        previous = [None]
        def read():
            value = check.run(CAMERA_STATE); row['readbacks'].append(value); save(); return value
        def stable(value):
            last, previous[0] = previous[0], value
            return (value['render_events'] >= row['request']['render_events_at_request'] + 2
                    and last is not None and camera_matches(value, last)
                    and all(abs(a - b) < 1.e-4 for a, b in zip(value['position'], row['request']['position'])))
        actual = check.wait('actual camera after two render events', stable, read)
        row['forward_cosine'] = forward_cosine(actual, target)
        row['selected'] = row['forward_cosine'] > .99; save()
        if row['selected']:
            return dict(actual, target=list(target))
    raise RuntimeError('Neither fixed SDK camera candidate aims at target; no capture')


def qpc():
    count, frequency = ctypes.c_longlong(), ctypes.c_longlong()
    ctypes.windll.kernel32.QueryPerformanceCounter(ctypes.byref(count))
    ctypes.windll.kernel32.QueryPerformanceFrequency(ctypes.byref(frequency))
    return count.value * 10000000 // frequency.value


def scene_view_matches(state, yaw, pitch, zoom):
    actual = state['camera_pose']
    return (abs((actual[0] - yaw + 180.) % 360. - 180.) < 1.e-8
            and abs(actual[1] - pitch) < 1.e-8 and abs(actual[2] - zoom) < 1.e-8)


def sides(source, label):
    faces = ('north', 'west') if label.endswith('vnw') else ('south', 'east')
    positions = ((3, 3, 2), (2, 3, 3)) if source == 'water_flow_corner_foreground' else ((3, 3, 3),) * 2
    return [{'position': list(position), 'layer': 0, 'face': face} for position, face in zip(positions, faces)]


def native_comparison_positions(source_cells, document_origin, reserved):
    """Observe the exact source and its complete one-cell neighborhood."""
    selected = {tuple(document_origin[axis] + pos[axis] + delta[axis] for axis in range(3))
                for pos, unused in source_cells for delta in
                ((x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1))}
    if not selected.issubset(set(map(tuple, reserved))):
        raise ValueError('Complete native comparison neighborhood exceeds the reserved air region')
    return sorted(selected)


def camera_matches(actual, expected):
    return (all(actual[key] == expected[key] for key in ('position', 'screen', 'fov'))
            and all(abs((a - b + 180.) % 360. - 180.) <= 1.e-6
                    for a, b in zip(actual['rotation'], expected['rotation'])))


def affine(state, native_size):
    entries = [row for row in state['liquid_control_requests'] if row['visible'] and any(row['visible'])]
    if not entries:
        raise ValueError('No visible native liquid doll for affine geometry')
    entry = entries[0]
    slot = entry['visible'].index(True)
    position, size, pose = entry['doll_positions'][slot], entry['doll_sizes'][slot], entry['poses'][slot]
    group = state['groups'][0]
    center = [value + 2. for value in group['origin']]
    unit = pose[0] * min(size)
    right, up, toward = state['basis']
    screen_center = (position[0] + size[0] / 2., position[1] + size[1] / 2. - min(size) / 4.)
    rx, uy = [unit * value for value in right], [-unit * value for value in up]
    return {'kind': 'affine', 'origin': [0., 0., 0.],
        'affine': [rx + [screen_center[0] - sum(center[i] * rx[i] for i in range(3))],
                   uy + [screen_center[1] - sum(center[i] * uy[i] for i in range(3))]],
        'toward': toward, 'screen': state['screen_size'], 'native_image_screen': native_size}


def alpha_signature(state, world):
    """Bind source, pose, body, model IDs and every uniform except water alpha."""
    fields = ('source_cells', 'origin', 'opacity', 'missing', 'body_entity', 'body_uniforms', 'body_parts') if world else (
        'source_cells', 'camera_pose', 'camera_pan', 'pivot', 'screen_size', 'model_name', 'parts')
    result = {key: state[key] for key in fields}
    groups = json.loads(json.dumps(state['liquid_groups']))
    for group in groups:
        uniforms = group['group'][3] if world else group['uniforms']
        uniforms[3][1] = None
    result['liquid_groups'] = groups
    if not world:
        controls = json.loads(json.dumps(state['liquid_control_requests']))
        for control in controls:
            for uniforms in control['uniforms'] or ():
                if uniforms and '4' in uniforms:
                    uniforms['4'][1] = None
            if control['ready_request'] is not None:
                control['ready_request'][0][3][3][1] = None
        result['liquid_control_requests'] = controls
    return result


class FiniteClient(base.Client):
    def __init__(self, normal_deadline, cleanup_deadline):
        self.normal_deadline, self.cleanup_deadline = normal_deadline, cleanup_deadline
        self.cleaning = False
        super().__init__(timeout=3.)

    def _post(self, *args, **kwargs):
        remaining = (self.cleanup_deadline if self.cleaning else self.normal_deadline) - time.time()
        if remaining <= 0:
            raise TimeoutError('Fixed priority capture/cleanup deadline elapsed; call not dispatched')
        self.timeout = min(3., remaining)
        return super()._post(*args, **kwargs)


class FiniteCheck(blueprints.BlueprintCheck):
    def wait(self, label, predicate, read):
        budget = (self.client.cleanup_deadline if self.client.cleaning else self.client.normal_deadline) - time.time()
        self.timeout = min(3., max(0., budget))
        return super().wait(label, predicate, read)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--capture-exe', required=True, type=Path)
    parser.add_argument('--calibration', required=True, type=Path)
    parser.add_argument('--physical', required=True, type=Path)
    parser.add_argument('--viewport-receipt', required=True, type=Path)
    parser.add_argument('--priority-world-alpha', action='store_true',
                        help='Eight native/full H/L side PNGs, then six Scene/full/missing alpha0/1 diagnostics')
    parser.add_argument('--normal-deadline-unix', type=float)
    parser.add_argument('--cleanup-deadline-unix', type=float)
    parser.add_argument('--native-write-compare', action='store_true',
                        help='H/L palette, direct SetBlockNew and full projection, with one empty native baseline')
    args = parser.parse_args()
    priority_mode = args.priority_world_alpha or args.native_write_compare
    if args.priority_world_alpha and args.native_write_compare:
        parser.error('Select one finite diagnostic mode')
    if args.output.exists():
        parser.error('Keep the finite original-art receipt fresh')
    if priority_mode and (args.normal_deadline_unix is None or args.cleanup_deadline_unix is None
            or not time.time() < args.normal_deadline_unix < args.cleanup_deadline_unix):
        parser.error('Priority mode requires ordered fresh absolute normal and cleanup deadlines')
    schedule = SCHEDULE[:2] if args.native_write_compare else SCHEDULE[:4] if priority_mode else SCHEDULE
    routes = ('native_palette', 'native_direct', 'full') if args.native_write_compare else ('native', 'full') if priority_mode else ('native', 'full', 'missing')
    original_count = 6 if args.native_write_compare else 8 if priority_mode else 24
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    session = load_session(args.session, args.owner, live=True)
    physical, calibration = json.loads(args.physical.read_bytes()), json.loads(args.calibration.read_bytes())
    viewport = json.loads(args.viewport_receipt.read_bytes())
    binding = {key: session[key] for key in ('owner', 'session_file', 'game_pid', 'game_identity')}
    if (not physical.get('passed') or not calibration.get('passed') or not calibration.get('restored')
            or any(physical['session_binding'][key] != session[key]
                   for key in ('owner', 'session_file', 'game_pid', 'game_identity'))):
        raise ValueError('Exact-session physical and stone-calibration prerequisites required')
    calibration_images = [view[key] for view in calibration['views'] for key in ('shown', 'hidden')]
    calibration_captures = [image['capture'] for image in calibration_images]
    if (not calibration.get('completed') or calibration.get('cleanup_errors')
            or calibration.get('session_file') != session['session_file']
            or len(calibration_captures) != 6
            or any(not row.get('ok') or not row.get('reliable') or any(row.get(key) != value
                for key, value in binding.items()) for row in calibration_captures + [viewport])):
        raise ValueError('Every stone/viewport capture must bind this exact current session')
    for image, capture in zip(calibration_images, calibration_captures):
        if (image['path'] != capture['path'] or image['sha256'] != capture['sha256']
                or oracle.fingerprint(image['path'])['sha256'] != capture['sha256']):
            raise ValueError('Archived stone image and native capture receipt differ')
    if oracle.fingerprint(viewport['path'])['sha256'] != viewport['sha256']:
        raise ValueError('Archived viewport image and native capture receipt differ')
    native_size = [viewport['width'], viewport['height']]
    if any([row['width'], row['height']] != native_size for row in calibration_captures):
        raise ValueError('Same-session stone calibration and full-native viewport dimensions changed')
    report = {'schema': 1, 'completed': False, 'restored': False, 'captures': {}, 'states': {},
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'schedule': schedule,
        'session_binding': binding,
        'prerequisites': {key: oracle.fingerprint(path) for key, path in
            (('physical', args.physical), ('calibration', args.calibration), ('viewport', args.viewport_receipt))},
        'cleanup_errors': [], 'created_qpc_100ns': qpc(), 'projection_geometry': {},
        'original_artwork_observed': False, 'side_uv_qualified': False, 'animation_qualified': False,
        'production_qualified': False, 'scope': 'Original-art-only24 diagnostic; structural marker controls absent'}
    if priority_mode:
        report.update(scope='Original-world8 then alpha6 appearance/disappearance diagnostic only',
            original_png_count=8, alpha_png_count=6, transparency_qualified=False,
            normal_deadline_unix=args.normal_deadline_unix, cleanup_deadline_unix=args.cleanup_deadline_unix,
            exclusions=['original Scene/missing side holdouts', 'sloped/falling C/F holdouts',
                'occupied neighbor', 'structural UV marker oracle', 'alpha0.45 translucent pixels',
                'independent animation', 'production qualification'])
    if args.native_write_compare:
        report.update(scope='H/L NW palette versus direct SetBlockNew native visibility diagnostic',
            hypothesis='Palette-only front-cell writes may update SDK readback without terrain mesh publication',
            original_png_count=6, empty_native_png_count=1, alpha_png_count=0,
            native_write_receipts={}, full_wait_reads={}, full_render_requests={})
    save = lambda: base.write(args.output, report)
    save()
    selected_client = FiniteClient(args.normal_deadline_unix, args.cleanup_deadline_unix) if priority_mode else base.Client(timeout=20)
    with selected_client as client:
        check_type = FiniteCheck if priority_mode else blueprints.BlueprintCheck
        check = check_type(client, args.output, 20.)
        installed = world_saved = visual_saved = environment_attempted = frame_observer_installed = False
        declarations = {}
        report['camera_settle_journal'] = []
        def set_camera(target, offset):
            return settle_camera(check, target, offset, report['camera_settle_journal'], save)
        def scene_setup(item):
            label, source, yaw, pitch, zoom, offset = item
            source_row = check.run(LOAD % ((source, yaw, pitch, zoom),))
            if source_row['source_cells'] != oracle.builtin_geometry(source)['source_cells']:
                raise RuntimeError('Actual source differs from fixed built-in: ' + label)
            report['states']['source_' + label] = source_row
            check.wait('initial source ' + label, workspace.scene_ready, lambda: check.run(SCENE_STATE))
            check.run('s.camera_view(%r,%r,%r)\ns.camera_pan=(0.,0.)\n_result=True' % (yaw, pitch, zoom))
            return check.wait('settled side view ' + label, lambda row: workspace.scene_ready(row) and
                             scene_view_matches(row, yaw, pitch, zoom), lambda: check.run(SCENE_STATE))
        def validate_frame(identity, state):
            declaration = declarations[identity]
            if identity.startswith('scene_'):
                if (not workspace.scene_ready(state) or state['source_cells'] != declaration['source_cells']
                        or affine(state, native_size) != declaration['projection']):
                    raise RuntimeError('Scene source, readiness or frozen projection differs: ' + identity)
            else:
                if not camera_matches(state['camera'], declaration['projection']):
                    raise RuntimeError('Camera or viewport differs from fixed preflight: ' + identity)
                if forward_cosine(state['camera'], declaration['projection']['target']) <= .99:
                    raise RuntimeError('Actual camera no longer aims at fixed target: ' + identity)
                if not identity.startswith('native_') and (
                        not workspace.world_ready(state) or state['source_cells'] != declaration['source_cells']):
                    raise RuntimeError('World owner source or readiness differs: ' + identity)
        def frame(identity, state):
            if priority_mode and time.time() >= args.normal_deadline_unix:
                raise TimeoutError('Normal priority deadline before original capture')
            before = state()
            report['states'][identity] = {'before': before}; save()
            validate_frame(identity, before)
            report['captures'][identity] = base.capture(args.session, args.owner,
                args.output.with_name(args.output.stem + '_' + identity + '.png'), args.capture_exe)
            report['states'][identity] = {'before': before, 'after': state()}
            save()
            validate_frame(identity, report['states'][identity]['after'])
            capture = report['captures'][identity]
            if ([capture['width'], capture['height']] != native_size
                    or capture['frame']['frame_qpc_100ns'] <= report['preflight']['created_qpc_100ns']):
                raise RuntimeError('Native viewport or preflight/capture clock ordering changed: ' + identity)
        def priority_alpha():
            check.run(workspace.SOURCE + '\n_result=True')
            report['alpha_source'] = check.run(workspace.LOAD % (('fence_rear', 'supported_positive'),))
            report['alpha_controls'] = {}
            expected_source = report['alpha_source']['cells']
            def capture_alpha(route, read, world):
                baseline = check.wait(route + ' alpha baseline',
                    workspace.world_ready if world else workspace.scene_ready, read)
                signature = alpha_signature(baseline, world)
                declaration = {'source_cells': expected_source, 'signature_except_water_alpha': signature}
                if world:
                    declaration['camera'] = check.run(CAMERA_STATE)
                    declaration['engine_regions'] = workspace.native_transparency_regions(
                        report['alpha_camera'], origin, calibration['vertical_fov'])
                else:
                    declaration['engine_regions'] = workspace.scene_transparency_regions(baseline)
                    declaration['engine_screen'] = baseline['screen_size']
                report['alpha_controls'][route] = {'preflight': declaration, 'phases': {}}
                save()
                for alpha in (0., 1.):
                    check.run((workspace.WORLD_ALPHA if world else workspace.SCENE_ALPHA) % alpha)
                    before = check.wait(route + ' alpha ' + str(alpha),
                        lambda value: workspace.alpha_ready(value, alpha, world), read)
                    if before['source_cells'] != expected_source or alpha_signature(before, world) != signature:
                        raise RuntimeError('Alpha holdout changed source, pose, body, IDs or other uniforms')
                    if world and not camera_matches(check.run(CAMERA_STATE), declaration['camera']):
                        raise RuntimeError('Alpha camera changed before capture')
                    identity = 'alpha_' + route + '_' + str(int(alpha))
                    time.sleep(.3)
                    if time.time() >= args.normal_deadline_unix:
                        raise TimeoutError('Normal priority deadline before alpha capture')
                    report['captures'][identity] = base.capture(args.session, args.owner,
                        args.output.with_name(args.output.stem + '_' + identity + '.png'), args.capture_exe)
                    after = read()
                    report['states'][identity] = {'before': before, 'after': after}
                    report['alpha_controls'][route]['phases'][str(int(alpha))] = identity
                    save()
                    if (not workspace.alpha_ready(after, alpha, world) or after['source_cells'] != expected_source
                            or alpha_signature(after, world) != signature
                            or [report['captures'][identity]['width'], report['captures'][identity]['height']] != native_size
                            or world and not camera_matches(check.run(CAMERA_STATE), declaration['camera'])):
                        raise RuntimeError('Alpha source or full native viewport changed across capture')
                check.run((workspace.WORLD_ALPHA if world else workspace.SCENE_ALPHA) % -1.)
            check.run('owner.open_workspace()\n_result=True')
            check.wait('alpha Scene mounted', lambda row: row['open'] and not row['transition'], check.navigation)
            capture_alpha('scene', lambda: check.run(SCENE_STATE), False)
            check.run('navigator.pop()\n_result=True')
            check.wait('alpha Scene closed', lambda row: not row['open'] and not row['transition'], check.navigation)
            target = tuple(origin[i] + (1.35 if i == 1 else .5) for i in range(3))
            report['alpha_camera'] = set_camera(target, (0., 0., 7.))
            if (report['alpha_camera']['fov'] != calibration['reported_fov']
                    or report['alpha_camera']['screen'] != calibration['views'][0]['camera']['screen']):
                raise RuntimeError('Alpha world camera differs from same-session stone calibration')
            check.run('s.origin=%r\ns.opacity=1.\ns.projection_outline=False\n_result=True' % (document_origin,))
            for missing in (False, True):
                route = 'missing' if missing else 'full'
                check.run('s.projection_missing=%r\nb.project()\n_result=True' % missing)
                capture_alpha(route, lambda: check.run(WORLD_STATE), True)
                check.run('b.stop_projection()\n_result=True')
        try:
            installed = True
            report['setup'] = check.run(blueprints.INSTALL_PROBE)
            frame_observer_installed = True
            report['render_observer'] = check.run(FRAME_INSTALL)
            if check.navigation()['open']:
                check.run('navigator.pop()\n_result=True')
                check.wait('close existing Scene', lambda row: not row['open'] and not row['transition'], check.navigation)
            check.run(PROFILE)
            check.run('owner.open_workspace()\n_result=True')
            check.wait('side Scene mounted', lambda row: row['open'] and not row['transition'], check.navigation)
            for item in (() if priority_mode else schedule):
                label, source, yaw, pitch, zoom, offset = item
                state = scene_setup(item)
                report['projection_geometry']['scene_' + label] = affine(state, native_size)
                declarations['scene_' + label] = {'id': 'scene_' + label, 'source_id': source,
                    'route': 'scene', 'role': 'original', 'view': label.rsplit('_', 1)[1],
                    'control': 'supported_positive', 'source_cells': state['source_cells'],
                    'projection': report['projection_geometry']['scene_' + label], 'sides': sides(source, label)}
                report['states']['preflight_scene_' + label] = state
                save()
            check.run('navigator.pop()\n_result=True')
            check.wait('close Scene for native holdouts', lambda row: not row['open'] and not row['transition'], check.navigation)
            visual_saved = True
            report['visual_saved'] = check.run(visuals.SAVE_VISUAL)
            environment_attempted = True
            report['environment'] = base.run(client, base.ENVIRONMENT, True)
            world_saved = True
            report['reservation'] = base.run(client, workspace.QUALIFICATION_PREPARE, True)
            base.run(client, base.CLEAR, True)
            base.run(client, workspace.FLOW % True, True)
            origin = tuple(report['reservation']['origin'])
            document_origin = tuple(value - 3 for value in origin)
            positions = report['reservation']['region']
            for label, source, yaw, pitch, zoom, offset in schedule:
                source_row = check.run(LOAD % ((source, yaw, pitch, zoom),))
                target = tuple(origin[i] + (.35 if i == 1 else .5) + (1. if source == 'water_falling_column_foreground' and i == 1 else 0.)
                               for i in range(3))
                camera = set_camera(target, offset)
                if (camera['fov'] != calibration['reported_fov'] or
                        any(camera['screen'] != view['camera']['screen'] for view in calibration['views'])):
                    raise RuntimeError('Stone calibration FOV or engine viewport differs: ' + label)
                report['projection_geometry']['world_' + label] = dict(camera, vertical_fov=calibration['vertical_fov'],
                    origin=list(document_origin), kind='perspective', native_image_screen=native_size)
                for route in routes:
                    identity = route + '_' + label
                    declarations[identity] = {'id': identity, 'source_id': source,
                        'route': route, 'role': 'native_original' if route.startswith('native') else 'original',
                        'view': label.rsplit('_', 1)[1], 'control': 'supported_positive',
                        'source_cells': source_row['source_cells'], 'sides': sides(source, label),
                        'projection': report['projection_geometry']['world_' + label]}
            preflight_rows = {identity: [oracle.side_preflight(declaration, side,
                oracle.builtin_geometry(declaration['source_id'])) for side in declaration['sides']]
                for identity, declaration in declarations.items()}
            if len(declarations) != original_count or any(not row['adequate'] for rows in preflight_rows.values() for row in rows):
                raise ValueError('The fixed original geometry matrix must be visible and low sides at least24 pixels')
            geometry_plan = {'schema': 1, 'kind': 'liquid_original_side_diagnostic24',
                'source_bindings': oracle.source_bindings(), 'declarations': list(declarations.values()),
                'session_binding': binding, 'prerequisites': report['prerequisites'], 'limits': oracle.LIMITS,
                'side_uv_qualified': False, 'production_qualified': False}
            if priority_mode:
                geometry_plan['kind'] = 'liquid_native_write_compare6' if args.native_write_compare else 'liquid_original_world_priority8'
            if args.native_write_compare:
                import analyze_liquid_native_write as visibility
                geometry_plan['native_write_visibility'] = {
                    'limits': visibility.LIMITS,
                    'analyzer': oracle.fingerprint(visibility.__file__),
                    'scope': 'Publication visibility only; independent native rendering gates remain false'}
            geometry_path = args.output.with_name(args.output.stem + '_geometry_plan.json')
            if geometry_path.exists():
                raise ValueError('Geometry plan must be fresh before first water PNG')
            base.write(geometry_path, geometry_plan)
            report['preflight'] = {'geometry_plan': oracle.fingerprint(geometry_path),
                'created_qpc_100ns': qpc(), 'geometry': preflight_rows, 'all_declared_ready': True,
                'declared_original_count': original_count, 'all24_ready': original_count == 24,
                'before_first_water_png': not report['captures']}
            save()
            check.run('owner.open_workspace()\n_result=True')
            check.wait('side Scene remounted', lambda row: row['open'] and not row['transition'], check.navigation)
            for item in (() if priority_mode else schedule):
                label = item[0]
                scene_setup(item)
                time.sleep(.3)
                frame('scene_' + label, lambda: check.run(SCENE_STATE))
            check.run('navigator.pop()\n_result=True')
            check.wait('close Scene after original holdouts', lambda row: not row['open'] and not row['transition'], check.navigation)
            for label, source, yaw, pitch, zoom, offset in schedule:
                source_row = check.run(LOAD % ((source, yaw, pitch, zoom),))
                fixed_camera = report['projection_geometry']['world_' + label]
                actual_camera = set_camera(fixed_camera['target'], offset)
                if not camera_matches(actual_camera, fixed_camera):
                    raise RuntimeError('Settled capture camera differs from frozen declaration: ' + label)
                save()
                cells = [(tuple(document_origin[i] + pos[i] for i in range(3)), value)
                         for pos, value in source_row['source_cells']]
                observed_positions = (native_comparison_positions(source_row['source_cells'], document_origin, positions)
                                      if args.native_write_compare else positions)
                if args.native_write_compare:
                    report.setdefault('native_observed_positions', {})[label] = observed_positions
                    save()
                def native_state():
                    return {'server': base.run(client, native.snapshot_code(observed_positions, True), True),
                            'client': check.run(native.snapshot_code(observed_positions)),
                            'camera': check.run(CAMERA_STATE)}
                expected = frozen.native_reference(cells)
                if args.native_write_compare and label == schedule[0][0]:
                    empty_before = native_state()
                    empty_expected = frozen.native_reference([])
                    if any(not native.matches(empty_before[side], empty_expected, observed_positions) for side in ('client','server')):
                        raise RuntimeError('Empty native baseline differs')
                    identity = 'native_empty_vnw'
                    if not camera_matches(empty_before['camera'], fixed_camera):
                        raise RuntimeError('Empty native baseline camera differs')
                    report['captures'][identity] = base.capture(args.session,args.owner,
                        args.output.with_name(args.output.stem+'_'+identity+'.png'),args.capture_exe)
                    empty_after = native_state()
                    report['states'][identity] = {'before':empty_before,'after':empty_after}; save()
                    if (not camera_matches(empty_after['camera'],fixed_camera) or
                            any(not native.matches(empty_after[side],empty_expected,observed_positions) for side in ('client','server'))):
                        raise RuntimeError('Empty native baseline changed across capture')
                writes = (('palette',workspace.WRITE),('direct',DIRECT_WRITE)) if args.native_write_compare else (('palette',workspace.WRITE),)
                for write_mode,write_code in writes:
                    requested_frames=check.run(CAMERA_STATE)['render_events']
                    write_receipt=base.run(client,write_code % native.wire(cells),True)
                    if args.native_write_compare:
                        report['native_write_receipts'][write_mode+'_'+label]={'request_render_events':requested_frames,'write':write_receipt}
                        save()
                    settled=check.wait('native write rendered '+write_mode+'/'+label,
                        lambda camera: camera['render_events']>=requested_frames+2 and camera_matches(camera,fixed_camera),
                        lambda: check.run(CAMERA_STATE))
                    if args.native_write_compare:
                        report['native_write_receipts'][write_mode+'_'+label]['settled_camera']=settled; save()
                    initial = native_state()
                    if any(not native.matches(initial[side], expected, observed_positions) for side in ('client', 'server')):
                        raise RuntimeError('Exact native original source readback differs: ' + label)
                    identity=('native_'+write_mode+'_' if args.native_write_compare else 'native_')+label
                    frame(identity, native_state)
                    captured = report['states'][identity]
                    if any(not native.matches(captured[point][side], expected, observed_positions)
                           for point in ('before', 'after') for side in ('client', 'server')):
                        raise RuntimeError('Native reference changed across original water capture: ' + label)
                base.run(client, workspace.WRITE % native.wire([]), True)
                check.run('s.origin=%r\ns.opacity=1.\ns.projection_outline=False\n_result=True' % (document_origin,))
                for missing in ((False,) if priority_mode else (False, True)):
                    route = 'missing' if missing else 'full'
                    if args.native_write_compare:
                        request_frames=check.run(CAMERA_STATE)['render_events']
                        report['full_render_requests'][label]=request_frames; save()
                    check.run('s.projection_missing=%r\nb.project()\n_result=True' % missing)
                    def read_world():
                        value=check.run(WORLD_STATE)
                        if args.native_write_compare:
                            value['camera']=check.run(CAMERA_STATE)
                            report['full_wait_reads'].setdefault(label, []).append(value); save()
                        return value
                    check.wait(route + '/' + label, lambda value: workspace.world_ready(value) and
                        (not args.native_write_compare or value['camera']['render_events']>=request_frames+2),read_world)
                    time.sleep(.3)
                    frame(route + '_' + label, lambda: dict(check.run(WORLD_STATE), camera=check.run(CAMERA_STATE)))
                    check.run('b.stop_projection()\n_result=True')
            if args.priority_world_alpha:
                priority_alpha()
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            if priority_mode:
                client.cleaning = True
            actions = [('projection_stop', lambda: check.run('b.stop_projection()\n_result=True'))]
            if world_saved:
                actions.extend((('native_clear', lambda: base.run(client, workspace.guarded_cleanup(
                    workspace.WRITE % native.wire([]), '_liquid_pose_world'), True)),
                    ('flow_restore', lambda: base.run(client, workspace.guarded_cleanup(
                        workspace.FLOW % False, '_liquid_pose_world'), True)),
                    ('world_restore', lambda: base.run(client, workspace.QUALIFICATION_CLEAN_WORLD, True))))
            if visual_saved:
                actions.append(('camera_restore', lambda: check.run(workspace.guarded_cleanup(
                    visuals.camera_restore_code(False), '_blueprint_visual_saved'))))
                actions.append(('visual_restore', lambda: check.run(workspace.guarded_cleanup('saved=sys._blueprint_visual_saved\ns.origin=saved["origin"]\n'
                    's.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                    'del sys._blueprint_visual_saved\n_result=True', '_blueprint_visual_saved'))))
            if installed:
                def restore_scene():
                    if check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                        check.wait('close side Scene', lambda row: not row['open'] and not row['transition'], check.navigation)
                    return check.run(workspace.guarded_cleanup('''if hasattr(sys,'_liquid_scene_saved_profile'):
 had,old=sys._liquid_scene_saved_profile
 if had:s.liquid_profile=old
 elif hasattr(s,'liquid_profile'):del s.liquid_profile
 del sys._liquid_scene_saved_profile
''' + blueprints.RESTORE, '_blueprint_qa_saved'))
                actions.append(('scene_restore', restore_scene))
                if priority_mode:
                    actions.append(('alpha_source_restore', lambda: check.run(
                        "if hasattr(sys,'_liquid_workspace_source'):del sys._liquid_workspace_source\n_result=True")))
            if environment_attempted:
                actions.append(('environment_restore', lambda: base.run(client, workspace.guarded_cleanup(
                    base.RESTORE_ENVIRONMENT, '_context_environment_saved'), True)))
            if frame_observer_installed:
                actions.append(('render_observer_removed', lambda: check.run(FRAME_REMOVE)))
            for label, action in actions:
                try:
                    report[label] = action()
                except Exception as error:
                    report['cleanup_errors'].append('%s: %s: %s' % (label, type(error).__name__, error))
                try:
                    save()
                except OSError as error:
                    report['cleanup_errors'].append('receipt persistence: %s: %s' % (type(error).__name__, error))
            report['restored'] = not report['cleanup_errors']
            save()
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'], 'captures': len(report['captures'])}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
