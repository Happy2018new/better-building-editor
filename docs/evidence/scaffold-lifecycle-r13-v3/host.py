import hashlib,json,os,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'.agents/skills/pyreact-debugging/scripts'))
import instances,_session,_window
from mcdk import Client,return_value
from capture_native_window import capture
SHARED=Path('D:/Happy2018newの个人文件/GitHub/better-building-editor')
GUARD=SHARED/'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
MCDK=SHARED/'.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
CAPTURE=SHARED/'.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
GUARD_SHA='04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93'
MCDK_SHA='b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9'
CAPTURE_SHA='cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
OWNER='scaffold-r13-lifecycle-v3'
OUTPUT=ROOT/'.runtime/scaffold-lifecycle-r13-v3'
OUTPUT.mkdir(exist_ok=False)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,data):
    (OUTPUT/name).write_text(json.dumps(data,ensure_ascii=True,indent=2)+'\n',encoding='ascii')
def capacity():
    cmd="@(Get-CimInstance Win32_Process -Filter \"Name='Minecraft.Windows.exe'\" | Select-Object ProcessId,ParentProcessId,ThreadCount,HandleCount,VirtualSize,KernelModeTime,UserModeTime,CreationDate)|ConvertTo-Json -Compress"
    run=subprocess.run(['powershell.exe','-NoProfile','-Command',cmd],capture_output=True,timeout=6,creationflags=subprocess.CREATE_NO_WINDOW)
    if run.returncode:raise RuntimeError('Capacity observation failed')
    rows=json.loads(run.stdout.decode('utf-8-sig') or '[]')
    return rows if isinstance(rows,list) else [rows]
def residual(row):return all(int(row[k])==0 for k in ('ThreadCount','HandleCount','VirtualSize','KernelModeTime','UserModeTime'))
DIAGNOSTIC_PACK=ROOT/'.runtime/scaffold-lifecycle-r13-v3-pack'
config={'included_mod_dirs':[str(DIAGNOSTIC_PACK)],'world_type':2,'world_seed':0,'game_mode':1,
    'auto_hot_reload_mods':False,'auto_hot_reload_ui':False,'auto_hot_reload_materials':False,'auto_hot_reload_shaders':False}
assert sha(GUARD)==GUARD_SHA and sha(MCDK)==MCDK_SHA and sha(CAPTURE)==CAPTURE_SHA,'Approved binary pin differs'
for name in ('block_registry.py','block_registry_data.py'):
    assert sha(ROOT/'behavior_pack/modern_projection/projection'/name)==sha(DIAGNOSTIC_PACK/'behavior_pack/modern_projection/projection'/name),'Minimal registry bytes differ'
config_path=ROOT/'.mcdev.json'
if config_path.exists():raise ValueError('Smoke requires absent worktree config')
config_path.write_text(json.dumps(config,indent=2)+'\n',encoding='ascii')
plan={'schema':1,'owner':OWNER,'launches_permitted':1,'outer_seconds':330,'wait_seconds':120,
 'pins':{str(p):sha(p) for p in (GUARD,MCDK,CAPTURE,config_path,Path(__file__),ROOT/'tools/probe_scaffold_state_lifecycle.py',ROOT/'tools/context_test_environment.py',ROOT/'tools/verify_debug_blueprints.py',ROOT/'tools/capture_native_window.py',ROOT/'tools/analyze_scaffold_state_lifecycle.py',ROOT/'tools/scaffold_diagnostic_world.py')},
 'foreground':_window.foreground_snapshot(),'background_only':True,'real_input':False,'resize':False,
 'created_at':datetime.now(timezone.utc).isoformat(), 'native_method':'17 sequential lifecycle controls; real GetBlockStates; direct versus semantic; support/scaffold/delayed035; v1', 'acceptance':{'editor':'pending','full':'pending','missing':'pending'}}
