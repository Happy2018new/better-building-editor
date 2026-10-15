"""One explicitly scheduled grass phase; all inputs are frozen before launch."""
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
PROJECT = ROOT / '.runtime/projects/frame-block-grass-overlay-r21-v1'
CONTROL = ROOT / '.runtime/frame-block-grass-overlay-r21-control-v1'
SCRIPTS = PROJECT / '.agents/skills/pyreact-debugging/scripts'
OWNER = 'item-r20'
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
    assert value['prepared'] and value['owner'] == OWNER
    assert Path(value['project']).resolve() == PROJECT.resolve()
    assert value['launcher_sha256'] == sha(Path(__file__))
    assert value['reviewer_sha256'] == sha(ROOT / '.runtime/frame_block_grass_r21_review.py')
    assert value['analysis_manifest_sha256'] == sha(ROOT / 'docs/evidence/frame-block-light-holdout-r21-v1/manifest.json')
    assert snapshot_digest(snapshot_sources(PROJECT)) == value['source_sha256']
    for name in ('candidate', 'source-textures'):
        assert sha(CONTROL / (name + '.json')) == value[name.replace('-', '_') + '_sha256']
    assert sha(PROJECT / '.mcdev.json') == value['configuration_sha256']
    configuration = json.loads((PROJECT / '.mcdev.json').read_bytes())
    assert all(configuration[key] is False for key in ('auto_hot_reload_mods',
        'auto_hot_reload_ui', 'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
    assert not (PROJECT / 'level.dat').exists()
    for relative, expected in value['external_host_files'].items():
        path = CONTROL / 'external-host' / relative
        assert path.is_file() and sha(path) == expected, 'Frozen external host missing or changed: ' + relative
    for relative, expected in value['binaries'].items():
        assert sha(ROOT / relative) == expected
    assert sha(Path(value['game_executable'])) == value['game_executable_sha256']
    for phase in value['phases']:
        assert sha(CONTROL / phase['matrix']) == phase['matrix_sha256']
        matrix = json.loads((CONTROL / phase['matrix']).read_bytes())
        assert len(matrix['cases']) == 1
        assert matrix['cases'][0]['item'] == ['minecraft:grass_block', 0]
        assert matrix['cases'][0]['view_angle_degrees'] == phase['angle']
        assert not matrix['cases'][0]['artificially_enchanted']
    return value


def preflight():
    frozen = plan()
    census = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
        "@(Get-CimInstance Win32_Process -Filter \"Name='Minecraft.Windows.exe'\" | "
        "Select-Object ProcessId,CreationDate,ThreadCount,HandleCount)|ConvertTo-Json -Compress"],
        check=True, capture_output=True, encoding='utf-8-sig', timeout=15,
        creationflags=subprocess.CREATE_NO_WINDOW)
    rows = json.loads(census.stdout or '[]')
    rows = rows if isinstance(rows, list) else [rows]
    games = [row for row in rows if process_identity(row['ProcessId']) is not None]
    own = []
    for path in registry_dir().glob('*/session.json'):
        session = json.loads(path.read_bytes())
        if (session.get('owner') == OWNER and session.get('game_pid')
                and process_identity(session['game_pid']) == session.get('game_identity')):
            own.append(session['id'])
    commit = commit_at_boundary()
    return {'schema': 1, 'read_only': True, 'owner': OWNER,
        'source_sha256': frozen['source_sha256'], 'external_observer_validated': True,
        'games': games, 'same_owner_live': own, 'commit': commit,
        'minimum_start_commit_gib': 9., 'runtime_commit_reserve_gib': 6.,
        'passed': not own and len(games) < 2 and commit['commit_available_bytes'] >= 9 * 1024 ** 3}


