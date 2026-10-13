"""Bounded native-only coordinate control; never fit boxes or screenshot offsets."""
import hashlib
import json
import os
from pathlib import Path
from types import ModuleType

from PIL import Image, ImageChops, ImageFilter

from verify_snow_h0_phase import (CAMERA_READ, CAMERA_SET, CROP, FRAME_INSTALL,
                                  SERVER_PREFLIGHT, SIZE, camera_matches,
                                  changed, constants, forward_cosine, helpers,
                                  palette_matches, save)

TARGETS = ((6, -48, 6), (7, -48, 6), (6, -48, 7), (-6, -48, -6))
CONTRACT = {'targets': [list(pos) for pos in TARGETS],
            'plant': 'minecraft:poppy', 'states': ['stone', 'blank', 'plant'],
            'client_server_clip_collision_before_after': True,
            'relative_camera_offset': [-2., .15, -2.5],
            'original_texture_only': True, 'native_only': True,
            'snapshot_fitting_allowed': False, 'production_acceptance': False,
            'selection_boxes_are_mesh_pivots': False,
            'stone_qualification_before_plant': True,
            'stone_reference_roi_sha256': 'ba7ccbb82bc5126b69ce5217e61826febe35356821160926de03c18c5018d0cb',
            'stone_reference_minimum_recall_precision': [.75, .75],
            'stone_reference_tolerance_pixels': 3,
            'stone_reference_area_ratio': [.5, 2.]}

NATIVE_PALETTE = '''target=%r
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(target,target,False)
data=palette.SerializeBlockPalette() if palette is not None else {}
_result=json.dumps(dict([('available',palette is not None)]+[(key,[[value[0],value[1],indices] for value,indices in data.get(key,{}).items()]) for key in ('common','extra')]))
'''


def replicated_palette(value, state):
    if value.get('available') is not True:
        return False
    if state == 'stone':
        return (any(item[0] == 'minecraft:stone' and item[1] == 0 for item in value['common']) and
                all(item[0] in ('minecraft:air','minecraft:stone') for item in value['common']) and
                all(item[0] == 'minecraft:air' for item in value['extra']))
    return palette_matches(value,state)

SERVER_BOXES = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._snow_visibility_native
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
pos=saved['target'];dimension=saved['dimension']
_result=json.dumps({'pos':pos,'front':info.GetBlockNew(pos,dimension),
 'clip':info.GetBlockClip(pos,dimension),'collision':info.GetBlockCollision(pos,dimension)})
'''
CLIENT_BOXES = '''pos=%r
info=b.factory.CreateBlockInfo(b.level)
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(pos,pos,False)
data=palette.SerializeBlockPalette() if palette is not None else {}
_result=json.dumps({'pos':pos,'front':info.GetBlock(pos),'clip':info.GetBlockClip(pos),
 'collision':info.GetBlockCollision(pos),
 'palette':dict((key,[[value[0],value[1],indices] for value,indices in data.get(key,{}).items()]) for key in ('common','extra'))})
'''
STONE = '''import json,sys
from modern_projection.server_system import WorldAdapter
saved=sys._snow_visibility_native
adapter=WorldAdapter(saved['player'])
assert adapter.info.SetBlockNew(saved['target'],{'name':'minecraft:stone','aux':0},0,saved['dimension'],True,False)
_result=True
'''
FRAME_REMOVE = '''if hasattr(sys,'_snow_h0_render_frames'):
 probe=sys._snow_h0_render_frames
 owner.UnListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'GameRenderTickEvent',probe,probe.tick)
 del sys._snow_h0_render_frames
_result=True
'''
SAVE_CAMERA = '''assert not s.projection_active and not b.preparing_entity
assert not hasattr(sys,'_native_plant_coordinate_camera')
cam=b.factory.CreateCamera(b.level)
sys._native_plant_coordinate_camera={'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'pitch_lock':cam.IsModCameraLockPitch(),'yaw_lock':cam.IsModCameraLockYaw(),
 'player':b.player_position.GetFootPos(),'fov':cam.GetFov()}
