"""Prepare offline; launch with a retained observer only after root scheduling."""
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
import traceback

os.environ['OPENBLAS_NUM_THREADS'] = '1'

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE_PROJECT = ROOT / '.runtime/projects/water-r20'
PROJECT = ROOT / '.runtime/projects/water-depth-cache-r21'
OUTPUT = ROOT / '.runtime/water-r21-depth-cache-ab-v1'
ORIGINAL_OWNER = 'water-r21-depth-cache-ab-v1'
OWNER = 'water-r20-depth-cache-ab-v1'
ORIGINAL_PLAN_SHA = 'd841ba845a2e98ec070a34a9e4d2a26a09fb9e9bb74c1256da551957fcb16b6c'
ORIGINAL_HOST_SHA = 'e54ec5b4f7560eab009305dec96a7cad9e29ef1b8b18a67faeab2e3cec17a7a2'
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
OBSERVER = ROOT / 'tools/watch_intrinsic_glint_exit_r21.py'
OBSERVER_SHA = 'aa436ee9a0f496554c69330d8456fa21b6bb551b63032f0b5a453ad9748646aa'
MCDK = ROOT / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
MCDK_SHA = 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9'
GUARD = ROOT / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
GUARD_SHA = '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93'
WATCHER = ROOT / 'tools/watch_owned_disabled_skin_assert_r20.py'
WATCHER_SHA = '704cc3de732c3315d046dbcee393d72cb34fd60f232e16f64978b3e61f9cad89'
WATCHER_STATUS = ROOT / '.runtime/disabled-skin-watch-r20-v2/status.json'
PRIOR_AMENDMENT = OUTPUT / 'operational-amendment-v1.json'
PRIOR_AMENDMENT_SHA = 'c681a3331a3faf9f4d49f02614f4b87dae6ea0cf37047204ddef1b29ae1f7c59'
AMENDMENT = OUTPUT / 'operational-amendment-v2.json'
ORIGINAL_FILES = ('plan.json', 'plan-receipt.json', 'launch-inputs.json',
                  'launch-mcdev.json', 'baseline_viewport.py')
SOURCE = 'behavior_pack/modern_projection/projection/liquid_viewport.py'
BASELINE_REF = '0898a8f6'
CANDIDATE_REF = 'a09aa9b9'
BASELINE_SHA = 'd07472df91d4c4cd93c2d7d84cd37c34c00cdac72ade470d290a6e125b0531cf'
CANDIDATE_SHA = '0f28e9f1bbc7faf6456de793b0d29378a7cc2bc0768c5ff07b4b61e404cda9d0'
BASE_CONTRACT = 'cb2b32de68b69f435d69b59cf296d8492d88984ddb96e10f020d7fdbd0aef806'
POSE = (35., 25., 4.6)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(name, value):
    path = OUTPUT / name
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='ascii')


def probe_for(project):
    sys.path.insert(0, str(project / 'tools'))
    import probe_product_water
    return probe_product_water


