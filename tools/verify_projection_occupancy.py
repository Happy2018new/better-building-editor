"""Verify automatic single-actor occupancy culling in a managed test world.

Run through run_live_check.py with the assigned session and owner. The default
case temporarily edits verified-air cells and restores them in finally. --probe
only reads runtime state and profiler capabilities.
"""
import argparse
import base64
import json
import time
from pathlib import Path

import verify_ui as ui
from _session import load_session
from mcdk import Client, return_value
from verify_projection_outline import game, server


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')


def probe(out):
    result = {'session': load_session(live=True), 'checks': []}
    result['client'] = game('''b=s.bridge
_result={"ready":s.ready,"active":s.projection_active,
         "size":s.editor.document.size,"blocks":len(s.editor.document.blocks),
         "actors":len(b.projection_entities)+int(bool(b.entity)),
         "preparing":bool(b.preparing_entity),"models":len(b.models),
         "origin":s.origin,"monitor":hasattr(b,"projection_occupancy")}''')
    result['server'] = server('''from modern_projection.server_system import WorldAdapter
a=WorldAdapter(p)
_result={"players":len(api.GetPlayerList()),
        "position":f.CreatePos(p).GetFootPos(),
        "dimension":f.CreateDimension(p).GetEntityDimensionId(),
        "fixture_restored":all(a.read(pos)==value for pos,value in api._occupancy_qa_saved)
             if hasattr(api,"_occupancy_qa_saved") else None}''')
    with Client() as client:
        for operation in ('/help', '/doctor'):
            result['profiler' + operation] = client.call('mc_profiler', {'op': operation})
        result['errors'] = client.call('get_latest_error_logs', {'max_count': 20})
    dump(out, result)
    print(json.dumps({'client': result['client'], 'server': result['server'],
                      'evidence': str(out)}, ensure_ascii=False, indent=2))


def setup_fixture():
    """Retain a small, loaded air fixture before any server block mutation."""
    return server('''from modern_projection.server_system import WorldAdapter
a=WorldAdapter(p)
foot=tuple(int(v) for v in f.CreatePos(p).GetFootPos())
offsets=tuple((x,0,0) for x in range(8))
choices=[(foot[0]+dx,foot[1]+dy,foot[2]+dz)
         for dy in (4,12,20) for dx in (3,-12) for dz in (3,-3)]
chosen=None
for origin in choices:
    saved=[((origin[0]+q[0],origin[1]+q[1],origin[2]+q[2]),
            a.read((origin[0]+q[0],origin[1]+q[1],origin[2]+q[2]))) for q in offsets]
    if all(value==("minecraft:air",0) for pos,value in saved):
        chosen=origin
        break
assert chosen is not None, "No loaded air fixture; refusing to replace world blocks"
api._occupancy_qa_saved=saved
_result=chosen''')


def install_probe(origin):
    return game('''import time
b=s.bridge
assert not s.projection_active and not b.preparing_entity, "Close the previous test projection first"
api._occupancy_qa_saved=(s.editor,s.origin,s.projection_missing,s.projection_outline,
                         s.solo_layer,b.geometry,b.factory)
cam=b.factory.CreateCamera(b.level)
api._occupancy_qa_camera=(cam.IsModCameraLockPitch(),cam.IsModCameraLockYaw())
api._occupancy_qa_records=[]
api._occupancy_qa_native=[]
class NativeGeometryProbe(object):
    def __init__(self,target,records,clock):
        self.target,self.records,self.clock=target,records,clock
    def __getattr__(self,name):
        return getattr(self.target,name)
    def CombineBlockPaletteToGeometry(self,*args):
        started=self.clock()
        result=self.target.CombineBlockPaletteToGeometry(*args)
        self.records.append({"name":args[1],"seconds":self.clock()-started})
        return result
class GeometryFactoryProbe(object):
    def __init__(self,target,records,clock,wrapper):
        self.target,self.records,self.clock,self.wrapper=target,records,clock,wrapper
    def __getattr__(self,name):
        return getattr(self.target,name)
    def CreateBlockGeometry(self,level):
        return self.wrapper(self.target.CreateBlockGeometry(level),self.records,self.clock)
b.factory=GeometryFactoryProbe(b.factory,api._occupancy_qa_native,time.clock,NativeGeometryProbe)
def wrap_geometry(original,records,native_records,clock,wall):
    def geometry(document,visible=None,name=None):
        data=document.palette_data(visible)
        sx,sy,sz=document.size
        count=sum(len(indices) for indices in data["common"].values())
        # Large-model timing must not include thousands of diagnostic tuples.
        points=None
        if count<=256:
            points=sorted((index//sz%sx,index//(sx*sz),index%sz)
                          for indices in data["common"].values() for index in indices)
        native_start=len(native_records)
        stamp=wall()
        started=clock()
        result=original(document,visible,name)
        records.append({"time":stamp,"seconds":clock()-started,"name":result,
                        "native_calls":native_records[native_start:],
                        "requested_name":name,"size":document.size,
                        "points":points,
                        "count":count})
        return result
    return geometry
b.geometry=wrap_geometry(b.geometry,api._occupancy_qa_records,api._occupancy_qa_native,time.clock,time.time)
from modern_projection.projection.model import Document,Editor
s.editor=Editor(Document((8,1,1),dict(((x,0,0),("minecraft:quartz_block",0)) for x in range(8))))
s.origin=''' + repr(tuple(origin)) + '''
s.projection_missing=True
s.projection_outline=False
s.solo_layer=False
b.project()
_result=True''')


