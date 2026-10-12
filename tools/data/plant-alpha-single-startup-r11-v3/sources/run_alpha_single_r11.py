"""One externally bounded alpha control with identity-bound cleanup."""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
from ctypes import wintypes

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parents[1]
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
OWNER = 'snow-r11-position'
NAME = 'snow-alpha-single-slot3-r11-v3'
PLAN = SHARED / '.runtime/plant-contract-r11/marked-poppy-plan-v1.json'
REPORT = ROOT / '.runtime/alpha-single-supervisor-r11-v3.json'
SNAPSHOT = ROOT / '.runtime/poppy-alpha-marker-r11-v3.json'
ARCHIVE = ROOT / '.runtime/alpha-single-original-bytes-r11-v3'
EXE = SHARED / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
DLL = SHARED / '.runtime/worktree-archive-r7/p0-integration/files/.runtime/native_focus_guard-final-r7/native_focus_guard.dll'
CAPTURE = SHARED / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
EXPECTED = {
    EXE: 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9',
    DLL: 'c22fa0cd0bdbfb7d9218d59573b61619111f9bd180562c9bd51c69276c11c178',
    CAPTURE: 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8',
    PLAN: 'cc3852cb22b99d676521e2d91bbf50d814e1464b736ff7ea7e6a11093aa67641',
}
COPY = {
    SCRIPTS / 'instances.py': SHARED / '.agents/skills/pyreact-debugging/scripts/instances.py',
    SCRIPTS / 'mcdk.py': SHARED / '.agents/skills/pyreact-debugging/scripts/mcdk.py',
    ROOT / '.mcdev.json': SHARED / '.runtime/r11-native/.mcdev.json',
}
COPY_SHA = ['284bd59957c6cb26f69faf6d87272cedf00d0d442bb75bbcefb1c4a7957e8096',
            '3e0e8fe912e12eb6448dfbc29ae8908ae2b55d68764b10ac476b588d166f52c3',
            'c3cbfd069298f2971d0041ad08bddcb567bcf23b1804be45204e8aed29231cfc']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


class IO(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in
                ('ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
                 'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]


class Limits(ctypes.Structure):
    _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64), ('PerJobUserTimeLimit', ctypes.c_int64),
                ('LimitFlags', wintypes.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wintypes.DWORD),
                ('Affinity', ctypes.c_size_t), ('PriorityClass', wintypes.DWORD),
                ('SchedulingClass', wintypes.DWORD)]


class Extended(ctypes.Structure):
    _fields_ = [('BasicLimitInformation', Limits), ('IoInfo', IO),
                ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]


def bounded(command, timeout, env=None, child_job=False):
    job = None
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    if child_job:
        job = kernel.CreateJobObjectW(None, None)
        limits = Extended()
        limits.BasicLimitInformation.LimitFlags = 0x2000
        if not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ctypes.WinError(ctypes.get_last_error())
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, encoding='utf8',
                               creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        if job and not kernel.AssignProcessToJobObject(job, wintypes.HANDLE(process._handle)):
            process.kill()
            process.communicate(timeout=5)
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            out, err = process.communicate(timeout=timeout)
            return {'returncode': process.returncode, 'stdout': out, 'stderr': err, 'timeout': False}
        except subprocess.TimeoutExpired:
            if job:
                kernel.CloseHandle(job)
                job = None
            else:
                process.kill()
            out, err = process.communicate(timeout=5)
            return {'returncode': process.returncode, 'stdout': out, 'stderr': err, 'timeout': True}
    finally:
        if job:
            kernel.CloseHandle(job)


