"""One finite native write comparison, dispatched without idle gaps."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
BASE = PROJECT / '.runtime/liquid-native-write-r13-v4b'
INSTANCES = PROJECT / '.agents/skills/pyreact-debugging/scripts/instances.py'
sys.path.insert(0, str(INSTANCES.parent))
from _session import process_identity
from liquid_passive_guard_r12_v8 import safe_binding, find_owned
from liquid_priority_guard_r12_v9 import run as guarded_run, cleanup
from read_native_capacity_snapshot_r12 import snapshot_processes


def ready_budgets(game_created, actual_ready):
    outer = min(actual_ready + 300., game_created + 480.)
    if actual_ready > game_created + 180. or outer - actual_ready < 300. - .001:
        raise TimeoutError('Actual world readiness left less than the complete three hundred second work/cleanup reserve')
    return actual_ready + 240., actual_ready + 270., outer


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='ascii')


def frozen(plan):
    for scope in ('runtime_pack_files', 'host_helper_files'):
        for relative, row in plan[scope].items():
            if sha(PROJECT / relative) != row['live']['sha256'] or sha(row['archive']['path']) != row['archive']['sha256']:
                raise ValueError('Frozen source changed: ' + relative)
    for row in plan['binaries'].values():
        if sha(row['path']) != row['sha256']:
            raise ValueError('Frozen binary changed: ' + row['path'])
    if sha(plan['configuration']['path']) != plan['configuration']['sha256']:
        raise ValueError('Frozen configuration changed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=('check', 'run'))
    args = parser.parse_args()
    plan = json.loads((BASE / 'plan.json').read_bytes())
    frozen(plan)
    if args.step == 'check':
        print(json.dumps({'passed': True, 'plan_sha256': sha(BASE / 'plan.json')}))
        return 0
    raw = json.loads(Path(plan['capacity_baseline']['path']).read_bytes())
    if sha(plan['capacity_baseline']['path']) != plan['capacity_baseline']['sha256']:
        raise ValueError('Reviewed raw capacity baseline changed')
    previous = {row['pid']: row for row in raw['samples'][-1]['minecraft_or_target_rows']}
    capacity = snapshot_processes()
    residual, active = [], []
    for row in capacity['rows']:
        baseline = previous.get(row['pid'])
        if (baseline == row and row['threads'] == row['handles'] == row['virtual_size_bytes'] == 0
                and all(row[key] == '0' for key in ('cycle_time', 'user_time_100ns', 'kernel_time_100ns'))
                and row['working_set_size_raw'] <= 65536 and row['private_page_count_raw'] <= 98304):
            residual.append(row)
        else:
            active.append(row)
    release = {'read_only': True, 'observed_at': capacity['captured_at_unix'], 'snapshot': capacity,
               'residual_non_schedulable': residual, 'active_or_uncertain': active,
               'active_count': len(active), 'residual_count': len(residual),
               'process_exit_or_destruction_proven': False,
               'root_capacity_interpretation': 'Exact unchanged20 zero-thread/handle/virtual/CPU rows are residual capacity only; all others count active.'}
    write(BASE / 'capacity-before-launch.json', release)
    if len(active) >= 5 or time.time() - capacity['captured_at_unix'] > 60:
        raise ValueError('Five active-or-uncertain games or stale snapshot; no launch attempted')
    config = PROJECT / '.mcdev.json'
    attempted = BASE / 'launch-attempt.json'
    if config.exists() or attempted.exists():
        raise ValueError('Original configuration absence and one cold launch required')
    owner = plan['owner']
    report = {'schema': 1, 'completed': False, 'passed': False, 'phase_receipts': {}, 'owner': owner,
              'scope': plan['scope'], 'plan_sha256': sha(BASE / 'plan.json'),
              'capacity_receipt_sha256': sha(BASE / 'capacity-before-launch.json'),
              'real_input_sent': False, 'activation': False, 'resize': False,
              'production_qualified': False, 'side_uv_qualified': False, 'animation_qualified': False,
              'transparency_qualified': False}
    report['persistence_errors'] = []
    def save():
        try:
            write(BASE / 'run.json', report)
        except OSError as error:
            report['persistence_errors'].append(str(error))
    session = None
    config_installed = False
    started_at = time.time()
    try:
        shutil.copyfile(plan['configuration']['path'], config)
        config_installed = True
        write(attempted, {'owner': owner, 'plan_sha256': report['plan_sha256'], 'started_at': started_at})
        save()
        if report['persistence_errors']:
            raise OSError('Initial run receipt could not be persisted')
        binaries = plan['binaries']
        command = [sys.executable, '-X', 'utf8', str(INSTANCES), 'start', '--project', str(PROJECT),
            '--owner', owner, '--name', owner, '--preset', 'ui', '--mcdk', binaries['mcdk']['path'],
            '--noactivate-dll', binaries['guard']['path'], '--noactivate-sha256', binaries['guard']['sha256'],
            '--noactivate-mcdk-sha256', binaries['mcdk']['sha256'], '--game-exe', plan['game_executable'], '--wait', '180']
        result, monitor = guarded_run(command, os.environ.copy(), 180., owner,
            BASE / 'launch-passive-health.json', startup=True, growth_enabled=False)
        for stream in ('stdout', 'stderr'):
            (BASE / ('launch-' + stream + '.txt')).write_bytes(getattr(result, stream))
        if monitor.get('observed_session'):
            session = json.loads(Path(monitor['observed_session']['session_file']).read_bytes())
            write(BASE / 'session-receipt.json', safe_binding(session))
            if session.get('game_identity'):
                game_created = int(session['game_identity']) / 10000000. - 11644473600.
                report.update(game_created_at_unix=game_created, startup_deadline_unix=game_created + 180.,
                              outer_deadline_unix=game_created + 480.)
        if result.returncode or session is None or not session.get('ready') or session['state'] != 'ready':
            raise RuntimeError('Single cold launch failed; preserve failure and do not retry')
        transport_ready_at = time.time()
        report['transport_ready_observed_at'] = transport_ready_at
        save()
        env = os.environ.copy()
        env.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=owner, MCDEV_MCP_URL=session['mcp_url'],
            MCDEV_GAME_PID=str(session['game_pid']), MCDEV_NATIVE_CAPTURE_HELPER=str(PROJECT / 'tools/capture_native_window.py'),
            MCDEV_NATIVE_CAPTURE_EXE=binaries['wgc']['path'])
        physical = BASE / 'physical-readiness.json'
        actual_world = BASE / 'actual-world-readiness.json'
        calibration = BASE / 'camera-calibration.json'
        def phase(name, command, deadline, growth_enabled=True):
            timeout = deadline - time.time()
            if name == 'physical':
                timeout = min(timeout, 60., report['startup_deadline_unix'] - time.time())
            if timeout <= 0:
                raise TimeoutError('Fixed ready-phase budget elapsed before ' + name)
            result, monitor = guarded_run(command, env, timeout, owner,
                BASE / (name + '-passive-health.json'), session, report['outer_deadline_unix'],
                growth_enabled=growth_enabled)
            for stream in ('stdout', 'stderr'):
                (BASE / (name + '-' + stream + '.txt')).write_bytes(getattr(result, stream))
            report['phase_receipts'][name] = {'returncode': result.returncode, 'monitor': str(BASE / (name + '-passive-health.json'))}
            save()
            if result.returncode or not monitor['passed']:
                raise RuntimeError('Phase failed, no replay: ' + name)
        py = [sys.executable, '-X', 'utf8']
        phase('actual-world', py + [str(PROJECT / 'tools/check_liquid_physical_readiness.py'),
            str(actual_world), '--actual-world-ready', '--wait', '180'], report['startup_deadline_unix'], False)
        actual = json.loads(actual_world.read_bytes())
        if not actual.get('passed') or not actual.get('actual_world_ready'):
            raise ValueError('Real business UiInit and stable actual-world gate required')
        ready_at = actual['actual_world_ready_at_unix']
        normal_deadline, fixture_deadline, outer_deadline = ready_budgets(game_created, ready_at)
        report.update(ready_observed_at=ready_at, normal_deadline_unix=normal_deadline,
                      fixture_cleanup_deadline_unix=fixture_deadline, outer_deadline_unix=outer_deadline,
                      full_work_cleanup_reserve_verified=True, actual_world_receipt_sha256=sha(actual_world))
        save()
        phase('preflight', py + [str(PROJECT / 'tools/capture_native_window.py'), '--output', str(BASE / 'preflight.png')], normal_deadline)
        phase('physical', py + [str(PROJECT / 'tools/check_liquid_physical_readiness.py'), str(physical), '--single-snapshot'], normal_deadline)
        phase('health', py + [str(PROJECT / '.runtime/runtime-health-r12/check_runtime_health.py'), str(BASE / 'runtime-health.json')], normal_deadline)
        phase('calibrate', py + [str(PROJECT / 'tools/verify_camera_projection.py'), str(calibration),
            '--timeout', '3', '--native-resolution', '--skyward-tilted', '--fixture-lift-y', '30'], normal_deadline)
        health = json.loads((BASE / 'runtime-health.json').read_bytes())
        if (not all(health.get(key) for key in ('passed', 'completed', 'binding_verified', 'timer_cleanup_verified'))
                or any(health[key]['runtime'] != '1.21.120.0' for key in ('client_before', 'server_before', 'client_after'))):
            raise ValueError('Exact native runtime and two timer cleanup health required')
        phase('original-priority', py + [str(PROJECT / 'tools/probe_liquid_original_sides.py'),
            '--session', session['session_file'], '--owner', owner, '--output', str(BASE / 'original-priority.json'),
            '--capture-exe', binaries['wgc']['path'], '--physical', str(physical), '--calibration', str(calibration),
            '--viewport-receipt', str(BASE / 'preflight.capture.json'), '--native-write-compare', '--fixture-height-above-foot', '2',
            '--normal-deadline-unix', str(normal_deadline), '--cleanup-deadline-unix', str(fixture_deadline)], fixture_deadline)
        report['completed'] = True
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
    finally:
        save()
        cleanup_errors = []
        try:
            if session is None:
                session = find_owned(owner, started_at)
            if session is not None:
                identities = {key: process_identity(session.get(key + '_pid')) if session.get(key + '_pid') else None for key in ('game', 'mcdk')}
                if any(identities.values()):
                    if report.get('outer_deadline_unix'):
                        cleanup(session, report, save, report['outer_deadline_unix'])
                    else:
                        cleanup(session, report, save, started_at + 240.)
                report['identities_after'] = {key: process_identity(session.get(key + '_pid')) if session.get(key + '_pid') else None for key in ('game', 'mcdk')}
                current = json.loads(Path(session['session_file']).read_bytes())
                report['session_stopped'] = current['state'] == 'stopped' and not current['ready']
            else:
                report['identities_after'] = {'game': None, 'mcdk': None}
                report['session_stopped'] = True
        except Exception as error:
            cleanup_errors.append('owned stop: %s: %s' % (type(error).__name__, error))
        try:
            if config_installed and report.get('session_stopped') and not any(report.get('identities_after', {'unknown': True}).values()):
                # Configuration restoration is independent of later source verification.
                if sha(config) != plan['configuration']['sha256']:
                    raise ValueError('Unknown configuration; refusing removal')
                shutil.copyfile(config, BASE / 'temporary-configuration-removed.json')
                config.unlink()
                report['host_configuration_restored'] = True
            frozen(plan)
            report['frozen_pack_and_helpers_unchanged'] = True
        except Exception as error:
            cleanup_errors.append('configuration/source restore: %s: %s' % (type(error).__name__, error))
        report['cleanup_errors'] = cleanup_errors
        if 'outer_deadline_unix' in report:
            report['outer_deadline_met'] = time.time() <= report['outer_deadline_unix']
            report['game_creation_to_stopped_seconds'] = time.time() - report['game_created_at_unix']
        if 'ready_observed_at' in report:
            report['ready_to_stopped_seconds'] = time.time() - report['ready_observed_at']
        report['passed'] = bool(report['completed'] and not report.get('error') and not cleanup_errors
            and not report['persistence_errors'] and report.get('session_stopped')
            and not any(report.get('identities_after', {'unknown': True}).values())
            and report.get('host_configuration_restored') and report.get('frozen_pack_and_helpers_unchanged')
            and report.get('outer_deadline_met'))
        save()
        if report['persistence_errors']:
            report['passed'] = False
            save()
    print(json.dumps({key: report.get(key) for key in ('completed', 'passed', 'error', 'host_configuration_restored', 'identities_after', 'ready_to_stopped_seconds')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