def snapshot():
    return game('''b=s.bridge
records=api._occupancy_qa_records
mesh=b.projection_mesh
occupancy=b.projection_occupancy
metrics=None
if occupancy is not None:
    metrics={key:getattr(occupancy,key) for key in ("reads","builds","commits",
             "last_poll_ms","max_poll_ms","last_build_ms","next_build","failed")}
    metrics["pending"]=len(occupancy.changed)
    metrics["hints"]=len(occupancy.hints)
    metrics["serial"]=occupancy.serial
    metrics["shader_updates"]=occupancy.shader.updates
    metrics["bank"]=occupancy.shader.bank
    metrics["prepare_ms"]=occupancy.last_prepare_ms
    metrics["bulk_calls"]=occupancy.bulk.calls if occupancy.bulk else 0
    metrics["bulk_sweeps"]=occupancy.bulk.sweeps if occupancy.bulk else 0
committed=None
if mesh:
    for record in reversed(records):
        if record["name"]==mesh[1]:
            committed=dict(record)
            break
if committed and occupancy is not None:
    committed["count"]=0 if occupancy.shader.empty else committed["count"]
    if committed["points"] is not None:
        committed["points"]=[point for point in committed["points"]
            if not occupancy.shader.empty]
_result={"active":s.projection_active,"preparing":bool(b.preparing_entity),
         "actor":b.entity,"actors":len(b.projection_entities)+int(bool(b.entity)),
         "split_actors":len(b.projection_entities),"models":len(b.models),
         "records":records,"committed":committed,"mesh":mesh,"metrics":metrics,
         "message":s.editor.message}''')


def check_client_callbacks(origin, evidence):
    """Exercise loaded client callbacks with the documented engine payloads."""
    result = game('''b=s.bridge
owner=b.system
occupancy=b.projection_occupancy
origin=''' + repr(tuple(origin)) + '''
saved=owner.hud.carried
observed=[]
try:
    owner.hud.carried=None
    for args in ({"pos":tuple(float(v) for v in origin)},
                 dict(zip(("x","y","z"),origin))):
        occupancy.hints.clear()
        occupancy.hint_queue.clear()
        owner.tool_prevent_break(args)
        observed.append(sorted(occupancy.hints))
    occupancy.hints.clear()
    occupancy.hint_queue.clear()
    from modern_projection.projection.tool_items import TERMINAL
    owner.hud.carried=TERMINAL
    cancelled={"pos":origin}
    owner.tool_prevent_break(cancelled)
    _result={"positions":observed,"cancelled":cancelled.get("cancel"),
             "cancelled_hints":len(occupancy.hints),
             "cleanup_loaded":"UnListenAllEvents" in owner.Destroy.im_func.func_code.co_names}
finally:
    owner.hud.carried=saved''')
    evidence['client_callbacks'] = result
    ui.check('loaded break callbacks accept pos and x/y/z engine payloads',
             result['positions'] == [[[0,0,0],[1,0,0]], [[0,0,0],[1,0,0]]])
    ui.check('cancelled tool interaction does not enqueue occupancy work',
             result['cancelled'] and result['cancelled_hints'] == 0)
    ui.check('loaded system destruction includes listener cleanup', result['cleanup_loaded'])


def wait_points(points, timeout=15):
    expected = sorted([list(point) for point in points])
    started = time.monotonic()
    actual = None
    while time.monotonic() - started < timeout:
        actual = snapshot()
        committed = actual['committed']
        if (actual['active'] and not actual['preparing'] and
                ((expected and committed and committed['points'] == expected) or
                 (not expected and (actual['mesh'] is None or committed and committed['count']==0)))):
            assert actual['split_actors'] == 0, actual
            actual['observed_seconds'] = time.monotonic() - started
            return actual
        time.sleep(.12)
    raise AssertionError({'expected_points': expected, 'last': actual})