def prepare():
    assert not PROJECT.exists() and not OUTPUT.exists(), 'Fresh project and evidence paths required'
    probe = probe_for(BASE_PROJECT)
    reference = read(ROOT / '.runtime/water-r20-state-v7/launch-inputs.json')['source_sha256']
    assert probe.snapshot_sources(BASE_PROJECT) == reference
    assert len(reference) == 3093 and probe.snapshot_digest(reference) == BASE_CONTRACT
    baseline = subprocess.check_output(['git', 'show', BASELINE_REF + ':' + SOURCE], cwd=str(ROOT))
    candidate = subprocess.check_output(['git', 'show', CANDIDATE_REF + ':' + SOURCE], cwd=str(ROOT))
    assert hashlib.sha256(baseline).hexdigest() == BASELINE_SHA
    assert hashlib.sha256(candidate).hexdigest() == CANDIDATE_SHA
    OUTPUT.mkdir()
    shutil.copytree(BASE_PROJECT, PROJECT)
    (PROJECT / SOURCE).write_bytes(candidate)
    (OUTPUT / 'baseline_viewport.py').write_bytes(baseline)
    expected = dict(reference)
    expected[SOURCE] = CANDIDATE_SHA
    actual = probe.snapshot_sources(PROJECT)
    assert actual == expected
    assert [name for name in actual if actual[name] != reference[name]] == [SOURCE]
    config = read(PROJECT / '.mcdev.json')
    assert all(config[name] is False for name in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                                  'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
    save('launch-inputs.json', {'source_sha256': actual,
                              'source_contract_sha256': probe.snapshot_digest(actual)})
    shutil.copy2(PROJECT / '.mcdev.json', OUTPUT / 'launch-mcdev.json')
    plan = {'schema': 1, 'prepared_only': True, 'runtime_action': False, 'started': False,
            'owner': ORIGINAL_OWNER, 'project': str(PROJECT), 'fixture': 'water_style_flow_east_wet',
            'baseline_ref': BASELINE_REF, 'candidate_ref': CANDIDATE_REF,
            'baseline_source_sha256': BASELINE_SHA, 'candidate_source_sha256': CANDIDATE_SHA,
            'source_files': len(actual), 'source_contract_sha256': probe.snapshot_digest(actual),
            'changed_source_paths_from_original_water_clone': [SOURCE],
            'launch_config_sha256': sha(PROJECT / '.mcdev.json'),
            'launch_inputs_sha256': sha(OUTPUT / 'launch-inputs.json'),
            'host_files_sha256': {str(path.relative_to(ROOT).as_posix()): sha(path) for path in
                                   (Path(__file__), HERE / 'embedded_ab.py', OUTPUT / 'baseline_viewport.py')},
            'natural_steady_ticks_per_side': 60, 'warmup_ticks': 5,
            'depth_change': 'session.move_depth(1), then restore the original target',
            'clip_control': 'natural owner callback result with clipped=True',
            'invalid_control': 'natural owner callback result with distance=512, then controls.retry()',
            'window_actions': [], 'screenshots': [], 'forced_stop': False,
            'production_qualified': False, 'original_elapsed_failures_resolved': False}
    save('plan.json', plan)
    save('plan-receipt.json', {'plan_sha256': sha(OUTPUT / 'plan.json'), 'prepared_only': True,
                              'runtime_action': False, 'started': False})
    print(json.dumps(plan, sort_keys=True))


def external_dependencies():
    pending = [OBSERVER, WATCHER, SCRIPTS / 'instances.py',
               ROOT / 'tools/census_intrinsic_glint_ui_r21.py']
    paths = set()
    while pending:
        path = pending.pop().resolve(strict=True)
        if path in paths:
            continue
        paths.add(path)
        tree = ast.parse(path.read_bytes(), filename=str(path))
        for node in ast.walk(tree):
            names = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                     else [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0
                     else [])
            for name in names:
                if not name:
                    continue
                for directory in (ROOT / 'tools', SCRIPTS):
                    dependency = directory / (name.split('.')[0] + '.py')
                    if dependency.is_file():
                        pending.append(dependency)
    return {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(paths)}


def amend():
    assert not AMENDMENT.exists(), 'Operational amendment already exists'
    assert sha(PRIOR_AMENDMENT) == PRIOR_AMENDMENT_SHA
    prior = read(PRIOR_AMENDMENT)
    assert sha(OUTPUT / 'plan.json') == ORIGINAL_PLAN_SHA
    plan = read(OUTPUT / 'plan.json')
    host_name = Path(__file__).relative_to(ROOT).as_posix()
    assert plan['owner'] == ORIGINAL_OWNER
    assert plan['host_files_sha256'][host_name] == ORIGINAL_HOST_SHA
    dependencies = external_dependencies()
    for path, expected in ((OBSERVER, OBSERVER_SHA), (WATCHER, WATCHER_SHA),
                           (MCDK, MCDK_SHA), (GUARD, GUARD_SHA)):
        assert sha(path) == expected, 'Approved operational dependency changed: ' + str(path)
    receipt = {'schema': 1, 'prepared_only': True, 'runtime_action': False, 'started': False,
               'original_owner': ORIGINAL_OWNER, 'operational_owner': OWNER,
               'reason': 'Preserve the covered owner; bound dedicated host BLAS threads and classify effective live processes',
               'prior_amendment': {'path': str(PRIOR_AMENDMENT), 'sha256': PRIOR_AMENDMENT_SHA},
               'superseded_operational_files_sha256': prior['operational_files_sha256'],
               'original_files_sha256': {name: sha(OUTPUT / name) for name in ORIGINAL_FILES},
               'superseded_host_sha256': ORIGINAL_HOST_SHA,
               'operational_files_sha256': {host_name: sha(__file__),
                   (HERE / 'README.md').relative_to(ROOT).as_posix(): sha(HERE / 'README.md')},
               'external_dependencies_sha256': dependencies,
               'observer': {'path': str(OBSERVER), 'sha256': OBSERVER_SHA,
                            'required_before_launch': True, 'retained_handles_before_ab': True},
               'noactivation': {'mcdk': {'path': str(MCDK), 'sha256': MCDK_SHA},
                                'dll': {'path': str(GUARD), 'sha256': GUARD_SHA}},
               'watcher': {'status': str(WATCHER_STATUS), 'host_sha256': WATCHER_SHA,
                           'required_owner_coverage': 'water-r20-*', 'maximum_age_seconds': 60},
               'minimum_launch_commit_gib': 9, 'minimum_phase_commit_gib': 6,
               'active_game_limit': 2, 'max_owned_handles': 210000,
               'host_environment': {'OPENBLAS_NUM_THREADS': '1'},
               'process_gate': 'Exclude only HandleCount=0/ThreadCount=0 with no live creation identity; count unresolved rows conservatively',
               'frozen_project_changed': False, 'production_qualified': False}
    with AMENDMENT.open('x', encoding='ascii') as handle:
        handle.write(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    validate_plan()
    print(json.dumps({'prepared_only': True, 'runtime_action': False, 'started': False,
                      'operational_owner': OWNER, 'amendment': str(AMENDMENT),
                      'amendment_sha256': sha(AMENDMENT)}))


def validate_plan():
    plan = read(OUTPUT / 'plan.json')
    assert sha(OUTPUT / 'plan.json') == ORIGINAL_PLAN_SHA
    assert ORIGINAL_PLAN_SHA == read(OUTPUT / 'plan-receipt.json')['plan_sha256']
    assert plan['owner'] == ORIGINAL_OWNER and Path(plan['project']).resolve() == PROJECT.resolve()
    amendment = read(AMENDMENT)
    assert sha(PRIOR_AMENDMENT) == PRIOR_AMENDMENT_SHA
    assert amendment['prior_amendment']['sha256'] == PRIOR_AMENDMENT_SHA
    assert amendment['host_environment'] == {'OPENBLAS_NUM_THREADS': '1'}
    assert os.environ['OPENBLAS_NUM_THREADS'] == '1'
    assert amendment['original_owner'] == ORIGINAL_OWNER and amendment['operational_owner'] == OWNER
    assert amendment['original_files_sha256']['plan.json'] == ORIGINAL_PLAN_SHA
    assert amendment['superseded_host_sha256'] == ORIGINAL_HOST_SHA
    for name, expected in amendment['original_files_sha256'].items():
        assert sha(OUTPUT / name) == expected, 'Original prepared data changed: ' + name
    for name, expected in amendment['operational_files_sha256'].items():
        assert sha(ROOT / name) == expected, 'Operational host changed: ' + name
    assert external_dependencies() == amendment['external_dependencies_sha256']
    for path, expected in ((OBSERVER, OBSERVER_SHA), (WATCHER, WATCHER_SHA),
                           (MCDK, MCDK_SHA), (GUARD, GUARD_SHA)):
        assert path.is_file() and sha(path) == expected, 'Missing or changed operational dependency: ' + str(path)
    assert sha(OUTPUT / 'launch-inputs.json') == plan['launch_inputs_sha256']
    assert sha(PROJECT / '.mcdev.json') == plan['launch_config_sha256']
    for name, expected in plan['host_files_sha256'].items():
        if name == Path(__file__).relative_to(ROOT).as_posix():
            assert expected == ORIGINAL_HOST_SHA
            continue
        assert sha(ROOT / name) == expected, 'Prepared host changed: ' + name
    probe = probe_for(PROJECT)
    assert probe.snapshot_sources(PROJECT) == read(OUTPUT / 'launch-inputs.json')['source_sha256']
    assert sha(PROJECT / SOURCE) == CANDIDATE_SHA
    return plan, probe


def watcher_coverage():
    status = read(WATCHER_STATUS)
    now = datetime.now(timezone.utc)
    age = (now - datetime.fromisoformat(status['checked_at'])).total_seconds()
    covered = any(OWNER == item or item.endswith('*') and len(item) > 1 and
                  OWNER.startswith(item[:-1]) for item in status['owners'])
    passed = (covered and status['host_sha256'] == WATCHER_SHA and 0 <= age <= 60 and
              now < datetime.fromisoformat(status['until']))
    return {'passed': passed, 'status': str(WATCHER_STATUS), 'checked_at': status['checked_at'],
            'until': status['until'], 'age_seconds': age, 'owner_covered': covered,
            'owners': status['owners'], 'host_sha256': status['host_sha256']}


def effective_games(raw, identity_reader):
    effective, exited_shells = [], []
    for row in raw:
        game = dict(row, identity=identity_reader(row['ProcessId']))
        if game['identity'] is None and game.get('HandleCount') == 0 and game.get('ThreadCount') == 0:
            game['classification'] = 'exited_shell_no_live_identity'
            exited_shells.append(game)
        else:
            game['classification'] = 'live_identity' if game['identity'] else 'unresolved_counted_conservatively'
            effective.append(game)
    return effective, exited_shells


def capacity(probe, session=None):
    sys.path.append(str(ROOT / 'tools'))
    from census_intrinsic_glint_ui_r21 import commit_at_boundary
    from _session import process_identity, registry_dir
    commit = commit_at_boundary()
    games = []
    for path in registry_dir().glob('*/session.json'):
        record = read(path)
        if (record.get('game_pid') and record.get('game_identity') and
                process_identity(record['game_pid']) == record['game_identity']):
            games.append({key: record.get(key) for key in ('id', 'owner', 'project', 'game_pid', 'game_identity')})
    census = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
        "@(Get-CimInstance Win32_Process -Filter \"Name='Minecraft.Windows.exe'\" | "
        "Select-Object ProcessId,HandleCount,ThreadCount)|ConvertTo-Json -Compress"],
        capture_output=True, text=True, encoding='utf-8-sig', timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW, check=True)
    raw_games = json.loads(census.stdout or '[]')
    raw_games = raw_games if isinstance(raw_games, list) else [raw_games]
    all_games, exited_shells = effective_games(raw_games, process_identity)
    # The canonical session metrics call also verifies the owned game identity.
    metrics = probe.workspace.transport.metrics(session['session_file'], OWNER) if session else None
    minimum_gib = 6 if session else 9
    own = [game for game in games if game.get('project') and Path(game['project']).resolve() == PROJECT.resolve()]
    if session:
        identity_ok = len(own) == 1 and own[0]['id'] == session['id'] and len(all_games) <= 2
    else:
        identity_ok = not own and len(all_games) < 2
    return {'passed': identity_ok and commit['commit_available_bytes'] >= minimum_gib * 1024 ** 3
                     and (metrics is None or metrics['handles'] < 210000),
            'commit': commit, 'minimum_commit_gib': minimum_gib, 'metrics': metrics,
            'live_managed_games': games, 'all_games': all_games,
            'raw_game_processes': raw_games, 'excluded_exited_shells': exited_shells,
            'effective_live_count': len(all_games),
            'runtime_action': session is not None, 'started': False}


