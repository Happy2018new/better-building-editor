"""Measure native missing-projection costs in one owned managed test world."""
import argparse
import base64
import json
import time
from pathlib import Path

from verify_projection_outline import game, server
from _session import load_session
from mcdk import Client


INSTALL = '''import time
b=s.bridge
assert not s.projection_active and not b.preparing_entity
api._context_perf_saved=(s.editor,s.origin,s.projection_missing,s.projection_outline,
                         s.solo_layer,b.geometry,b.factory)
api._context_perf_records=[]
api._context_perf_native=[]
api._context_perf_ticks=[]
api._context_perf_probe={"active":True}
def heartbeat(timer,probe,ticks,clock):
    def tick():
        if not probe["active"]:
            return
        ticks.append((clock(),timer.GetFps()))
        timer.AddTimer(.05,tick)
    timer.AddTimer(.05,tick)
heartbeat(b.factory.CreateGame(b.level),api._context_perf_probe,
          api._context_perf_ticks,time.time)
class NativeProbe(object):
    def __init__(self,target,records,clock):
        self.target,self.records,self.clock=target,records,clock
    def __getattr__(self,name):
        return getattr(self.target,name)
    def CombineBlockPaletteToGeometry(self,*args):
        started=self.clock()
        result=self.target.CombineBlockPaletteToGeometry(*args)
        self.records.append({"name":args[1],"seconds":self.clock()-started,
                             "result":result})
        return result
class FactoryProbe(object):
    def __init__(self,target,records,clock,wrapper):
        self.target,self.records,self.clock,self.wrapper=target,records,clock,wrapper
    def __getattr__(self,name):
        return getattr(self.target,name)
    def CreateBlockGeometry(self,level):
        return self.wrapper(self.target.CreateBlockGeometry(level),self.records,self.clock)
b.factory=FactoryProbe(b.factory,api._context_perf_native,time.clock,NativeProbe)
def wrap_geometry(original,records,clock):
    def geometry(*args,**kwargs):
        started=clock()
        prepared=kwargs.get("prepared")
        result=original(*args,**kwargs)
        batches=prepared.get("_context_batches",()) if prepared else ()
        encoded=(sum(len(entries) for unused,unused2,palette in batches
                     for entries in palette["common"].values()) if batches else
                 sum(len(entries) for entries in prepared["common"].values()) if prepared else None)
        records.append({"name":result,"seconds":clock()-started,
                        "logical_size":args[0].size,
                        "native_volume":prepared["volume"] if prepared else None,
                        "context_chunks":len(batches),"encoded_cells":encoded})
        return result
    return geometry
b.geometry=wrap_geometry(b.geometry,api._context_perf_records,time.clock)
s.projection_missing=True
s.projection_outline=False
s.solo_layer=False
s.origin=tuple(v+(36 if i==1 else 3) for i,v in enumerate(b.player_origin()))
_result={"origin":s.origin,"ready":s.ready}
'''

SNAPSHOT = '''b=s.bridge
o=b.projection_occupancy
work=b.projection_work
_result={"active":s.projection_active,"preparing":bool(b.preparing_entity),
         "work_pending":work is not None and not work.ready and not work.error,
         "work_error":work.error if work is not None else None,
         "actor":b.entity,"actors":len(b.projection_entities)+int(bool(b.entity)),
         "mesh":b.projection_mesh,"message":s.editor.message,
         "context_attached":sum(len(parts) for parts in b.projection_shader.parts) if b.projection_shader is not None else 0,
         "geometry":api._context_perf_records,"native":api._context_perf_native,
         "ticks":api._context_perf_ticks,
         "occupancy":None if o is None else {"bank":o.shader.bank,"commits":o.commits,
             "failed":o.failed,"pending":len(o.changed),"builds":o.builds,
             "last_prepare_ms":o.last_prepare_ms,"last_build_ms":o.last_build_ms}}
'''