def wait_count(count, timeout=45):
    started = time.monotonic()
    actual = None
    while time.monotonic() - started < timeout:
        actual = snapshot()
        committed = actual['committed']
        if (actual['active'] and not actual['preparing'] and committed and
                committed['count'] == count and actual['metrics']):
            actual['observed_seconds'] = time.monotonic() - started
            assert actual['actors'] == 1 and actual['split_actors'] == 0, actual
            return actual
        time.sleep(.15)
    raise AssertionError({'expected_count': count, 'last': actual})


def capture_fixture(origin, label, width=8, camera_height=3.):
    game('''b=s.bridge
cam=b.factory.CreateCamera(b.level)
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
cam.DepartCamera()
origin=''' + repr(tuple(origin)) + '''
width=''' + repr(width) + '''
height=''' + repr(camera_height) + '''
pos=(origin[0]+width*.5-.2,origin[1]+height,origin[2]-width)
target=(origin[0]+width*.5-.2,origin[1]+.5,origin[2]+.5)
rot=api.GetRotFromDir(tuple(target[i]-pos[i] for i in range(3)))
cam.SetCameraPos(pos)
cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
_result=True''')
    time.sleep(.5)
    with Client() as client:
        captured = client.call('capture_game_window', {})
    block = next(item for item in captured['content'] if item.get('type') == 'image')
    path = ui.OUT / ('projection_occupancy_' + label + '.jpg')
    path.write_bytes(base64.b64decode(block['data']))
    return str(path)


def world_burst(origin):
    return server('''from modern_projection.server_system import WorldAdapter
adapter=WorldAdapter(p)
timer=f.CreateGame(api.GetLevelId())
origin=''' + repr(tuple(origin)) + '''
stats={"changes":0,"done":False}
api._occupancy_qa_burst=stats
def install_burst(adapter,timer,origin,stats):
    def step(index):
        if stats.get("cancel"):
            stats["done"]=True
            return
        x=index%8
        value=("minecraft:glass",0) if (index//8)%2==0 else ("minecraft:air",0)
        pos=(origin[0]+x,origin[1],origin[2])
        assert adapter.write(pos,value), (pos,value)
        # Server API is used only to edit this temporary fixture. No product
        # server hook or notification: the client discovers every change.
        stats["changes"]+=1
        if index<63:
            timer.AddTimer(.05,step,index+1)
        else:
            stats["done"]=True
    step(0)
install_burst(adapter,timer,origin,stats)
_result=True''')


def check_burst(origin, evidence):
    before = snapshot()
    hint_position = [origin[0], origin[1], origin[2]]
    game('''occupancy=s.bridge.projection_occupancy
for unused in range(100):
    occupancy.hint(''' + repr(tuple(hint_position)) + ''')
_result=True''')
    ui.check('duplicate client hints remain bounded', snapshot()['metrics']['hints'] <= 8)
    world_burst(origin)
    started = time.monotonic()
    progress = []
    status = None
    while time.monotonic() - started < 12:
        state = snapshot()
        status = server('_result=api._occupancy_qa_burst')
        progress.append({'elapsed': time.monotonic()-started, 'status': status,
                         'metrics': state['metrics']})
        if status['done']:
            break
        time.sleep(.12)
    assert status and status['done'], status
    final = wait_points((x, 0, 0) for x in range(8))
    builds = final['metrics']['builds'] - before['metrics']['builds']
    ui.check('64 rapid block changes merge into bounded native rebuilds', 0 < builds < 32)
    ui.check('continuous edits commit buffers before burst ends', any(
        not row['status']['done'] and row['metrics']['shader_updates'] > before['metrics']['shader_updates']
        for row in progress))
    ui.check('automatic refresh retains the same complete actor',
             final['actor'] == before['actor'] and final['actors'] == 1)
    ui.check('dynamic native model names are bounded to two slots',
             len(set(row['requested_name'] for row in final['records']
                     if row['requested_name'])) <= 2)
    ui.check('dynamic updates do not grow the content cache', final['models'] == before['models'])
    evidence['samples']['burst'] = {'before': before, 'after': final, 'progress': progress}


def write_cells(origin, entries):
    return server('''from modern_projection.server_system import WorldAdapter
a=WorldAdapter(p)
origin=''' + repr(tuple(origin)) + '''
entries=''' + repr(entries) + '''
results=[]
for x,name,aux in entries:
    pos=(origin[0]+x,origin[1],origin[2])
    assert a.write(pos,(name,aux)), (pos,name,aux)
    results.append((x,a.read(pos)))
_result=results''')


