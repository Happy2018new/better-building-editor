"""One nonmutating guarded minimal-BP contrast to three pre-world crashes."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SHARED = Path('D:/Happy2018newの个人文件/GitHub/better-building-editor')
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / '.agents/skills/pyreact-debugging/scripts')]
import _session
import _window
import scaffold_diagnostic_world as world
from capture_native_window import capture
from mcdk import Client, return_value

OWNER = 'background-minimal-r14-preworld-v1'
OUT = ROOT / '.runtime/minimal-startup-r14-v1'
OUT.mkdir(exist_ok=False)
PACK = OUT / 'minimal-pack'
world.build_pack(ROOT, PACK)
MCDK = SHARED / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
GUARD = SHARED / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
WGC = SHARED / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
PINS = {MCDK: 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9',
        GUARD: '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93',
        WGC: 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'}
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
for path, expected in PINS.items():
    if sha(path) != expected:
        raise ValueError('Approved binary differs: ' + str(path))
CONFIG = ROOT / '.mcdev.json'
if CONFIG.exists():
    raise ValueError('Own config already exists')
config = {'included_mod_dirs': [str(PACK)], 'world_type': 2, 'world_seed': 0, 'game_mode': 1,
          'auto_hot_reload_mods': False, 'auto_hot_reload_ui': False,
          'auto_hot_reload_materials': False, 'auto_hot_reload_shaders': False}
CONFIG.write_text(json.dumps(config, indent=2) + '\n', encoding='ascii')
config_sha = sha(CONFIG)
def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
plan = {'schema': 1, 'owner': OWNER, 'created_at': datetime.now(timezone.utc).isoformat(),
        'hypothesis': 'Minimal BP versus full-pack crash before engine logs and world IPC',
        'launches_permitted': 1, 'outer_seconds': 240, 'cleanup_seconds': 40,
        'background_only': True, 'activation_resize_desktop_input': False,
        'block_or_actor_writes': False, 'production_acceptance': False,
        'pins': {str(path): sha(path) for path in [Path(__file__), Path(world.__file__), CONFIG] + list(PINS)},
        'pack_pins': {str(path.relative_to(OUT)): sha(path) for path in PACK.rglob('*') if path.is_file()}}
save('plan.json', plan)
report = {'schema': 1, 'owner': OWNER, 'completed': False, 'launches': 0, 'checks': [],
          'cleanup_errors': [], 'production_acceptance': False}
started = time.monotonic()
session = launcher = None
def checkpoint():
    save('report.json', report)
def find_session():
    rows = [json.loads(path.read_bytes()) for path in _session.registry_dir().glob('*/session.json')]
    matches = [row for row in rows if row.get('owner') == OWNER and Path(row.get('project', '')).resolve() == ROOT]
    if len(matches) > 1:
        raise RuntimeError('Ambiguous minimal owner sessions')
    return matches[0] if matches else None
def guard():
    if _session.process_identity(session['game_pid']) != session['game_identity']:
        raise RuntimeError('Owned minimal game creation identity changed')
    value = _window.background_guard_state(session['game_pid'], 'Minecraft.Windows.exe')
    report['checks'].append({'at_seconds': time.monotonic() - started, 'guard': value})
    checkpoint()
    if not value['background_safe'] or value['windows'] and not value['window_noactivate']:
        raise RuntimeError('Minimal background guard failed')
try:
    command = "@(Get-CimInstance Win32_Process -Filter \"Name='Minecraft.Windows.exe'\" | Select-Object ProcessId,ThreadCount,HandleCount,VirtualSize,KernelModeTime,UserModeTime)|ConvertTo-Json -Compress"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command], capture_output=True,
                            timeout=6, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError('Capacity census failed')
    rows = json.loads(result.stdout.decode('utf-8-sig') or '[]')
    rows = rows if isinstance(rows, list) else [rows]
    active = [row for row in rows if any(int(row[key]) != 0 for key in
              ('ThreadCount', 'HandleCount', 'VirtualSize', 'KernelModeTime', 'UserModeTime'))]
    report['capacity'] = {'rows': rows, 'active': active}
    if len(active) >= 5:
        raise RuntimeError('No owned-game capacity')
    report['foreground_before'] = _window.foreground_snapshot()
    if report['foreground_before']['process'].lower().startswith('minecraft'):
        raise RuntimeError('Game already foreground')
    args = [sys.executable, '-X', 'utf8', str(ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'),
            'start', '--project', str(ROOT), '--owner', OWNER, '--name', OWNER, '--preset', 'ui', '--wait', '120',
            '--mcdk', str(MCDK), '--noactivate-dll', str(GUARD), '--noactivate-sha256', PINS[GUARD],
            '--noactivate-mcdk-sha256', PINS[MCDK], '--game-exe',
            'D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/Minecraft.Windows.exe']
    with (OUT / 'launch-stdout.txt').open('wb') as stdout, (OUT / 'launch-stderr.txt').open('wb') as stderr:
        launcher = subprocess.Popen(args, cwd=ROOT, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(launches=1, launcher_pid=launcher.pid, launcher_identity=_session.process_identity(launcher.pid))
        checkpoint()
        while launcher.poll() is None:
            if time.monotonic() - started >= 160:
                raise TimeoutError('Minimal launch deadline')
            session = find_session()
            if session and session.get('game_pid'):
                guard()
            time.sleep(.5)
    report['launcher_returncode'] = launcher.returncode
    session = find_session()
    if not session or not session.get('ready'):
        raise RuntimeError('Minimal world did not bind: ' + str(session and session.get('error')))
    report['session'] = session
    os.environ.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=OWNER)
    with Client(timeout=8) as client:
        deadline = min(started + 195, time.monotonic() + 30)
        while time.monotonic() < deadline:
            guard()
            client.timeout = min(8, max(.1, deadline - time.monotonic()))
            value = return_value(client.call('execute_code', {'code': world.CLIENT, 'is_client': True, 'direct_return': True}))
            report['world'] = value
            checkpoint()
            if value.get('ui_initialized') and value.get('render_ticks', 0) >= 2 and world.foot_valid(value.get('foot')):
                break
            time.sleep(.5)
        else:
            raise RuntimeError('Minimal UiInit and loaded player did not initialize')
    report['capture'] = capture(session['session_file'], OWNER, OUT / 'world.png', WGC)
    report['completed'] = True
except Exception as error:
    report['error'] = type(error).__name__ + ': ' + str(error)
finally:
    try:
        session = find_session()
        if session:
            if not session.get('game_pid'):
                from run_native_single_door import complete_cleanup_binding
                session = complete_cleanup_binding(session)
            report['session_before_stop'] = session
            try:
                result = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'),
                                         'stop', '--session', session['session_file'], '--owner', OWNER],
                                        capture_output=True, text=True, encoding='utf8', timeout=20,
                                        creationflags=subprocess.CREATE_NO_WINDOW)
                report['normal_stop'] = {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
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
        report['cleanup_errors'].append('Owned cleanup: ' + repr(error))
    if CONFIG.is_file() and sha(CONFIG) == config_sha:
        CONFIG.unlink()
    else:
        report['cleanup_errors'].append('Private config changed; removal refused')
    report['pins_unchanged'] = {str(path): sha(path) == expected for path, expected in PINS.items()}
    report['foreground_after'] = _window.foreground_snapshot()
    report['elapsed_seconds'] = time.monotonic() - started
    checkpoint()
print(json.dumps({key: report.get(key) for key in ('completed', 'error', 'cleanup_errors', 'identities_after_stop', 'elapsed_seconds')}))
