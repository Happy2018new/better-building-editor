"""One guarded cold start for a raw-air control and true-state lifecycle v2.

The one fresh diagnostic world is retired in finally. No activation, resizing,
desktop input, inventory read or fallback capture is permitted by this runner.
The user's own foreground observation does not interrupt its guarded tests.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SHARED = Path('D:/Happy2018newの个人文件/GitHub/better-building-editor')
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
import _session
import _window
from mcdk import Client, return_value
from capture_native_window import capture
import scaffold_diagnostic_world as world
import probe_scaffold_single_air_runtime as air_control
import probe_scaffold_runtime_lifecycle as lifecycle
import scaffold_native_palette_readback as palette_readback
import probe_scaffold_runtime_catalogue as catalogue

OWNER = 'scaffold-r13e-runtime-lifecycle-v2'
GAME = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/Minecraft.Windows.exe')
GUARD = SHARED / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
MCDK = SHARED / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
WGC = SHARED / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
PINS = {GUARD: '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93',
        MCDK: 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9',
        WGC: 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'}
OUTER_SECONDS, CLEANUP_SECONDS = 330, 70


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def foreground_metadata():
    allowed = _window.user_foreground_allowed()
    return {'background_only': not allowed, 'user_foreground_allowed': allowed,
            'foreground_policy': 'allow_user_foreground' if allowed else 'background_only',
            'agent_activation_allowed': False, 'activation_fallback': False}


def scaffold_guard_satisfied(guard, pid, require_window=False):
    if not _window.foreground_policy_satisfied(guard, pid):
        return False
    windows = guard.get('windows', [])
    return ((not require_window or bool(windows))
            and (not windows or guard.get('window_noactivate') is True))


def startup_foreground_satisfied(snapshot):
    return _window.user_foreground_allowed() or not snapshot.get('process', '').lower().startswith('minecraft')


def archive_sources(root, output, sources):
    """Retain exact source bytes alongside the paths and hashes used to run."""
    source_pins, archive_pins = {}, {}
    for path in sources:
        path = path.resolve()
        relative = path.relative_to(root.resolve())
        target = output / 'sources' / relative
        raw = path.read_bytes()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        value = hashlib.sha256(raw).hexdigest()
        source_pins[str(path)] = value
        archive_pins[str(target.relative_to(output))] = value
    return source_pins, archive_pins


def census():
    command = ('@(Get-CimInstance Win32_Process -Filter "Name=\'Minecraft.Windows.exe\'" | '
               'Select-Object ProcessId,ThreadCount,HandleCount,VirtualSize,KernelModeTime,UserModeTime,CreationDate)'
               '|ConvertTo-Json -Compress')
    run = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command], capture_output=True,
                         timeout=6, creationflags=subprocess.CREATE_NO_WINDOW)
    if run.returncode:
        raise RuntimeError('Active game census failed')
    rows = json.loads(run.stdout.decode('utf-8-sig') or '[]')
    return rows if isinstance(rows, list) else [rows]


def residual(row):
    return all(int(row[key]) == 0 for key in ('ThreadCount', 'HandleCount', 'VirtualSize', 'KernelModeTime', 'UserModeTime'))


def physical_ready(client, server):
    """The air raw value is kept; loaded ground and UI provide admission."""
    if (not isinstance(client, dict) or not isinstance(server, dict)
            or client.get('runtime') != world.RUNTIME or server.get('runtime') != world.RUNTIME
            or client.get('ui_initialized') is not True or type(client.get('render_ticks')) is not int
            or client['render_ticks'] < 2 or not client.get('player') or client['player'] != server.get('player')
            or type(server.get('dimension')) is not int or server['dimension'] != 0 or not world.foot_valid(client.get('foot'))
            or not world.foot_valid(server.get('foot'))
            or any(abs(a - b) > .125 for a, b in zip(client['foot'], server['foot']))):
        return False
    ground = server.get('ground', {})
    if (not isinstance(ground, dict) or not isinstance(ground.get('states'), dict)
            or not isinstance(ground.get('front'), dict) or type(ground['front'].get('aux')) is not int
            or ground['front'].get('name') in (None, 'minecraft:air', 'minecraft:unknown')):
        return False
    reserve = server.get('reserve', [])
    return (len(reserve) == len(world.OFFSETS)
            and {tuple(row.get('offset', ())) for row in reserve} == set(world.OFFSETS)
            and all(lifecycle.dry_air(row) for row in reserve))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--execute', action='store_true', help='The reviewed plan permits exactly one guarded launch')
    parser.add_argument('--air-observation', type=Path, help='Independent native air/ground palette encoding read')
    parser.add_argument('--catalogue-count', type=int, default=0, help='Optional first semantic segment, maximum 256 states')
    args = parser.parse_args()
    os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
    foreground_policy = foreground_metadata()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    pack = output / 'diagnostic-pack'
    world.build_pack(ROOT, pack)
    sources = [Path(__file__), Path(world.__file__), Path(air_control.__file__), Path(lifecycle.__file__),
               Path(air_control.base.__file__), Path(palette_readback.__file__),
               ROOT / 'tools/probe_scaffold_palette_air_readback.py',
               Path(catalogue.__file__), ROOT / 'tools/derive_scaffold_runtime_support.py',
               Path(lifecycle.base.__file__), ROOT / 'tools/capture_native_window.py',
               ROOT / 'tools/context_test_environment.py', ROOT / 'tools/verify_debug_blueprints.py',
               ROOT / 'tools/run_native_single_door.py',
               ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py',
               ROOT / '.agents/skills/pyreact-debugging/scripts/_session.py',
               ROOT / '.agents/skills/pyreact-debugging/scripts/_window.py',
               ROOT / '.agents/skills/pyreact-debugging/scripts/mcdk.py']
    source_pins, archive_pins = archive_sources(ROOT, output, sources)
    for path, expected in PINS.items():
        if digest(path) != expected:
            raise ValueError('Reviewed binary pin differs: ' + str(path))
    config = {'included_mod_dirs': [str(pack)], 'world_type': 2, 'world_seed': 0, 'game_mode': 1,
              'auto_hot_reload_mods': False, 'auto_hot_reload_ui': False,
              'auto_hot_reload_materials': False, 'auto_hot_reload_shaders': False}
    def save(name, data):
        (output / name).write_text(json.dumps(data, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    near_server = world.SERVER.replace('ground[1]+19', 'ground[1]+3')
    if near_server == world.SERVER:
        raise ValueError('Near-read template changed')
    plan = {'schema': 1, 'owner': OWNER, 'created_at': datetime.now(timezone.utc).isoformat(),
            'status': 'prepared_not_executed', 'launches_permitted': 1, 'outer_seconds': OUTER_SECONDS,
            'cleanup_seconds': CLEANUP_SECONDS, 'world_seconds': 65,
            'real_input': False, 'resize': False, 'config': config,
            'source_pins': source_pins, 'source_archive_pins': archive_pins,
            'binary_pins': {str(path): expected for path, expected in PINS.items()},
            'pack_pins': {str(path.relative_to(output)): digest(path) for path in pack.rglob('*') if path.is_file()},
            'payload_sha256': {'world_client': hashlib.sha256(world.CLIENT.encode('ascii')).hexdigest(),
                               'world_server': hashlib.sha256(near_server.encode('ascii')).hexdigest()},
            'acceptance': lifecycle.ACCEPTANCE, 'native_sequence': [air_control.METHOD, lifecycle.METHOD]}
    plan.update(foreground_policy)
    if not 0 <= args.catalogue_count <= catalogue.MAX_COUNT:
        raise ValueError('Catalogue segment exceeds the bounded 256-state limit')
    plan['catalogue_count'] = args.catalogue_count
    if args.catalogue_count:
        plan['native_sequence'].append(catalogue.METHOD)
    save('plan.json', plan)
    if args.air_observation is not None:
        observation_raw = args.air_observation.read_bytes()
        observation = json.loads(observation_raw)
        air_encoding = palette_readback.encoding_from_observation(observation)
        (output / 'air-observation.json').write_bytes(observation_raw)
        plan['air_observation_sha256'] = hashlib.sha256(observation_raw).hexdigest()
        plan['air_encoding'] = air_encoding
        save('plan.json', plan)
    if not args.execute:
        print(json.dumps({'prepared': True, 'plan': str(output / 'plan.json')}))
        return 0
    if args.air_observation is None:
        raise ValueError('Execute requires an independent native palette air encoding observation')
    config_path = ROOT / '.mcdev.json'
    if config_path.exists():
        raise ValueError('Own worktree configuration already exists')
    config_path.write_text(json.dumps(config, indent=2) + '\n', encoding='ascii')
    config_hash = digest(config_path)
    report = {'schema': 1, 'completed': False, 'launches': 0, 'checks': [], 'world_observations': [],
              'world_qualified': False, 'cleanup_errors': [], 'acceptance': lifecycle.ACCEPTANCE}
    report.update(foreground_policy)
    session = launcher = child = None
    child_identity = None
    started = time.monotonic()
    deadline = started + OUTER_SECONDS
    def timeout(limit, reserve=CLEANUP_SECONDS):
        remaining = deadline - time.monotonic() - reserve
        if remaining <= 0:
            raise TimeoutError('Absolute scaffold budget reached')
        return min(limit, remaining)
    def checkpoint():
        save('report.json', report)
    def find_session():
        rows = [json.loads(path.read_bytes()) for path in _session.registry_dir().glob('*/session.json')]
        rows = [row for row in rows if row.get('owner') == OWNER and Path(row.get('project', '')).resolve() == ROOT]
        if len(rows) > 1:
            raise RuntimeError('Ambiguous scaffold owner sessions')
        return rows[0] if rows else None
    def observe_guard():
        if _session.process_identity(session['game_pid']) != session['game_identity']:
            raise RuntimeError('Owned game creation identity changed')
        guard = _window.background_guard_state(session['game_pid'], GAME.name)
        report['checks'].append({'at_seconds': time.monotonic() - started, 'guard': guard})
        checkpoint()
        if not scaffold_guard_satisfied(guard, session['game_pid']):
            raise RuntimeError('Passive noactivation guard failed')
    try:
        first = census()
        time.sleep(.2)
        second = census()
        stale = [row for row in first if residual(row) and row in second]
        active = [row for row in second if row not in stale]
        report['capacity'] = {'before': first, 'after': second, 'stable_residuals': stale, 'active': active}
        report['foreground_before'] = _window.foreground_snapshot()
        checkpoint()
        if len(active) >= 5:
            raise RuntimeError('Five-game capacity reached')
        if not startup_foreground_satisfied(report['foreground_before']):
            raise RuntimeError('A game is already foreground')
        command = [sys.executable, '-X', 'utf8', str(ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'),
                   'start', '--project', str(ROOT), '--owner', OWNER, '--name', OWNER, '--preset', 'ui',
                   '--wait', '120', '--mcdk', str(MCDK), '--noactivate-dll', str(GUARD),
                   '--noactivate-sha256', PINS[GUARD], '--noactivate-mcdk-sha256', PINS[MCDK], '--game-exe', str(GAME)]
        with (output / 'launch-stdout.txt').open('wb') as stdout, (output / 'launch-stderr.txt').open('wb') as stderr:
            launcher = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr,
                                        creationflags=subprocess.CREATE_NO_WINDOW)
            report.update(launches=1, launcher_pid=launcher.pid, launcher_identity=_session.process_identity(launcher.pid))
            checkpoint()
            while launcher.poll() is None:
                if time.monotonic() - started > 160:
                    raise TimeoutError('Guarded startup budget reached')
                session = find_session()
                if session and session.get('game_pid'):
                    observe_guard()
                time.sleep(.5)
        report['launcher_returncode'] = launcher.returncode
        session = find_session()
        if not session or not session.get('ready'):
            raise RuntimeError('Guarded startup did not reach a ready session')
        report['session'] = session
        os.environ.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=OWNER)
        with Client(timeout=10) as client:
            world_deadline = min(started + 230, time.monotonic() + 65, deadline - 110)
            stable, previous = 0, None
            while time.monotonic() < world_deadline:
                observe_guard()
                client.timeout = min(10, max(.1, world_deadline - time.monotonic()))
                cli = return_value(client.call('execute_code', {'code': world.CLIENT, 'is_client': True, 'direct_return': True}))
                srv = return_value(client.call('execute_code', {'code': near_server, 'is_client': False, 'direct_return': True}))
                admitted = physical_ready(cli, srv)
                foot = srv.get('foot')
                stable = stable + 1 if admitted and (previous is None or all(abs(a - b) <= .125 for a, b in zip(foot, previous))) else 0
                previous = foot if admitted else None
                report['world_observations'].append({'client': cli, 'server': srv, 'admitted': admitted, 'stable_samples': stable})
                checkpoint()
                if stable >= 3:
                    report['world_qualified'] = True
                    report['world'] = srv
                    break
                time.sleep(.5)
            if not report['world_qualified']:
                raise RuntimeError('UiInit, actual render ticks, stable feet and loaded ground did not qualify')
            observe_guard()
            report['capture'] = capture(session['session_file'], OWNER, output / 'world.png', WGC)
            foot = report['world']['foot']
            origin = tuple(int(math.floor(foot[i])) + (4, 2, 4)[i] for i in range(3))
            payload = air_control.payload(report['world']['player'], foot, report['world']['dimension'], origin, air_encoding)
            report['single_payload_sha256'] = hashlib.sha256(payload.encode('ascii')).hexdigest()
            (output / 'single-server.py').write_text(payload, encoding='ascii')
            checkpoint()
            client.timeout = timeout(15, 95)
            report['single_air'] = return_value(client.call('execute_code', {'code': payload, 'is_client': False, 'direct_return': True}))
            observe_guard()
            checkpoint()
            if not report['single_air']['completed'] or not report['single_air']['restored']:
                raise RuntimeError('Single stone/raw-air control failed')
        env = os.environ.copy()
        env.update(MCDEV_MCP_URL=session['mcp_url'])
        with (output / 'probe-stdout.txt').open('wb') as stdout, (output / 'probe-stderr.txt').open('wb') as stderr:
            child = subprocess.Popen([sys.executable, '-X', 'utf8', str(ROOT / 'tools/probe_scaffold_runtime_lifecycle.py'),
                                      str(output / 'native.json'), '--fresh-owned-flow-allowed',
                                      '--air-observation', str(output / 'air-observation.json')], cwd=ROOT, env=env,
                                     stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
            child_identity = _session.process_identity(child.pid)
            child_deadline = time.monotonic() + timeout(60)
            while child.poll() is None:
                if time.monotonic() >= child_deadline:
                    raise TimeoutError('Native lifecycle child budget reached')
                observe_guard()
                time.sleep(.5)
        report['native'] = json.loads((output / 'native.json').read_bytes())
        report['child_returncode'] = child.returncode
        if child.returncode:
            raise RuntimeError('True-state lifecycle failed; raw report retained')
        if args.catalogue_count:
            with (output / 'catalogue-stdout.txt').open('wb') as stdout, (output / 'catalogue-stderr.txt').open('wb') as stderr:
                child = subprocess.Popen([sys.executable, '-X', 'utf8', str(ROOT / 'tools/probe_scaffold_runtime_catalogue.py'),
                                          str(output / 'catalogue.json'), '--fresh-owned-flow-allowed', '--start-index', '0',
                                          '--count', str(args.catalogue_count), '--air-observation', str(output / 'air-observation.json')],
                                         cwd=ROOT, env=env, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
                child_identity = _session.process_identity(child.pid)
                child_deadline = time.monotonic() + timeout(90)
                while child.poll() is None:
                    if time.monotonic() >= child_deadline:
                        raise TimeoutError('Native semantic segment child budget reached')
                    observe_guard()
                    time.sleep(.5)
            report['catalogue'] = json.loads((output / 'catalogue.json').read_bytes())
            if child.returncode:
                raise RuntimeError('Native semantic segment failed; partial raw evidence retained')
            from derive_scaffold_runtime_support import capabilities
            report['catalogue_capabilities'] = capabilities([report['catalogue']])
        report['completed'] = True
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
    finally:
        try:
            if child and child.poll() is None:
                _session.terminate_owned(child.pid, child_identity)
                child.wait(timeout=timeout(5, 25))
        except Exception as error:
            report['cleanup_errors'].append('Native child: ' + repr(error))
        try:
            native_path = output / 'native.json'
            if native_path.is_file():
                report['native'] = json.loads(native_path.read_bytes())
                if report['native'].get('restored') is not True and session and session.get('ready'):
                    with Client(timeout=timeout(8, 30)) as client:
                        code = lifecycle.native_restore() % (lifecycle.MARKER, report['native']['identity'])
                        report['supervisor_restore'] = return_value(client.call('execute_code', {'code': code, 'is_client': False, 'direct_return': True}))
        except Exception as error:
            report['cleanup_errors'].append('Native restore: ' + repr(error))
        try:
            catalogue_path = output / 'catalogue.json'
            if catalogue_path.is_file():
                report['catalogue'] = json.loads(catalogue_path.read_bytes())
                if report['catalogue'].get('restored') is not True and session and session.get('ready'):
                    with Client(timeout=timeout(8, 30)) as client:
                        code = catalogue.restore_payload(report['catalogue']['identity'])
                        report['catalogue_supervisor_restore'] = return_value(client.call('execute_code', {'code': code, 'is_client': False, 'direct_return': True}))
        except Exception as error:
            report['cleanup_errors'].append('Semantic catalogue restore: ' + repr(error))
        try:
            session = find_session()
            if session:
                if not session.get('game_pid'):
                    from run_native_single_door import complete_cleanup_binding
                    session = complete_cleanup_binding(session)
                report['session_before_stop'] = session
                try:
                    stopped = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'),
                                              'stop', '--session', session['session_file'], '--owner', OWNER],
                                             capture_output=True, text=True, encoding='utf8', timeout=timeout(20, 0),
                                             creationflags=subprocess.CREATE_NO_WINDOW)
                    report['normal_stop'] = {'returncode': stopped.returncode, 'stdout': stopped.stdout, 'stderr': stopped.stderr}
                except Exception as error:
                    report['normal_stop_error'] = repr(error)
                for kind in ('game', 'mcdk'):
                    pid, identity = session.get(kind + '_pid'), session.get(kind + '_identity')
                    if pid and _session.process_identity(pid) == identity:
                        _session.terminate_owned(pid, identity)
                report['identities_after_stop'] = {kind: _session.process_identity(session[kind + '_pid'])
                    if session.get(kind + '_pid') else None for kind in ('game', 'mcdk')}
            if launcher and launcher.poll() is None:
                _session.terminate_owned(launcher.pid, report['launcher_identity'])
        except Exception as error:
            report['cleanup_errors'].append('Owned process cleanup: ' + repr(error))
        if config_path.is_file() and digest(config_path) == config_hash:
            config_path.unlink()
        else:
            report['cleanup_errors'].append('Private configuration changed; removal refused')
        report['source_pins_unchanged'] = all(path.is_file() and digest(path) == plan['source_pins'][str(path)] for path in sources)
        report['source_archive_pins_unchanged'] = all((output / path).is_file() and digest(output / path) == value
            for path, value in plan['source_archive_pins'].items())
        report['pack_pins_unchanged'] = all((output / path).is_file() and digest(output / path) == value for path, value in plan['pack_pins'].items())
        if (not report['source_pins_unchanged'] or not report['source_archive_pins_unchanged']
                or not report['pack_pins_unchanged']):
            report['cleanup_errors'].append('Frozen source or diagnostic pack changed during execution')
        report['foreground_after'] = _window.foreground_snapshot()
        report['elapsed_seconds'] = time.monotonic() - started
        checkpoint()
    print(json.dumps({key: report.get(key) for key in ('completed', 'error', 'cleanup_errors', 'identities_after_stop', 'elapsed_seconds')}))
    return 0 if report['completed'] and not report['cleanup_errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
