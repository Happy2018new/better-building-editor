"""Bounded owned h0 native/projection phase; the caller owns startup and cleanup."""
import ast
from collections import deque
import hashlib
import json
import math
import os
from pathlib import Path
from types import ModuleType

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
FOCUS = (1, 1, 1)
CROP = (498, 276, 1495, 828)
SIZE = (1994, 1105)
KINDS = ('covered', 'snow', 'plant', 'blank')


def constants(path, names):
    tree = ast.parse(Path(path).read_bytes())
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    values[target.id] = ast.literal_eval(node.value)
    if set(values) != set(names):
        raise ValueError('Required frozen snippets are unavailable')
    return values


def helpers(path, names):
    tree = ast.parse(Path(path).read_bytes())
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in nodes} != set(names):
        raise ValueError('Required frozen pixel helpers are unavailable')
    scope = {'Image': Image, 'ImageDraw': ImageDraw, 'deque': deque}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)
    return {name: scope[name] for name in names}


def save(path, value):
    temporary = Path(path).with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    temporary.replace(path)


def palette_matches(data, kind):
    expected = 'minecraft:air' if kind == 'blank' else (
        'minecraft:snow_layer' if kind in ('covered', 'snow') else 'minecraft:poppy')
    front, back = data['common'], data['extra']
    if any(row[0] not in ('minecraft:air', expected) for row in front):
        return False
    expected_aux = 8 if kind == 'covered' else 0
    if kind != 'blank' and not any(row[0] == expected and row[1] == expected_aux for row in front):
        return False
    extra = 'minecraft:poppy' if kind == 'covered' else 'minecraft:air'
    return (all(row[0] in ('minecraft:air', extra) for row in back) and
            (kind != 'covered' or any(row[0] == extra and row[1] == 0 for row in back)))


def camera_matches(value, expected, player):
    return (all(abs(value['position'][i] - expected['position'][i]) < .01 for i in range(3)) and
            all(abs((value['rotation'][i] - expected['rotation'][i] + 180.) % 360. - 180.) < .01 for i in range(3)) and
            all(abs(value['player'][i] - player[i]) < .1 for i in range(3)))


def forward_cosine(value, center):
    forward = value['forward']
    direction = [center[i] - value['position'][i] for i in range(3)]
    if not all(math.isfinite(axis) for vector in (forward, direction) for axis in vector):
        raise ValueError('Actual camera forward or target direction is not finite')
    denominator = math.sqrt(sum(axis * axis for axis in forward) * sum(axis * axis for axis in direction))
    if denominator <= 0:
        raise ValueError('Actual camera forward or target direction has no length')
    return sum(forward[i] * direction[i] for i in range(3)) / denominator


def placement_matches(value, origin, player):
    """Validate physical actor readback plus acknowledged owner offset submissions."""
    anchor = (player[0], player[1] + 1., player[2])
    if not value['mesh'] or not value['offsets'] or value['actor'] != value['mesh'][0]:
        return False
    if tuple(value['mesh'][2]) != tuple(origin) or tuple(value['session_origin']) != tuple(origin):
        return False
    for actual in (value['actor_position'], value['mesh'][3], value['shader_anchor']):
        if actual is None or not all(math.isfinite(axis) for axis in actual):
            return False
        if any(abs(actual[i] - anchor[i]) >= .01 for i in range(3)):
            return False
    for part in value['offsets']:
        record = part['native_submission']
        if not record or record.get('result') is not True:
            return False
        offset, chunk, actual = record['offset'], part['chunk'], value['actor_position']
        if not all(math.isfinite(axis) for axis in offset):
            return False
        restored_origin = (actual[0] - offset[0] - .5 - chunk[0],
                           actual[1] + offset[1] - chunk[1],
                           actual[2] - offset[2] - .5 - chunk[2])
        if any(abs(restored_origin[i] - origin[i]) >= .01 for i in range(3)):
            return False
    return all(abs(value['player'][i] - player[i]) < .1 for i in range(3))


def placement_signature(value):
    return {'actor': value['actor'], 'mesh': value['mesh'], 'actor_position': value['actor_position'],
            'offsets': [{'model': part['model'], 'chunk': part['chunk'], 'context': part['context'],
                        'offset': part['native_submission']['offset'], 'result': part['native_submission']['result']}
                       for part in value['offsets']]}


def changed(first, second, threshold=20):
    delta = ImageChops.difference(first, second).split()
    maximum = ImageChops.lighter(ImageChops.lighter(delta[0], delta[1]), delta[2])
    return maximum.point(lambda value: 255 if value > threshold else 0)


def capture_schedule(plan):
    if plan.get('plant_candidate') is None:
        return [(mode, kind) for mode in ('native', 'projection') for kind in KINDS]
    if plan.get('capture_schedule') != 'candidate_positive_first':
        raise ValueError('Centered candidate requires plant positive controls first')
    return [('native', 'plant'), ('native', 'blank'), ('projection', 'plant'), ('projection', 'blank'),
            ('native', 'snow'), ('native', 'covered'), ('projection', 'snow'), ('projection', 'covered')]