def cpu_capture(client):
    started = client.call('mc_profiler', {'op': '/start', 'args': {
        'kind': 'python.cpu', 'target': 'client', 'clock': 'wall',
        'duration_seconds': 5, 'storage': 'memory'}})['structuredContent']
    identity = started['job']['id']
    time.sleep(6.)
    status = client.call('mc_profiler', {'op': '/status',
                         'args': {'job_id': identity}})['structuredContent']
    result = {'start': started, 'status': status}
    for label, extra in (('top', {}), ('occupancy', {'filter': 'occupancy'})):
        result[label] = client.call('mc_profiler', {'op': '/query', 'args': dict(
            {'job_id': identity, 'view': 'hotspots', 'limit': 20}, **extra)})['structuredContent']
    return result


def profile_idle(evidence):
    """Same rendered actor and world, only disable/enable the occupancy hook."""
    before = snapshot()
    game('''api._occupancy_qa_profile=s.bridge.projection_occupancy
s.bridge.projection_occupancy=None
_result=True''')
    with Client(timeout=25) as client:
        try:
            baseline = cpu_capture(client)
        finally:
            game('s.bridge.projection_occupancy=api._occupancy_qa_profile\n_result=True')
        candidate = cpu_capture(client)
        comparison = client.call('mc_profiler', {'op': '/compare', 'args': {
            'baseline_job_id': baseline['start']['job']['id'],
            'candidate_job_id': candidate['start']['job']['id'],
            'view': 'hotspots', 'limit': 20}})['structuredContent']
    after = snapshot()
    ui.check('profiling preserves actor and does not rebuild idle geometry',
             before['actor'] == after['actor'] and
             len(before['records']) == len(after['records']))
    evidence['profile'] = {'clock': 'wall', 'seconds_per_capture': 5,
                           'before': before['metrics'], 'after': after['metrics'],
                           'baseline': baseline, 'candidate': candidate,
                           'comparison': comparison}


