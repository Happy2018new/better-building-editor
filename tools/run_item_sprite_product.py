"""One bounded, background-only editor/world item fixture acceptance launch."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SHARED = Path('D:/Happy2018new\u306e\u4e2a\u4eba\u6587\u4ef6/GitHub/better-building-editor')
SCRIPTS = ROOT/'.agents/skills/pyreact-debugging/scripts'
sys.path.insert(0, str(SCRIPTS))
from mcdk import Client, return_value
import _session, _window
from capture_native_window import capture
from verify_debug_blueprints import BlueprintCheck, INSTALL_PROBE, RESTORE

OWNER = 'item-product-r14-v1'
OUTPUT = ROOT/'.runtime'/OWNER
GUARD = SHARED/'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
MCDK = SHARED/'.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
WGC = SHARED/'.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
PINS = {GUARD:'04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93',
        MCDK:'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9',
        WGC:'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'}
STATE = '''items=s.item_preview
controls=s.item_controls
_result=json.dumps({'groups':len(items.groups) if items else None,
 'plan_ready':bool(items and items.published==items.signature()),
 'pending':controls.pending if controls else None,
 'error':str((items.error if items else '') or (controls.error if controls else '') or s.item_error),
 'enabled':s.item_profile is not None,'blocks':len(s.editor.document.blocks),
 'banks':[{'key':repr(key),'front':entry['renderer'].front,
  'ids':entry['renderer'].ids,'visible':entry['renderer'].visible,
  'uniforms':entry['renderer'].uniforms} for key,entry in controls.registry.items()
  if entry.get('renderer')] if controls else []})
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (OUTPUT/name).write_text(json.dumps(value, ensure_ascii=True, indent=2)+'\n', encoding='ascii')


def find_session():
    rows = [json.loads(path.read_bytes()) for path in _session.registry_dir().glob('*/session.json')]
    rows = [row for row in rows if row.get('owner')==OWNER and Path(row.get('project','')).resolve()==ROOT]
    if len(rows)>1:
        raise RuntimeError('Ambiguous owner sessions')
    return rows[0] if rows else None


def main():
    OUTPUT.mkdir(parents=True, exist_ok=False)
    for path, expected in PINS.items():
        if sha(path)!=expected:
            raise ValueError('Background startup pin changed: '+str(path))
    config_path=ROOT/'.mcdev.json'
    if config_path.exists():
        raise ValueError('Worktree launch config must be absent')
    config={'included_mod_dirs':[str(ROOT)],'world_type':2,'world_seed':0,'game_mode':1,
            'auto_hot_reload_mods':False,'auto_hot_reload_ui':False,
            'auto_hot_reload_materials':False,'auto_hot_reload_shaders':False}
    config_path.write_text(json.dumps(config,indent=2)+'\n',encoding='ascii')
    config_sha=sha(config_path)
    report={'schema':1,'completed':False,'background_only':True,'fixture':'test.entities.item_contents',
            'launches':0,'cleanup_errors':[],'captures':[],'checks':[],
            'production_qualified':False,'pins':{str(p):h for p,h in PINS.items()},
            'source':subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip()}
    started=time.monotonic()
    launcher=session=None
    installed=False
    try:
        capacity_cmd="@(Get-CimInstance Win32_Process -Filter \"Name='Minecraft.Windows.exe'\" | Select-Object ProcessId,ThreadCount,HandleCount,VirtualSize,KernelModeTime,UserModeTime)|ConvertTo-Json -Compress"
        census=subprocess.run(['powershell.exe','-NoProfile','-Command',capacity_cmd],capture_output=True,
                              timeout=6,creationflags=subprocess.CREATE_NO_WINDOW)
        if census.returncode:
            raise RuntimeError('Game capacity observation failed')
        rows=json.loads(census.stdout.decode('utf-8-sig') or '[]')
        rows=rows if isinstance(rows,list) else [rows]
        active=[row for row in rows if any(int(row[k]) for k in
                ('ThreadCount','HandleCount','VirtualSize','KernelModeTime','UserModeTime'))]
        report['capacity']=active
        if len(active)>=5:
            raise RuntimeError('No active-game slot available')
        if _window.foreground_snapshot()['process'].lower().startswith('minecraft'):
            raise RuntimeError('A game is already foreground')
        command=[sys.executable,'-X','utf8',str(SCRIPTS/'instances.py'),'start','--project',str(ROOT),
                 '--owner',OWNER,'--name',OWNER,'--preset','ui','--wait','120','--mcdk',str(MCDK),
                 '--noactivate-dll',str(GUARD),'--noactivate-sha256',PINS[GUARD],
                 '--noactivate-mcdk-sha256',PINS[MCDK],'--game-exe',
                 'D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/Minecraft.Windows.exe']
        with (OUTPUT/'launch-stdout.txt').open('wb') as stdout,(OUTPUT/'launch-stderr.txt').open('wb') as stderr:
            launcher=subprocess.Popen(command,cwd=ROOT,stdout=stdout,stderr=stderr,
                                      creationflags=subprocess.CREATE_NO_WINDOW)
            report['launches']=1
            report['launcher_identity']=_session.process_identity(launcher.pid)
            while launcher.poll() is None and time.monotonic()-started<160:
                session=find_session()
                if session and session.get('game_pid'):
                    guard=_window.background_guard_state(session['game_pid'],Path(session['game_executable']).name)
                    report['checks'].append({'seconds':time.monotonic()-started,'guard':guard})
                    save('report.json',report)
                    if not guard['background_safe'] or guard['windows'] and not guard['window_noactivate']:
                        raise RuntimeError('Background startup guard failed')
                time.sleep(.5)
            if launcher.poll() is None:
                raise TimeoutError('Bounded startup did not finish')
        session=find_session()
        if session is None or not session.get('ready'):
            raise RuntimeError('Startup did not reach ready: '+str(session))
        report['session']=session
        os.environ.update(MCDEV_SESSION_FILE=session['session_file'],MCDEV_OWNER=OWNER)
        with Client(timeout=15) as client:
            check=BlueprintCheck(client,OUTPUT/'blueprints.json',45)
            check.wait('actual workspace initialization',lambda value:bool(value),lambda: return_value(
                client.call('execute_code',{'code':"import mod.client.extraClientApi as api\nowner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')\n_result=owner is not None and owner.session is not None\n",'is_client':True,'direct_return':True})))
            check.run(INSTALL_PROBE)
            installed=True
            check.run('from modern_projection.projection.item_sprite_profile import candidate_profile\n'
                      's.item_profile=candidate_profile()\n_result=True')
            def native_capture(label, tree=None):
                state=check.wait('item controls '+label,lambda value:value['plan_ready'] and
                                 not value['pending'] and not value['error'],lambda:check.run(STATE))
                save(label+'.state.json',state)
                if tree is not None:
                    save(label+'.tree.json',tree)
                result=capture(session['session_file'],OWNER,OUTPUT/(label+'.png'),WGC)
                report['captures'].append({'label':label,'capture':result,'state':state})
                save('report.json',report)
                return result
            check.capture=native_capture
            check.page()
            report['fixture']=check.fixture('test.entities.item_contents')
            for index in range(3):
                time.sleep(.8)
                native_capture('editor_temporal_'+str(index))
            check.run("from modern_projection.projection.cell import AIR\n"
                      "from modern_projection.projection.native_appearance import FRAME_NAMES\n"
                      "from modern_projection.projection.cell import foreground\n"
                      "changes=dict((pos,AIR) for pos,cell in s.editor.document.blocks.items() if foreground(cell)[0] in FRAME_NAMES)\n"
                      "assert s.editor._commit('Item regression remove',changes,respect_selection=False,whole=True)==6\n"
                      "s.refresh_preview()\ns.emit()\n_result=True")
            native_capture('editor_removed')
            check.run('assert s.editor.undo()\ns.refresh_preview()\ns.emit()\n_result=True')
            native_capture('editor_undo')
            report['logs']=client.call('get_latest_error_logs',{'max_count':40})
            report['completed']=True
            report['native_world_acceptance']='pending; editor diagnostic run only'
            save('report.json',report)
            if installed:
                check.run(RESTORE)
                installed=False
                check.run('s.item_profile=None\nnavigator.pop()\n_result=True')
    except Exception as error:
        report['error']=type(error).__name__+': '+str(error)
    finally:
        try:
            session=find_session()
            if session:
                if not session.get('game_pid'):
                    from run_native_single_door import complete_cleanup_binding
                    session=complete_cleanup_binding(session)
                report['session_before_stop']=session
                if session.get('game_pid'):
                    result=subprocess.run([sys.executable,'-X','utf8',str(SCRIPTS/'instances.py'),'stop',
                        '--session',session['session_file'],'--owner',OWNER],capture_output=True,text=True,
                        encoding='utf8',timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
                    report['stop']={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
                for kind in ('game','mcdk'):
                    if session.get(kind+'_pid') and _session.process_identity(session[kind+'_pid'])==session[kind+'_identity']:
                        _session.terminate_owned(session[kind+'_pid'],session[kind+'_identity'])
                report['identities_after_stop']={kind:_session.process_identity(session[kind+'_pid'])
                    if session.get(kind+'_pid') else None for kind in ('game','mcdk')}
            if launcher and launcher.poll() is None:
                _session.terminate_owned(launcher.pid,report['launcher_identity'])
                launcher.wait(timeout=5)
        except Exception as error:
            report['cleanup_errors'].append(type(error).__name__+': '+str(error))
        if config_path.exists() and sha(config_path)==config_sha:
            config_path.unlink()
        else:
            report['cleanup_errors'].append('Worktree configuration changed; cleanup refused')
        report['elapsed_seconds']=time.monotonic()-started
        save('report.json',report)
    print(json.dumps({k:report.get(k) for k in ('completed','error','elapsed_seconds','cleanup_errors')},ensure_ascii=True))
    return 0 if report['completed'] else 1


if __name__=='__main__':
    sys.exit(main())