def plant_positive_controls(paths, roi, output):
    results = {}
    for mode in ('native', 'projection'):
        with Image.open(paths[mode]['plant']) as plant, Image.open(paths[mode]['blank']) as blank:
            mask = ImageChops.multiply(changed(plant.convert('RGB').crop(CROP), blank.convert('RGB').crop(CROP)), roi)
        path = output / (mode + '_early_plant_mask.png')
        mask.save(path)
        count = mask.histogram()[255]
        results[mode] = {'plant_pixels': count, 'minimum_pixels': 80, 'passed': count >= 80,
                         'mask': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    return {'modes': results, 'passed': all(row['passed'] for row in results.values()),
            'geometry_fidelity_accepted': False, 'production_acceptance': False}


def clear_native_for_projection(run, wait, reference, palette_code):
    mutation = run(reference['NATIVE_MUTATE'] % ('poppy', 'blank', 0), True)
    palette = wait('native target blank before projection capture',
                   lambda value: palette_matches(value, 'blank'), lambda: run(palette_code))
    if mutation['front']['name'] != 'minecraft:air':
        raise AssertionError(('Native target was not cleared before projection capture', mutation))
    return {'mutation': mutation, 'palette_before': palette, 'support_preserved_by_target_only_mutation': True}


def analyze_controls(paths, roi, output):
    results, frames = {}, {}
    for mode in ('native', 'projection'):
        images = {kind: Image.open(paths[mode][kind]).convert('RGB').crop(CROP) for kind in KINDS}
        frames[mode] = images
        plant = ImageChops.multiply(changed(images['plant'], images['blank']), roi)
        snow = ImageChops.multiply(changed(images['snow'], images['blank']), roi)
        contribution = ImageChops.multiply(changed(images['covered'], images['snow']), roi)
        record = {'plant_pixels': plant.histogram()[255], 'snow_pixels': snow.histogram()[255],
                  'covered_minus_snow_pixels': contribution.histogram()[255],
                  'plant_bounds': plant.getbbox(), 'snow_bounds': snow.getbbox(),
                  'contribution_bounds': contribution.getbbox(), 'positive_control': plant.histogram()[255] >= 80}
        for name, mask in (('plant', plant), ('snow', snow), ('contribution', contribution)):
            path = output / (mode + '_' + name + '_mask.png')
            mask.save(path)
            record[name + '_mask'] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        results[mode] = record
    comparisons = {}
    for kind in ('plant', 'snow', 'covered'):
        native = ImageChops.multiply(changed(frames['native'][kind], frames['native']['blank']), roi)
        actual = ImageChops.multiply(changed(frames['projection'][kind], frames['projection']['blank']), roi)
        expected_count, actual_count = native.histogram()[255], actual.histogram()[255]
        recall = ImageChops.multiply(native, actual.filter(ImageFilter.MaxFilter(7))).histogram()[255] / max(1, expected_count)
        precision = ImageChops.multiply(actual, native.filter(ImageFilter.MaxFilter(7))).histogram()[255] / max(1, actual_count)
        comparisons[kind] = {'native_pixels': expected_count, 'projection_pixels': actual_count,
                             'recall_3px': recall, 'precision_3px': precision,
                             'diagnostic_match': expected_count >= 80 and recall >= .75 and precision >= .75
                              and .5 <= actual_count / max(1, expected_count) <= 2.}
    return {'modes': results, 'native_projection': comparisons,
            'positive_controls_passed': all(value['positive_control'] for value in results.values()),
            'diagnostic_matches': all(value['diagnostic_match'] for value in comparisons.values()),
            'production_acceptance': False, 'native_mesh_or_offset_authority': False}


PALETTE = '''target=%r
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(target,target,False)
data=palette.SerializeBlockPalette() if palette is not None else {}
_result=json.dumps(dict((key,[[value[0],value[1],indices] for value,indices in data.get(key,{}).items()]) for key in ('common','extra')))
'''
CAMERA_READ = '''cam=b.factory.CreateCamera(b.level)
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'forward':cam.GetForward(),'render_events':getattr(getattr(sys,'_snow_h0_render_frames',None),'count',None),
 'pitch_lock':cam.IsModCameraLockPitch(),'yaw_lock':cam.IsModCameraLockYaw(),
 'player':b.player_position.GetFootPos(),'fov':cam.GetFov(),
 'screen':b.factory.CreateGame(b.level).GetScreenSize()})
'''
CAMERA_SET = '''center=%r
position=%r
direction=api.GetRotFromDir(tuple(center[i]-position[i] for i in range(3)))
yaw_adjustment=%r
rotation=(direction[0],direction[1]+yaw_adjustment,0.)
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position) and cam.SetCameraRotation(rotation)
_result=json.dumps({'target':center,'position':position,'rotation':rotation,
 'sdk_GetRotFromDir':direction,'yaw_adjustment':yaw_adjustment,
 'render_events_at_request':getattr(sys._snow_h0_render_frames,'count',None)})
'''
SERVER_PREFLIGHT = '''import json,sys
import mod.server.extraServerApi as server_api
from modern_projection.server_system import WorldAdapter
players=server_api.GetPlayerList()
assert len(players)==1, ('Owned fixture requires one player',players)
player=players[0]
adapter=WorldAdapter(player)
rows=[]
for pos in %r:
 assert -64<=pos[1]<320
 front=adapter.info.GetBlockNew(pos,adapter.dimension)
 assert front and front['name']=='minecraft:air', ('Fixed target must be loaded air',pos,front)
 palette=adapter.palette_block.GetBlockPaletteBetweenPos(adapter.dimension,pos,pos,False)
 assert palette is not None, ('Fixed terrain palette unavailable',pos)
 data=palette.SerializeBlockPalette()
 assert all(value[0]=='minecraft:air' for key in ('common','extra') for value in data.get(key,{})), (pos,data)
 rows.append({'position':pos,'front':front})
_result=json.dumps({'cells':rows,'dimension':adapter.dimension,
 'player_foot':adapter.factory.CreatePos(player).GetFootPos(),
 'player_flying':adapter.factory.CreateFly(player).IsPlayerFlying()})
'''


FRAME_INSTALL = '''assert not hasattr(sys,'_snow_h0_render_frames'), 'Previous h0 render observer needs cleanup'
class SnowH0RenderFrames(object):
 def __init__(self):self.count=0
 def tick(self,unused):self.count+=1
probe=SnowH0RenderFrames()
sys._snow_h0_render_frames=probe
owner.ListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'GameRenderTickEvent',probe,probe.tick)
_result=json.dumps({'render_events':probe.count,'source':'actual GameRenderTickEvent'})
'''

OFFSET_INSTALL = '''assert not hasattr(sys,'_snow_h0_offsets'), 'Previous h0 offset probe needs cleanup'
class SnowH0OffsetJournal(object):
 def __init__(self,factory):self.factory=factory;self.probe=None;self.records=[];self.offsets={}
journal=SnowH0OffsetJournal(b.factory)
sys._snow_h0_offsets=journal
class SnowH0ActorRenderProbe(object):
 def __init__(self,target,entity):self.target=target;self.entity=entity
 def __getattr__(self,name):return getattr(self.target,name)
 def submit(self,method,args,kwargs):
  name,offset=args[:2]
  row={'actor':self.entity,'model':name,'method':method,'offset':offset,
       'render_events':getattr(sys._snow_h0_render_frames,'count',None),'attempted':True}
  journal.records.append(row)
  try:
   result=getattr(self.target,method)(*args,**kwargs)
   row['result']=result
   if result is True:journal.offsets[(self.entity,name)]=row
   return result
  except Exception as error:
   row['error']=str(error)
   raise
 def AddActorBlockGeometry(self,*args,**kwargs):return self.submit('AddActorBlockGeometry',args,kwargs)
 def SetActorBlockGeometryOffset(self,*args,**kwargs):return self.submit('SetActorBlockGeometryOffset',args,kwargs)
class SnowH0OffsetFactoryProbe(object):
 def __init__(self,target):self.target=target
 def __getattr__(self,name):return getattr(self.target,name)
 def CreateActorRender(self,entity):return SnowH0ActorRenderProbe(self.target.CreateActorRender(entity),entity)
journal.probe=SnowH0OffsetFactoryProbe(b.factory)
b.factory=journal.probe
_result=json.dumps({'installed':True,'native_offset_getter_available_from_official_docs':False,
 'evidence':'actual native Add/Set call arguments and boolean acknowledgments, not GPU readback'})
'''
PLACEMENT_READ = '''mesh=b.projection_mesh
parts=b.context_models.get(mesh[1],()) if mesh else ()
journal=sys._snow_h0_offsets
_result=json.dumps({'actor':b.entity,'mesh':mesh,'session_origin':s.origin,
 'actor_position':b.factory.CreatePos(b.entity).GetPos() if b.entity else None,
 'shader_anchor':getattr(b.projection_shader,'anchor',None),
 'player':b.player_position.GetFootPos(),'render_events':sys._snow_h0_render_frames.count,
 'offsets':[{'model':name,'chunk':chunk,'context':context,'native_submission':journal.offsets.get((b.entity,name))} for name,chunk,context in parts],
 'native_submission_count':len(journal.records),'evidence':'actual actor GetPos plus native offset submission acknowledgment; no public offset getter'})
'''
OFFSET_REMOVE = '''if hasattr(sys,'_snow_h0_offsets'):
 journal=sys._snow_h0_offsets
 if b.factory is journal.probe:b.factory=journal.factory
 assert b.factory is not journal.probe
 _result=json.dumps({'removed':True,'native_offset_submissions':journal.records})
 del sys._snow_h0_offsets
else:_result=json.dumps({'removed':True,'installation_not_observed':True})
'''


PLANT_PROFILE_RESTORE = '''from modern_projection.projection.plant_position import POSITION_PLANT_PROXIES
if hasattr(sys,'_snow_h0_plant_profiles'):
 POSITION_PLANT_PROXIES.clear()
 POSITION_PLANT_PROXIES.update(sys._snow_h0_plant_profiles)
 del sys._snow_h0_plant_profiles
_result=json.dumps({'default_empty':not POSITION_PLANT_PROXIES,'journal_absent':not hasattr(sys,'_snow_h0_plant_profiles')})
'''


def candidate_profile_install_code(candidate):
    if candidate is None:
        return None
    if (candidate.get('identifier') != 'modern_projection:diagnostic_centered_poppy' or
            candidate.get('alpha_top_height') != .6875 or
            candidate.get('production_default_enabled') is not False or
            candidate.get('xz_translation') != [0., 0.] or
            candidate.get('unit_cross_height') != 1. or
            candidate.get('geometry_fit_allowed') is not False or
            candidate.get('native_random_offset_applied') is not False):
        raise ValueError('Unsupported diagnostic plant candidate contract')
    return '''from modern_projection.projection.plant_position import POSITION_PLANT_PROXIES
assert not POSITION_PLANT_PROXIES, 'Default plant profiles must stay empty'
assert not hasattr(sys,'_snow_h0_plant_profiles')
sys._snow_h0_plant_profiles=dict(POSITION_PLANT_PROXIES)
POSITION_PLANT_PROXIES[('minecraft:poppy',0)]=lambda position:(%r,.6875)
_result=json.dumps({'installed':True,'default_before':False,'identifier':%r,
 'xz_translation':[0.,0.],'native_random_offset_applied':False,'production_acceptance':False})
''' % (candidate['identifier'], candidate['identifier'])


def run_phase(plan, host, session, output, work_deadline, restore_deadline, health):
    output = Path(output)
    receipt = output / 'h0-phase.json'
    result = {'schema': 1, 'started': True, 'completed': False, 'production_acceptance': False,
              'session': session['id'], 'condition': plan['texture_condition'], 'rows': [],
              'cleanup_errors': [], 'mutation_attempted': False}
    save(receipt, result)
    reference = constants(plan['files']['snow_reference']['path'],
                          ('LOAD', 'NATIVE_SETUP', 'NATIVE_MUTATE', 'NATIVE_SNOW', 'NATIVE_CLEANUP'))
    blueprint = constants(plan['files']['blueprint_reference']['path'], ('CLIENT', 'INSTALL_PROBE', 'RESTORE'))
    visual = constants(plan['files']['visual_reference']['path'], ('SAVE_VISUAL', 'PROJECTION_STATUS', 'PROJECTION_SOURCE'))
    module = ModuleType('frozen_h0_mcdk')
    module.__file__ = plan['files']['mcdk_client']['path']
    exec(compile(Path(module.__file__).read_bytes(), module.__file__, 'exec'), module.__dict__)
    environment = {key: os.environ.get(key) for key in ('MCDEV_SESSION_FILE', 'MCDEV_OWNER', 'MCDEV_MCP_URL')}
    os.environ.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=session['owner'], MCDEV_MCP_URL=session['mcp_url'])
    stage_deadline = min(work_deadline, host.now() + 10)
    restoring = False

    class BoundedClient(module.Client):
        def _post(self, *args, **kwargs):
            if not restoring:
                health()
            self.timeout = min(3., stage_deadline - host.now())
            if self.timeout <= 0:
                raise TimeoutError('H0 SDK stage deadline exhausted')
            return super()._post(*args, **kwargs)

        def close(self):
            self.timeout = max(.001, min(1., restore_deadline - host.now()))
            super().close()

    client = None
    mutation_attempted = False
    player = None
    pose = None
    visual_saved = None
    target = tuple(plan['target'])
    support = tuple(plan['support'])
    origin = tuple(plan['projection_origin'])
    center = tuple(axis + .5 for axis in target)
    position = tuple(center[i] + plan['public_camera_offset'][i] for i in range(3))
    palette_code = PALETTE % (target,)
    camera_code = None
    preflight_code = SERVER_PREFLIGHT % ((target, support),)
    frame_observer_installed = False
    offset_probe_installed = False

    def run(code, server=False):
        value = module.return_value(client.call('execute_code', {'code': code if server else blueprint['CLIENT'] + code,
                                                                 'is_client': not server, 'direct_return': True}))
        return json.loads(value) if isinstance(value, str) else value

    def stage(seconds):
        nonlocal stage_deadline
        stage_deadline = min(work_deadline, host.now() + seconds)
        if stage_deadline <= host.now():
            raise TimeoutError('H0 work deadline exhausted')

    def wait(label, predicate, read):
        value = None
        while host.now() < stage_deadline:
            if not restoring:
                health()
            value = read()
            if predicate(value):
                return value
            host.sleep(min(.1, max(0, stage_deadline - host.now())))
        raise TimeoutError(label + ': ' + str(value))

    def capture(label):
        health()
        current = run(CAMERA_READ)
        before = wait('actual render frame after state/camera request',
                      lambda value: value['render_events'] >= current['render_events'] + 2,
                      lambda: run(CAMERA_READ))
        if not camera_matches(before, pose, player):
            raise AssertionError(('Camera or player drift before capture', before, pose, player))
        baseline = result.get('fixed_camera_readback')
        if baseline and (before['screen'] != baseline['screen'] or abs(before['fov'] - baseline['fov']) > .01):
            raise AssertionError(('H0 FOV/screen drift across states', baseline, before))
        seconds = min(5., stage_deadline - host.now())
        if seconds <= 0:
            raise TimeoutError('H0 stage has no capture budget')
        path = output / (label + '.png')
        row = {'label': label, 'path': str(path), 'first_capture_attempt_locked': True,
               'before': before, 'forward_cosine_before': forward_cosine(before, center), 'elapsed_before': host.now()}
        result['rows'].append(row)
        save(receipt, result)
        if row['forward_cosine_before'] <= .99:
            raise AssertionError(('Actual GetForward alignment does not exceed 0.99 before capture', row))
        observation = host.observe(session, plan, path, seconds)
        row['capture'] = observation
        save(receipt, result)
        detail = json.loads(observation['stdout']) if observation.get('stdout') else {}
        if not detail.get('reliable') or detail.get('state_before') != 'ready' or detail.get('state_after') != 'ready':
            raise AssertionError(('First h0 capture failed', label, observation))
        if (detail['pixels']['width'], detail['pixels']['height']) != SIZE:
            raise AssertionError('H0 physical PNG size changed; no resize or recrop')
        after = run(CAMERA_READ)
        row['after'] = after
        row['forward_cosine_after'] = forward_cosine(after, center)
        if row['forward_cosine_after'] <= .99:
            raise AssertionError(('Actual GetForward alignment does not exceed 0.99 after capture', row))
        if not camera_matches(after, pose, player) or abs(after['fov'] - before['fov']) > .01 or after['screen'] != before['screen']:
            raise AssertionError(('H0 camera/FOV/screen/player drift after capture', before, after))
        save(receipt, result)
        return path

    try:
        candidate_install = candidate_profile_install_code(plan.get('plant_candidate'))
        client = BoundedClient(timeout=3)
        client.__enter__()
        result['preflight'] = run(preflight_code, True)
        player = result['preflight']['player_foot']
        mutation_attempted = result['mutation_attempted'] = True
        save(receipt, result)
        run(blueprint['INSTALL_PROBE'])
        if candidate_install is not None:
            result['plant_candidate'] = run(candidate_install)
            save(receipt, result)
        visual_saved = run(visual['SAVE_VISUAL'] + '''sys._blueprint_visual_saved['fov']=cam.GetFov()
_result=json.dumps(sys._blueprint_visual_saved)
''')
        result['original_player_follow_camera'] = visual_saved
        save(receipt, result)
        result['client_chunk_event_observation'] = run('''dimension=%r
target=%r
observed=list(owner.projection_loaded_chunks)
_result=json.dumps({'source':'existing ChunkLoadedClientEvent/ChunkAcquireDiscardedClientEvent set',
 'observed_chunks':len(observed),'target_chunk':[target[0]//16,target[2]//16],
 'target_section_y':target[1]//16,'matching_xz':[row for row in observed if row[0]==dimension and row[1]==target[0]//16 and row[2]==target[2]//16],
 'native_section_mesh_ready_proven':False})
''' % (result['preflight']['dimension'], target))
        save(receipt, result)
        frame_observer_installed = True
        result['render_frame_observer'] = run(FRAME_INSTALL)
        offset_probe_installed = True
        result['native_offset_probe'] = run(OFFSET_INSTALL)
        result['native_setup'] = run(reference['NATIVE_SETUP'] % (target,), True)
        before_camera = run(CAMERA_READ)
        result['camera_before_request'] = before_camera
        # A fresh owned cold session starts in player-follow mode; no movement is applied.
        stage(12)
        result['camera_direction_candidates'] = []
        for yaw_adjustment in (180., 0.):
            candidate = {'yaw_adjustment': yaw_adjustment, 'pose_request_attempted': True,
                         'predeclared_sdk_semantics': True, 'readbacks': [], 'captures_before_selection': 0}
            result['camera_direction_candidates'].append(candidate)
            save(receipt, result)
            candidate_code = CAMERA_SET % (center, position, yaw_adjustment)
            candidate['pose'] = run(candidate_code)
            save(receipt, result)

            def read_candidate():
                value = run(CAMERA_READ)
                candidate['readbacks'].append(value)
                save(receipt, result)
                return value

            actual_camera = wait('camera candidate readback after actual render events',
                                lambda value: value['render_events'] >= candidate['pose']['render_events_at_request'] + 2 and
                                              camera_matches(value, candidate['pose'], player), read_candidate)
            candidate['forward_cosine'] = forward_cosine(actual_camera, center)
            candidate['selected'] = candidate['forward_cosine'] > .99
            save(receipt, result)
            if candidate['selected']:
                pose, camera_code = candidate['pose'], candidate_code
                result['camera'] = pose
                result['actual_camera_direction'] = {'readback': actual_camera, 'target': center,
                    'forward_cosine': candidate['forward_cosine'], 'actual_GetForward': True,
                    'predeclared_yaw_candidates': [180., 0.], 'minimum_cosine_exclusive': .99,
                    'qualification_capture_started': False}
                save(receipt, result)
                break
        if camera_code is None:
            raise AssertionError(('Neither predeclared SDK camera direction reaches cosine >0.99', result['camera_direction_candidates']))
        qualification = run('base=%r\n' % (target,) + '''
cam=b.factory.CreateCamera(b.level)
points=[tuple(base[i]+delta[i] for i in range(3)) for delta in ((x,y,z) for x in (0.,1.) for y in (0.,1.) for z in (0.,1.))]
native=[cam.WorldToScreenPoint(*point) for point in points] if hasattr(cam,'WorldToScreenPoint') else None
_result=json.dumps({'points':points,'native':native,'screen':b.factory.CreateGame(b.level).GetScreenSize(),'fov':cam.GetFov(),'version':api.GetMinecraftVersion()})
''')
        roi = Image.new('L', (CROP[2] - CROP[0], CROP[3] - CROP[1]))
        if qualification['native'] is not None:
            values = qualification['native']
            if len(values) != 8 or not all(value['isInScreen'] and 0 <= value['depth'] <= 1 and
                       all(math.isfinite(value[key]) for key in ('screenX', 'screenY', 'depth')) for value in values):
                raise AssertionError('Actual world-cell projection failed qualification')
            convex_hull = helpers(plan['files']['snow_reference']['path'], ('convex_hull',))['convex_hull']
            scale = (SIZE[0] / qualification['screen'][0], SIZE[1] / qualification['screen'][1])
            points = convex_hull((value['screenX'] * scale[0] - CROP[0], value['screenY'] * scale[1] - CROP[1]) for value in values)
            ImageDraw.Draw(roi).polygon(points, fill=255)
            qualification.update(method='actual_public_WorldToScreenPoint', polygon=points)
        else:
            run('''import json,sys
from modern_projection.server_system import WorldAdapter
saved=sys._snow_visibility_native
adapter=WorldAdapter(saved['player'])
assert adapter.info.SetBlockNew(saved['target'],{'name':'minecraft:stone','aux':0},0,saved['dimension'],True,False)
_result=True
''', True)
            wait('native stone replication', lambda value: any(row[0] == 'minecraft:stone' for row in value['common']), lambda: run(palette_code))
            stone = capture('qualification_stone')
            run(reference['NATIVE_MUTATE'] % ('poppy', 'blank', 0), True)
            wait('qualification blank replication', lambda value: palette_matches(value, 'blank'), lambda: run(palette_code))
            blank = capture('qualification_blank')
            with Image.open(stone) as first, Image.open(blank) as second:
                signal = changed(first.convert('RGB').crop(CROP), second.convert('RGB').crop(CROP))
            pixel_helpers = helpers(plan['files']['camera_reference']['path'], ('largest_component', 'fill_enclosed_holes'))
            roi = pixel_helpers['fill_enclosed_holes'](pixel_helpers['largest_component'](signal))
            qualification.update(method='same_session_native_stone_blank_cell_silhouette',
                                 stone=str(stone), blank=str(blank), pixels=roi.histogram()[255],
                                 bounds=roi.getbbox(), analytical_projection_or_fov_fit=False)
            result['qualification'] = qualification
            save(receipt, result)
            signal.save(output / 'qualification-difference.png')
            roi.save(output / 'qualification-component.png')
            if roi.histogram()[255] < 1000:
                raise AssertionError('Same-session native stone cell lacks 1000 observable pixels')
        roi_path = output / 'qualified-cell-roi.png'
        roi.save(roi_path)
        qualification.update(roi=str(roi_path), roi_sha256=hashlib.sha256(roi_path.read_bytes()).hexdigest())
        result['qualification'] = qualification
        result['fixed_camera_readback'] = run(CAMERA_READ)
        paths = {'native': {}, 'projection': {}}
        def capture_native(kind):
            stage(6)
            run('b.stop_projection()\n_result=True')
            native = run(reference['NATIVE_MUTATE'] % ('poppy', kind, 0), True)
            if kind == 'covered':
                native = run(reference['NATIVE_SNOW'] % 1, True)
                if native['result'] is not True:
                    raise AssertionError(('SetSnowBlock failed', native))
            expected = 'minecraft:air' if kind == 'blank' else ('minecraft:snow_layer' if kind in ('covered', 'snow') else 'minecraft:poppy')
            if native['front']['name'] != expected:
                raise AssertionError(('Native requested front mismatch', native))
            if kind in ('covered', 'snow') and (native['states']['height'] != 0 or bool(native['states']['covered_bit']) != (kind == 'covered')):
                raise AssertionError(('Native requested snow state mismatch', native))
            replicated = wait('native ' + kind + ' palette', lambda value: palette_matches(value, kind), lambda: run(palette_code))
            host.sleep(min(.25, max(0, stage_deadline - host.now())))
            path = capture('native_' + kind + '_h0')
            palette_after = run(palette_code)
            if not palette_matches(palette_after, kind):
                raise AssertionError(('Native palette drift during capture', kind, palette_after))
            paths['native'][kind] = path
            result['rows'][-1].update(kind=kind, mode='native', readback=native,
                                      client_palette=replicated, client_palette_after=palette_after)
            save(receipt, result)
        def capture_projection(kind):
            stage(8)
            journal = {'kind': kind, 'projection_request_attempted': False}
            result.setdefault('projection_state_journals', []).append(journal)
            save(receipt, result)
            run('b.stop_projection()\n_result=True')
            journal['native_target_cleared'] = clear_native_for_projection(run, wait, reference, palette_code)
            save(receipt, result)
            source = run(reference['LOAD'] % ('poppy', 0, kind))
            journal['source'] = source
            save(receipt, result)
            if kind != 'blank':
                journal['projection_request_attempted'] = True
                save(receipt, result)
                run('s.origin=%r\ns.opacity=1.\ns.projection_missing=False\ns.projection_outline=False\nb.project()\n_result=True' % (origin,))
                status = wait('projection ' + kind, lambda value: value['active'] and value['ready'] and
                              not value['preparing'] and value['actors'] == 1 and value['mesh'] and value['scale'] is not None,
                              lambda: run(visual['PROJECTION_STATUS']))
                journal['initial_ready_status'] = status
                render_baseline = run(CAMERA_READ)['render_events']

                def read_placement():
                    value = run(PLACEMENT_READ)
                    journal.setdefault('placement_reads', []).append(value)
                    save(receipt, result)
                    return value

                placement = wait('ordinary render owner settles compensated projection placement',
                    lambda value: value['render_events'] >= render_baseline + 2 and placement_matches(value, origin, player),
                    read_placement)
                journal['settled_placement_before_capture'] = placement
                status = run(visual['PROJECTION_STATUS'])
                if not status['part_scales'] or any(scale != [1.,1.,1.] for scale in status['part_scales']):
                    raise AssertionError(('Projection part scale is not the declared unit scale',status))
                submitted = run(visual['PROJECTION_SOURCE'])
                journal['actual_native_palettes'] = run('''_result=json.dumps([row for row in sys._blueprint_qa_records
 if row['nonce']==sys._blueprint_qa_nonce and row['editor_id']==id(s.editor)
 and row['document_id']==id(s.editor.document)])
''')
                journal.update(status_before_capture=status, source_before_capture=submitted)
                save(receipt, result)
                if not (submitted['work_current'] and submitted['cache_current'] and submitted['origin_current'] and
                        submitted['editor_id'] == source['editor_id'] and submitted['document_id'] == source['document_id'] and
                        submitted['fixture'] == 'snow.visibility.poppy.' + kind + '.0'):
                    raise AssertionError(('Projection source stale', submitted, source))
            else:
                status = run(visual['PROJECTION_STATUS'])
                submitted = None
                if status['active'] or status['actors']:
                    raise AssertionError(('Blank projection still active', status))
            run(camera_code)
            host.sleep(min(.25, max(0, stage_deadline - host.now())))
            path = capture('projection_' + kind + '_h0')
            native_after = run(palette_code)
            journal['native_target_cleared']['palette_after'] = native_after
            save(receipt, result)
            if not palette_matches(native_after, 'blank'):
                raise AssertionError(('Native target became occupied during projection capture', kind, native_after))
            final_status = run(visual['PROJECTION_STATUS'])
            final_source = run(visual['PROJECTION_SOURCE']) if kind != 'blank' else None
            journal.update(status_after_capture=final_status, source_after_capture=final_source)
            if kind != 'blank':
                final_placement = run(PLACEMENT_READ)
                journal['placement_after_capture'] = final_placement
                save(receipt, result)
                if not placement_matches(final_placement, origin, player):
                    raise AssertionError(('Compensated projection placement drift during capture', placement, final_placement))
                if placement_signature(final_placement) != placement_signature(placement):
                    raise AssertionError(('Projection physical actor/offset changed after settled baseline', placement, final_placement))
            if kind != 'blank' and any(final_source.get(key) != submitted.get(key) for key in
                         ('editor_id', 'document_id', 'fixture', 'nonce', 'serial', 'model', 'work_current', 'cache_current', 'origin_current')):
                raise AssertionError(('Projection source drift during capture', submitted, final_source))
            if final_status['actor'] != status['actor'] or final_status['mesh'] != status['mesh']:
                raise AssertionError(('Projection actor/mesh drift during capture', status, final_status))
            if kind != 'blank' and (final_status['parts'] != status['parts'] or
                    final_status['part_scales'] != status['part_scales'] or final_status['origin'] != status['origin']):
                raise AssertionError(('Projection logical origin/parts/scale drift during capture',status,final_status))
            paths['projection'][kind] = path
            result['rows'][-1].update(kind=kind, mode='projection', source=source, status=status,
                                      submitted=submitted, final_status=final_status, final_source=final_source)
            save(receipt, result)
        schedule = capture_schedule(plan)
        result['capture_schedule'] = [list(row) for row in schedule]
        save(receipt, result)
        for index, (mode, kind) in enumerate(schedule):
            (capture_native if mode == 'native' else capture_projection)(kind)
            if plan.get('plant_candidate') is not None and index == 3:
                result['early_plant_positive_controls'] = plant_positive_controls(paths, roi, output)
                save(receipt, result)
                if not result['early_plant_positive_controls']['passed']:
                    raise AssertionError('Centered candidate plant positive control failed; snow matrix not started')
        result['pixels'] = analyze_controls(paths, roi, output)
        if host.now() > work_deadline:
            raise TimeoutError('H0 measured work deadline exceeded')
        result['completed'] = True
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        restoring = True
        stage_deadline = restore_deadline
        if client is not None and mutation_attempted:
            try:
                cleanup = run('''import json,sys
if hasattr(sys,'_snow_visibility_native'):
''' + '\n'.join(' ' + line for line in reference['NATIVE_CLEANUP'].splitlines()) + '''
else:_result=json.dumps([])
''', True)
                result['native_cleanup'] = cleanup
                if any(value.get('clean') is False for value in cleanup):
                    result['cleanup_errors'].append('Native fixture/world cleanup readback failed')
            except Exception as error:
                result['cleanup_errors'].append('Native cleanup: ' + str(error))
            try:
                stage_deadline = min(restore_deadline, host.now() + 5.)
                restore = '''b.stop_projection()
if hasattr(sys,'_snow_h0_plant_profiles'):
 from modern_projection.projection.plant_position import POSITION_PLANT_PROXIES
 POSITION_PLANT_PROXIES.clear()
 POSITION_PLANT_PROXIES.update(sys._snow_h0_plant_profiles)
 del sys._snow_h0_plant_profiles
if hasattr(sys,'_blueprint_visual_saved'):
 saved=sys._blueprint_visual_saved
 s.origin=saved['origin']
 s.opacity=saved['opacity']
 s.projection_missing=saved['missing']
 s.projection_outline=saved['outline']
 cam=b.factory.CreateCamera(b.level)
 cam.ResetCameraPos()
 cam.UnDepartCamera()
 assert cam.SetCameraRotation(saved['camera_rot'])
 cam.LockModCameraPitch(saved['pitch_lock'])
 cam.LockModCameraYaw(saved['yaw_lock'])
 assert all(abs(b.player_position.GetFootPos()[i]-saved['player'][i])<.1 for i in range(3)), 'Player moved; no corrective teleport'
if hasattr(sys,'_blueprint_qa_saved'):
''' + '\n'.join(' ' + line for line in blueprint['RESTORE'].splitlines()) + '''
_result=json.dumps({'requested':True,'render_events':getattr(getattr(sys,'_snow_h0_render_frames',None),'count',None),
 'saved_camera_retained':hasattr(sys,'_blueprint_visual_saved')})
'''
                result['client_restore_requested'] = run(restore)
                save(receipt, result)
                if visual_saved is not None:
                    expected = {'position': visual_saved['camera_pos'], 'rotation': visual_saved['camera_rot']}
                    frame_baseline = result['client_restore_requested']['render_events']

                    def restored_readback():
                        value = run(CAMERA_READ)
                        result.setdefault('client_restore_reads', []).append(value)
                        save(receipt, result)
                        return value

                    def restored_after_render_events(value):
                        rendered = (not frame_observer_installed or
                                    value['render_events'] >= frame_baseline + 2)
                        return (rendered and camera_matches(value, expected, visual_saved['player']) and
                                value['pitch_lock'] == visual_saved['pitch_lock'] and
                                value['yaw_lock'] == visual_saved['yaw_lock'] and
                                abs(value['fov'] - visual_saved['fov']) < .01)

                    result['client_restored'] = wait('Original follow camera restoration after render events',
                                                    restored_after_render_events, restored_readback)
                    run("del sys._blueprint_visual_saved\n_result=True")
                    result['saved_camera_journal_cleared_after_verified_readback'] = True
                stage_deadline = restore_deadline
                after = run(preflight_code, True)
                result['post_restore'] = after
                if after['player_flying'] != result['preflight']['player_flying'] or any(abs(after['player_foot'][i] - player[i]) >= .1 for i in range(3)):
                    raise AssertionError('Player foot/flight drift; no corrective movement')
            except Exception as error:
                result['saved_camera_journal_retained_on_failure'] = visual_saved is not None
                result['cleanup_errors'].append('Client/player restoration: ' + str(error))
            finally:
                stage_deadline = restore_deadline
                if offset_probe_installed:
                    try:
                        result['native_offset_probe_removed'] = run(OFFSET_REMOVE)
                    except Exception as error:
                        result['cleanup_errors'].append('Native offset probe cleanup: ' + str(error))
                if frame_observer_installed:
                    try:
                        result['render_frame_observer_removed'] = run('''if hasattr(sys,'_snow_h0_render_frames'):
 probe=sys._snow_h0_render_frames
 owner.UnListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'GameRenderTickEvent',probe,probe.tick)
 del sys._snow_h0_render_frames
_result=True
''')
                    except Exception as error:
                        result['cleanup_errors'].append('Render observer cleanup: ' + str(error))
                if plan.get('plant_candidate') is not None:
                    try:
                        result['plant_candidate_restored'] = run(PLANT_PROFILE_RESTORE)
                        if result['plant_candidate_restored'] != {'default_empty': True, 'journal_absent': True}:
                            raise AssertionError('Diagnostic plant profile restoration failed')
                    except Exception as error:
                        result['cleanup_errors'].append('Plant candidate profile cleanup: ' + str(error))
        if client is not None:
            client.close()
        for key, previous in environment.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous
        save(receipt, result)
    return result
