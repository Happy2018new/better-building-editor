"""Focused R29 transform smoke in a freshly frozen independent managed world.

Uses ordinary cold Session gates unchanged. Semantic callbacks, publication,
occupancy and server readback are evidence of their named behavior only; this
does not qualify water, portal/book pixels, native hit boxes or phone input.
All world mutations restore their bounded, initially-air test region.
"""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
sys.path[:0] = [str(SCRIPTS), str(ROOT / 'tools')]
from _session import load_session, read_json, process_identity
from mcdk import Client, return_value
from probe_projection_transform_r29 import commit_memory
from verify_debug_blueprints import BlueprintCheck

WGC_SHA = 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
SERVER = """import json
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
f=api.GetEngineCompFactory()
p=api.GetPlayerList()[0]
a=WorldAdapter(p)
"""
STATUS = """t=b.projection_target
w=b.projection_work
o=b.projection_occupancy
def cells(doc):
 return [[pos,list(value)] for pos,value in sorted(doc.blocks.items())]
_result=json.dumps({'busy':s.busy,'active':s.projection_active,
 'message':s.editor.message,'progress':s.progress,'draft_operations':s.projection_transform,
 'origin':s.origin,'source':{'id':id(s.editor.document),'size':s.editor.document.size,
  'cells':cells(s.editor.document),'revision':s.editor.revision},
 'target':None if t is None else {'id':id(t),'origin':t.origin,'operations':t.operations,
  'size':t.size,'source_key':t.source_key,'cells':cells(t.document),
  'hidden':sorted(t.hidden),'layer':t.layer},
 'work':None if w is None else {'ready':w.ready,'error':str(w.error or ''),
  'size':w.document.size,'cells':cells(w.document),'origin':w.origin},
 'occupancy':None if o is None else {'size':o.size,'origin':o.origin,'cells':cells(o.document),
  'state':list(o.state),'rendered':list(o.rendered),'hidden':sorted(o.hidden),
  'layer':o.layer,'targets':list(o.targets),'reads':o.reads,'commits':o.commits,
  'changed':len(o.changed),'attaching':o.attaching,'building':o.build is not None},
 'preparing':b.projection_preparation is not None,'pending':b.pending,
 'profiles':dict((name,getattr(s,name) is not None)
   for name in ('liquid_profile','portal_profile','book_profile'))})
"""
INSTALL = """assert not s.busy and s.edit_job is None and s.io_job is None
assert not s.projection_active and not b.projection_requested
assert s.pending_confirm is None and b.pending is None
assert not hasattr(sys,'_r29_transform_saved')
fields=('origin','projection_transform','projection_missing','projection_outline',
 'apply_air','page','progress','solo_layer','section','view','direct_mode','name','focus_view',
 'focused','box_anchor','canvas_x','canvas_z','paste_origin','paste_pinned',
 'camera_pose','camera_yaw','camera_pitch','zoom','camera_pan','camera_pivot',
 'camera_depth','camera_depth_pose','camera_focus_request','camera_reset_animated')
sys._r29_transform_saved={'editor':s.editor,'fields':dict((k,getattr(s,k)) for k in fields),
 'save_preferences':b.save_preferences,'workspace':navigator.contains('modern_projection_workspace')}
cam=b.factory.CreateCamera(b.level)
sys._r29_transform_saved['camera_locks']=(cam.IsModCameraLockPitch(),cam.IsModCameraLockYaw())
sys._r29_transform_saved['render_distance']=b.factory.CreateActorRender(b.player).GetEntityRenderDistance()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
b.factory.CreateActorRender(b.player).SetEntityRenderDistance(256.)
def discard_r29_preferences(value):return True
b.save_preferences=discard_r29_preferences
s.projection_outline=True
s.projection_missing=False
s.apply_air=False
s.solo_layer=False
s.projection_transform=()
from modern_projection.projection.model import Document,Editor
s.editor=Editor(Document((4,3,5),{
 (0,0,0):('minecraft:gold_block',0),(3,0,0):('minecraft:diamond_block',0),
 (0,2,4):('minecraft:emerald_block',0),(3,2,4):('minecraft:redstone_block',0),
 (1,1,2):('minecraft:oak_stairs',0),(2,1,3):('minecraft:oak_log',0)},
 name='R29 detached transform fixture'))
s.refresh_preview()
owner.open_workspace()
s.set('page','projection')
_result=True
"""
RESERVE = """assert not hasattr(api,'_r29_transform_saved')
foot=tuple(int(v) for v in f.CreatePos(p).GetFootPos())
selected=None
for dy in (24,32,40):
 origin=(foot[0]+8,min(220,foot[1]+dy),foot[2]+8)
 saved=[((origin[0]+x,origin[1]+y,origin[2]+z),
         a.read((origin[0]+x,origin[1]+y,origin[2]+z)))
        for y in range(3) for x in range(8) for z in range(8)]
 if all(value==('minecraft:air',0) for pos,value in saved):
  selected=origin
  break
assert selected is not None,'No fully-loaded initially-air 8x3x8 region found'
player=f.CreatePlayer(p)
api._r29_transform_saved={'cells':saved,'mode':f.CreateGame(api.GetLevelId()).GetPlayerGameType(p),
 'abilities':player.GetPlayerAbilities(),'foot':f.CreatePos(p).GetFootPos(),
 'flying':f.CreateFly(p).IsPlayerFlying()}
player.SetPlayerGameType(1)
player.SetOperatorCommandAbility(True)
player.SetBuildAbility(True)
player.SetMineAbility(True)
_result=json.dumps({'origin':selected,'reserved_cells':len(saved)})
"""
RESTORE_SERVER = """saved=api._r29_transform_saved
restore_errors=[]
def attempt(label,operation):
 try:
  result=operation()
  if result is False:restore_errors.append({'phase':label,'error':'API returned False'})
  return result
 except Exception as error:
  restore_errors.append({'phase':label,'type':type(error).__name__,'error':repr(error)})
  return None
for pos,value in saved['cells']:
 attempt('write:'+repr(pos),lambda pos=pos,value=value:a.write(pos,value))
wrong=[]
for pos,value in saved['cells']:
 actual=attempt('read:'+repr(pos),lambda pos=pos:a.read(pos))
 if actual!=value:wrong.append({'position':pos,'actual':actual,'expected':value})
player=attempt('player_component',lambda:f.CreatePlayer(p))
attempt('mode',lambda:player.SetPlayerGameType(saved['mode']))
attempt('operator',lambda:player.SetOperatorCommandAbility(saved['abilities']['op']))
attempt('build',lambda:player.SetBuildAbility(saved['abilities']['build']))
attempt('mine',lambda:player.SetMineAbility(saved['abilities']['mine']))
attempt('foot',lambda:f.CreatePos(p).SetFootPos(saved['foot']))
attempt('flight',lambda:f.CreateFly(p).ChangePlayerFlyState(
 saved['mode']==1 or saved['flying'],saved['flying']))
actual_mode=attempt('read_mode',lambda:f.CreateGame(api.GetLevelId()).GetPlayerGameType(p))
actual_abilities=attempt('read_abilities',lambda:player.GetPlayerAbilities())
actual_foot=attempt('read_foot',lambda:f.CreatePos(p).GetFootPos())
# False is a valid readback for IsPlayerFlying, so do not treat it as a setter failure.
try:actual_flying=f.CreateFly(p).IsPlayerFlying()
except Exception as error:
 restore_errors.append({'phase':'read_flight','type':type(error).__name__,'error':repr(error)})
 actual_flying=None
readback={'mode':actual_mode,'expected_mode':saved['mode'],
 'abilities':actual_abilities,'expected_modified_abilities':dict(
  (key,saved['abilities'][key]) for key in ('op','build','mine')),
 'foot':actual_foot,'expected_foot':saved['foot'],
 'flying':actual_flying,'expected_flying':saved['flying']}
readback['mode_matches']=actual_mode==saved['mode']
readback['abilities_match']=actual_abilities is not None and all(
 actual_abilities.get(key)==saved['abilities'][key] for key in ('op','build','mine'))
readback['foot_matches']=actual_foot is not None and all(
 abs(actual_foot[i]-saved['foot'][i])<=.02 for i in range(3))
readback['flight_matches']=actual_flying==saved['flying']
accepted=not restore_errors and not wrong and all(
 readback[key] for key in ('mode_matches','abilities_match','foot_matches','flight_matches'))
if accepted:del api._r29_transform_saved
_result=json.dumps({'restored_cells':len(saved['cells']),'exact_world_readback':not wrong,
 'world_differences':wrong,'player_readback':readback,'errors':restore_errors,'accepted':accepted})
"""
RESTORE_CLIENT = """saved=sys._r29_transform_saved
restore_errors=[]
def attempt(label,operation):
 try:return operation()
 except Exception as error:
  restore_errors.append({'phase':label,'type':type(error).__name__,'error':repr(error)})
  return None
attempt('stop_projection',b.stop_projection)
s.pending_confirm=None
s.editor=saved['editor']
for key,value in saved['fields'].items():setattr(s,key,value)
b.save_preferences=saved['save_preferences']
cam=attempt('camera_component',lambda:b.factory.CreateCamera(b.level))
attempt('camera_follow_position',lambda:cam.ResetCameraPos())
attempt('camera_follow_player',lambda:cam.UnDepartCamera())
attempt('camera_pitch_lock',lambda:cam.LockModCameraPitch(saved['camera_locks'][0]))
attempt('camera_yaw_lock',lambda:cam.LockModCameraYaw(saved['camera_locks'][1]))
render=attempt('render_component',lambda:b.factory.CreateActorRender(b.player))
attempt('render_distance',lambda:render.SetEntityRenderDistance(saved['render_distance']))
attempt('refresh_preview',s.refresh_preview)
attempt('emit',s.emit)
if not saved['workspace'] and navigator.contains('modern_projection_workspace'):
 attempt('workspace_close',navigator.pop)
actual_locks=(attempt('read_pitch_lock',lambda:cam.IsModCameraLockPitch()),
              attempt('read_yaw_lock',lambda:cam.IsModCameraLockYaw()))
actual_distance=attempt('read_render_distance',lambda:render.GetEntityRenderDistance())
readback={'editor_matches':s.editor is saved['editor'],
 'fields_match':all(getattr(s,key)==value for key,value in saved['fields'].items()),
 'preference_writer_matches':b.save_preferences is saved['save_preferences'],
 'camera_locks':actual_locks,'expected_camera_locks':saved['camera_locks'],
 'render_distance':actual_distance,'expected_render_distance':saved['render_distance']}
readback['camera_locks_match']=actual_locks==saved['camera_locks']
readback['render_distance_matches']=actual_distance is not None and abs(
 actual_distance-saved['render_distance'])<.01
accepted=not restore_errors and all(readback[key] for key in (
 'editor_matches','fields_match','preference_writer_matches','camera_locks_match','render_distance_matches'))
if accepted:del sys._r29_transform_saved
_result=json.dumps({'readback':readback,'errors':restore_errors,'accepted':accepted})
"""


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


