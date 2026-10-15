"""One scheduled low-memory banner pose launch with exact retained-process observation."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
sys.path[:0] = [str(HERE), str(SCRIPTS), str(ROOT / 'tools')]
import run as probe
import instances
from _session import load_session, process_identity
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from watch_intrinsic_glint_exit_r21 import watch

OWNER, PROJECT, OUTPUT = probe.OWNER, probe.PROJECT, probe.OUTPUT
CONTROL = OUTPUT / 'runtime-launch'
MANIFEST = OUTPUT / 'launcher-inputs.json'
BINARIES = {
    'mcdk': ROOT / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe',
    'dll': ROOT / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll',
    'game': Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/Minecraft.Windows.exe')}
APPROVED = {
    'mcdk': 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9',
    'dll': '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93'}
STOP_DEPENDENCIES = (
    '.runtime/banner-scale-control-r21/host.py',
    '.agents/skills/pyreact-debugging/scripts/instances.py',
    '.agents/skills/pyreact-debugging/scripts/_session.py',
    '.agents/skills/pyreact-debugging/scripts/_window.py',
    '.agents/skills/pyreact-debugging/scripts/mcdk.py',
    '.agents/skills/pyreact-debugging/scripts/setup_mcdk.py')
read, sha, save = probe.prepare.read, probe.prepare.sha, probe.prepare.save


def dependencies():
    paths = {Path(__file__).resolve()}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if name != '__main__' and filename:
            path = Path(filename).resolve()
            if path.is_file() and path.is_relative_to(ROOT):
                paths.add(path)
    paths.add(ROOT / '.runtime/shield_instances_native_discovery_r20.py')
    return {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(paths)}


def freeze():
    plan = probe.validate_inputs()
    assert not MANIFEST.exists() and not CONTROL.exists()
    save(MANIFEST, {'schema': 1, 'owner': OWNER, 'project': str(PROJECT),
        'source_sha256': plan['source_sha256'], 'plan_sha256': sha(OUTPUT / 'plan.json'),
        'dependency_sha256': dependencies(),
        'binary_sha256': {name: sha(path) for name, path in BINARIES.items()},
        'maximum_active_mc': 2, 'minimum_free_commit_gib': 6,
        'handle_boundary': 210000, 'automatic_start': False, 'automatic_replay': False,
        'force_stop': False, 'retain_host_exec_until_both_exit': True,
        'all_four_reload_flags_false': True, 'agent_activation_allowed': False})
    validate()
    print(json.dumps({'frozen': True, 'owner': OWNER, 'source_sha256': plan['source_sha256'],
                      'dependency_count': len(dependencies()), 'runtime_started': False}))


def validate(host_only=False):
    frozen = read(MANIFEST)
    assert frozen['owner'] == OWNER
    assert Path(frozen['project']).resolve() == PROJECT.resolve()
    current = dependencies()
    if host_only:
        assert all(current[name] == frozen['dependency_sha256'][name] for name in STOP_DEPENDENCIES)
        return frozen
    assert frozen['dependency_sha256'] == current, 'Frozen host dependency changed'
    plan = probe.validate_inputs()
    assert frozen['source_sha256'] == plan['source_sha256']
    assert frozen['plan_sha256'] == sha(OUTPUT / 'plan.json')
    for name, path in BINARIES.items():
        assert sha(path) == frozen['binary_sha256'][name]
        if name in APPROVED:
            assert sha(path) == APPROVED[name]
    return frozen


def census():
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
        '@(Get-CimInstance Win32_Process -Filter "Name=\'Minecraft.Windows.exe\'" | '
        'Select-Object ProcessId,HandleCount) | ConvertTo-Json -Compress'],
        capture_output=True, encoding='utf-8-sig', check=True, timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW)
    rows = json.loads(result.stdout or '[]')
    if not isinstance(rows, list):
        rows = [rows]
    for row in rows:
        row['identity'] = process_identity(row['ProcessId'])
    return [row for row in rows if row['identity'] is not None]


def resources(prelaunch=False):
    row = {'at': datetime.now(timezone.utc).isoformat(), 'games': census(),
           'commit': commit_at_boundary(), 'prelaunch': prelaunch}
    assert len(row['games']) <= (1 if prelaunch else 2), 'Global MC budget'
    assert row['commit']['commit_available_bytes'] >= 6 * 1024 ** 3, 'Free commit below 6 GiB'
    if not prelaunch:
        session = bound(live=True)
        own = [game for game in row['games'] if game['ProcessId'] == session['game_pid']
               and game['identity'] == session['game_identity']]
        assert len(own) == 1 and own[0]['HandleCount'] < 210000
    return row


def bound(live=False):
    ready = read(CONTROL / 'ready-summary.json')
    session = load_session(ready['session_file'], OWNER, live=live)
    assert Path(session['project']).resolve() == PROJECT.resolve()
    for key in ('id', 'owner', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity'):
        assert ready[key] == session[key]
    return session


def alive(session):
    return {kind: process_identity(session[kind + '_pid']) == session[kind + '_identity']
            for kind in ('game', 'mcdk')}


def launch(scheduled):
    assert scheduled, 'The parent schedules this one-shot launch'
    validate()
    assert not (CONTROL / 'start-request.json').exists(), 'Never replay this launch'
    guard = resources(prelaunch=True)
    CONTROL.mkdir(exist_ok=True)
    save(CONTROL / 'start-request.json', {'at': datetime.now(timezone.utc).isoformat(),
        'owner': OWNER, 'project': str(PROJECT), 'resources': guard, 'replay_allowed': False})
    command = [sys.executable, '-B', '-X', 'utf8',
        str(ROOT / '.runtime/shield_instances_native_discovery_r20.py'), 'start',
        '--project', str(PROJECT), '--owner', OWNER, '--name', OWNER, '--wait', '180',
        '--preset', 'ui', '--game-exe', str(BINARIES['game']), '--mcdk', str(BINARIES['mcdk']),
        '--noactivate-mcdk-sha256', APPROVED['mcdk'], '--noactivate-dll', str(BINARIES['dll']),
        '--noactivate-sha256', APPROVED['dll']]
    record = {'at': datetime.now(timezone.utc).isoformat(), 'replay_allowed': False}
    try:
        with (CONTROL / 'start.stdout.json').open('xb') as stdout, (CONTROL / 'start.stderr.txt').open('xb') as stderr:
            result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr,
                env=dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND='1'),
                creationflags=subprocess.CREATE_NO_WINDOW)
        record['returncode'] = result.returncode
    except BaseException as error:
        record['error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        save(CONTROL / 'start-result.json', record)
    assert result.returncode == 0, 'Preserve failed startup; never replay'
    startup = read(CONTROL / 'start.stdout.json')
    session = load_session(startup['session_file'], OWNER, live=True)
    assert Path(session['project']).resolve() == PROJECT.resolve()
    assert all(read(Path(session['session_file']).parent / '.mcdev.json')[key] is False
               for key in probe.prepare.RELOADS)
    for key in ('id', 'owner', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity'):
        assert startup[key] == session[key]
    protection = session['noactivation']
    assert protection['requested'] and protection['agent_activation_allowed'] is False
    for name in APPROVED:
        assert protection[name]['sha256'] == APPROVED[name]
        assert Path(protection[name]['path']).resolve() == BINARIES[name].resolve()
    ready = {key: session[key] for key in ('id', 'owner', 'project', 'session_file', 'state',
             'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')}
    save(CONTROL / 'ready-summary.json', ready)
    print(json.dumps({'ready': ready, 'keep_this_host_exec_alive': True}), flush=True)
    result = watch(Path(ready['session_file']), OWNER, CONTROL / 'exact-exit.json')
    print(json.dumps({'exact_exit_completed': result['completed'],
                      'processes': result['processes'], 'normal_lifecycle_accepted': False}), flush=True)


def stop():
    validate(host_only=True)
    session = bound()
    attempted = (CONTROL / 'stop-request.json').exists()
    if attempted:
        assert not any(alive(session).values()), 'Normal close already sent; do not resend while live'
    label = 'finalize' if attempted else 'stop'
    save(CONTROL / (label + '-request.json'), {'at': datetime.now(timezone.utc).isoformat(),
         'owner': OWNER, 'process_alive': alive(session), 'force': False})
    record = {'owner': OWNER, 'force': False, 'completed': False}
    try:
        result = instances.stop(session, False)
        record.update(state=result['state'], process_alive=alive(session))
        assert result['state'] == 'stopped' and not any(record['process_alive'].values())
        record['completed'] = True
    except BaseException as error:
        record['error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        save(CONTROL / (label + '-result.json'), record)
    print(json.dumps(record))


def status():
    validate(host_only=True)
    row = {'owner': OWNER, 'started': (CONTROL / 'start-request.json').exists(), 'mutations': False}
    if (CONTROL / 'ready-summary.json').exists():
        session = bound()
        row.update(state=session['state'], process_alive=alive(session))
    if (CONTROL / 'exact-exit.json').exists():
        row['exact_exit'] = read(CONTROL / 'exact-exit.json')
    print(json.dumps(row))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'verify', 'preflight', 'launch', 'status', 'stop'))
    parser.add_argument('--scheduled-by-root', action='store_true')
    args = parser.parse_args()
    if args.action == 'freeze':
        freeze()
    elif args.action == 'launch':
        launch(args.scheduled_by_root)
    elif args.action == 'stop':
        stop()
    elif args.action == 'status':
        status()
    else:
        frozen = validate()
        result = {'verified': True, 'owner': OWNER, 'source_sha256': frozen['source_sha256']}
        if args.action == 'preflight':
            result['resources'] = resources(prelaunch=not (CONTROL / 'ready-summary.json').exists())
        print(json.dumps(result))