plan['pack_inventory']={str(p.relative_to(ROOT)):sha(p) for p in sorted(DIAGNOSTIC_PACK.rglob('*')) if p.is_file() and p.suffix not in ('.pyc','.pyo')}
plan['changed_from_v2']='Actual UiInitFinished flag +2 render ticks, bounded synchronized stable client/server feet, server loaded ground and exact17dry reserve; minimal BP and independent SDK method remain; no editor visual acceptance'
plan['registry_source_pins']={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'behavior_pack/modern_projection/projection/block_registry.py',ROOT/'behavior_pack/modern_projection/projection/block_registry_data.py')}


write('plan.json',plan)
report={'schema':1,'completed':False,'cleanup_errors':[],'launches':0,'checks':[]}
session=None
launcher=None
probe_process=None
probe_identity=None
started=time.monotonic()
absolute_deadline=started+330
def remaining_timeout(limit,reserve=70):
    remaining=absolute_deadline-time.monotonic()-reserve
    if remaining<=0:raise TimeoutError('Absolute lifecycle supervisor budget reached')
    return min(limit,remaining)
def save():write('report.json',report)
def find_session():
    rows=[]
    for p in _session.registry_dir().glob('*/session.json'):
        data=json.loads(p.read_bytes())
        if data.get('owner')==OWNER and Path(data.get('project','')).resolve()==ROOT:
            rows.append(data)
    if len(rows)>1:raise RuntimeError('Ambiguous owner smoke sessions')
    return rows[0] if rows else None
