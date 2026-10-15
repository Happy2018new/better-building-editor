"""Owner-bound v12 preflight/start/capture; raw session receipts stay private."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
sys.path[:0] = [str(TOOLS), str(SCRIPTS)]
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from probe_product_water import snapshot_digest, snapshot_sources
from _session import _identity, _kernel, process_identity

OWNER = 'portal-r21-native-candidate-v12'
CONTROL = ROOT / '.runtime/portal-native-candidate-control-r21-v12'
PROJECT = ROOT / '.runtime/projects/portal-r21-native-candidate-v12'
OUTPUT = ROOT / '.runtime/portal-native-candidate-observed-r21-v12'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='ascii', newline='\n')


def census():
    command = ('ConvertTo-Json -Compress -InputObject @(Get-CimInstance Win32_Process -Filter '
               '"Name=\'Minecraft.Windows.exe\'" | Select-Object ProcessId,HandleCount,ThreadCount)')
    listed = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', command],
                                                text=True, encoding='utf8'))
    kernel, rows = _kernel(), []
    for item in listed:
        row = dict(item, identity=None, blocks_launch=True)
        handle = kernel.OpenProcess(0x1000 | 0x100000, False, item['ProcessId'])
        if not handle:
            row.update(state='not_openable', winerror=ctypes.get_last_error(),
                       blocks_launch=bool(item['HandleCount'] or item['ThreadCount']))
        else:
            try:
                waited, code = kernel.WaitForSingleObject(handle, 0), wintypes.DWORD()
                if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                    raise ctypes.WinError(ctypes.get_last_error())
                row.update(wait_result=waited, exit_code=code.value, identity=_identity(kernel, handle))
                if waited == 0 or code.value != 259:
                    row.update(state='exited', blocks_launch=False)
                elif waited == 258 and code.value == 259 and row['identity'] is not None:
                    row['state'] = 'live'
                else:
                    row['state'] = 'uncertain'
            finally:
                kernel.CloseHandle(handle)
        rows.append(row)
    return rows


def preflight(require_no_game=False):
    prepared = json.loads((CONTROL / 'prepared-summary.json').read_bytes())
    frozen = json.loads((CONTROL / 'launch-inputs.json').read_bytes())['files']
    host_freeze = json.loads((CONTROL / 'host-freeze.json').read_bytes())
    for relative, expected in host_freeze.items():
        assert sha(ROOT / relative) == expected, relative
    assert snapshot_sources(PROJECT) == frozen
    assert snapshot_digest(frozen) == prepared['source_contract_sha256']
    config = (PROJECT / '.mcdev.json').read_bytes()
    assert sha(PROJECT / '.mcdev.json') == prepared['config_sha256']
    assert all(json.loads(config)[key] is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                                          'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
    assert not (CONTROL / 'start.stdout.json').exists(), 'This cold launch has already been used'
    assert not OUTPUT.exists()
    native = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data')
    assert (PROJECT / 'resource_pack/materials/portal.material').read_bytes() == (
        native / 'resource_packs/vanilla/materials/portal.material').read_bytes()
    assert not (PROJECT / 'resource_pack/shaders/glsl/r21_portal_fixed_time_native.vertex').exists()
    measured = ROOT / '.runtime/projects/portal-r20-native-v10/resource_pack/shaders/glsl/r19_native_portal_world.vertex'
    assert (PROJECT / 'resource_pack/shaders/glsl/modern_projection_portal_native_world.vertex').read_bytes() == measured.read_bytes()
    compiled = json.loads((ROOT / prepared['compile_report']).read_bytes())
    axes = json.loads((ROOT / prepared['ui_axes_report']).read_bytes())
    assert compiled['passed'] and axes['result']['passed']
    for name, expected in compiled['source_sha256'].items():
        assert sha(PROJECT / 'resource_pack/shaders/glsl' / name) == expected
    assert sha(PROJECT / 'resource_pack/shaders/glsl/modern_projection_portal_native_ui.vertex') == axes['shader_sha256']
    assert sha(TOOLS / 'watch_intrinsic_glint_exit_r21.py') == prepared['exit_observer_sha256']
    watcher = json.loads((ROOT / '.runtime/disabled-skin-watch-portal-r21-v12/status.json').read_bytes())
    assert watcher['owners'] == [OWNER] and not any(watcher[key] for key in ('errors', 'other_assertions', 'known_assert_recoveries'))
    assert process_identity(55680) == '134365769130132257'
    assert (datetime.now(timezone.utc) - datetime.fromisoformat(watcher['checked_at'])).total_seconds() < 20.
    memory, processes = commit_at_boundary(), census()
    assert memory['commit_available_bytes'] >= 6 * 1024 ** 3
    if require_no_game:
        assert not any(row['blocks_launch'] for row in processes), 'A live or uncertain MC process blocks launch'
    report = {'owner': OWNER, 'source_contract_sha256': prepared['source_contract_sha256'],
              'host_sha256': sha(Path(__file__)), 'memory': memory, 'memory_metric': 'CommitLimit-CommitTotal',
              'physical_memory_is_a_gate': False, 'process_census': processes,
              'launch_blocking_count': sum(row['blocks_launch'] for row in processes),
              'no_game_gate_required': require_no_game, 'all_reload_flags_false': True,
              'watcher_checked_at': watcher['checked_at'], 'child_environment': {'OPENBLAS_NUM_THREADS': '1'},
              'normal_time': True, 'native_gate': False, 'qualification': False}
    save(CONTROL / 'preflight-summary.json', report)
    print(json.dumps(report), flush=True)
    return report


def start():
    preflight(True)
    previous = json.loads(Path('C:/Users/Happy2018new/.pyreact-debug/instances/d3ce3a87949844aa8e95f052bab420ef/session.json').read_bytes())
    assert previous['owner'] == 'portal-r20-native-v10' and previous['state'] == 'stopped'
    guard = previous['noactivation']
    for name in ('mcdk', 'dll'):
        assert sha(Path(guard[name]['path'])) == guard[name]['sha256']
    command = [sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / 'instances.py'),
               'start', '--project', str(PROJECT), '--owner', OWNER, '--name', OWNER,
               '--wait', '180', '--preset', 'ui', '--game-exe', previous['game_executable'],
               '--mcdk', guard['mcdk']['path'], '--noactivate-mcdk-sha256', guard['mcdk']['sha256'],
               '--noactivate-dll', guard['dll']['path'], '--noactivate-sha256', guard['dll']['sha256']]
    with (CONTROL / 'start.stdout.json').open('x', encoding='utf8') as stdout, (
            CONTROL / 'start.stderr.txt').open('x', encoding='utf8') as stderr:
        result = subprocess.run(command, cwd=ROOT,
            env=dict(os.environ, OPENBLAS_NUM_THREADS='1', MCDEV_ALLOW_USER_FOREGROUND='1'),
            stdout=stdout, stderr=stderr, timeout=300)
    assert result.returncode == 0, 'Inspect private startup receipts before any next action'
    session = json.loads((CONTROL / 'start.stdout.json').read_bytes())
    ready = {key: session[key] for key in ('session_file', 'owner', 'state', 'game_pid',
                                          'game_identity', 'mcdk_pid', 'mcdk_identity')}
    assert ready['state'] == 'ready' and ready['owner'] == OWNER
    save(CONTROL / 'ready-summary.json', ready)
    print(json.dumps(ready), flush=True)
    subprocess.run([sys.executable, '-B', '-X', 'utf8', str(TOOLS / 'watch_intrinsic_glint_exit_r21.py'),
                    '--session', ready['session_file'], '--owner', OWNER,
                    '--output', str(CONTROL / 'exact-exit-observation.json')], cwd=ROOT, check=True)


def capture():
    frozen = json.loads((CONTROL / 'launch-inputs.json').read_bytes())['files']
    host_freeze = json.loads((CONTROL / 'host-freeze.json').read_bytes())
    for relative, expected in host_freeze.items():
        assert sha(ROOT / relative) == expected
    assert snapshot_sources(PROJECT) == frozen
    ready = json.loads((CONTROL / 'ready-summary.json').read_bytes())
    assert ready['owner'] == OWNER and ready['state'] == 'ready'
    observed = json.loads((CONTROL / 'exact-exit-observation.json').read_bytes())
    assert all(observed['processes'][kind]['state'] == 'live' for kind in ('game', 'mcdk'))
    command = [sys.executable, '-B', '-X', 'utf8', str(PROJECT / 'tools/probe_portal_native_candidate_r21.py'),
               '--project', str(PROJECT), '--session', ready['session_file'], '--owner', OWNER, '--output', str(OUTPUT)]
    with (CONTROL / 'capture.stdout.txt').open('x', encoding='utf8') as stdout, (
            CONTROL / 'capture.stderr.txt').open('x', encoding='utf8') as stderr:
        result = subprocess.run(command, cwd=PROJECT,
            env=dict(os.environ, OPENBLAS_NUM_THREADS='1', PYTHONPATH=str(SCRIPTS)),
            stdout=stdout, stderr=stderr, timeout=210)
    print(json.dumps({'capture_returncode': result.returncode, 'report_exists': (OUTPUT / 'report.json').exists()}))
    assert result.returncode == 0, 'Inspect retained capture report and cleanup before any retry'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'start', 'capture'))
    args = parser.parse_args()
    {'preflight': preflight, 'start': start, 'capture': capture}[args.action]()