def health(output):
    sys.path.insert(0, str(SCRIPTS))
    from mcdk import Client, return_value
    from _session import load_session
    from _window import background_guard_state
    session = load_session(live=True)
    report = {'schema': 1, 'passed': False, 'fixture_mutation_attempted': False,
              'timer_cleanup_verified': False, 'render_progress_proven': False, 'requests': []}
    pending = False
    def execute(client, code, side):
        row = {'code': code, 'is_client': side, 'started_at': now()}
        report['requests'].append(row)
        save(output, report)
        try:
            response = client.call('execute_code', {'code': code, 'is_client': side, 'direct_return': True})
            row['response'] = response
            value = return_value(response)
            return json.loads(value) if isinstance(value, str) else value
        finally:
            row['finished_at'] = now()
            save(output, report)
    try:
        guard = background_guard_state(session['game_pid'], Path(session['game_executable']).name)
        report['guard'] = guard
        assert guard['background_safe'] and guard['window_noactivate']
        assert guard['windows'] and all(not w['minimized'] and w['width'] >= 640 and w['height'] >= 360
                                       for w in guard['windows'])
        with Client(timeout=5) as client:
            for side, module, api_name in ((True, 'client', 'Client'), (False, 'server', 'Server')):
                nonce = uuid.uuid4().hex
                code = ("import json,os,sys,time\nimport mod.%s.extra%sApi as api\n"
                        "_result=json.dumps({'runtime':api.GetMinecraftVersion(),'pid':os.getpid(),"
                        "'token':getattr(sys,'_pyreact_mcdk_session',None),'nonce':%r,'clock':time.clock()})"
                        % (module, api_name, nonce))
                identity = execute(client, code, side)
                assert identity['pid'] == session['game_pid'] and identity['token'] == session['token']
                assert identity['nonce'] == nonce and identity['runtime'] == '1.21.120.0'
                report[module] = identity
            pending = True
            report['timer_start'] = execute(client, """import json,sys,time
import mod.server.extraServerApi as api
assert not hasattr(sys,'_snow_r11_alpha_timer')
state={'started':time.time(),'callbacks':[]}
sys._snow_r11_alpha_timer=state
game=api.GetEngineCompFactory().CreateGame(api.GetLevelId())
game.AddTimer(.2,lambda current=state:current['callbacks'].append(time.time()))
game.AddTimer(.4,lambda current=state:current['callbacks'].append(time.time()))
_result=json.dumps({'started':state['started']})""", False)
            time.sleep(.8)
            report['timer_stop'] = execute(client, """import json,sys,time
state=sys._snow_r11_alpha_timer
observed={'started':state['started'],'callbacks':list(state['callbacks']),'now':time.time()}
del sys._snow_r11_alpha_timer
observed['restored']=not hasattr(sys,'_snow_r11_alpha_timer')
_result=json.dumps(observed)""", False)
            pending = False
            stop = report['timer_stop']
            report['timer_cleanup_verified'] = stop['restored']
            assert len(stop['callbacks']) == 2 and stop['started'] < stop['callbacks'][0] < stop['callbacks'][1] <= stop['now']
            assert report['timer_cleanup_verified']
            report['passed'] = True
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
    finally:
        if pending:
            try:
                with Client(timeout=3) as client:
                    report['timer_cleanup'] = execute(client,
                        "import sys\nif hasattr(sys,'_snow_r11_alpha_timer'):del sys._snow_r11_alpha_timer\n_result=True", False)
                    report['timer_cleanup_verified'] = report['timer_cleanup'] is True
            except Exception as error:
                report['timer_cleanup_error'] = str(error)
        save(output, report)
    print(json.dumps({'passed': report['passed'], 'timer_cleanup_verified': report['timer_cleanup_verified']}))
    return 0 if report['passed'] else 1