_result=json.dumps(sys._native_plant_coordinate_camera)
'''
RESTORE_CAMERA = '''if hasattr(sys,'_native_plant_coordinate_camera'):
 saved=sys._native_plant_coordinate_camera
 cam=b.factory.CreateCamera(b.level)
 cam.ResetCameraPos();cam.UnDepartCamera()
 assert cam.SetCameraRotation(saved['rotation'])
 cam.LockModCameraPitch(saved['pitch_lock']);cam.LockModCameraYaw(saved['yaw_lock'])
 assert all(abs(b.player_position.GetFootPos()[i]-saved['player'][i])<.1 for i in range(3)), 'Player moved; no corrective teleport'
_result=json.dumps({'render_events':getattr(getattr(sys,'_snow_h0_render_frames',None),'count',None)})
'''


def boxes_consistent(before, after, target, expected):
    """Check raw position/state stability; do not equate AABB centers with meshes."""
    for snapshot in (before, after):
        server, client = snapshot['server'], snapshot['client']
        if tuple(server['pos']) != target or tuple(client['pos']) != target:
            return False
        if server['front']['name'] != expected or client['front'][0] != expected:
            return False
        if type(server['front']['aux']) is not int or type(client['front'][1]) is not int:
            return False
        if server['front']['aux'] != client['front'][1]:
            return False
        for key in ('clip', 'collision'):
            if server[key] != client[key] or (key == 'clip' and expected != 'minecraft:air' and server[key] is None):
                return False
    return before == after


def stone_coverage(actual, reference):
    expected_count, actual_count = reference.histogram()[255], actual.histogram()[255]
    recall = ImageChops.multiply(reference, actual.filter(ImageFilter.MaxFilter(7))).histogram()[255] / max(1, expected_count)
    precision = ImageChops.multiply(actual, reference.filter(ImageFilter.MaxFilter(7))).histogram()[255] / max(1, actual_count)
    return {'reference_pixels': expected_count, 'actual_pixels': actual_count,
            'recall_3px': recall, 'precision_3px': precision,
            'passed': expected_count >= 1000 and actual_count >= 1000 and recall >= .75 and precision >= .75 and
                      .5 <= actual_count / max(1, expected_count) <= 2.,
            'plant_geometry_or_offset_fitted': False}


class NativePositionControl:
    """One session, explicit stage bounds, journaled native cells and camera."""
    def __init__(self, plan, host, session, output, work_deadline, restore_deadline, health):
        self.plan, self.host, self.session = plan, host, session
        self.output, self.receipt = Path(output), Path(output) / 'native-position-phase.json'
        self.work_deadline, self.restore_deadline = work_deadline, restore_deadline
        self.health = health
        self.stage_deadline = min(work_deadline, host.now() + 10)
        self.restoring = False
        self.client = None
        self.camera_saved = None
        self.camera_save_attempted = False
        self.camera_mutation_attempted = False
        self.observer_attempted = False
        self.fixture_attempted = False
        self.pose = None
        self.player = None
        self.screen_baseline = None
        self.center = None
        self.target = None
        self.result = {'schema': 1, 'started': True, 'completed': False,
                       'production_acceptance': False, 'native_mesh_or_offset_authority': False,
                       'session': session['id'], 'contract': CONTRACT, 'rows': [],
                       'cleanup_errors': [], 'mutation_attempted': False}
        self.reference = constants(plan['files']['snow_reference']['path'],
                                   ('NATIVE_SETUP', 'NATIVE_MUTATE', 'NATIVE_CLEANUP'))
        self.prefix = constants(plan['files']['blueprint_reference']['path'], ('CLIENT',))['CLIENT']
        self.module = ModuleType('frozen_native_position_mcdk')
        self.module.__file__ = plan['files']['mcdk_client']['path']
        exec(compile(Path(self.module.__file__).read_bytes(), self.module.__file__, 'exec'), self.module.__dict__)
        control = self

        class BoundedClient(self.module.Client):
            def _post(client, *args, **kwargs):
                if not control.restoring:
                    control.health()
                client.timeout = min(3., control.stage_deadline - control.host.now())
                if client.timeout <= 0:
                    raise TimeoutError('Native coordinate SDK stage deadline exhausted')
                return super()._post(*args, **kwargs)

            def close(client):
                client.timeout = max(.001, min(1., control.restore_deadline - control.host.now()))
                super().close()

        self.client_class = BoundedClient

    def persist(self):
        save(self.receipt, self.result)

    def stage(self, seconds):
        self.stage_deadline = min(self.work_deadline, self.host.now() + seconds)
        if self.stage_deadline <= self.host.now():
            raise TimeoutError('Native coordinate work deadline exhausted')

    def run(self, code, server=False):
        value = self.module.return_value(self.client.call('execute_code',
            {'code': code if server else self.prefix + code,
             'is_client': not server, 'direct_return': True}))
        return json.loads(value) if isinstance(value, str) else value

    def wait(self, label, predicate, read):
        value = None
        while self.host.now() < self.stage_deadline:
            value = read()
            if predicate(value):
                return value
            self.host.sleep(min(.1, max(0, self.stage_deadline - self.host.now())))
        raise TimeoutError(label + ': ' + str(value))

    def raw_boxes(self):
        return {'server': self.run(SERVER_BOXES, True),
                'client': self.run(CLIENT_BOXES % (self.target,))}

    def select_camera(self, row):
        self.stage(10)
        self.center = tuple(axis + .5 for axis in self.target)
        position = tuple(self.center[i] + CONTRACT['relative_camera_offset'][i] for i in range(3))
        row['camera_candidates'] = []
        self.pose = None
        for adjustment in (180., 0.):
            candidate = {'yaw_adjustment': adjustment, 'predeclared_sdk_semantics': True,
                         'captures_before_selection': 0}
            row['camera_candidates'].append(candidate)
            self.camera_mutation_attempted = True
            self.persist()
            pose = self.run(CAMERA_SET % (self.center, position, adjustment))
            candidate['pose'] = pose
            actual = self.wait('Native coordinate camera render/readback',
                lambda value: value['render_events'] >= pose['render_events_at_request'] + 2 and
                              camera_matches(value, pose, self.player), lambda: self.run(CAMERA_READ))
            candidate['actual'] = actual
            candidate['forward_cosine'] = forward_cosine(actual, self.center)
            self.persist()
            if candidate['forward_cosine'] > .99:
                self.pose = pose
                break
        if self.pose is None:
            raise AssertionError('Neither fixed SDK yaw candidate has actual GetForward cosine > .99')

    def capture(self, row, state):
        label = 'position_%02d_%s' % (row['index'], state)
        before_boxes = self.raw_boxes()
        baseline = self.run(CAMERA_READ)
        before = self.wait('Two actual render events before coordinate capture',
            lambda value: value['render_events'] >= baseline['render_events'] + 2,
            lambda: self.run(CAMERA_READ))
        if not camera_matches(before, self.pose, self.player) or forward_cosine(before, self.center) <= .99:
            raise AssertionError('Coordinate camera/player/forward mismatch before capture')
        if self.screen_baseline is None:
            self.screen_baseline = {'screen': before['screen'], 'fov': before['fov']}
        if before['screen'] != self.screen_baseline['screen'] or abs(before['fov']-self.screen_baseline['fov']) > .01:
            raise AssertionError('Native coordinate FOV/screen drift')
        path = self.output / (label + '.png')
        capture = {'state': state, 'path': str(path), 'before': before,
                   'boxes_before': before_boxes, 'first_capture_attempt_locked': True}
        row['captures'].append(capture)
        self.persist()
        seconds = min(5., self.stage_deadline - self.host.now())
        if seconds <= 0:
            raise TimeoutError('No native coordinate capture budget')
        capture['observation'] = self.host.observe(self.session, self.plan, path, seconds)
        self.persist()
        detail = json.loads(capture['observation']['stdout']) if capture['observation'].get('stdout') else {}
        if not detail.get('reliable') or detail.get('state_before') != 'ready' or detail.get('state_after') != 'ready':
            raise AssertionError('First native coordinate capture unreliable; no replacement')
        if (detail['pixels']['width'], detail['pixels']['height']) != SIZE:
            raise AssertionError('Native coordinate physical image dimensions changed')
        after = self.run(CAMERA_READ)
        after_boxes = self.raw_boxes()
        capture.update(after=after, boxes_after=after_boxes)
        expected = 'minecraft:poppy' if state == 'plant' else 'minecraft:air' if state == 'blank' else 'minecraft:stone'
        capture['raw_boxes_stable_and_client_server_equal'] = boxes_consistent(before_boxes, after_boxes, self.target, expected)
        self.persist()
        if not capture['raw_boxes_stable_and_client_server_equal']:
            raise AssertionError('Native coordinate box/state changed across capture')
        if (not camera_matches(after, self.pose, self.player) or forward_cosine(after, self.center) <= .99 or
                after['screen'] != before['screen'] or abs(after['fov']-before['fov']) > .01):
            raise AssertionError('Coordinate camera/player/forward drift after capture')
        return path

    def cleanup_fixture(self):
        exists = self.run("import sys\n_result=hasattr(sys,'_snow_visibility_native')", True)
        cleanup = self.run(self.reference['NATIVE_CLEANUP'], True) if exists else []
        if any(item.get('clean') is False for item in cleanup):
            raise AssertionError('Native coordinate fixture cleanup readback failed')
        self.fixture_attempted = False
        return cleanup

    def coordinate(self, index, target):
        self.target = target
        row = {'index': index, 'target': list(target), 'captures': []}
        self.result['rows'].append(row)
        self.stage(8)
        self.fixture_attempted = True
        self.persist()
        row['fixture'] = self.run(self.reference['NATIVE_SETUP'] % (target,), True)
        support = (target[0], target[1]-1, target[2])
        row['support_palette'] = self.wait('Native dirt support replication',
            lambda value: value.get('available') is True and
                          any(item[0] == 'minecraft:dirt' and item[1] == 0 for item in value['common']) and
                          all(item[0] in ('minecraft:air','minecraft:dirt') for item in value['common']) and
                          all(item[0] == 'minecraft:air' for item in value['extra']),
            lambda: self.run(NATIVE_PALETTE % (support,)))
        self.select_camera(row)
        paths = {}
        roi = None
        for state in CONTRACT['states']:
            self.stage(9)
            if state == 'stone':
                self.run(STONE, True)
            else:
                self.run(self.reference['NATIVE_MUTATE'] % ('poppy', state, 0), True)
            palette = NATIVE_PALETTE % (target,)
            self.wait('Native coordinate state replication',
                lambda value: replicated_palette(value,state), lambda: self.run(palette))
            paths[state] = self.capture(row, state)
            if state == 'blank':
                with Image.open(paths['stone']) as stone, Image.open(paths['blank']) as blank:
                    signal = changed(stone.convert('RGB').crop(CROP), blank.convert('RGB').crop(CROP))
                functions = helpers(self.plan['files']['camera_reference']['path'], ('largest_component', 'fill_enclosed_holes'))
                roi = functions['fill_enclosed_holes'](functions['largest_component'](signal))
                with Image.open(self.plan['files']['native_stone_reference_roi']['path']) as reference:
                    if roi.size != reference.size:
                        raise AssertionError('Frozen native stone reference size changed')
                    row['stone_qualification'] = stone_coverage(roi, reference.convert('L'))
                roi.save(self.output / ('position_%02d_roi.png' % index))
                self.persist()
                if not row['stone_qualification']['passed']:
                    raise AssertionError('Complete native stone footprint failed frozen coverage; poppy not placed')
        with Image.open(paths['blank']) as blank, Image.open(paths['plant']) as plant:
            mask = ImageChops.multiply(changed(plant.convert('RGB').crop(CROP), blank.convert('RGB').crop(CROP)), roi)
        roi_path, mask_path = self.output / ('position_%02d_roi.png' % index), self.output / ('position_%02d_plant_mask.png' % index)
        roi.save(roi_path);mask.save(mask_path)
        row['pixels'] = {'stone_roi': roi.histogram()[255], 'plant': mask.histogram()[255],
                         'roi_sha256': hashlib.sha256(roi_path.read_bytes()).hexdigest(),
                         'plant_mask_sha256': hashlib.sha256(mask_path.read_bytes()).hexdigest(),
                         'stone_roi_bounds': roi.getbbox(), 'plant_bounds': mask.getbbox(),
                         'fitting_allowed': False, 'native_mesh_or_offset_authority': False}
        self.persist()
        if row['pixels']['stone_roi'] < 1000 or row['pixels']['plant'] < 80:
            raise AssertionError('Native coordinate stone/plant visibility positive control failed')
        self.stage(8)
        row['cleanup'] = self.cleanup_fixture()
        self.persist()

    def restore(self):
        self.restoring = True
        self.stage_deadline = self.restore_deadline
        if self.client is None:
            return
        if self.fixture_attempted:
            try:
                self.result['final_native_cleanup'] = self.cleanup_fixture()
            except Exception as error:
                self.result['cleanup_errors'].append('Native coordinate fixture cleanup: ' + str(error))
        if self.camera_save_attempted:
            try:
                self.stage_deadline = min(self.restore_deadline, self.host.now() + 5.)
                if self.camera_saved is None:
                    self.camera_saved = self.run("_result=json.dumps(getattr(sys,'_native_plant_coordinate_camera',None))")
                if self.camera_saved is None:
                    raise AssertionError('Attempted camera save has no journal/readback')
                requested = self.run(RESTORE_CAMERA)
                saved = self.camera_saved
                self.result['camera_restore_requested'] = requested
                self.result['camera_restored'] = self.wait('Original player-follow camera after render events',
                    lambda value: (not self.camera_mutation_attempted or value['render_events'] >= requested['render_events'] + 2) and
                      camera_matches(value, saved, saved['player']) and
                      value['pitch_lock'] == saved['pitch_lock'] and value['yaw_lock'] == saved['yaw_lock'] and
                      abs(value['fov']-saved['fov']) < .01, lambda: self.run(CAMERA_READ))
                self.run("del sys._native_plant_coordinate_camera\n_result=True")
            except Exception as error:
                self.result['cleanup_errors'].append('Native coordinate camera restoration: ' + str(error))
        self.stage_deadline = self.restore_deadline
        if self.observer_attempted:
            try:
                self.result['render_observer_removed'] = self.run(FRAME_REMOVE)
            except Exception as error:
                self.result['cleanup_errors'].append('Native coordinate observer removal: ' + str(error))
        try:
            self.result['post_restore'] = self.run(SERVER_PREFLIGHT % (self.cells,), True)
            self.result['client_empty_readbacks'] = [
                {'position': pos, 'palette': self.wait('Restored native target/support client blank',
                    lambda value: replicated_palette(value,'blank'), lambda pos=pos: self.run(NATIVE_PALETTE % (pos,)))}
                for pos in self.cells]
            before, after = self.result['preflight'], self.result['post_restore']
            if before['player_flying'] != after['player_flying'] or any(abs(before['player_foot'][i]-after['player_foot'][i]) >= .1 for i in range(3)):
                raise AssertionError('Player position or flight changed; no corrective movement')
        except Exception as error:
            self.result['cleanup_errors'].append('Native coordinate final empty/player readback: ' + str(error))
        try:
            self.client.close()
        except Exception as error:
            self.result['cleanup_errors'].append('Native coordinate client close: ' + str(error))

    def execute(self):
        environment = {key: os.environ.get(key) for key in ('MCDEV_SESSION_FILE', 'MCDEV_OWNER', 'MCDEV_MCP_URL')}
        os.environ.update(MCDEV_SESSION_FILE=self.session['session_file'], MCDEV_OWNER=self.session['owner'], MCDEV_MCP_URL=self.session['mcp_url'])
        self.cells = tuple(pos for target in TARGETS for pos in (target, (target[0],target[1]-1,target[2])))
        self.persist()
        try:
            self.client = self.client_class(timeout=3)
            self.client.__enter__()
            self.result['preflight'] = self.run(SERVER_PREFLIGHT % (self.cells,), True)
            self.player = self.result['preflight']['player_foot']
            self.camera_save_attempted = True
            self.camera_saved = self.run(SAVE_CAMERA)
            self.result['camera_before'] = self.camera_saved
            self.observer_attempted = True
            self.result['mutation_attempted'] = True
            self.result['frame_observer'] = self.run(FRAME_INSTALL)
            for index, target in enumerate(TARGETS):
                self.coordinate(index, target)
            if self.host.now() > self.work_deadline:
                raise TimeoutError('Native coordinate work deadline exceeded')
            self.result['completed'] = True
        except Exception as error:
            self.result['error'] = type(error).__name__ + ': ' + str(error)
        finally:
            try:
                self.restore()
            finally:
                for key, value in environment.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
                self.persist()
        return self.result


def run_phase(plan, host, session, output, work_deadline, restore_deadline, health):
    if plan.get('native_coordinate_control') != CONTRACT:
        raise ValueError('Native coordinate control contract changed')
    return NativePositionControl(plan, host, session, output, work_deadline, restore_deadline, health).execute()
