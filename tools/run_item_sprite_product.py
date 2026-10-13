"""One bounded, background-only editor/world item fixture acceptance launch."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import argparse

ROOT = Path(__file__).resolve().parents[1]
SHARED = Path('D:/Happy2018new\u306e\u4e2a\u4eba\u6587\u4ef6/GitHub/better-building-editor')
SCRIPTS = ROOT/'.agents/skills/pyreact-debugging/scripts'
sys.path.insert(0, str(SCRIPTS))
from mcdk import Client, return_value
import _session, _window
from capture_native_window import capture
from verify_debug_blueprints import BlueprintCheck, INSTALL_PROBE, RESTORE
from item_sprite_capture_contract import snapshot_sources, snapshot_digest
from item_sprite_calibration import calibrate
from item_sprite_closeup import run as run_closeup
from context_test_environment import run as run_environment, SETUP as SETUP_ENVIRONMENT, RESTORE as RESTORE_ENVIRONMENT

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
 'camera_pose':s.camera_pose,'camera_pan':s.camera_pan,'camera_depth':s.camera_depth_pose,
 'screen_size':b.factory.CreateGame(b.level).GetScreenSize(),
 'groups_data':[{'key':repr(group.key),'origin':group.origin,'model':group.model_name,
  'uniforms':group.uniforms} for group in items.groups.values()] if items else [],
 'banks':[{'key':repr(key),'front':entry['renderer'].front,
  'ids':entry['renderer'].ids,'visible':entry['renderer'].visible,
  'uniforms':entry['renderer'].uniforms,'poses':entry['renderer'].poses,
  'doll_positions':[ref.current.GetGlobalPosition() for ref in entry['dolls']],
  'doll_sizes':[ref.current.GetSize() for ref in entry['dolls']]}
  for key,entry in controls.registry.items()
  if entry.get('renderer')] if controls else []})
'''
CAMERA = '''cam=b.factory.CreateCamera(b.level)
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'screen':b.factory.CreateGame(b.level).GetScreenSize(),'fov':cam.GetFov()})
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    def redact(row):
        if isinstance(row, dict):
            return {key:redact(data) for key,data in row.items() if key not in ('token','title')}
        if isinstance(row, (list,tuple)):
            return [redact(data) for data in row]
        return row
    (OUTPUT/name).write_text(json.dumps(redact(value), ensure_ascii=True, indent=2)+'\n', encoding='ascii')


def find_session():
    rows = [json.loads(path.read_bytes()) for path in _session.registry_dir().glob('*/session.json')]
    rows = [row for row in rows if row.get('owner')==OWNER and Path(row.get('project','')).resolve()==ROOT]
    if len(rows)>1:
        raise RuntimeError('Ambiguous owner sessions')
    return rows[0] if rows else None


def world_matrix(check, client, session, report):
    saved=check.run("_result={'origin':s.origin,'missing':s.projection_missing,'outline':s.projection_outline}")
    position=None
    wrote=False
    def server(code):
        response=client.call('execute_code',{'code':
            "import mod.server.extraServerApi as serverApi\nplayers=serverApi.GetPlayerList()\n"
            "assert len(players)==1\nfrom modern_projection.server_system import WorldAdapter\n"
            "adapter=WorldAdapter(players[0])\n"+code,'is_client':False,'direct_return':True})
        if response.get('isError'):
            raise RuntimeError(response)
        return return_value(response)
    state_source='''companion=b.projection_liquid
owners=getattr(companion,'companions',(companion,)) if companion else ()
item_owners=[item for item in owners if item.__class__.__name__=='ItemProjection']
_result=json.dumps({'active':s.projection_active,'preparing':bool(b.preparing_entity),
 'groups':sum(len(item.renderer.active) for item in item_owners),
 'slots':sum(int(row['group'].uniforms[3][1]) for item in item_owners for row in item.renderer.active.values()),
 'origin':s.origin,'groups_data':[{'key':repr(row['group'].key),'origin':row['group'].origin,
  'uniforms':row['group'].uniforms,'anchor':row['anchor'],'visible':row['visible']}
  for item in item_owners for row in item.renderer.active.values()],
 'error':str(companion.error or companion.renderer.error) if companion and (companion.error or companion.renderer.error) else '',
 'occupied':list(b.projection_occupancy.state) if b.projection_occupancy else None,
 'pending_pair':bool(b.projection_occupancy and b.projection_occupancy.pending_pair)})
'''
    def sample(label, expected_slots):
        state=check.wait(label,lambda value:value['active'] and not value['preparing']
                         and value['slots']==expected_slots and not value['error'] and not value['pending_pair'],
                         lambda:check.run(state_source))
        save(label+'.state.json',state)
        camera_before=check.run(CAMERA)
        image=capture(session['session_file'],OWNER,OUTPUT/(label+'.png'),WGC)
        camera_after=check.run(CAMERA)
        report['captures'].append({'label':label,'capture':image,'state':state,
            'camera_before':camera_before,'camera_after':camera_after,
            'camera_expected':report['world_camera']})
        save('report.json',report)
        return state
    try:
        position=check.run("foot=b.player_origin()\ns.origin=(foot[0]+4,foot[1]+6,foot[2]+4)\n"
            "s.projection_missing=False\ns.projection_outline=False\ns.emit()\n"
            "b.project()\n_result=tuple(s.origin[axis]+(10,2,3)[axis] for axis in range(3))")
        check.wait('world item build',lambda value:value['active'] and not value['preparing']
                   and value['slots']==4 and not value['error'],lambda:check.run(state_source))
        check.run("navigator.pop()\n_result=True")
        check.wait('closed editor',lambda value:not value['open'] and not value['transition'],check.navigation)
        report['world_camera']=check.run("cam=b.factory.CreateCamera(b.level)\ncam.DepartCamera()\n"
            "from modern_projection.projection.debug_item_blueprints import VISUAL_CASE\n"
            "center=tuple(s.origin[axis]+s.editor.document.size[axis]*.5 for axis in range(3))\n"
            "offset=VISUAL_CASE['camera']['world_offset']\n"
            "camera_pos=tuple(center[axis]+offset[axis] for axis in range(3))\n"
            "rotation=api.GetRotFromDir(tuple(center[axis]-camera_pos[axis] for axis in range(3)))\n"
            "cam.SetCameraPos(camera_pos)\ncam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))\n"
            "_result={'position':camera_pos,'target':center,'rotation':(rotation[0],rotation[1]+180.,0.),"
            "'screen':b.factory.CreateGame(b.level).GetScreenSize(),'fov':cam.GetFov()}")
        time.sleep(1.)
        for index in range(3):
            time.sleep(.8)
            sample('world_full_'+str(index),4)
        check.run("companion=b.projection_liquid\nowners=getattr(companion,'companions',(companion,))\n"
            "items=[item for item in owners if item.__class__.__name__=='ItemProjection']\n"
            "assert len(items)==1\nassert not hasattr(sys,'_item_world_qa_muted')\n"
            "sys._item_world_qa_muted=items[0]\nassert items[0].renderer.set_visible(False)\n_result=True")
        try:
            sample('world_full_items_hidden',4)
        finally:
            check.run("assert sys._item_world_qa_muted.renderer.set_visible(True)\n"
                      "del sys._item_world_qa_muted\n_result=True")
        check.run('b.toggle_missing()\n_result=True')
        sample('world_missing_air',4)
        server("from modern_projection.projection.cell import AIR\n"
               "position="+repr(tuple(position))+"\nassert adapter.read(position)==AIR\n_result=True")
        # The only native block mutation is a confirmed-air cell in this owned test world.
        wrote=True
        server("adapter.write("+repr(tuple(position))+",('minecraft:stone',0))\n_result=True")
        report['world_test_cell']=list(position)
        save('report.json',report)
        check.run('b.projection_interaction('+repr(tuple(position))+')\n_result=True')
        sample('world_missing_occupied',3)
        server("adapter.write("+repr(tuple(position))+",('minecraft:air',0))\n_result=True")
        wrote=False
        check.run('b.projection_interaction('+repr(tuple(position))+')\n_result=True')
        sample('world_missing_restored',4)
        report['native_world_acceptance']='fresh full/missing/occupied/restored captures require pixel scoring'
    finally:
        if wrote:
            server("adapter.write("+repr(tuple(position))+",('minecraft:air',0))\n_result=True")
        if position is not None:
            report['world_cell_restored']=server("from modern_projection.projection.cell import AIR\n_result=adapter.read("+repr(tuple(position))+")==AIR")
        check.run("b.stop_projection()\ncam=b.factory.CreateCamera(b.level)\n"
                  "cam.ResetCameraPos()\ncam.UnDepartCamera()\n"
                  "s.origin="+repr(tuple(saved['origin']))+"\ns.projection_missing="+repr(saved['missing'])+"\n"
                  "s.projection_outline="+repr(saved['outline'])+"\nowner.open_workspace()\n_result=True")
        report['world_models_released']=check.run('_result=b.projection_liquid is None and not b.projection_retired_liquids')
        save('report.json',report)


def main(with_world=False, camera_calibration=None, with_closeup=False, native_reference=False):
    os.environ['MCDEV_ALLOW_USER_FOREGROUND']='1'
    OUTPUT.mkdir(parents=True, exist_ok=False)
    for path, expected in PINS.items():
        if sha(path)!=expected:
            raise ValueError('Background startup pin changed: '+str(path))
    calibration = ({'path':str(camera_calibration.resolve()), 'sha256':sha(camera_calibration),
                    'data':json.loads(camera_calibration.read_bytes())}
                   if camera_calibration is not None else None)
    inputs=snapshot_sources(ROOT)
    config_path=ROOT/'.mcdev.json'
    if config_path.exists():
        raise ValueError('Worktree launch config must be absent')
    config={'included_mod_dirs':[str(ROOT)],'world_type':2,'world_seed':0,'game_mode':1,
            'auto_hot_reload_mods':False,'auto_hot_reload_ui':False,
            'auto_hot_reload_materials':False,'auto_hot_reload_shaders':False}
    config_path.write_text(json.dumps(config,indent=2)+'\n',encoding='ascii')
    config_sha=sha(config_path)
    report={'schema':2,'completed':False,'background_only':False,'fixture':'test.entities.item_contents',
            'user_foreground_allowed':True,'agent_activation_allowed':False,
            'foreground_policy':'allow_user_foreground','guarded_no_activation':True,
            'world_requested':with_world,
            'launches':0,'cleanup_errors':[],'captures':[],'checks':[],
            'production_qualified':False,'pins':{str(p):h for p,h in PINS.items()},
            'launch_inputs':inputs,'launch_inputs_sha256':snapshot_digest(inputs),
            'source':subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip()}
    if calibration is not None:
        report['camera_calibration']=calibration
    started=time.monotonic()
    launcher=session=None
    installed=environment_saved=False
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
                    guard['identity_matches']=bool(session.get('game_identity') and
                        _session.process_identity(session['game_pid'])==session['game_identity'])
                    report['checks'].append({'seconds':time.monotonic()-started,'guard':guard})
                    save('report.json',report)
                    if not guard['identity_matches'] or guard['windows'] and not guard['window_noactivate']:
                        raise RuntimeError('Background startup guard failed')
                time.sleep(.5)
            if launcher.poll() is None:
                raise TimeoutError('Bounded startup did not finish')
        session=find_session()
        if session is None or not session.get('ready'):
            raise RuntimeError('Startup did not reach ready: '+str(session.get('error') if session else 'missing session'))
        report['session']=session
        os.environ.update(MCDEV_SESSION_FILE=session['session_file'],MCDEV_OWNER=OWNER)
        with Client(timeout=15) as client:
            check=BlueprintCheck(client,OUTPUT/'blueprints.json',45)
            check.wait('actual workspace initialization',lambda value:bool(value),lambda: return_value(
                client.call('execute_code',{'code':"import mod.client.extraClientApi as api\nowner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')\n_result=owner is not None and owner.session is not None\n",'is_client':True,'direct_return':True})))
            check.run(INSTALL_PROBE)
            installed=True
            report['environment']=run_environment(client,SETUP_ENVIRONMENT)
            environment_saved=True
            check.run('from modern_projection.projection.item_sprite_profile import candidate_profile\n'
                      'assert not hasattr(sys,"_item_product_saved_profile")\n'
                      'sys._item_product_saved_profile=s.item_profile\n'
                      's.item_profile=candidate_profile()\n_result=True')
            if with_world:
                calibrated=calibrate(check,session,OWNER,OUTPUT,WGC,save)
                calibration_path=OUTPUT/'camera.json'
                report['camera_calibration']={'path':str(calibration_path.resolve()),
                    'sha256':sha(calibration_path),'data':calibrated}
                if calibrated['cleanup_errors']:
                    raise RuntimeError('Independent camera cleanup failed')
            def native_capture(label, tree=None):
                if label=='test_entities_item_contents':
                    expected_pose=check.run('from modern_projection.projection.debug_item_blueprints import VISUAL_CASE\n'
                              's.camera_view(*VISUAL_CASE["camera"]["editor"])\n'
                              '_result=VISUAL_CASE["camera"]["editor"]')
                    check.wait('source-facing camera',lambda pose:len(pose)==len(expected_pose) and
                        all(abs(a-b)<.0001 for a,b in zip(pose,expected_pose)),
                        lambda:check.run('_result=s.camera_pose'))
                state=(check.run(STATE) if label=='testing_page' else
                       check.wait('item controls '+label,lambda value:value['plan_ready'] and
                                  not value['pending'] and not value['error'],lambda:check.run(STATE)))
                save(label+'.state.json',state)
                if tree is not None:
                    save(label+'.tree.json',tree)
                result=capture(session['session_file'],OWNER,OUTPUT/(label+'.png'),WGC)
                after=check.run(STATE)
                report['captures'].append({'label':label,'capture':result,'state':state,'state_after':after})
                save('report.json',report)
                return result
            check.capture=native_capture
            check.page()
            report['fixture_state']=check.fixture('test.entities.item_contents')
            for index in range(3):
                time.sleep(.8)
                native_capture('editor_temporal_'+str(index))
            check.run("assert not hasattr(sys,'_item_qa_muted')\n"
                "sys._item_qa_muted=(s.item_controls,s.item_controls.closed,"
                "[(entry['renderer'],tuple(entry['renderer'].visible)) for entry in s.item_controls.registry.values()])\n"
                "s.item_controls.closed=True\n"
                "for renderer,visible in sys._item_qa_muted[2]:\n"
                " for slot in (0,1):renderer._show(slot,False)\n_result=True")
            try:
                native_capture('editor_items_hidden')
            finally:
                check.run("controls,closed,rows=sys._item_qa_muted\n"
                    "for renderer,visible in rows:\n"
                    " for slot in (0,1):renderer._show(slot,visible[slot])\n"
                    "controls.closed=closed\ndel sys._item_qa_muted\n_result=True")
            check.run("from modern_projection.projection.cell import AIR\n"
                      "from modern_projection.projection.native_appearance import FRAME_NAMES\n"
                      "from modern_projection.projection.cell import foreground\n"
                      "changes=dict((pos,AIR) for pos,cell in s.editor.document.blocks.items() if foreground(cell)[0] in FRAME_NAMES)\n"
                      "assert s.editor._commit('Item regression remove',changes,respect_selection=False,whole=True)==6\n"
                      "s.refresh_preview()\ns.emit()\n_result=True")
            native_capture('editor_removed')
            check.run('assert s.editor.undo()\ns.refresh_preview()\ns.emit()\n_result=True')
            native_capture('editor_undo')
            check.run('s.editor.layer=1\ns.display_mode("section")\n_result=True')
            native_capture('editor_cutaway')
            check.run('s.display_mode("full")\n_result=True')
            native_capture('editor_cutaway_restored')
            if with_world:
                world_matrix(check,client,session,report)
            if with_closeup:
                run_closeup(check,client,session,report,STATE,CAMERA,OUTPUT,WGC,save,native_reference)
            report['logs']=client.call('get_latest_error_logs',{'max_count':40})
            report['completed']=True
            if not with_world:
                report['native_world_acceptance']='pending; editor diagnostic run only'
            save('report.json',report)
            if installed:
                check.run(RESTORE)
                installed=False
                check.run('s.item_profile=sys._item_product_saved_profile\n'
                          'del sys._item_product_saved_profile\nnavigator.pop()\n_result=True')
            if environment_saved:
                report['environment_restored']=run_environment(client,RESTORE_ENVIRONMENT)
                environment_saved=False
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
        report['inputs_after']=snapshot_sources(ROOT)
        report['source_unchanged']=report['launch_inputs']==report['inputs_after']
        if session:
            log_path=Path(session['session_file']).parent/'mcdk.log'
            if log_path.exists():
                lines=log_path.read_text(encoding='utf8',errors='replace').splitlines()
                report['native_shader_errors']=[{'line':index+1,'shader':line.split('Compiler error ',1)[1],
                    'detail':lines[index+1] if index+1<len(lines) else ''}
                    for index,line in enumerate(lines)
                    if 'Compiler error shaders/glsl/modern_projection_item_sprite' in line]
        save('report.json',report)
    print(json.dumps({k:report.get(k) for k in ('completed','error','elapsed_seconds','cleanup_errors')},ensure_ascii=True))
    return 0 if report['completed'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',default='v1')
    parser.add_argument('--world',action='store_true',help='Also test full/missing projection and one restored occupied cell')
    parser.add_argument('--camera-calibration',type=Path,
                        help='Independent world camera calibration required by pixel scoring')
    parser.add_argument('--closeup',action='store_true',help='Also record enlarged ordinary/enchanted/empty controls for at least seven seconds per route')
    parser.add_argument('--native-reference',action='store_true',help='Compare closeup against SDK-written actual frame blocks and typed item readback')
    args=parser.parse_args()
    if not args.run_id or any(char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for char in args.run_id):
        parser.error('run-id must contain only ASCII letters, numbers, hyphens or underscores')
    OWNER='item-product-r14-'+args.run_id
    OUTPUT=ROOT/'.runtime'/OWNER
    if args.closeup and not args.world:
        parser.error('--closeup requires --world for independent calibration')
    if args.native_reference and not args.closeup:
        parser.error('--native-reference requires --closeup')
    sys.exit(main(args.world,args.camera_calibration,args.closeup,args.native_reference))