def main():
    report = {'schema': 1, 'owner': OWNER, 'name': NAME, 'started_at': now(),
              'production_acceptance': False, 'marker_pixels_verified': False, 'phases': [],
              'total_run_timeout_seconds': 150, 'launches': 0, 'backup': [], 'cleanup_errors': []}
    if REPORT.exists() or SNAPSHOT.exists() or ARCHIVE.exists():
        raise ValueError('Supervisor evidence must be fresh')
    session = None
    marker = None
    started = None
    def phase(label, command, env=None, job=True):
        remaining = 150 - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError('Total run deadline reached')
        row = {'label': label, 'command': command, 'started_at': now(), 'timeout_seconds': remaining}
        report['phases'].append(row)
        save(REPORT, report)
        row.update(bounded(command, remaining, env, job))
        row['finished_at'] = now()
        save(REPORT, report)
        if row['timeout'] or row['returncode']:
            raise RuntimeError('Bounded phase failed: ' + label)
        return row
    try:
        for path, expected in EXPECTED.items():
            assert sha(path) == expected, str(path)
        ARCHIVE.mkdir()
        for index, (target, source) in enumerate(COPY.items()):
            assert sha(source) == COPY_SHA[index], str(source)
            backup = ARCHIVE / target.name
            shutil.copyfile(target, backup)
            report['backup'].append({'target': str(target), 'backup': str(backup), 'sha256': sha(backup)})
            shutil.copyfile(source, target)
            assert sha(target) == COPY_SHA[index]
        report['frozen_sources'] = {str(p): sha(p) for p in [*EXPECTED, *COPY, Path(__file__), ROOT/'tools/verify_marked_native_plant.py',
                                                           ROOT/'tools/verify_camera_projection.py', ROOT/'tools/capture_native_window.py']}
        sys.path.insert(0, str(SCRIPTS))
        sys.path.insert(0, str(ROOT/'tools'))
        from _session import registry_dir, process_identity
        import prepare_marked_native_plant as marker
        live = []
        for path in registry_dir().glob('*/session.json'):
            data = json.loads(path.read_bytes())
            if data.get('game_pid') and process_identity(data['game_pid']) == data.get('game_identity'):
                live.append({'id': data['id'], 'owner': data['owner'], 'pid': data['game_pid']})
        report['live_before'] = live
        assert len(live) <= 4, live
        report['marker'] = marker.prepare(PLAN, SNAPSHOT)
        assert report['marker']['native_alpha_sha256'] == report['marker']['candidate_alpha_sha256']
        started = time.monotonic()
        report['launches'] = 1
        launch = phase('launch', [sys.executable, '-X', 'utf8', str(SCRIPTS/'instances.py'), 'start',
            '--project', str(ROOT), '--owner', OWNER, '--name', NAME, '--mcdk', str(EXE),
            '--noactivate-dll', str(DLL), '--noactivate-sha256', EXPECTED[DLL],
            '--noactivate-mcdk-sha256', EXPECTED[EXE], '--wait', '60'], job=False)
        session = json.loads(launch['stdout'])
        report['session'] = {k: session[k] for k in ('id','session_file','artifacts','game_pid','game_identity','mcdk_pid','mcdk_identity','owner','project')}
        print(json.dumps({'session': report['session']}), flush=True)
        assert session['ready'] and session['owner'] == OWNER and Path(session['project']).resolve() == ROOT
        env = os.environ.copy()
        env.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=OWNER,
                   MCDEV_MCP_URL=session['mcp_url'], MCDEV_GAME_PID=str(session['game_pid']),
                   MCDEV_NATIVE_CAPTURE_HELPER=str(ROOT/'tools/capture_native_window.py'),
                   MCDEV_NATIVE_CAPTURE_EXE=str(CAPTURE))
        artifacts = Path(session['artifacts'])
        phase('runtime_health', [sys.executable,'-X','utf8',str(Path(__file__)),'--health',
                                 str(artifacts/'snow-alpha-runtime-health-r11-v3.json')], env)
        camera = artifacts/'snow-camera-alpha-single-r11-v3.json'
        phase('camera', [sys.executable,'-X','utf8',str(ROOT/'tools/verify_camera_projection.py'),
                         str(camera),'--native-resolution','--timeout','15','--skyward-tilted','--fixture-lift-y','24'], env)
        phase('alpha_single', [sys.executable,'-X','utf8',str(ROOT/'tools/verify_marked_native_plant.py'),
            str(artifacts/'poppy-alpha-single-r11-v3.json'),'--plan',str(PLAN),
            '--camera-calibration',str(camera),'--marker-snapshot',str(SNAPSHOT),
            '--stage','alpha_marker','--partition','calibration','--single-positive-control'], env)
        report['observation_completed'] = True
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
        report['observation_completed'] = False
    finally:
        sys.path.insert(0, str(SCRIPTS))
        from _session import registry_dir, process_identity
        if session is None:
            for path in registry_dir().glob('*/session.json'):
                data = json.loads(path.read_bytes())
                if data.get('name') == NAME and data.get('owner') == OWNER and Path(data['project']).resolve() == ROOT:
                    session = data
                    break
        if session:
            report['session'] = {k: session.get(k) for k in ('id','session_file','artifacts','game_pid','game_identity','mcdk_pid','mcdk_identity','owner','project')}
            command = [sys.executable,'-X','utf8',str(SCRIPTS/'instances.py'),'stop',
                       '--session',session['session_file'],'--owner',OWNER]
            try:
                report['normal_stop'] = bounded(command, 22)
                alive = [kind for kind in ('game','mcdk') if session.get(kind+'_pid') and
                         process_identity(session[kind+'_pid']) == session.get(kind+'_identity')]
                if alive:
                    report['force_stop_after_inspection'] = {'live_owned_kinds': alive, 'result': bounded(command+['--force'], 15)}
                report['owned_processes_dead'] = all(not session.get(k+'_pid') or
                    process_identity(session[k+'_pid']) != session.get(k+'_identity') for k in ('game','mcdk'))
            except Exception as error:
                report['cleanup_errors'].append('stop: '+str(error))
        if SNAPSHOT.exists() and marker:
            try:
                report['marker_restore'] = marker.restore(SNAPSHOT)
                report['marker_override_absent'] = not (ROOT/'resource_pack/textures/blocks/flower_rose.png').exists()
            except Exception as error:
                report['cleanup_errors'].append('marker: '+str(error))
        for backup in report['backup']:
            try:
                shutil.copyfile(backup['backup'], backup['target'])
                backup['restored'] = sha(Path(backup['target'])) == backup['sha256']
                assert backup['restored']
            except Exception as error:
                report['cleanup_errors'].append('file: '+str(error))
        report['native_texture_unchanged'] = sha(Path(json.loads(PLAN.read_bytes())['texture_source']['installed_path'])) == json.loads(PLAN.read_bytes())['texture_source']['sha256']
        report['finished_at'] = now()
        report['run_elapsed_seconds'] = time.monotonic()-started if started else None
        save(REPORT, report)
    print(json.dumps({'supervisor': str(REPORT), 'observation_completed': report['observation_completed'],
                      'owned_processes_dead': report.get('owned_processes_dead'), 'cleanup_errors': report['cleanup_errors']}))
    return 0 if report['observation_completed'] and not report['cleanup_errors'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--health', type=Path)
    args = parser.parse_args()
    sys.exit(health(args.health) if args.health else main())