def fingerprint(project):
    return {path.relative_to(project).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for pack in ('behavior_pack', 'resource_pack') for path in (project / pack).rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo')}


def one(rows, label):
    values = list(rows)
    if len(values) != 1:
        raise AssertionError((label, [(v.get('type'), v.get('id'), v.get('key')) for v in values]))
    return values[0]


def walk(node):
    if node is not None:
        yield node
        for child in node.get('children', ()):
            yield from walk(child)


def process_handles(pid):
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessHandleCount.argtypes = (wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD))
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x1000,False,pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        value = wintypes.DWORD()
        if not kernel.GetProcessHandleCount(handle,ctypes.byref(value)):
            raise ctypes.WinError(ctypes.get_last_error())
        return value.value
    finally:
        kernel.CloseHandle(handle)


def projection_settings(tree):
    matches = []
    def visit(node, ancestors):
        if node is None:
            return
        if node.get('type') == 'ProjectionSettings':
            matches.append((node, ancestors))
        for child in node.get('children', ()):
            visit(child, ancestors + [node])
    visit(tree, [])
    active = [(node, ancestors) for node, ancestors in matches
              if all(v.get('props', {}).get('active') is not False for v in ancestors
                     if v.get('type') == 'RetainedPane')]
    selected = one((node for node, ancestors in active), 'active ProjectionSettings')
    ancestors = next(ancestors for node, ancestors in active if node is selected)
    motion = one((v for v in ancestors if v.get('type') == 'PageMotion'), 'projection PageMotion')
    assert motion.get('props', {}).get('page') == 'projection'
    return selected


