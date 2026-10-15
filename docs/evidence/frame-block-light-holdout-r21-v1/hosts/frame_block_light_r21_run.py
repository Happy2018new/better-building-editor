"""Inspect or explicitly schedule the frozen item-only base-light holdouts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / '.runtime/projects/frame-block-r21-light-holdout-v1'
CONTROL = ROOT / '.runtime/frame-block-r21-light-holdout-control-v1'
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
OWNER = 'item-r20'
WGC = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
WGC_SHA = 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
MCDK = ROOT / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
MCDK_SHA = 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9'
GUARD = ROOT / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
GUARD_SHA = '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93'
sys.path[:0] = [str(PROJECT / 'tools'), str(SCRIPTS)]
from item_sprite_capture_contract import snapshot_sources, snapshot_digest
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from _session import process_identity, registry_dir, load_session


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    path = CONTROL / name
    assert not path.exists(), 'Retain existing operation evidence: ' + name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='ascii')


def plan():
    value = json.loads((CONTROL / 'plan.json').read_bytes())
    assert value['prepared'] and not value['started'] and value['owner'] == OWNER
    assert Path(value['project']).resolve() == PROJECT.resolve()
    assert value['launcher_sha256'] == sha(Path(__file__))
    assert snapshot_digest(snapshot_sources(PROJECT)) == value['source_sha256']
    assert value['candidate_sha256'] == sha(CONTROL / 'candidate.json')
    assert value['configuration_sha256'] == sha(PROJECT / '.mcdev.json')
    assert value['source_textures_sha256'] == sha(CONTROL / 'source-textures.json')
    config = json.loads((PROJECT / '.mcdev.json').read_bytes())
    assert all(config[key] is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
        'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
    for phase in value['phases']:
        assert sha(CONTROL / phase['matrix']) == phase['matrix_sha256']
    return value


def preflight():
    frozen = plan()
    for path, expected in ((WGC, WGC_SHA), (MCDK, MCDK_SHA), (GUARD, GUARD_SHA)):
        assert sha(path) == expected, 'Reviewed runtime helper differs: ' + str(path)
    census = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
        "@(Get-CimInstance Win32_Process -Filter \"Name='Minecraft.Windows.exe'\" | "
        "Select-Object ProcessId,CreationDate,ThreadCount,HandleCount)|ConvertTo-Json -Compress"],
        check=True, capture_output=True, encoding='utf-8-sig', timeout=15,
        creationflags=subprocess.CREATE_NO_WINDOW)
    games = json.loads(census.stdout or '[]')
    games = games if isinstance(games, list) else [games]
    live = [row for row in games if process_identity(row['ProcessId']) is not None]
    own = []
    for path in registry_dir().glob('*/session.json'):
        session = json.loads(path.read_bytes())
        if (session.get('owner') == OWNER and session.get('game_pid')
                and process_identity(session['game_pid']) == session.get('game_identity')):
            own.append({key: session[key] for key in ('id', 'game_pid', 'game_identity', 'state')})
    commit = commit_at_boundary()
    return {'schema': 1, 'owner': OWNER, 'started': False,
        'source_sha256': frozen['source_sha256'], 'games': live, 'same_owner_live': own,
        'commit': commit, 'minimum_start_commit_gib': 9., 'runtime_commit_reserve_gib': 6.,
        'passed': not own and len(live) < 2 and commit['commit_available_bytes'] >= 9 * 1024 ** 3,
        'read_only': True}


def ready():
    frozen = plan()
    row = json.loads((CONTROL / 'ready-summary.json').read_bytes())
    session = load_session(row['session_file'], OWNER, live=True)
    assert Path(session['project']).resolve() == PROJECT.resolve()
    assert all(row[kind + '_identity'] == session[kind + '_identity'] for kind in ('game', 'mcdk'))
    return frozen, session


def start(scheduled):
    assert scheduled, 'Root must schedule this runtime window explicitly'
    state = preflight()
    assert state['passed'], 'Capacity or same-owner preflight failed'
    save('launch-preflight.json', state)
    save('launch-attempt.json', {'at': datetime.now(timezone.utc).isoformat(), 'scheduled_by_root': True})
    command = [sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / 'instances.py'), 'start',
        '--project', str(PROJECT), '--owner', OWNER, '--name', 'frame-block-r21-light-holdout-v1',
        '--wait', '180', '--preset', 'ui', '--game-exe',
        'D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/Minecraft.Windows.exe',
        '--mcdk', str(MCDK), '--noactivate-mcdk-sha256', MCDK_SHA,
        '--noactivate-dll', str(GUARD), '--noactivate-sha256', GUARD_SHA]
    result = subprocess.run(command, cwd=str(ROOT), env=dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND='1'),
        capture_output=True, encoding='utf-8', timeout=300, creationflags=subprocess.CREATE_NO_WINDOW)
    (CONTROL / 'start.stdout.txt').write_text(result.stdout, encoding='utf-8')
    (CONTROL / 'start.stderr.txt').write_text(result.stderr, encoding='utf-8')
    assert result.returncode == 0, 'Inspect retained private startup evidence before considering another action'
    session = json.loads(result.stdout)
    save('ready-summary.json', {key: session[key] for key in ('id', 'owner', 'state', 'project',
        'session_file', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')})
    with (CONTROL / 'exit-watch.stdout.txt').open('w', encoding='ascii') as stdout, (
            CONTROL / 'exit-watch.stderr.txt').open('w', encoding='ascii') as stderr:
        watcher = subprocess.Popen([sys.executable, '-B', '-X', 'utf8',
            str(PROJECT / 'tools/watch_intrinsic_glint_exit_r21.py'),
            '--session', session['session_file'], '--owner', OWNER,
            '--output', str(CONTROL / 'exact-exit.json')], cwd=str(PROJECT),
            stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
    save('exit-watch-start.json', {'pid': watcher.pid, 'identity': process_identity(watcher.pid)})
    deadline = time.monotonic() + 10.
    while not (CONTROL / 'exact-exit.json').exists() and time.monotonic() < deadline and watcher.poll() is None:
        time.sleep(.2)
    assert (CONTROL / 'exact-exit.json').exists(), 'Retained-handle exit observer must be ready before captures'
    save('commit-after-start.json', commit_at_boundary())
    return {key: session[key] for key in ('id', 'owner', 'state', 'game_pid', 'game_identity')}


def execute(action, phase):
    frozen, session = ready()
    assert commit_at_boundary()['commit_available_bytes'] >= 6 * 1024 ** 3
    observer = json.loads((CONTROL / 'exact-exit.json').read_bytes())
    assert not observer['completed']
    for kind in ('game', 'mcdk'):
        assert observer['processes'][kind]['pid'] == session[kind + '_pid']
        assert observer['processes'][kind]['identity'] == session[kind + '_identity']
    environment = dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND='1',
        MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=OWNER, MCDEV_MCP_URL=session['mcp_url'])
    if action == 'probe':
        command = [sys.executable, '-B', '-X', 'utf8', str(PROJECT / 'tools/probe_frame_block_enchantment_r21.py'),
            '--session', session['session_file'], '--owner', OWNER,
            '--output', str(CONTROL / 'artificial-enchantment-probe.json'),
            '--maximum-handles', '190000', '--minimum-commit-gib', '6']
    else:
        requested = next(row for row in frozen['phases'] if row['id'] == phase)
        if requested['contains_quartz_control']:
            probe = json.loads((CONTROL / 'artificial-enchantment-probe.json').read_bytes())
            assert all(probe[key] for key in ('passed', 'completed', 'restored')) and not probe['cleanup_errors']
            assert probe['game_pid'] == session['game_pid'] and probe['game_identity'] == session['game_identity']
            probe_requirement = 'same_session_typed_probe_passed_and_restored'
        else:
            probe_requirement = 'not_required_for_phase'
        for previous in frozen['phases'][:frozen['phases'].index(requested)]:
            outcome = json.loads((CONTROL / (previous['id'] + '-outcome.json')).read_bytes())
            assert outcome['phase_ready_for_review'], 'Prior phase must be complete and restored'
        save(phase + '-attempt.json', {'at': datetime.now(timezone.utc).isoformat(),
            'scheduled_by_root': True, 'artificial_enchantment_probe': probe_requirement})
        command = [sys.executable, '-B', '-X', 'utf8', str(PROJECT / 'tools/frame_block_light_r21_host.py'),
            '--session', session['session_file'], '--control', str(CONTROL),
            '--phase', phase, '--wgc', str(WGC)]
    return subprocess.call(command, cwd=str(PROJECT), env=environment, creationflags=subprocess.CREATE_NO_WINDOW)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'start', 'probe', 'capture'))
    parser.add_argument('--scheduled-by-root', action='store_true')
    parser.add_argument('--phase')
    args = parser.parse_args()
    if args.action == 'preflight':
        print(json.dumps(preflight()))
    elif args.action == 'start':
        print(json.dumps(start(args.scheduled_by_root)))
    else:
        if args.action == 'capture' and not args.phase:
            parser.error('capture requires one --phase; no automatic multi-phase run')
        raise SystemExit(execute(args.action, args.phase))