def preflight():
    plan, probe = validate_plan()
    resource = capacity(probe)
    coverage = watcher_coverage()
    return {'prepared_only': True, 'runtime_action': False, 'started': False,
            'operational_owner': OWNER, 'original_owner': ORIGINAL_OWNER,
            'source_contract_sha256': plan['source_contract_sha256'],
            'amendment_sha256': sha(AMENDMENT), 'launch_preflight': resource,
            'watcher_coverage': coverage, 'observer_exists_and_hash_bound': True,
            'host_environment': {'OPENBLAS_NUM_THREADS': os.environ['OPENBLAS_NUM_THREADS']},
            'passed': resource['passed'] and coverage['passed']}


def retained_observer(session):
    receipt = read(OUTPUT / 'exit-watcher.json')
    assert receipt['script_sha256'] == OBSERVER_SHA
    assert receipt['session_file'] == session['session_file'] and receipt['owner'] == OWNER
    from _session import process_identity
    assert receipt['identity'] and process_identity(receipt['pid']) == receipt['identity'], 'Exact exit observer is no longer live'
    retained = read(OUTPUT / 'process-exits.json')
    assert retained['session'] == session['id'] and retained['owner'] == OWNER
    assert retained['process_or_window_mutation'] is False
    assert set(retained['processes']) == {'game', 'mcdk'}
    for kind in ('game', 'mcdk'):
        row = retained['processes'][kind]
        assert row['pid'] == session[kind + '_pid'] and row['identity'] == session[kind + '_identity']
        expected = session['game_executable'] if kind == 'game' else session['noactivation']['mcdk']['path']
        assert Path(row['executable']).resolve() == Path(expected).resolve()
        assert row['state'] == 'live'
    return retained