def wait_active(timeout, previous_actor=None):
    started = time.monotonic()
    latest, retained = None, 0
    while time.monotonic() - started < timeout:
        latest = game(SNAPSHOT)
        if latest['work_error']:
            raise RuntimeError(latest['work_error'])
        if previous_actor is not None and (latest['work_pending'] or latest['preparing']):
            assert latest['actor'] == previous_actor and latest['actors'] == 1, latest
            retained += 1
        if (latest['active'] and not latest['preparing'] and not latest['work_pending']
                and latest['actor']):
            latest['previous_actor_retained_polls'] = retained
            return latest
        if latest['occupancy'] and latest['occupancy']['failed']:
            raise RuntimeError(latest)
        time.sleep(.2)
    raise TimeoutError(latest)


def wait_bank(bank, actor, timeout):
    started = time.monotonic()
    latest = None
    while time.monotonic() - started < timeout:
        latest = game(SNAPSHOT)
        current = latest['occupancy']
        if current and current['bank'] != bank and not current['pending']:
            assert latest['actor'] == actor and latest['actors'] == 1, latest
            return latest
        if current and current['failed']:
            raise RuntimeError(latest)
        time.sleep(.2)
    raise TimeoutError(dict((key, value) for key, value in latest.items() if key != 'ticks'))