def run(out, visual=False, large=False, profile=False):
    bound = load_session(live=True)
    assert bound, 'A validated, isolated instance is required'
    evidence = {'session_id': bound['id'], 'checks': ui.checks, 'samples': {}}
    origin = None
    installed = False
    try:
        origin = setup_fixture()
        evidence['origin'] = origin
        install_probe(origin)
        installed = True
        initial = wait_points((x, 0, 0) for x in range(8))
        evidence['samples']['initial'] = initial
        ui.check('initial projection uses one complete actor', initial['actors'] == 1)
        check_client_callbacks(origin, evidence)
        if visual:
            evidence['initial_image'] = capture_fixture(origin, 'initial')
        evidence['writes'] = write_cells(origin, [(0, 'minecraft:gold_block', 0),
            (1, 'minecraft:glass', 0), (2, 'minecraft:stained_glass', 3),
            (3, 'minecraft:smooth_stone_slab', 0)])
        occupied = wait_points((x, 0, 0) for x in range(4, 8))
        evidence['samples']['occupied'] = occupied
        ui.check('wrong material, glass, stained glass and slab hide entire cells',
                 occupied['actors'] == 1)
        if visual:
            evidence['occupied_image'] = capture_fixture(origin, 'occupied')
        write_cells(origin, [(x, 'minecraft:air', 0) for x in range(4)])
        restored = wait_points((x, 0, 0) for x in range(8))
        evidence['samples']['restored'] = restored
        ui.check('removed world blocks restore projection automatically', restored['actors'] == 1)
        if visual:
            evidence['restored_image'] = capture_fixture(origin, 'restored')
        before_idle = snapshot()
        time.sleep(2.)
        after_idle = snapshot()
        ui.check('unchanged world does not resubmit geometry',
                 len(after_idle['records']) == len(before_idle['records']))
        ui.check('idle retains model and actor identity',
                 after_idle['actor'] == before_idle['actor'] and
                 after_idle['models'] == before_idle['models'])
        evidence['samples']['idle'] = after_idle
        check_burst(origin, evidence)
        write_cells(origin, [(x, 'minecraft:glass', 0) for x in range(8)])
        empty = wait_points([])
        ui.check('fully occupied projection retains tracking while geometry is empty', empty['active'])
        write_cells(origin, [(4, 'minecraft:air', 0)])
        one = wait_points([(4, 0, 0)])
        ui.check('one removed block restores geometry after all cells were occupied', one['actors'] == 1)
        evidence['samples']['empty_then_restored'] = one
        write_cells(origin, [(4, 'minecraft:glass', 0)])
        wait_points([])
        game('s.bridge.stop_projection()\ns.bridge.project()\n_result=True')
        initial_empty = wait_points([])
        ui.check('initially occupied area starts tracking without creating an actor',
                 initial_empty['actors'] == 0 and initial_empty['metrics'] is not None)
        write_cells(origin, [(0, 'minecraft:air', 0)])
        first_reappearance = wait_points([(0, 0, 0)])
        ui.check('initially empty geometry creates one actor when a block is removed',
                 first_reappearance['actors'] == 1)
        evidence['samples']['initial_empty_then_restored'] = first_reappearance
        write_cells(origin, [(x, 'minecraft:air', 0) for x in range(8)])
        wait_points((x, 0, 0) for x in range(8))
        game('''b=s.bridge
b.stop_projection()
s.editor=Editor(Document((64,128,64),dict(((x,0,0),("minecraft:quartz_block",0)) for x in range(8))))
b.project()
_result=True''')
        sparse = wait_points((x, 0, 0) for x in range(8))
        ui.check('maximum document bounds still use one complete actor',
                 sparse['actors'] == 1 and sparse['committed']['size'] == [64,128,64])
        write_cells(origin, [(7, 'minecraft:glass', 0)])
        large_changed = wait_points((x, 0, 0) for x in range(7))
        ui.check('maximum bounds react to occupancy without splitting entities', large_changed['actors'] == 1)
        evidence['samples']['large'] = large_changed
        if large:
            write_cells(origin, [(x, 'minecraft:air', 0) for x in range(8)])
            game('''s.bridge.stop_projection()
s.editor=Editor(Document((64,128,64),dict(((x,y,z),("minecraft:quartz_block",0))
                for y in range(20) for x in range(32) for z in range(32))))
s.bridge.project()
_result=True''')
            dense = wait_count(20480)
            ui.check('20,480-block maximum-bound projection stays one complete actor', dense['actors'] == 1)
            write_cells(origin, [(0, 'minecraft:glass', 0)])
            game('''occupancy=s.bridge.projection_occupancy
occupancy.hint(''' + repr(tuple(origin)) + ''')
_result=True''')
            dense_changed = wait_count(20479)
            ui.check('large native update preserves the original actor', dense_changed['actor'] == dense['actor'])
            ui.check('large model occupancy change merges one native geometry rebuild',
                     dense_changed['metrics']['builds'] == dense['metrics']['builds']+1 and
                     not dense_changed['metrics']['failed'])
            evidence['samples']['dense'] = {'before': dense, 'after': dense_changed}
        if profile:
            profile_idle(evidence)
        evidence['status'] = 'passed'
    finally:
        # Each side is independently restored even if an IPC check failed.
        restore_errors = []
        if installed:
            try:
                game('''s.bridge.stop_projection()
cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos()
cam.UnDepartCamera()
cam.LockModCameraPitch(api._occupancy_qa_camera[0])
cam.LockModCameraYaw(api._occupancy_qa_camera[1])
s.editor,s.origin,s.projection_missing,s.projection_outline,s.solo_layer,s.bridge.geometry,s.bridge.factory=api._occupancy_qa_saved
s.refresh_preview()
s.emit()
_result=True''')
            except Exception as exc:
                restore_errors.append('client: ' + str(exc))
        if origin is not None:
            try:
                server('''from modern_projection.server_system import WorldAdapter
if hasattr(api,"_occupancy_qa_burst"):
    api._occupancy_qa_burst["cancel"]=True
a=WorldAdapter(p)
for pos,value in api._occupancy_qa_saved:
    assert a.write(pos,value), pos
_result=True''')
            except Exception as exc:
                restore_errors.append('server: ' + str(exc))
        evidence['restore_errors'] = restore_errors
        dump(out, evidence)
        if restore_errors:
            raise AssertionError(restore_errors)
    print('Evidence: ' + str(out), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true', help='Only read runtime and profiler capabilities')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--visual', action='store_true', help='Capture actual before/occupied/restored frames')
    parser.add_argument('--large', action='store_true', help='Also exercise a 20,480-block full-size model')
    parser.add_argument('--profile', action='store_true', help='Compare five-second idle client CPU captures')
    args = parser.parse_args()
    out = args.output or ui.OUT / ('projection_occupancy_baseline.json' if args.probe else
                                  'projection_occupancy_checks.json')
    if args.probe:
        probe(out)
    else:
        run(out, args.visual, args.large, args.profile)


if __name__ == '__main__':
    main()