class TransformCheck(BlueprintCheck):
    def __init__(self, client, binding, output, cutoff, report, watcher_path, watcher_sha):
        super().__init__(client, output / 'report.json', 45)
        self.binding, self.directory, self.cutoff, self.report = binding, output, cutoff, report
        self.cleaning = False
        self.watcher_path, self.watcher_sha, self.previous_handles = watcher_path, watcher_sha, {}

    def guard(self):
        current = load_session(self.binding['session_file'], self.binding['owner'], live=True)
        assert all(current.get(key) == self.binding.get(key) for key in
            ('id', 'owner', 'project', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity', 'mcp_url'))
        memory = commit_memory()
        handles = {kind:process_handles(current[kind+'_pid']) for kind in ('game','mcdk')}
        sample = dict(at=time.time(),handles=handles,**memory)
        self.report.setdefault('memory_samples', []).append(sample)
        if not self.cleaning:
            assert datetime.now(timezone.utc) < self.cutoff, 'Reached the owned test cutoff'
            assert memory['headroom_bytes'] >= 6 * 1024 ** 3, memory
            assert all(value<200000 and value-self.previous_handles.get(kind,value)<10000
                       for kind,value in handles.items()),sample
            watch = read_json(self.watcher_path)
            assert watch['owners']==[self.binding['owner']] and watch['host_sha256']==self.watcher_sha
            assert not watch['errors'] and not watch['other_assertions'],watch
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(watch['checked_at'])).total_seconds()
            assert 0<=age<60,('Assertion watcher is stale',age)
            assert all(process_identity(current[kind+'_pid'])==current[kind+'_identity']
                       for kind in ('game','mcdk'))
        self.previous_handles=handles

    def run(self, code):
        self.guard()
        # The embedded game uses Python 2 and narrow unicode.
        code = code.encode('ascii', 'backslashreplace').decode('ascii')
        return super().run(code)

    def server(self, code):
        self.guard()
        response = self.client.call('execute_code', {'code': SERVER + code,
            'is_client': False, 'direct_return': True})
        if response.get('isError'):
            raise RuntimeError(response)
        value = return_value(response)
        return json.loads(value) if isinstance(value, str) else value

    def state(self):
        return self.run(STATUS)

    def ready(self):
        def accepted(value):
            if value['work'] and value['work']['error']:
                raise AssertionError(value)
            return (not value['busy'] and not value['preparing'] and value['active'] and
                    value['target'] is not None and value['work'] is not None and value['work']['ready'])
        return self.wait('complete transformed publication', accepted, self.state)

    def settings(self):
        def mounted():
            tree = self.command('dump_tree')['tree']
            if not any(v.get('type') == 'ProjectionSettings' for v in walk(tree)):
                return None
            return projection_settings(tree)
        return self.wait('active projection settings', lambda v: v is not None,
                         mounted)

    def click_action(self, label):
        component = self.wait('action mounts ' + label, lambda rows: len(rows) == 1, lambda:
            [v for v in walk(self.settings()) if v.get('type') == 'Action' and
             v.get('props', {}).get('label') == label])
        button = one((v for v in walk(component[0]) if v.get('type') == 'Button'), label + ' Button')
        self.command('click', button['id'])

    def click_segment(self, identity):
        component = one((v for v in walk(self.settings()) if v.get('type') == 'SegmentChoice'
                         and v.get('props', {}).get('identity') == identity), identity)
        button = one((v for v in walk(component) if v.get('type') == 'Button'), identity + ' Button')
        self.command('click', button['id'])

    def capture(self, label, executable):
        self.guard()
        path = self.directory / (label + '.png')
        command = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'tools/capture_native_window.py'),
            '--session', self.binding['session_file'], '--owner', self.binding['owner'],
            '--output', str(path), '--executable', str(executable)]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding='utf8', errors='replace', timeout=45)
        receipt = dict(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        save(self.directory / (label + '.capture-host.json'), receipt)
        assert result.returncode == 0, receipt
        return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def world_capture(self, label, origin, executable):
        self.run("if navigator.contains('modern_projection_workspace'):navigator.pop()\n_result=True")
        self.wait('workspace hidden for world capture', lambda v:not v['open'] and not v['transition'],
                  self.navigation)
        center=tuple(origin[i]+(2.5,1.5,2.)[i] for i in range(3))
        position=tuple(center[i]+(7.,5.,-10.)[i] for i in range(3))
        self.server('assert f.CreateFly(p).ChangePlayerFlyState(True)\n'
                    'assert f.CreatePos(p).SetFootPos(%r)\n_result=True' % (position,))
        time.sleep(.6)
        receipt=self.run("""cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
center=%r
position=%r
rot=api.GetRotFromDir(tuple(center[i]-position[i] for i in range(3)))
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
_result=json.dumps({'position':position,'center':center,'rotation':(rot[0],rot[1]+180.,0.)})
""" % (center,position))
        time.sleep(.8)
        receipt['capture']=self.capture(label,executable)
        self.run("owner.open_workspace()\ns.set('page','projection')\n_result=True")
        self.wait('workspace reopened after world capture', lambda v:v['open'] and not v['transition'],
                  self.navigation)
        return receipt


def run_smoke(check, allow_write, executable):
    report = check.report
    installed = reserved = False
    try:
        installed = True
        check.run(INSTALL)
        reserved = True
        reservation = check.server(RESERVE)
        origin = tuple(reservation['origin'])
        check.run('s.origin=%r\ns.emit()\n_result=True' % (origin,))
        report['reservation'] = reservation
        original = check.state()['source']
        check.click_segment('rotate_y90')
        check.click_action('X镜像')
        draft = check.state()
        assert draft['draft_operations'] == ['rotate_y90', 'mirror_x'], draft
        report['ui_capture'] = check.capture('rotation-mirror-controls', executable)
        check.click_action('生成投影')
        first = check.ready()
        target = first['target']
        assert target['operations'] == ['rotate_y90', 'mirror_x'] and target['size'] == [5, 3, 4], first
        # Independent 90-degree then target-X mirror coordinate oracle: (z,y,x).
        source_materials = {tuple(pos): value for pos, value in original['cells']}
        mapped = {tuple(pos): value for pos, value in target['cells']}
        for pos in ((0,0,0), (3,0,0), (0,2,4), (3,2,4)):
            x, y, z = pos
            assert mapped[(z,y,x)] == source_materials[pos], (pos, mapped)
        assert first['source'] == original
        assert first['work']['cells'] == target['cells'] and first['work']['origin'] == list(origin)
        report['first_publication'] = first
        report['full_world_capture']=check.world_capture('full-transformed-world',origin,executable)
        check.click_segment('rotate_y180')
        changed = check.state()
        assert changed['target'] == target and changed['source'] == original, changed
        rejected = check.run("""try:
 b.check_progress()
 _result=json.dumps({'rejected':False})
except ValueError as error:
 _result=json.dumps({'rejected':True,'reason':unicode(error)})
""")
        assert rejected['rejected'], rejected
        report['stale_settings_progress_rejected'] = rejected
        check.click_segment('rotate_y90')
        # Test real missing occupancy in the same transformed coordinate system.
        check.run('s.projection_missing=True\nb.project()\n_result=True')
        missing = check.ready()
        assert missing['target']['cells'] == target['cells']
        local = (4, 2, 3)
        world = tuple(origin[i] + local[i] for i in range(3))
        check.server('assert a.write(%r,("minecraft:stone",0))\n_result=True' % (world,))
        observed = check.wait('one transformed occupied cell', lambda state:
            state['occupancy'] is not None and state['occupancy']['state'].count(2) == 1 and
            state['occupancy']['rendered'].count(2) == 1 and
            not state['occupancy']['building'] and not state['occupancy']['attaching'],
            check.state)
        index = (local[1] * 5 + local[0]) * 4 + local[2]
        assert observed['occupancy']['state'][index] == 2, observed
        assert observed['occupancy']['cells'] == target['cells'], observed
        report['occupied_state'] = observed
        report['occupied_world_capture']=check.world_capture('missing-occupied-world',origin,executable)
        check.run('b.check_progress()\n_result=True')
        progress = check.wait('server progress with one wrong cell', lambda state:
            not state['busy'] and state['progress'] is not None, check.state)
        assert progress['progress']['wrong'] == 1 and progress['progress']['missing'] == 5, progress
        report['occupied_progress'] = progress
        check.server('assert a.write(%r,("minecraft:air",0))\n_result=True' % (world,))
        restored = check.wait('restored missing cell', lambda state:
            state['occupancy'] is not None and state['occupancy']['state'].count(2) == 0 and
            state['occupancy']['rendered'].count(2) == 0 and
            not state['occupancy']['building'] and not state['occupancy']['attaching'],
            check.state)
        report['restored_occupancy'] = restored
        report['restored_world_capture']=check.world_capture('missing-restored-world',origin,executable)
        if allow_write:
            # Confirmation captures the committed target, even if the draft
            # origin/rotation changes before its callback is accepted.
            check.click_segment('world')
            check.click_action('应用到世界')
            title = check.run('assert s.pending_confirm is not None\n_result=json.dumps(s.pending_confirm[0])')
            report['confirmation_capture']=check.capture('frozen-world-confirmation',executable)
            check.run('s.origin=%r\ns.set_projection_rotation("rotate_y180")\ns.accept()\n_result=True' %
                      ((origin[0] + 1, origin[1], origin[2]),))
            applied = check.wait('confirmed server write', lambda state:
                not state['busy'] and state['pending'] is None, check.state)
            assert '已写入' in applied['message'], applied
            expected = target['cells']
            readback = check.server("""origin=%r
expected=%r
rows=[]
for pos,value in expected:
 world=tuple(origin[i]+pos[i] for i in range(3))
 actual=a.read(world)
 canonical=a.canonical(tuple(value))
 rows.append({'position':pos,'actual':actual,'expected':canonical,'matches':actual==canonical})
_result=json.dumps(rows)
""" % (origin, expected))
            assert all(row['matches'] for row in readback), readback
            # Entire reserved box is checked, including air and the changed
            # draft origin: no unintended placement may escape the snapshot.
            full = check.server("""origin=%r
expected=dict((tuple(pos),tuple(value)) for pos,value in %r)
wrong=[]
for y in range(3):
 for x in range(8):
  for z in range(8):
   pos=(x,y,z)
   value=a.canonical(expected.get(pos,('minecraft:air',0)))
   actual=a.read(tuple(origin[i]+pos[i] for i in range(3)))
   if actual!=value:wrong.append({'position':pos,'actual':actual,'expected':value})
_result=json.dumps({'checked':192,'wrong':wrong})
""" % (origin, expected))
            assert not full['wrong'], full
            check.run('s.origin=%r\ns.set_projection_rotation("rotate_y90")\nb.check_progress()\n_result=True' % (origin,))
            complete = check.wait('progress matches actual transformed world', lambda state:
                not state['busy'] and state['progress'] is not None and
                state['progress']['correct'] == 6, check.state)
            report['world_write'] = {'confirmation_title':title,'readback':readback,
                'bounded_air_readback':full,'completed_progress':complete}
            check.run('b.stop_projection()\n_result=True')
            report['native_world_reference_capture']=check.world_capture(
                'actual-transformed-blocks-reference',origin,executable)
        report['source_unchanged'] = check.state()['source'] == original
        assert report['source_unchanged']
        report['feature_checks_passed'] = True
    except BaseException as error:
        report['feature_failure']={'type':type(error).__name__,'error':str(error)}
        raise
    finally:
        check.cleaning = True
        cleanup_errors = []
        if installed:
            try:
                check.run('b.cancel_world()\nb.stop_projection()\n_result=True')
                check.wait('cancel outstanding operation', lambda state: not state['busy'], check.state)
            except Exception as error:
                cleanup_errors.append({'phase':'cancel','type':type(error).__name__,'error':str(error)})
        if reserved:
            try:
                saved_world = check.server("_result=hasattr(api,'_r29_transform_saved')")
                report['world_restoration'] = check.server(RESTORE_SERVER) if saved_world else 'No reservation was installed'
                if saved_world and not report['world_restoration']['accepted']:
                    cleanup_errors.append({'phase':'world_restore_readback','details':report['world_restoration']})
            except Exception as error:
                cleanup_errors.append({'phase':'world','type':type(error).__name__,'error':str(error)})
        if installed:
            try:
                saved_client = check.run("_result=hasattr(sys,'_r29_transform_saved')")
                report['client_restoration'] = check.run(RESTORE_CLIENT) if saved_client else 'No fixture was installed'
                if saved_client and not report['client_restoration']['accepted']:
                    cleanup_errors.append({'phase':'client_restore_readback','details':report['client_restoration']})
            except Exception as error:
                cleanup_errors.append({'phase':'client','type':type(error).__name__,'error':str(error)})
        report['cleanup_errors'] = cleanup_errors
        save(check.directory / 'report.json', report)
        if cleanup_errors and 'feature_failure' not in report:
            raise RuntimeError(cleanup_errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cutoff', required=True, help='Explicit ISO8601 UTC cutoff')
    parser.add_argument('--wgc', type=Path, required=True)
    parser.add_argument('--allow-world-write', action='store_true')
    parser.add_argument('--assertion-status',type=Path,required=True)
    parser.add_argument('--assertion-sha256',required=True)
    args = parser.parse_args()
    if not args.allow_world_write:
        parser.error('This independent-world smoke includes occupancy writes; use --allow-world-write')
    project = args.project.resolve(strict=True)
    assert '.runtime' in project.parts and project != ROOT
    assert args.owner.startswith('r29-')
    cutoff = datetime.fromisoformat(args.cutoff.replace('Z', '+00:00'))
    assert cutoff.tzinfo is not None and datetime.now(timezone.utc) < cutoff
    frozen = json.loads(args.freeze.read_bytes())
    assert Path(frozen['project']).resolve() == project
    assert fingerprint(project) == frozen['files'], 'Cold project differs from exact frozen source'
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==frozen['host_files'][
        'tools/probe_projection_transform_r29_live.py'],'Live host differs from frozen reviewed host'
    assert hashlib.sha256(args.wgc.read_bytes()).hexdigest() == WGC_SHA
    binding = load_session(args.session, args.owner, live=True)
    assert Path(binding['project']).resolve() == project
    os.environ.update(MCDEV_SESSION_FILE=binding['session_file'], MCDEV_OWNER=args.owner,
                      MCDEV_MCP_URL=binding['mcp_url'], MCDEV_GAME_PID=str(binding['game_pid']),
                      MCDEV_ALLOW_USER_FOREGROUND='0')
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'owner':args.owner,'project':str(project),'started_at':datetime.now(timezone.utc).isoformat(),
        'source_freeze_sha256':hashlib.sha256(args.freeze.read_bytes()).hexdigest(),
        'host_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'world_write_requested':args.allow_world_write,'water_qualified':False,
        'portal_or_book_qualified':False,'native_hitboxes_qualified':False,
        'world_pixels_qualified':False,
        'feature_checks_passed':False,'scope':'Ordinary cold Session; semantic callbacks + actual publication/server readback'}
    with Client(timeout=35) as client:
        check = TransformCheck(client, binding, args.output, cutoff, report,
                               args.assertion_status,args.assertion_sha256)
        try:
            run_smoke(check, args.allow_world_write, args.wgc)
            report['frozen_source_unchanged'] = fingerprint(project) == frozen['files']
            assert report['frozen_source_unchanged']
        except BaseException as error:
            report['failure'] = {'type':type(error).__name__,'error':str(error)}
            raise
        finally:
            report['finished_at'] = datetime.now(timezone.utc).isoformat()
            save(args.output / 'report.json', report)
    print(json.dumps({'passed':report['feature_checks_passed'],'report':str(args.output/'report.json')}))


if __name__ == '__main__':
    main()