def start(scheduled):
    assert scheduled, 'Root must explicitly schedule this runtime window'
    frozen = plan()
    state = preflight()
    assert state['passed'], 'Capacity or same-owner preflight failed'
    save('launch-preflight.json', state)
    save('launch-attempt.json', {'at': datetime.now(timezone.utc).isoformat(), 'scheduled_by_root': True})
    helpers = frozen['helpers']
    command = [sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / 'instances.py'), 'start',
        '--project', str(PROJECT), '--owner', OWNER, '--name', 'frame-block-grass-overlay-r21-v1',
        '--wait', '180', '--preset', 'ui', '--game-exe', frozen['game_executable'],
        '--mcdk', str(ROOT / helpers['mcdk']), '--noactivate-mcdk-sha256', frozen['binaries'][helpers['mcdk']],
        '--noactivate-dll', str(ROOT / helpers['guard']), '--noactivate-sha256', frozen['binaries'][helpers['guard']]]
    result = subprocess.run(command, cwd=str(ROOT), env=dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND='1'),
        capture_output=True, encoding='utf-8', timeout=300, creationflags=subprocess.CREATE_NO_WINDOW)
    (CONTROL / 'start.stdout.txt').write_text(result.stdout, encoding='utf-8')
    (CONTROL / 'start.stderr.txt').write_text(result.stderr, encoding='utf-8')
    assert result.returncode == 0, 'Inspect retained startup evidence; do not replay start'
    session = json.loads(result.stdout)
    save('ready-summary.json', {key: session[key] for key in ('id', 'owner', 'state', 'project',
        'session_file', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')})
    observer = CONTROL / 'external-host/tools/watch_intrinsic_glint_exit_r21.py'
    assert sha(observer) == frozen['external_host_files']['tools/watch_intrinsic_glint_exit_r21.py']
    with (CONTROL / 'exit-watch.stdout.txt').open('w', encoding='ascii') as stdout, (
            CONTROL / 'exit-watch.stderr.txt').open('w', encoding='ascii') as stderr:
        watcher = subprocess.Popen([sys.executable, '-B', '-X', 'utf8', str(observer),
            '--session', session['session_file'], '--owner', OWNER,
            '--output', str(CONTROL / 'exact-exit.json')], cwd=str(observer.parents[1]),
            stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
    save('exit-watch-start.json', {'pid': watcher.pid, 'identity': process_identity(watcher.pid),
        'observer_sha256': sha(observer)})
    deadline = time.monotonic() + 10.
    exact = None
    while time.monotonic() < deadline and watcher.poll() is None:
        try:
            exact = json.loads((CONTROL / 'exact-exit.json').read_bytes())
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(.2)
            continue
        break
    assert exact is not None, 'Exact process handles must be retained before capture'
    assert not exact['completed']
    for kind in ('game', 'mcdk'):
        assert exact['processes'][kind]['identity'] == session[kind + '_identity']
        assert exact['processes'][kind]['pid'] == session[kind + '_pid']
    save('commit-after-start.json', commit_at_boundary())
    return {key: session[key] for key in ('id', 'owner', 'state', 'game_pid', 'game_identity')}


def capture(phase_id, scheduled, front_review, reviewed):
    assert scheduled, 'Each phase requires explicit root scheduling'
    frozen = plan()
    phase = next(row for row in frozen['phases'] if row['id'] == phase_id)
    saved = json.loads((CONTROL / 'ready-summary.json').read_bytes())
    session = load_session(saved['session_file'], OWNER, live=True)
    assert Path(session['project']).resolve() == PROJECT.resolve()
    assert all(session[key] == saved[key] for key in ('game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity'))
    exact = json.loads((CONTROL / 'exact-exit.json').read_bytes())
    assert not exact['completed']
    for kind in ('game', 'mcdk'):
        assert exact['processes'][kind]['identity'] == session[kind + '_identity']
        assert exact['processes'][kind]['pid'] == session[kind + '_pid']
    assert commit_at_boundary()['commit_available_bytes'] >= 6 * 1024 ** 3
    review_sha = None
    if phase_id != 'front':
        assert reviewed and front_review is not None, 'Root must inspect the first shown images before oblique phases'
        front = json.loads((CONTROL / 'front-outcome.json').read_bytes())
        assert front['phase_ready_for_review']
        review = json.loads(front_review.read_bytes())
        assert review['phase'] == 'front' and review['batch_completed']
        assert review['planned_source_sha256'] == frozen['source_sha256']
        assert review['source_report_sha256'] == front['report_sha256']
        assert review['reviewer_sha256'] == frozen['reviewer_sha256']
        assert review['runtime_outcome_sha256'] == sha(CONTROL / 'front-outcome.json')
        review_sha = sha(front_review)
    for previous in frozen['phases'][:frozen['phases'].index(phase)]:
        outcome = json.loads((CONTROL / (previous['id'] + '-outcome.json')).read_bytes())
        assert outcome['phase_ready_for_review'], 'Prior phase incomplete; no automatic retry'
    save(phase_id + '-attempt.json', {'at': datetime.now(timezone.utc).isoformat(),
        'scheduled_by_root': True, 'first_image_reviewed_by_root': reviewed,
        'front_review_sha256': review_sha, 'artificial_enchantment_probe': 'not_required_for_plain_grass'})
    command = [sys.executable, '-B', '-X', 'utf8', str(PROJECT / 'tools/frame_block_light_r21_host.py'),
        '--session', session['session_file'], '--control', str(CONTROL), '--phase', phase_id,
        '--wgc', str(ROOT / frozen['helpers']['wgc'])]
    environment = dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND='1', MCDEV_SESSION_FILE=session['session_file'],
        MCDEV_OWNER=OWNER, MCDEV_MCP_URL=session['mcp_url'])
    return subprocess.call(command, cwd=str(PROJECT), env=environment, creationflags=subprocess.CREATE_NO_WINDOW)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('check', 'preflight', 'start', 'capture'))
    parser.add_argument('--phase', choices=('front', 'left75', 'right75'))
    parser.add_argument('--scheduled-by-root', action='store_true')
    parser.add_argument('--front-review', type=Path)
    parser.add_argument('--first-image-reviewed-by-root', action='store_true')
    args = parser.parse_args()
    if args.action == 'check':
        frozen = plan()
        print(json.dumps({'read_only': True, 'source_sha256': frozen['source_sha256'],
            'external_observer_validated': True, 'started': False, 'production_qualified': False}))
    elif args.action == 'preflight':
        print(json.dumps(preflight()))
    elif args.action == 'start':
        print(json.dumps(start(args.scheduled_by_root)))
    else:
        if args.phase is None:
            parser.error('capture requires exactly one --phase')
        raise SystemExit(capture(args.phase, args.scheduled_by_root, args.front_review, args.first_image_reviewed_by_root))
