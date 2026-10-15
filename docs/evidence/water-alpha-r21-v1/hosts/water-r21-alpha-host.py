"""Prepare and run one owner-bound water alpha route at each natural boundary."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / '.runtime/projects/water-r20'
OUTPUT = ROOT / '.runtime/water-r21-alpha-v1'
PRIOR = ROOT / '.runtime/water-r20-state-v7'
OWNER = 'water-r21-alpha-v1'
CONTRACT = 'cb2b32de68b69f435d69b59cf296d8492d88984ddb96e10f020d7fdbd0aef806'
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
MCDK = ROOT / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
GUARD = ROOT / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
CAPTURE = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
CASES = ('wet_oak_fence', 'wet_glass_pane', 'wet_oak_slab', 'wet_oak_stairs')
sys.path[:0] = [str(ROOT / 'tools'), str(SCRIPTS)]
from _session import process_identity, registry_dir
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from probe_product_water import snapshot_sources, snapshot_digest

HOST_FILES = [Path(__file__), ROOT / '.runtime/water-r21-alpha-launch.py',
    SCRIPTS / 'instances.py', SCRIPTS / '_session.py',
    ROOT / 'tools/census_intrinsic_glint_ui_r21.py',
    ROOT / 'tools/analyze_product_water.py', ROOT / 'tools/water_native_projection.py',
    ROOT / 'tools/analyze_liquid_workspace.py', MCDK, GUARD, CAPTURE]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(name, value):
    with (OUTPUT / name).open('x', encoding='ascii') as handle:
        handle.write(json.dumps(value, sort_keys=True, indent=2) + '\n')


def observe(name, value):
    attempt = 1
    while (OUTPUT / ('%s-%d.json' % (name, attempt))).exists():
        attempt += 1
    save('%s-%d.json' % (name, attempt), value)


def validate_sources():
    launch = read(PRIOR / 'launch-inputs.json')
    current = snapshot_sources(PROJECT)
    assert current == launch['source_sha256'], 'Frozen water clone changed'
    assert len(current) == 3093 and snapshot_digest(current) == CONTRACT
    config = read(PROJECT / '.mcdev.json')
    assert all(config[key] is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                               'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
    assert sha(PROJECT / '.mcdev.json') == sha(PRIOR / 'launch-mcdev.json')
    return launch


def prepare():
    launch = validate_sources()
    assert not OUTPUT.exists(), 'Fresh one-use output directory required'
    OUTPUT.mkdir()
    shutil.copy2(PRIOR / 'launch-inputs.json', OUTPUT / 'launch-inputs.json')
    shutil.copy2(PROJECT / '.mcdev.json', OUTPUT / 'launch-mcdev.json')
    plan = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
        'owner': OWNER, 'project': str(PROJECT), 'source_files': len(launch['source_sha256']),
        'source_contract_sha256': CONTRACT, 'source_reference': str(PRIOR / 'launch-inputs.json'),
        'launch_inputs_sha256': sha(OUTPUT / 'launch-inputs.json'),
        'launch_config_sha256': sha(OUTPUT / 'launch-mcdev.json'),
        'host_files_sha256': {str(path.relative_to(ROOT).as_posix()): sha(path) for path in HOST_FILES},
        'window_actions': [], 'capture_host_suspensions': [], 'game_suspensions': [],
        'active_game_limit': 2, 'minimum_launch_commit_gib': 9., 'minimum_phase_commit_gib': 6.,
        'max_handles': 210000, 'max_batch_seconds': 600, 'cases': list(CASES),
        'expected_per_route': {'base_rows': 24, 'visibility_captures': 8, 'alpha_captures': 24, 'captures': 56},
        'phases': ['fresh_owner_launch', 'same_session_stone_calibration', 'full_alpha4',
                   'restore_and_offline_review', 'separately_scheduled_missing_alpha4', 'normal_stop'],
        'automatic_missing_route': False, 'calibration_reuse_from_v7': False,
        'capacity_checks': 'Before launch and each complete phase; existing probe guards handles before captures.'}
    save('plan.json', plan)
    save('plan-receipt.json', {'schema': 1, 'prepared_only': True,
        'plan_sha256': sha(OUTPUT / 'plan.json'), 'started': False})
    print(json.dumps({'prepared_only': True, 'owner': OWNER, 'output': str(OUTPUT),
                      'source_files': 3093, 'source_contract_sha256': CONTRACT}))


def validate_plan():
    plan = read(OUTPUT / 'plan.json')
    assert sha(OUTPUT / 'plan.json') == read(OUTPUT / 'plan-receipt.json')['plan_sha256']
    assert plan['owner'] == OWNER and Path(plan['project']).resolve() == PROJECT.resolve()
    assert plan['production_qualified'] is False and plan['source_contract_sha256'] == CONTRACT
    assert sha(OUTPUT / 'launch-inputs.json') == plan['launch_inputs_sha256']
    assert sha(PROJECT / '.mcdev.json') == plan['launch_config_sha256']
    for name, expected in plan['host_files_sha256'].items():
        assert sha(ROOT / name) == expected, 'Prepared host changed: ' + name
    validate_sources()
    return plan


def census():
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
        "@(Get-CimInstance Win32_Process -Filter \"Name='Minecraft.Windows.exe'\" | "
        "Select-Object ProcessId,HandleCount)|ConvertTo-Json -Compress"],
        capture_output=True, text=True, encoding='utf-8-sig', timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW, check=True)
    games = json.loads(result.stdout or '[]')
    games = games if isinstance(games, list) else [games]
    for game in games:
        game['identity'] = process_identity(game['ProcessId'])
    return [game for game in games if game['identity'] is not None]


def bound(live=True):
    start = read(OUTPUT / 'start.json')
    session = read(start['session_file'])
    for field in ('id', 'owner', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity'):
        assert session.get(field) == start.get(field), 'Session binding changed: ' + field
    assert session['owner'] == OWNER and Path(session['project']).resolve() == PROJECT.resolve()
    if live:
        assert session['ready'] is True and session['noactivation']['window_noactivate'] is True
        for kind in ('game', 'mcdk'):
            assert process_identity(session[kind + '_pid']) == session[kind + '_identity']
    return session


def preflight(launch=False):
    plan = validate_plan()
    games, own = census(), []
    for path in registry_dir().glob('*/session.json'):
        session = read(path)
        if (session.get('project') and Path(session['project']).resolve() == PROJECT.resolve()
                and session.get('game_pid') and process_identity(session['game_pid']) == session.get('game_identity')):
            own.append({key: session.get(key) for key in ('id', 'owner', 'game_pid', 'game_identity')})
    commit = commit_at_boundary()
    minimum = plan['minimum_launch_commit_gib' if launch else 'minimum_phase_commit_gib']
    if launch:
        identity_ok = not own and len(games) < plan['active_game_limit']
    else:
        session = bound()
        current = [game for game in games if game['ProcessId'] == session['game_pid']
                   and game['identity'] == session['game_identity']]
        identity_ok = (len(own) == len(current) == 1 and len(games) <= plan['active_game_limit']
                       and current[0]['HandleCount'] < plan['max_handles'])
    return {'schema': 1, 'started': False, 'launch_preflight': launch, 'owner': OWNER,
        'games': games, 'same_project_live': own, 'commit': commit, 'minimum_commit_gib': minimum,
        'passed': identity_ok and commit['commit_available_bytes'] >= minimum * 1024 ** 3}


def start_once():
    state = preflight(launch=True)
    assert state['passed'], 'Launch capacity or frozen-project check failed'
    assert not (OUTPUT / 'start.json').exists(), 'This output has already launched'
    save('launch-attempt.json', {'schema': 1, 'one_use': True, 'preflight': state,
                              'plan_sha256': sha(OUTPUT / 'plan.json')})
    config = read(OUTPUT / 'launch-mcdev.json')
    command = [sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / 'instances.py'), 'start',
        '--project', str(PROJECT), '--owner', OWNER, '--name', OUTPUT.name,
        '--game-exe', config['game_executable_path'], '--preset', 'ui', '--wait', '180',
        '--mcdk', str(MCDK), '--noactivate-mcdk-sha256',
        'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9',
        '--noactivate-dll', str(GUARD), '--noactivate-sha256',
        '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93']
    result = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, encoding='utf8',
        env=dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND='1'), creationflags=subprocess.CREATE_NO_WINDOW)
    save('launch-execution.json', {'argv': command, 'returncode': result.returncode,
                                 'stdout': result.stdout, 'stderr': result.stderr})
    if result.stdout.strip():
        save('start.json', json.loads(result.stdout))
    assert result.returncode == 0, 'Launch failed; retain registry and launch diagnostics'
    state = preflight()
    save('after-launch.json', state)
    print(json.dumps({'ready': state['passed'], 'session': bound()['id'], 'owner': OWNER,
                      'source_contract_sha256': CONTRACT, 'next_phase': 'calibration'}))
    return 0 if state['passed'] else 1


def execute(name, command, stop=False):
    if not stop:
        state = preflight()
        observe(name + '-preflight', state)
        assert state['passed'], 'Phase capacity or identity check failed'
    session = bound(live=not stop)
    environment = dict(os.environ, MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=OWNER,
                       MCDEV_MCP_URL=session.get('mcp_url', ''), MCDEV_ALLOW_USER_FOREGROUND='1')
    result = subprocess.run(command, cwd=str(ROOT), env=environment,
        capture_output=True, text=True, encoding='utf8', creationflags=subprocess.CREATE_NO_WINDOW)
    save(name + '-execution.json', {'argv': command, 'returncode': result.returncode,
                                   'stdout': result.stdout, 'stderr': result.stderr})
    if result.returncode == 0 and not stop:
        report = read(OUTPUT / (name + '.json'))
        assert report['completed'] is True and report['restored'] is True and report['cleanup_errors'] == []
        validate_sources()
        commit = commit_at_boundary()
        save(name + '-restored.json', {'schema': 1, 'completed': True, 'restored': True,
            'report_sha256': sha(OUTPUT / (name + '.json')), 'source_contract_sha256': CONTRACT,
            'commit': commit, 'minimum_runtime_commit_met': commit['commit_available_bytes'] >= 6 * 1024 ** 3})
    print(json.dumps({'phase': name, 'returncode': result.returncode, 'stderr': result.stderr[-2000:]}))
    return result.returncode


def capture_phase(name):
    assert not (OUTPUT / (name + '.json')).exists(), 'Fresh phase output required'
    if name == 'calibration':
        command = [sys.executable, '-B', '-X', 'utf8', str(PROJECT / 'tools/verify_camera_projection.py'),
            str(OUTPUT / 'calibration.json'), '--native-resolution', '--skyward-tilted',
            '--fixture-lift-y', '64', '--native-api', '--native-capture-exe', str(CAPTURE)]
    else:
        route = name.split('-', 1)[0]
        assert route in ('full', 'missing')
        if route == 'missing':
            review = read(OUTPUT / 'full-alpha4-review.json')
            assert review['source_sha256'] == sha(OUTPUT / 'full-alpha4.json')
            assert review['evidence_valid'] is True and review['restored'] is True
        session = bound()
        command = [sys.executable, '-B', '-X', 'utf8', str(PROJECT / 'tools/probe_product_water.py'),
            '--session', session['session_file'], '--owner', OWNER, '--capture-exe', str(CAPTURE),
            '--launch-inputs', str(OUTPUT / 'launch-inputs.json'), '--output', str(OUTPUT / (name + '.json')),
            '--camera-calibration', str(OUTPUT / 'calibration.json'), '--world-fixture-lift-y', '64',
            '--world-view-scale', '.5', '--frozen', '--controls', 'all', '--visibility-controls',
            '--measure-budgets', '--alpha-controls', '--route', route,
            '--max-handles', '210000', '--max-seconds', '600']
        for case in CASES:
            command.extend(('--case', case))
    return execute(name, command)


def review_full():
    validate_plan()
    source_path = OUTPUT / 'full-alpha4.json'
    source = read(source_path)
    assert all(source[key] is True for key in ('completed', 'restored', 'source_unchanged'))
    assert source['cleanup_errors'] == [] and source['routes'] == ['full']
    assert len(source['captures']) == 56 and len(source['rows']) == 24
    assert not (OUTPUT / 'full-alpha4-review.json').exists(), 'Retain the previous review'
    import numpy as np
    import analyze_liquid_workspace as workspace
    import analyze_product_water as product
    original_rgb = product.rgb
    with tempfile.TemporaryDirectory(prefix='water-alpha-r21-') as directory:
        cache = {}

        def decoded_rgb(path):
            key = str(Path(path).resolve(strict=True))
            if key not in cache:
                target = Path(directory) / ('decoded-%d.npy' % len(cache))
                np.save(target, original_rgb(path), allow_pickle=False)
                cache[key] = target
            return np.load(cache[key], mmap_mode='r', allow_pickle=False)

        product.rgb = workspace.rgb = decoded_rgb
        try:
            results = {'original': product.analyze(source_path),
                       'native': product.analyze(source_path, native_world_geometry=True)}
        finally:
            product.rgb = workspace.rgb = original_rgb
    for name, result in results.items():
        result.update(diagnostic_only=True, production_qualified=False)
        save('full-alpha4-' + name + '-analysis.json', result)
    summary = {'schema': 1, 'source_sha256': sha(source_path), 'restored': True,
        'evidence_valid': all(result['evidence_valid'] for result in results.values()),
        'alpha_controls': {name: {key: row['passed'] for key, row in result['alpha_controls'].items()}
                           for name, result in results.items()},
        'production_qualified': False, 'automatic_missing_route': False}
    save('full-alpha4-review.json', summary)
    print(json.dumps(summary))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'preflight', 'calibration', 'full', 'review-full', 'missing', 'stop'))
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'preflight':
        print(json.dumps(preflight(launch=not (OUTPUT / 'start.json').exists())))
    elif args.action == 'review-full':
        review_full()
    elif args.action == 'stop':
        session = bound(live=False)
        attempt = 1
        while (OUTPUT / ('stop-attempt-%d-execution.json' % attempt)).exists():
            attempt += 1
        return execute('stop-attempt-%d' % attempt,
            [sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / 'instances.py'), 'stop',
             '--session', session['session_file'], '--owner', OWNER], stop=True)
    else:
        return capture_phase('calibration' if args.action == 'calibration' else args.action + '-alpha4')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