try:
    first=capacity();time.sleep(.2);second=capacity()
    stable=[r for r in first if residual(r) and r in second]
    active=[r for r in second if r not in stable]
    report['capacity']={'before':first,'verified':second,'unchanged_residuals':len(stable),'active':active}
    save()
    if len(active)>=5:raise RuntimeError('No active-game capacity')
    if _window.foreground_snapshot()['process'].lower().startswith('minecraft'):raise RuntimeError('Game already foreground')
    command=[sys.executable,'-X','utf8',str(ROOT/'.agents/skills/pyreact-debugging/scripts/instances.py'),'start',
       '--project',str(ROOT),'--owner',OWNER,'--name',OWNER,'--preset','ui','--wait','120',
       '--mcdk',str(MCDK),'--noactivate-dll',str(GUARD),'--noactivate-sha256',sha(GUARD),
       '--noactivate-mcdk-sha256',sha(MCDK),'--game-exe','D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/Minecraft.Windows.exe']
    with (OUTPUT/'launch-stdout.txt').open('wb') as stdout,(OUTPUT/'launch-stderr.txt').open('wb') as stderr:
        launcher=subprocess.Popen(command,cwd=ROOT,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
        report['launches']=1;report['launcher_pid']=launcher.pid;report['launcher_identity']=_session.process_identity(launcher.pid);save()
        while launcher.poll() is None and time.monotonic()-started<160:
            session=find_session()
            if session and session.get('game_pid'):
                guard=_window.background_guard_state(session['game_pid'],Path(session['game_executable']).name)
                check={'at_seconds':time.monotonic()-started,'state':session['state'],'guard':guard}
                report['checks'].append(check);save()
                if not guard['background_safe'] or guard['windows'] and not guard['window_noactivate']:
                    raise RuntimeError('Passive smoke observed noactivation violation')
            time.sleep(.5)
        if launcher.poll() is None:raise TimeoutError('Bounded launcher did not finish')
    report['launcher_returncode']=launcher.returncode
    session=find_session()
    if session is None:raise RuntimeError('No owner-bound session')
    report['session']=session;save()
    if not session.get('ready'):
        # A failed readiness probe is not a usable world. Capture only a diagnostic
        # owned window, without changing the registration's failed/starting state.
        try:
            if _session.process_identity(session['game_pid'])!=session['game_identity']:
                raise RuntimeError('Startup capture game identity changed')
            guard=_window.background_guard_state(session['game_pid'],Path(session['game_executable']).name)
            if not guard['background_safe'] or not guard['window_noactivate']:
                raise RuntimeError('Startup capture background guard failed')
            window=_window._find_game_window(guard['windows'],pid=session['game_pid'],process_name=Path(session['game_executable']).name)
            if window is None or window['minimized']:
                raise RuntimeError('Startup capture owned visible window unavailable')
            png=OUTPUT/'startup-failed.png'
            result=subprocess.run([str(CAPTURE),str(window['hwnd']),str(session['game_pid']),session['game_identity'],str(png.resolve())],capture_output=True,text=True,encoding='utf8',timeout=remaining_timeout(15),creationflags=subprocess.CREATE_NO_WINDOW)
            after=_window.background_guard_state(session['game_pid'],Path(session['game_executable']).name)
            report['startup_capture']={'qualified_world':False,'purpose':'Failed startup diagnosis only','returncode':result.returncode,'stderr':result.stderr,'stdout':result.stdout,'guard_before':guard,'guard_after':after}
            if result.returncode==0 and png.is_file():
                report['startup_capture']['png_sha256']=sha(png)
        except Exception as error:
            report['startup_capture_error']=type(error).__name__+': '+str(error)
        save()
        raise RuntimeError('Startup did not reach ready: '+str(session.get('error')))
    os.environ.update(MCDEV_SESSION_FILE=session['session_file'],MCDEV_OWNER=OWNER)
    from scaffold_diagnostic_world import CLIENT,SERVER,ready
    with Client(timeout=10) as client:
        world_deadline=min(started+230,time.monotonic()+75,absolute_deadline-90)
        previous_foot=None
        stable=0
        report['world_observations']=[]
        report['world_qualified']=False
        while time.monotonic()<world_deadline:
            client.timeout=min(10,max(.1,world_deadline-time.monotonic()))
            report['world']=return_value(client.call('execute_code',{'code':CLIENT,'is_client':True,'direct_return':True}))
            report['server_world']=return_value(client.call('execute_code',{'code':SERVER,'is_client':False,'direct_return':True}))
            admitted=ready(report['world'],report['server_world'])
            foot=report['server_world']['foot']
            stable=stable+1 if admitted and (previous_foot is None or all(abs(a-b)<=.125 for a,b in zip(foot,previous_foot))) else 0
            previous_foot=foot if admitted else None
            report['world_observations'].append({'at_seconds':time.monotonic()-started,'client':report['world'],'server':report['server_world'],'admitted':admitted,'stable_samples':stable})
            save()
            if stable>=3:
                report['world_qualified']=True
                break
            time.sleep(.5)
        if report['world_qualified'] is not True:
            raise RuntimeError('Actual UiInit, stable bounded feet and native loaded reserve did not initialize')
    save()
    if remaining_timeout(20)<20:raise TimeoutError('No bounded WGC time before cleanup reserve')
    report['capture']=capture(session['session_file'],OWNER,OUTPUT/'world.png',CAPTURE)
    env=os.environ.copy()
    env.update(MCDEV_SESSION_FILE=session['session_file'],MCDEV_OWNER=OWNER,MCDEV_MCP_URL=session['mcp_url'])
    with (OUTPUT/'probe-stdout.txt').open('wb') as stdout,(OUTPUT/'probe-stderr.txt').open('wb') as stderr:
        probe_deadline=time.monotonic()+remaining_timeout(120)
        probe_process=subprocess.Popen([sys.executable,'-X','utf8',str(ROOT/'tools/probe_scaffold_state_lifecycle.py'),str(OUTPUT/'native.json'),'--fresh-owned-flow-allowed'],cwd=ROOT,env=env,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
        probe_identity=_session.process_identity(probe_process.pid)
        report['probe_pid']=probe_process.pid;report['probe_identity']=probe_identity
        report['probe_checks']=[];save()
        while probe_process.poll() is None:
            if time.monotonic()>=probe_deadline:raise TimeoutError('Bounded native lifecycle probe did not finish')
            if _session.process_identity(session['game_pid'])!=session['game_identity']:
                raise RuntimeError('Native lifecycle game identity changed')
            guard=_window.background_guard_state(session['game_pid'],Path(session['game_executable']).name)
            report['probe_checks'].append({'at_seconds':time.monotonic()-started,'guard':guard});save()
            if not guard['background_safe'] or not guard['window_noactivate']:
                raise RuntimeError('Native lifecycle passive background guard failed')
            time.sleep(.5)
    report['probe_returncode']=probe_process.returncode
    report['native']=json.loads((OUTPUT/'native.json').read_bytes())
    if probe_process.returncode:raise RuntimeError('Owned lifecycle diagnostic failed; raw native evidence retained')
    from analyze_scaffold_state_lifecycle import analyze
    analysis=analyze(report['native'])
    write('analysis.json',analysis)
    report['analysis_sha256']=sha(OUTPUT/'analysis.json')
    report['completed']=True;save()
except Exception as error:
    report['error']=type(error).__name__+': '+str(error);save()
finally:
    try:
        if probe_process is not None and probe_process.poll() is None:
            _session.terminate_owned(probe_process.pid,probe_identity)
            probe_process.wait(timeout=remaining_timeout(5,0))
        native_path=OUTPUT/'native.json'
        if native_path.is_file():
            report['native']=json.loads(native_path.read_bytes())
            if report['native'].get('restored') is not True and session and session.get('state')=='ready':
                from probe_scaffold_state_lifecycle import MARKER,RESTORE
                from context_test_environment import run
                with Client(timeout=remaining_timeout(8,20)) as client:
                    report['supervisor_native_restore']=run(client,RESTORE%(MARKER,{key:report['native']['provenance'][key] for key in ('session_id','owner','game_pid','game_identity','run_id')}))
    except Exception as error:report['cleanup_errors'].append('Native child/restore: '+type(error).__name__+': '+str(error))
    try:
        session=find_session()
        if session:
            if not session.get('game_pid'):
                from run_native_single_door import complete_cleanup_binding
                session=complete_cleanup_binding(session)
            report['session_before_stop']=session
            if session.get('game_pid'):
                try:
                    result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'.agents/skills/pyreact-debugging/scripts/instances.py'),'stop','--session',session['session_file'],'--owner',OWNER],capture_output=True,text=True,encoding='utf8',timeout=remaining_timeout(20,0),creationflags=subprocess.CREATE_NO_WINDOW)
                    report['normal_stop']={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
                except Exception as error:
                    report['normal_stop_error']=type(error).__name__+': '+str(error)
            for kind in ('game','mcdk'):
                if session.get(kind+'_pid') and _session.process_identity(session[kind+'_pid'])==session[kind+'_identity']:
                    _session.terminate_owned(session[kind+'_pid'],session[kind+'_identity'])
            report['identities_after_stop']={kind:_session.process_identity(session[kind+'_pid']) if session.get(kind+'_pid') else None for kind in ('game','mcdk')}
            report['session_after_stop']=find_session()
        if launcher and launcher.poll() is None:
            _session.terminate_owned(launcher.pid,report['launcher_identity'])
            launcher.wait(timeout=remaining_timeout(5,0))
    except Exception as error:report['cleanup_errors'].append(type(error).__name__+': '+str(error))
    if config_path.exists() and sha(config_path)==plan['pins'][str(config_path)]:config_path.unlink()
    else:report['cleanup_errors'].append('Worktree configuration changed, restoration refused')
    report['pins_unchanged']={p:sha(Path(p))==h for p,h in plan['pins'].items() if p!=str(config_path)}
    report['pack_inventory_unchanged']=all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in plan['pack_inventory'].items())
    report['elapsed_seconds']=time.monotonic()-started;save()
print(json.dumps({k:report.get(k) for k in ('completed','error','launches','elapsed_seconds','cleanup_errors','identities_after_stop')},ensure_ascii=True))
