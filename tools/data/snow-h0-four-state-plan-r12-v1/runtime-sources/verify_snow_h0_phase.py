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
TARGET = (6, 117, 6)
FOCUS = (1, 1, 1)
ORIGIN = (5, 116, 5)
POSITION = (4.5, 117.65, 4.)
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
            all(abs(value['rotation'][i] - expected['rotation'][i]) < .01 for i in range(3)) and
            all(abs(value['player'][i] - player[i]) < .1 for i in range(3)))


def changed(first, second, threshold=20):
    delta = ImageChops.difference(first, second).split()
    maximum = ImageChops.lighter(ImageChops.lighter(delta[0], delta[1]), delta[2])
    return maximum.point(lambda value: 255 if value > threshold else 0)


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


PALETTE = '''target=(6,117,6)
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(target,target,False)
data=palette.SerializeBlockPalette() if palette is not None else {}
_result=json.dumps(dict((key,[[value[0],value[1],indices] for value,indices in data.get(key,{}).items()]) for key in ('common','extra')))
'''
CAMERA_READ = '''cam=b.factory.CreateCamera(b.level)
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'player':b.player_position.GetFootPos(),'fov':cam.GetFov(),
 'screen':b.factory.CreateGame(b.level).GetScreenSize()})
'''
CAMERA_SET = '''center=(6.5,117.5,6.5)
position=(4.5,117.65,4.)
direction=api.GetRotFromDir(tuple(center[i]-position[i] for i in range(3)))
rotation=(direction[0],direction[1]+180.,0.)
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position) and cam.SetCameraRotation(rotation)
_result=json.dumps({'target':center,'position':position,'rotation':rotation})
'''
SERVER_PREFLIGHT = '''import json,sys
import mod.server.extraServerApi as server_api
from modern_projection.server_system import WorldAdapter
players=server_api.GetPlayerList()
assert len(players)==1, ('Owned fixture requires one player',players)
player=players[0]
adapter=WorldAdapter(player)
rows=[]
for pos in ((6,117,6),(6,116,6)):
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
            health()
            value = read()
            if predicate(value):
                return value
            host.sleep(min(.1, max(0, stage_deadline - host.now())))
        raise TimeoutError(label + ': ' + str(value))

    def capture(label):
        health()
        before = run(CAMERA_READ)
        if not camera_matches(before, pose, player):
            raise AssertionError(('Camera or player drift before capture', before, pose, player))
        seconds = min(5., stage_deadline - host.now())
        if seconds <= 0:
            raise TimeoutError('H0 stage has no capture budget')
        path = output / (label + '.png')
        row = {'label': label, 'path': str(path), 'first_capture_attempt_locked': True,
               'before': before, 'elapsed_before': host.now()}
        result['rows'].append(row)
        save(receipt, result)
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
        if not camera_matches(after, pose, player) or abs(after['fov'] - before['fov']) > .01 or after['screen'] != before['screen']:
            raise AssertionError(('H0 camera/FOV/screen/player drift after capture', before, after))
        save(receipt, result)
        return path

    try:
        client = BoundedClient(timeout=3)
        client.__enter__()
        result['preflight'] = run(SERVER_PREFLIGHT, True)
        player = result['preflight']['player_foot']
        mutation_attempted = result['mutation_attempted'] = True
        save(receipt, result)
        run(blueprint['INSTALL_PROBE'])
        run(visual['SAVE_VISUAL'])
        result['native_setup'] = run(reference['NATIVE_SETUP'] % (TARGET,), True)
        pose = run(CAMERA_SET)
        result['camera'] = pose
        # A fresh owned cold session starts in player-follow mode; no movement is applied.
        stage(12)
        qualification = run('''base=(6,117,6)
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
            wait('native stone replication', lambda value: any(row[0] == 'minecraft:stone' for row in value['common']), lambda: run(PALETTE))
            stone = capture('qualification_stone')
            run(reference['NATIVE_MUTATE'] % ('poppy', 'blank', 0), True)
            wait('qualification blank replication', lambda value: palette_matches(value, 'blank'), lambda: run(PALETTE))
            blank = capture('qualification_blank')
            with Image.open(stone) as first, Image.open(blank) as second:
                signal = changed(first.convert('RGB').crop(CROP), second.convert('RGB').crop(CROP))
            pixel_helpers = helpers(plan['files']['camera_reference']['path'], ('largest_component', 'fill_enclosed_holes'))
            roi = pixel_helpers['fill_enclosed_holes'](pixel_helpers['largest_component'](signal))
            if roi.histogram()[255] < 1000:
                raise AssertionError('Same-session native stone cell lacks 1000 observable pixels')
            qualification.update(method='same_session_native_stone_blank_cell_silhouette',
                                 stone=str(stone), blank=str(blank), pixels=roi.histogram()[255],
                                 bounds=roi.getbbox(), analytical_projection_or_fov_fit=False)
        roi_path = output / 'qualified-cell-roi.png'
        roi.save(roi_path)
        qualification.update(roi=str(roi_path), roi_sha256=hashlib.sha256(roi_path.read_bytes()).hexdigest())
        result['qualification'] = qualification
        paths = {'native': {}, 'projection': {}}
        for kind in KINDS:
            stage(6)
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
            replicated = wait('native ' + kind + ' palette', lambda value: palette_matches(value, kind), lambda: run(PALETTE))
            host.sleep(min(.25, max(0, stage_deadline - host.now())))
            path = capture('native_' + kind + '_h0')
            palette_after = run(PALETTE)
            if not palette_matches(palette_after, kind):
                raise AssertionError(('Native palette drift during capture', kind, palette_after))
            paths['native'][kind] = path
            result['rows'][-1].update(kind=kind, mode='native', readback=native,
                                      client_palette=replicated, client_palette_after=palette_after)
            save(receipt, result)
        for kind in KINDS:
            stage(8)
            run('b.stop_projection()\n_result=True')
            source = run(reference['LOAD'] % ('poppy', 0, kind))
            if kind != 'blank':
                run('s.origin=(5,116,5)\ns.opacity=1.\ns.projection_missing=False\ns.projection_outline=False\nb.project()\n_result=True')
                status = wait('projection ' + kind, lambda value: value['active'] and value['ready'] and
                              not value['preparing'] and value['actors'] == 1 and value['mesh'] and value['scale'] is not None,
                              lambda: run(visual['PROJECTION_STATUS']))
                submitted = run(visual['PROJECTION_SOURCE'])
                if not (submitted['work_current'] and submitted['cache_current'] and submitted['origin_current'] and
                        submitted['editor_id'] == source['editor_id'] and submitted['document_id'] == source['document_id'] and
                        submitted['fixture'] == 'snow.visibility.poppy.' + kind + '.0'):
                    raise AssertionError(('Projection source stale', submitted, source))
            else:
                status = run(visual['PROJECTION_STATUS'])
                submitted = None
                if status['active'] or status['actors']:
                    raise AssertionError(('Blank projection still active', status))
            run(CAMERA_SET)
            host.sleep(min(.25, max(0, stage_deadline - host.now())))
            path = capture('projection_' + kind + '_h0')
            final_status = run(visual['PROJECTION_STATUS'])
            final_source = run(visual['PROJECTION_SOURCE']) if kind != 'blank' else None
            if kind != 'blank' and any(final_source.get(key) != submitted.get(key) for key in
                         ('editor_id', 'document_id', 'fixture', 'nonce', 'serial', 'model', 'work_current', 'cache_current', 'origin_current')):
                raise AssertionError(('Projection source drift during capture', submitted, final_source))
            if final_status['actor'] != status['actor'] or final_status['mesh'] != status['mesh']:
                raise AssertionError(('Projection actor/mesh drift during capture', status, final_status))
            paths['projection'][kind] = path
            result['rows'][-1].update(kind=kind, mode='projection', source=source, status=status,
                                      submitted=submitted, final_status=final_status, final_source=final_source)
            save(receipt, result)
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
                restore = '''b.stop_projection()
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
 del sys._blueprint_visual_saved
if hasattr(sys,'_blueprint_qa_saved'):
''' + '\n'.join(' ' + line for line in blueprint['RESTORE'].splitlines()) + '\n_result=True\n'
                result['client_restored'] = run(restore)
                after = run(SERVER_PREFLIGHT, True)
                result['post_restore'] = after
                if after['player_flying'] != result['preflight']['player_flying'] or any(abs(after['player_foot'][i] - player[i]) >= .1 for i in range(3)):
                    raise AssertionError('Player foot/flight drift; no corrective movement')
            except Exception as error:
                result['cleanup_errors'].append('Client/player restoration: ' + str(error))
        if client is not None:
            client.close()
        for key, previous in environment.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous
        save(receipt, result)
    return result