def launch(args):
    assert args.scheduled_by_root, 'Explicit root runtime scheduling is required'
    assert not args.session, 'Launch creates a fresh session; do not pass an existing one'
    assert not (OUTPUT / 'launch-attempt.json').exists(), 'One-use launch already attempted; inspect before retrying'
    assert not (OUTPUT / 'process-exits.json').exists(), 'Exit observation output must be fresh'
    assert not (OUTPUT / 'ab-report.json').exists(), 'Existing A/B evidence must not be replayed'
    before = preflight()
    assert before['passed'], 'Launch resource capacity or main watcher coverage failed'
    config = read(PROJECT / '.mcdev.json')
    command = [sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / 'instances.py'), 'start',
               '--project', str(PROJECT), '--owner', OWNER, '--name', OWNER,
               '--game-exe', config['game_executable_path'], '--preset', 'ui', '--wait', '180',
               '--mcdk', str(MCDK), '--noactivate-mcdk-sha256', MCDK_SHA,
               '--noactivate-dll', str(GUARD), '--noactivate-sha256', GUARD_SHA]
    with (OUTPUT / 'launch-attempt.json').open('x', encoding='ascii') as handle:
        handle.write(json.dumps({'command': command, 'preflight': before,
                                 'amendment_sha256': sha(AMENDMENT)}, indent=2) + '\n')
    with (OUTPUT / 'start.stdout.json').open('x', encoding='utf8') as stdout, \
            (OUTPUT / 'start.stderr.txt').open('x', encoding='utf8') as stderr:
        result = subprocess.run(command, cwd=ROOT,
                                env=dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND='1', OPENBLAS_NUM_THREADS='1'),
                                stdout=stdout, stderr=stderr, timeout=300,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    save('launch-result.json', {'returncode': result.returncode, 'automatic_retry': False})
    assert result.returncode == 0, 'Inspect startup evidence and owned processes before any next action'
    from _session import load_session, process_identity
    startup = read(OUTPUT / 'start.stdout.json')
    session = load_session(startup['session_file'], OWNER, live=True)
    assert Path(session['project']).resolve() == PROJECT.resolve()
    assert session['ready'] and session['noactivation']['window_noactivate']
    for name in ('mcdk', 'dll'):
        assert session['noactivation'][name]['sha256'] == (MCDK_SHA if name == 'mcdk' else GUARD_SHA)
    exit_record = OUTPUT / 'process-exits.json'
    with (OUTPUT / 'process-exits.stdout.txt').open('x', encoding='utf8') as stdout, \
            (OUTPUT / 'process-exits.stderr.txt').open('x', encoding='utf8') as stderr:
        watcher = subprocess.Popen([sys.executable, '-B', '-X', 'utf8', str(OBSERVER),
            '--session', session['session_file'], '--owner', OWNER, '--output', str(exit_record)],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
            env=dict(os.environ, OPENBLAS_NUM_THREADS='1'),
            creationflags=subprocess.CREATE_NO_WINDOW)
    save('exit-watcher.json', {'pid': watcher.pid, 'identity': process_identity(watcher.pid),
        'session_file': session['session_file'], 'owner': OWNER, 'output': str(exit_record),
        'script': str(OBSERVER), 'script_sha256': OBSERVER_SHA})
    deadline = time.monotonic() + 15.
    retained = None
    while watcher.poll() is None and time.monotonic() < deadline:
        if exit_record.exists():
            try:
                retained = retained_observer(session)
                break
            except (OSError, json.JSONDecodeError):
                pass
        time.sleep(.1)
    assert retained is not None, 'Exact owned exit handles were not retained; leave the owner for root inspection'
    plan, probe = validate_plan()
    after = capacity(probe, session)
    coverage = watcher_coverage()
    save('launch-postflight.json', {'capacity': after, 'watcher_coverage': coverage,
        'exact_process_handles_retained': retained['processes'], 'amendment_sha256': sha(AMENDMENT),
        'source_contract_sha256': plan['source_contract_sha256'], 'wgc_requested': False})
    assert after['passed'], 'Post-launch identity or 6 GiB execution gate failed; retain observer and report to root'
    assert coverage['passed'], 'Main DisabledSkin watcher coverage changed during launch'
    summary = {key: session[key] for key in ('id', 'owner', 'session_file', 'state',
                 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')}
    summary['exact_process_handles_retained'] = True
    save('launch-ready.json', summary)
    print(json.dumps(summary))
    return 0


def install_code():
    baseline = (OUTPUT / 'baseline_viewport.py').read_bytes().decode('ascii')
    embedded = (HERE / 'embedded_ab.py').read_text(encoding='ascii')
    return '''import hashlib
from modern_projection.projection import liquid_viewport,liquid_render,liquid_transport
assert not hasattr(sys,'_water_depth_ab')
baseline_source=%r
assert hashlib.sha256(baseline_source.encode('ascii')).hexdigest()==%r
namespace={'__name__':'modern_projection.projection._water_depth_baseline_r21',
 '__package__':'modern_projection.projection'}
eval(compile(baseline_source,'water-depth-baseline','exec'),namespace)
instrumentation={}
eval(compile(%r,'water-depth-instrumentation','exec'),instrumentation)
engine=instrumentation['WaterDepthAB'](s,liquid_viewport,liquid_render,liquid_transport,
 namespace['LiquidControls'].update)
sys._water_depth_ab=engine
engine.install()
_result={'installed':True,'registry_entries':len(s.liquid_controls.registry)}
''' % (baseline, BASELINE_SHA, embedded)


def count(phase, field, warmup=False):
    return sum(row[field] for row in phase['warmup_rows' if warmup else 'rows'])


def run(args):
    assert args.scheduled_by_root and args.session, 'Explicit root scheduling and session are required'
    plan, probe = validate_plan()
    target = OUTPUT / 'ab-report.json'
    assert not target.exists(), 'One-use report already exists; do not replay a timed-out run'
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve()), MCDEV_OWNER=OWNER,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    from _session import load_session
    session = load_session(args.session, OWNER, live=True)
    assert Path(session['project']).resolve() == PROJECT.resolve()
    assert session['ready'] and session['noactivation']['window_noactivate']
    ready = read(OUTPUT / 'launch-ready.json')
    for key in ('id', 'owner', 'session_file', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity'):
        assert ready[key] == session[key], 'Unified launch session binding changed: ' + key
    exit_observation = retained_observer(session)
    assert watcher_coverage()['passed'], 'Main DisabledSkin watcher coverage is unavailable'
    before = probe.snapshot_sources(PROJECT)
    report = {'schema': 1, 'completed': False, 'restored': False, 'cleanup_errors': [],
              'diagnostic_only': True, 'production_qualified': False,
              'original_elapsed_failures_resolved': False, 'phases': {}, 'capacity': [],
              'session_binding': {key: session[key] for key in ('id', 'owner', 'game_pid', 'game_identity')},
              'source_contract_sha256': plan['source_contract_sha256'],
              'host_sha256': sha(__file__), 'operational_amendment_sha256': sha(AMENDMENT),
              'exact_process_handles_retained': exit_observation['processes'],
              'window_actions': [], 'screenshots': []}

    def checkpoint(label):
        state = capacity(probe, session)
        report['capacity'].append({'phase': label, 'state': state})
        save(target.name, report)
        assert state['passed'], 'Owned identity or canonical resource capacity failed'

    with probe.base.Client(timeout=45) as client:
        check = probe.blueprints.BlueprintCheck(client, target, 45.)
        installed = False
        try:
            checkpoint('before_workspace')
            assert not check.navigation()['open'], 'Use the fresh scheduled owner with its workspace closed'
            installed = True
            check.run(probe.blueprints.INSTALL_PROBE)
            report['profile'] = check.run(probe.PROFILE % (True, True))
            check.run('owner.open_workspace()\n_result=True')
            check.wait('open workspace', lambda state: state['open'] and not state['transition'], check.navigation)
            report['load'] = check.run(probe.LOAD % (('flow_east', 'wet', POSE),))
            report['ready'] = check.wait('single flow east fixture',
                probe.stable_scene_predicate(POSE, (0., 0.), probe.workspace.scene_ready),
                lambda: check.run(probe.SCENE_STATE))
            report['install'] = check.run(install_code())
            assert report['install']['registry_entries'] > 0

            def phase(name, mode='candidate', ticks=60, warmup=5, before_code=''):
                checkpoint(name)
                check.run(before_code + "\n_result=sys._water_depth_ab.begin(%r,%r,%d,%d)" %
                          (name, mode, ticks, warmup))
                state = check.wait(name + ' natural owner frames', lambda state: state['done'],
                                   lambda: check.run('_result=json.dumps(sys._water_depth_ab.state())'))
                report['phases'][name] = state
                save(target.name, report)
                return state

            baseline = phase('baseline', 'baseline')
            candidate = phase('candidate')
            assert count(baseline, 'source_validations') > 0
            assert count(candidate, 'source_validations') == 0
            assert baseline['after'] == candidate['after']
            for value in (baseline, candidate):
                assert all(row['returned'] and not row['pending'] and row['error'] is None for row in value['rows'])
                assert all(not row[field] for row in value['rows'] for field in
                           ('native_submissions', 'native_uniform_writes', 'native_visibility'))
            for field in ('view_callbacks', 'pose_callbacks', 'renderer_validations', 'publication_restores'):
                assert [row[field] for row in baseline['rows']] == [row[field] for row in candidate['rows']]
                assert count(candidate, field) > 0

            original_depth = check.run('_result=s.camera_depth')
            depth = phase('depth', before_code='s.move_depth(1)')
            assert count(depth, 'source_validations') + count(depth, 'source_validations', True) > 0
            report['depth_ready'] = check.wait('depth target',
                lambda state: abs(state['actual'] - state['target']) < .0001 and not state['pending'],
                lambda: check.run("_result={'actual':s.camera_depth_pose,'target':s.camera_depth,'pending':s.liquid_controls.pending}"))
            report['depth_snapshot'] = check.run('_result=json.dumps(sys._water_depth_ab.snapshot())')
            assert report['depth_snapshot']['entries'] != candidate['after']['entries']
            check.run("s.camera_depth=%r\ns.emit('camera_depth')\n_result=True" % original_depth)
            check.wait('restored depth target',
                lambda state: abs(state['actual'] - original_depth) < .0001 and not state['pending'],
                lambda: check.run("_result={'actual':s.camera_depth_pose,'pending':s.liquid_controls.pending}"))

            clipped = phase('clip', 'clip', 1, 0)
            assert clipped['rows'][0]['cached_entries'] == 0
            assert all(not any(entry['visible']) for entry in clipped['after']['entries'])
            unclip = phase('unclip')
            assert not unclip['after']['pending'] and unclip['after']['error'] is None
            assert count(unclip, 'source_validations', True) > 0
            invalid = phase('invalid', 'invalid', 1, 0)
            assert invalid['rows'][0]['cached_entries'] == 0 and invalid['after']['pending']
            assert 'signed16 depth range' in invalid['after']['error']
            assert invalid['before']['entries'] == invalid['after']['entries']
            retry = phase('retry', before_code='s.liquid_controls.retry()')
            assert count(retry, 'source_validations', True) > 0
            assert not retry['after']['pending'] and retry['after']['error'] is None
            assert [entry['ready_request'] for entry in retry['after']['entries']] == [
                entry['ready_request'] for entry in unclip['after']['entries']]
            checkpoint('after_lifecycle')
            report['completed'] = True
        except Exception:
            report['error'] = traceback.format_exc()
        finally:
            try:
                restored = check.run("""if hasattr(sys,'_water_depth_ab'):
 _result=sys._water_depth_ab.uninstall()
 assert _result['restored']
 del sys._water_depth_ab
else:_result={'restored':True,'not_installed':True}
""")
                report['wrappers_restore'] = restored
            except Exception:
                report['cleanup_errors'].append({'phase': 'wrappers', 'error': traceback.format_exc()})
            if installed:
                for label, code in (('close', 'if navigator.top is not None:navigator.pop()\n_result=True'),
                                    ('workspace', probe.RESTORE_PROFILE)):
                    try:
                        report[label + '_restore'] = check.run(code)
                    except Exception:
                        report['cleanup_errors'].append({'phase': label, 'error': traceback.format_exc()})
            report['source_unchanged'] = before == probe.snapshot_sources(PROJECT)
            report['restored'] = not report['cleanup_errors'] and report['source_unchanged']
            save(target.name, report)
    print(json.dumps({key: report.get(key) for key in
                      ('completed', 'restored', 'source_unchanged', 'cleanup_errors', 'error')}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'amend', 'preflight', 'launch', 'run'))
    parser.add_argument('--session')
    parser.add_argument('--scheduled-by-root', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'amend':
        amend()
    elif args.action == 'preflight':
        print(json.dumps(preflight()))
    elif args.action == 'launch':
        raise SystemExit(launch(args))
    else:
        raise SystemExit(run(args))
