"""One guarded, read-only minimal-BP startup contrast; no automatic relaunch."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SHARED = Path('D:/Happy2018new\u306e\u4e2a\u4eba\u6587\u4ef6/GitHub/better-building-editor')
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / '.agents/skills/pyreact-debugging/scripts')]
import _session
import _window
import scaffold_diagnostic_world as world
from capture_native_window import capture
from managed_registry_snapshot import find_owner_session
from mcdk import Client, return_value

OWNER = 'background-minimal-r14-preworld-v2'
OUT = ROOT / '.runtime/minimal-startup-r14-v2'
MCDK = SHARED / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
GUARD = SHARED / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
WGC = SHARED / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
PROBE = Path('D:/bbe-r13e-scaffold/tools/probe_scaffold_palette_air_readback.py')
PINS = {MCDK: 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9',
        GUARD: '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93',
        WGC: 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8',
        PROBE: '08b14a0914c189972df1dc86338a90564bf0c798b1f3f056749165e9b0d0efb8'}
FULL_CLIENT = '''def _baseline_world_client_r14():
 import mod.client.extraClientApi as api
 player=api.GetLocalPlayerId()
 system=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
 return {'player':player,'foot':api.GetEngineCompFactory().CreatePos(player).GetFootPos() if player else None,
  'runtime':api.GetMinecraftVersion(),'ui_initialized':system is not None and system.session is not None and system.hud is not None,
  'readiness_source':'existing UiInitFinished session/hud initialization'}
_result=_baseline_world_client_r14()
del _baseline_world_client_r14
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(full_baseline=False, baseline_rp=False):
    global OWNER, OUT
    if full_baseline:
        OWNER = 'background-baseline-r14-preworld-v1'
        OUT = ROOT / '.runtime/baseline-startup-r14-v1'
    elif baseline_rp:
        OWNER = 'background-minimal-baseline-rp-r14-v1'
        OUT = ROOT / '.runtime/minimal-baseline-rp-startup-r14-v1'
    for path, expected in PINS.items():
        if sha(path) != expected:
            raise ValueError('Frozen input differs: ' + str(path))
    tree = ast.parse(PROBE.read_bytes())
    assignments = [node for node in tree.body if isinstance(node, ast.Assign)
                   and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                   and node.targets[0].id == 'SERVER']
    if len(assignments) != 1:
        raise ValueError('Frozen palette probe SERVER assignment differs')
    palette_code = ast.literal_eval(assignments[0].value)
    if hashlib.sha256(palette_code.encode('utf8')).hexdigest() != 'd1257625ac2b01711cefabc88046d450410429530990cba76df4e3ebf4a3721d':
        raise ValueError('Frozen palette server code differs')
    CONFIG = ROOT / '.mcdev.json'
    if CONFIG.exists():
        raise ValueError('Own config already exists')
    OUT.mkdir(exist_ok=False)
    PACK = OUT / 'minimal-pack'
    production_source_pins = None
    if full_baseline or baseline_rp:
        unchanged = subprocess.run(['git', 'diff', '--exit-code', '52189693', '--', 'behavior_pack', 'resource_pack'],
                                   cwd=ROOT, capture_output=True, timeout=10)
        untracked = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard', '--', 'behavior_pack', 'resource_pack'],
                                   cwd=ROOT, capture_output=True, timeout=10)
        tracked = subprocess.run(['git', 'ls-files', '-z', '--', 'behavior_pack', 'resource_pack'],
                                 cwd=ROOT, capture_output=True, timeout=10)
        if unchanged.returncode or untracked.returncode or untracked.stdout or tracked.returncode:
            raise ValueError('Baseline 52189693 production packs are not exact')
        production_paths = [ROOT / name.decode('utf8') for name in tracked.stdout.split(b'\0') if name]
        if baseline_rp:
            production_paths = [path for path in production_paths if path.relative_to(ROOT).parts[0] == 'resource_pack']
        production_source_pins = {str(path.relative_to(ROOT)): sha(path) for path in production_paths}
    if full_baseline:
        pack_pins = production_source_pins
    else:
        world.build_pack(ROOT, PACK)
        if baseline_rp:
            for source in production_paths:
                target = PACK / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        pack_pins = {str(path.relative_to(OUT)): sha(path) for path in PACK.rglob('*') if path.is_file()}
    config = {'included_mod_dirs': [str(ROOT if full_baseline else PACK)], 'world_type': 2, 'world_seed': 0, 'game_mode': 1,
              'auto_hot_reload_mods': False, 'auto_hot_reload_ui': False,
              'auto_hot_reload_materials': False, 'auto_hot_reload_shaders': False}
    CONFIG.write_text(json.dumps(config, indent=2) + '\n', encoding='ascii')
    config_sha = sha(CONFIG)

    def save(name, value):
        (OUT / name).write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')

    plan = {'schema': 2, 'owner': OWNER, 'created_at': datetime.now(timezone.utc).isoformat(),
            'hypothesis': 'Minimal BP versus full-pack crash before engine logs and world IPC',
            'changed_condition': ('Serial exact baseline 52189693 full packs' if full_baseline else
                                  'Healthy minimal BP plus exact baseline 52189693 RP' if baseline_rp else
                                  'Bounded PermissionError-only manifest read retry'),
            'pack_mode': 'baseline-full' if full_baseline else 'minimal-baseline-rp' if baseline_rp else 'minimal',
            'launches_permitted': 1, 'outer_seconds': 240, 'cleanup_seconds': 40,
            'background_only': True, 'activation_resize_desktop_input': False,
            'block_or_actor_writes': False, 'production_acceptance': False,
            'pins': {str(path): sha(path) for path in [Path(__file__), Path(world.__file__),
                     ROOT / 'tools/managed_registry_snapshot.py', CONFIG] + list(PINS)},
            'pack_pins': pack_pins, 'production_source_pins': production_source_pins}
    save('plan.json', plan)
    report = {'schema': 2, 'owner': OWNER, 'completed': False, 'launches': 0, 'checks': [],
              'registry_read_retries': [], 'cleanup_errors': [], 'production_acceptance': False}
    started = time.monotonic()
    session = launcher = None

    def checkpoint():
        save('report.json', report)

    def guard():
        if _session.process_identity(session['game_pid']) != session['game_identity']:
            raise RuntimeError('Owned minimal game creation identity changed')
        value = _window.background_guard_state(session['game_pid'], 'Minecraft.Windows.exe')
        report['checks'].append({'at_seconds': time.monotonic() - started, 'guard': value})
        checkpoint()
        if not value['background_safe'] or value['windows'] and not value['window_noactivate']:
            raise RuntimeError('Minimal background guard failed')

    def read_retry(receipt):
        report['registry_read_retries'].append(dict(receipt, at_seconds=time.monotonic() - started))
        checkpoint()
        if time.monotonic() - started >= 195:
            raise TimeoutError('Minimal manifest read exceeded observation deadline')
        if session and session.get('game_pid'):
            guard()

    def find_session():
        return find_owner_session(_session.registry_dir(), OWNER, ROOT, timeout=.75, on_retry=read_retry)

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
                if time.monotonic() - started >= 150:
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
            deadline = min(started + 175, time.monotonic() + 25)
            while time.monotonic() < deadline:
                guard()
                client.timeout = min(8, max(.1, deadline - time.monotonic()))
                value = return_value(client.call('execute_code', {'code': FULL_CLIENT if full_baseline else world.CLIENT,
                                                                  'is_client': True, 'direct_return': True}))
                report['world'] = value
                checkpoint()
                if (value.get('runtime') == '1.21.120.0' and value.get('ui_initialized') is True
                        and (full_baseline or value.get('render_ticks', 0) >= 2) and world.foot_valid(value.get('foot'))):
                    break
                time.sleep(.5)
            else:
                raise RuntimeError('Minimal UiInit and loaded player did not initialize')
            guard()
            client.timeout = min(8, max(.1, started + 185 - time.monotonic()))
            report['palette_readback'] = return_value(client.call('execute_code',
                {'code': palette_code, 'is_client': False, 'direct_return': True}))
            checkpoint()
        guard()
        report['capture'] = capture(session['session_file'], OWNER, OUT / 'world.png', WGC)
        guard()
        report['completed'] = True
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        if launcher and launcher.poll() is None:
            try:
                _session.terminate_owned(launcher.pid, report['launcher_identity'])
            except Exception as error:
                report['cleanup_errors'].append('Launcher cleanup: ' + repr(error))
        try:
            try:
                current = find_session()
                if current is not None:
                    session = current
            except Exception as error:
                report['cleanup_manifest_error'] = repr(error)
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
        except Exception as error:
            report['cleanup_errors'].append('Owned cleanup: ' + repr(error))
        if CONFIG.is_file() and sha(CONFIG) == config_sha:
            CONFIG.unlink()
        else:
            report['cleanup_errors'].append('Private config changed; removal refused')
        report['pins_unchanged'] = {str(path): sha(path) == expected for path, expected in PINS.items()}
        if production_source_pins is not None:
            report['production_pack_pins_unchanged'] = {name: sha(ROOT / name) == expected
                                                       for name, expected in production_source_pins.items()}
        report['mounted_pack_pins_unchanged'] = {name: sha((ROOT if full_baseline else OUT) / name) == expected
                                                for name, expected in pack_pins.items()}
        if (not all(report['pins_unchanged'].values())
                or not all(report['mounted_pack_pins_unchanged'].values())
                or not all(report.get('production_pack_pins_unchanged', {}).values())):
            report['completed'] = False
            report['error'] = 'Frozen input or mounted pack bytes changed during observation'
        report['foreground_after'] = _window.foreground_snapshot()
        report['elapsed_seconds'] = time.monotonic() - started
        checkpoint()
    print(json.dumps({key: report.get(key) for key in ('completed', 'error', 'cleanup_errors',
                                                    'identities_after_stop', 'elapsed_seconds')}))
    return 0 if report['completed'] and not report['cleanup_errors'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--baseline-full', action='store_true', help='One serial exact 52189693 full-pack contrast')
    group.add_argument('--baseline-rp', action='store_true', help='One serial exact 52189693 RP with healthy minimal BP')
    args = parser.parse_args()
    sys.exit(main(full_baseline=args.baseline_full, baseline_rp=args.baseline_rp))