def summary(samples):
    if not samples:
        return None
    ordered = sorted(samples)
    return {'count': len(ordered), 'min': ordered[0], 'median': ordered[len(ordered) // 2],
            'p95': ordered[min(len(ordered) - 1, int(len(ordered) * .95))],
            'max': ordered[-1]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--sides', type=int, nargs='+', default=[16, 24, 32])
    parser.add_argument('--timeout', type=float, default=120.)
    parser.add_argument('--no-screenshots', action='store_true')
    parser.add_argument('--prepare-only', action='store_true',
                        help='Measure initial native submission without camera or world mutations')
    parser.add_argument('--full', action='store_true',
                        help='Measure full projection preparation without occupancy scans; requires --prepare-only')
    args = parser.parse_args()
    if args.full and not args.prepare_only:
        parser.error('--full requires --prepare-only')
    session = load_session(live=True)
    session = dict((key, value) for key, value in session.items() if key != 'token')
    report = {'schema': 1, 'kind': 'native production missing-projection performance',
              'session': session, 'rows': [], 'limitations': [
                  'Concurrent game instances compete for the same CPU/GPU.',
                  'SDK FPS is the engine estimate; timer gaps measure client responsiveness.',
                  'Combine timing ends at SDK return, not at a render-thread/GPU fence.',
                  'Wall time includes asynchronous scheduling and IPC polling.',
                  'Dense stone is a stress fixture, not a representative building.']}
    installed = False
    saved_world = False
    try:
        report['setup'] = game(INSTALL)
        installed = True
        if args.full:
            game('s.projection_missing=False\n_result=True')
            report['kind'] = 'native full-projection preparation performance'
        if not args.prepare_only:
            server('''from modern_projection.server_system import WorldAdapter
a=WorldAdapter(p)
position=''' + repr(tuple(report['setup']['origin'])) + '''
value=a.read(position)
assert value==("minecraft:air",0),"Refuse nonair mutation fixture"
api._context_perf_saved_world=(position,value)
_result=True''')
            saved_world = True
        for side in args.sides:
            assert 1 <= side <= 64
            previous_actor = game('_result=s.bridge.entity')
            started = time.monotonic()
            game('''b=s.bridge
from modern_projection.projection.model import Document,Editor
n=''' + repr(side) + '''
d=Document((n,n,n))
for y in range(n):
    for x in range(n):
        for z in range(n):
            d.blocks[x,y,z]=("minecraft:stone",0)
s.editor=Editor(d)
api._context_perf_records[:]=[]
api._context_perf_native[:]=[]
api._context_perf_ticks[:]=[]
api._context_perf_started=__import__("time").time()
b.project()
_result=True''')
            initial = wait_active(args.timeout, previous_actor)
            elapsed = time.monotonic() - started
            assert initial['actors'] == 1, initial
            if args.prepare_only:
                row={'side':side,'logical_cells':side**3,'initial_wall_seconds':elapsed,'initial':initial}
                report['rows'].append(row)
                print(json.dumps({'side':side,'initial_wall_seconds':elapsed,
                                  'actors':initial['actors'],'attached':initial['context_attached'],
                                  'geometry':initial['geometry'],'native':initial['native']}),flush=True)
                continue
            game('''from modern_projection.pyreact import navigator
if navigator.contains("modern_projection_workspace"):
    navigator.pop()
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
origin=s.origin
n=''' + repr(side) + '''
pos=(origin[0]-n*.9,origin[1]+n*.75,origin[2]-n*1.2)
target=tuple(origin[i]+n*.5 for i in range(3))
rotation=api.GetRotFromDir(tuple(target[i]-pos[i] for i in range(3)))
cam.SetCameraPos(pos)
cam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))
_result=True''')
            time.sleep(2.)
            game('api._context_perf_ticks[:]=[]\n_result=True')
            time.sleep(5.)
            settled = game(SNAPSHOT)
            ticks = settled['ticks']
            gaps = [(ticks[i][0] - ticks[i-1][0]) * 1000 for i in range(1, len(ticks))]
            initial_ticks = initial['ticks']
            initial_gaps = [(initial_ticks[i][0] - initial_ticks[i-1][0]) * 1000
                            for i in range(1, len(initial_ticks))]
            row = {'side': side, 'logical_cells': side ** 3, 'initial_wall_seconds': elapsed,
                   'initial': initial, 'settled': settled, 'settled_fps': summary([t[1] for t in ticks]),
                   'settled_timer_gap_ms': summary(gaps), 'prepare_timer_gap_ms': summary(initial_gaps)}
            report['rows'].append(row)
            print(json.dumps({'side': side, 'initial_wall_seconds': elapsed,
                              'geometry': initial['geometry'], 'native': initial['native'],
                              'settled_fps': row['settled_fps'],
                              'timer_gap_ms': row['settled_timer_gap_ms']}, ensure_ascii=False), flush=True)
            if not args.no_screenshots:
                with Client() as client:
                    captured = client.call('capture_game_window', {})
                image = next(item for item in captured['content'] if item.get('type') == 'image')
                screenshot = args.output.with_name(args.output.stem + '-%d.jpg' % side)
                screenshot.parent.mkdir(parents=True, exist_ok=True)
                screenshot.write_bytes(base64.b64decode(image['data']))
                row['screenshot'] = str(screenshot)
            server('''from modern_projection.server_system import WorldAdapter
position,value=api._context_perf_saved_world
assert WorldAdapter(p).write(position,("minecraft:glass",0))
_result=True''')
            game('''o=s.bridge.projection_occupancy
o.hint(o.origin)
_result=True''')
            dynamic = wait_bank(settled['occupancy']['bank'], settled['actor'], args.timeout)
            server('''from modern_projection.server_system import WorldAdapter
position,value=api._context_perf_saved_world
assert WorldAdapter(p).write(position,value)
_result=True''')
            game('''o=s.bridge.projection_occupancy
o.hint(o.origin)
_result=True''')
            restored = wait_bank(dynamic['occupancy']['bank'], settled['actor'], args.timeout)
            row['dynamic'] = dynamic
            row['restored'] = restored
        report['completed'] = True
    except Exception as exc:
        report['completed'] = False
        report['error'] = repr(exc)
        raise
    finally:
        if saved_world:
            server('''from modern_projection.server_system import WorldAdapter
position,value=api._context_perf_saved_world
adapter=WorldAdapter(p)
if adapter.read(position)!=value:
    assert adapter.write(position,value)
_result=True''')
        if installed:
            if not args.prepare_only:
                game('s.bridge.factory.CreateCamera(s.bridge.level).UnDepartCamera()\n_result=True')
            game('''b=s.bridge
b.stop_projection()
api._context_perf_probe["active"]=False
s.editor,s.origin,s.projection_missing,s.projection_outline,s.solo_layer,b.geometry,b.factory=api._context_perf_saved
s.refresh_preview()
s.emit()
_result=True''')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
