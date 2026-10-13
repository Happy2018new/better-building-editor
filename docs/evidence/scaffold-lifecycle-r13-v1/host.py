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
GUARD=Path('D:/bbe-r13-background/.runtime/native_focus_guard-r13-v1/native_focus_guard.dll')
MCDK=SHARED/'.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
CAPTURE=SHARED/'.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
OWNER='scaffold-r13-lifecycle-v1'
OUTPUT=ROOT/'.runtime/scaffold-lifecycle-r13-v1'
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
config={'included_mod_dirs':[str(ROOT)],'world_type':2,'world_seed':0,'game_mode':1,
    'auto_hot_reload_mods':False,'auto_hot_reload_ui':False,'auto_hot_reload_materials':False,'auto_hot_reload_shaders':False}
config_path=ROOT/'.mcdev.json'
if config_path.exists():raise ValueError('Smoke requires absent worktree config')
config_path.write_text(json.dumps(config,indent=2)+'\n',encoding='ascii')
plan={'schema':1,'owner':OWNER,'launches_permitted':1,'outer_seconds':210,'wait_seconds':120,
 'pins':{str(p):sha(p) for p in (GUARD,MCDK,CAPTURE,config_path,Path(__file__),ROOT/'tools/probe_scaffold_state_lifecycle.py',ROOT/'tools/context_test_environment.py',ROOT/'tools/verify_debug_blueprints.py',ROOT/'tools/capture_native_window.py')},
 'foreground':_window.foreground_snapshot(),'background_only':True,'real_input':False,'resize':False,
 'created_at':datetime.now(timezone.utc).isoformat(), 'native_method':'17 sequential lifecycle controls; real GetBlockStates; direct versus semantic; support/scaffold/delayed035; v1', 'acceptance':{'editor':'pending','full':'pending','missing':'pending'}}
plan['pack_inventory']={str(p.relative_to(ROOT)):sha(p) for folder in ('behavior_pack','resource_pack') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and p.suffix not in ('.pyc','.pyo')}

write('plan.json',plan)
report={'schema':1,'completed':False,'cleanup_errors':[],'launches':0,'checks':[]}
session=None
launcher=None
started=time.monotonic()
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
    if not session.get('ready'):raise RuntimeError('Startup did not reach ready: '+str(session.get('error')))
    os.environ.update(MCDEV_SESSION_FILE=session['session_file'],MCDEV_OWNER=OWNER)
    code="import mod.client.extraClientApi as api\nsystem=api.GetSystem('ModernProjection','ModernProjectionClientSystem')\nplayer=api.GetLocalPlayerId()\n_result={'player':player,'foot':api.GetEngineCompFactory().CreatePos(player).GetFootPos(),'system':system is not None,'workspace':system is not None and system.session is not None}\n"
    with Client(timeout=10) as client:
        world_deadline=min(started+185,time.monotonic()+25)
        while time.monotonic()<world_deadline:
            report['world']=return_value(client.call('execute_code',{'code':code,'is_client':True,'direct_return':True}))
            save()
            if report['world']['workspace'] and report['world']['foot']:break
            time.sleep(.5)
        if not report['world'].get('workspace'):raise RuntimeError('Actual UiInit workspace did not initialize')
    save()
    report['capture']=capture(session['session_file'],OWNER,OUTPUT/'world.png',CAPTURE)
    env=os.environ.copy()
    env.update(MCDEV_SESSION_FILE=session['session_file'],MCDEV_OWNER=OWNER,MCDEV_MCP_URL=session['mcp_url'])
    with (OUTPUT/'probe-stdout.txt').open('wb') as stdout,(OUTPUT/'probe-stderr.txt').open('wb') as stderr:
        result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/probe_scaffold_state_lifecycle.py'),str(OUTPUT/'native.json'),'--fresh-owned-flow-allowed'],cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
    report['probe_returncode']=result.returncode
    report['native']=json.loads((OUTPUT/'native.json').read_bytes())
    if result.returncode:raise RuntimeError('Owned lifecycle diagnostic failed; raw native evidence retained')
    report['completed']=True;save()
except Exception as error:
    report['error']=type(error).__name__+': '+str(error);save()
finally:
    try:
        session=find_session()
        if session:
            if not session.get('game_pid'):
                from run_native_single_door import complete_cleanup_binding
                session=complete_cleanup_binding(session)
            report['session_before_stop']=session
            if session.get('game_pid'):
                result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'.agents/skills/pyreact-debugging/scripts/instances.py'),'stop','--session',session['session_file'],'--owner',OWNER],capture_output=True,text=True,encoding='utf8',timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
                report['normal_stop']={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
            for kind in ('game','mcdk'):
                if session.get(kind+'_pid') and _session.process_identity(session[kind+'_pid'])==session[kind+'_identity']:
                    _session.terminate_owned(session[kind+'_pid'],session[kind+'_identity'])
            report['identities_after_stop']={kind:_session.process_identity(session[kind+'_pid']) if session.get(kind+'_pid') else None for kind in ('game','mcdk')}
            report['session_after_stop']=find_session()
        if launcher and launcher.poll() is None:
            _session.terminate_owned(launcher.pid,report['launcher_identity'])
            launcher.wait(timeout=5)
    except Exception as error:report['cleanup_errors'].append(type(error).__name__+': '+str(error))
    if config_path.exists() and sha(config_path)==plan['pins'][str(config_path)]:config_path.unlink()
    else:report['cleanup_errors'].append('Worktree configuration changed, restoration refused')
    report['pins_unchanged']={p:sha(Path(p))==h for p,h in plan['pins'].items() if p!=str(config_path)}
    report['pack_inventory_unchanged']=all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in plan['pack_inventory'].items())
    report['elapsed_seconds']=time.monotonic()-started;save()
print(json.dumps({k:report.get(k) for k in ('completed','error','launches','elapsed_seconds','cleanup_errors','identities_after_stop')},ensure_ascii=True))
