"""Collect reviewed semantic support segments in one existing fresh owner.

Preparation launches nothing and writes no capability evidence. Execution uses
the exact managed session from instances.py exec, leaves game retirement to its
owner, and stops on a failed segment while preserving its native observations.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import derive_scaffold_runtime_support as derive
import probe_scaffold_runtime_catalogue as probe
import run_scaffold_runtime_lifecycle as supervisor

ROOT = Path(__file__).resolve().parents[1]
METHOD = 'same exact fresh owner; sequential bounded semantic scaffold segments; v1'
CLEANUP_SECONDS = 30


def segment_ranges(start, count):
    size = len(probe.dump_states())
    if (type(start) is not int or type(count) is not int
            or not 0 <= start < size or not 0 < count <= size - start):
        raise ValueError('Requested collection must fit the current dump exactly')
    return [{'start_index': index, 'count': min(probe.MAX_COUNT, start + count - index)}
            for index in range(start, start + count, probe.MAX_COUNT)]


def validate_owned_segment(report, session, source):
    identity = report.get('identity', {})
    expected = {'session_id': session['id'], 'owner': session['owner'],
                'game_pid': session['game_pid'], 'game_identity': session['game_identity']}
    if any(identity.get(key) != value for key, value in expected.items()):
        raise ValueError('Segment was not measured by this exact managed game')
    return derive.validate_segment(report, source)


def verify_pins(output, source_pins, archive_pins):
    if any(not Path(path).is_file() or supervisor.digest(Path(path)) != expected
           for path, expected in source_pins.items()):
        raise ValueError('Frozen collection source changed')
    if any(not (output / path).is_file() or supervisor.digest(output / path) != expected
           for path, expected in archive_pins.items()):
        raise ValueError('Archived collection source changed')


def completed_reports(output, records):
    """Validate receipt bytes while holding only one raw segment in memory."""
    for record in records:
        raw = (output / record['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError('Completed native segment receipt changed')
        yield json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--air-observation', type=Path, required=True)
    parser.add_argument('--start-index', type=int, default=0)
    parser.add_argument('--count', type=int, default=probe.MAX_COUNT)
    parser.add_argument('--max-seconds', type=int, default=240)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--fresh-owned-flow-allowed', action='store_true')
    args = parser.parse_args()
    os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
    foreground_policy = supervisor.foreground_metadata()
    ranges = segment_ranges(args.start_index, args.count)
    if not 120 <= args.max_seconds <= 7200:
        parser.error('Use an absolute collection budget in 120..7200 seconds')
    if args.execute and not args.fresh_owned_flow_allowed:
        parser.error('Execution requires an explicitly fresh owned allowed-flow baseline')
    observation_raw = args.air_observation.read_bytes()
    encoding = supervisor.palette_readback.encoding_from_observation(json.loads(observation_raw))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'air-observation.json').write_bytes(observation_raw)
    sources = [Path(__file__), Path(probe.__file__), Path(probe.common.__file__),
               Path(derive.__file__), Path(supervisor.__file__), Path(supervisor.lifecycle.__file__),
               Path(supervisor.palette_readback.__file__), Path(supervisor.world.__file__),
               Path(supervisor.air_control.__file__), Path(supervisor.air_control.base.__file__),
               ROOT / 'tools/capture_native_window.py',
               ROOT / 'tools/context_test_environment.py', ROOT / 'tools/verify_debug_blueprints.py',
               ROOT / 'behavior_pack/modern_projection/projection/block_registry.py',
               ROOT / 'behavior_pack/modern_projection/projection/block_registry_data.py',
               ROOT / 'behavior_pack/modern_projection/projection/__init__.py',
               ROOT / '.agents/skills/pyreact-debugging/scripts/_session.py',
               ROOT / '.agents/skills/pyreact-debugging/scripts/_window.py',
               ROOT / '.agents/skills/pyreact-debugging/scripts/mcdk.py']
    source_pins, archive_pins = supervisor.archive_sources(ROOT, output, sources)
    source = source_pins[str(Path(probe.__file__).resolve())]
    def save(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    plan = {'schema': 1, 'method': METHOD, 'status': 'prepared_not_executed',
            'created_at': datetime.now(timezone.utc).isoformat(), 'launches_permitted': 0,
            'real_input': False, 'resize': False,
            'max_seconds': args.max_seconds, 'cleanup_seconds': CLEANUP_SECONDS, 'ranges': ranges,
            'game_version': probe.common.registry.SOURCE_VERSION,
            'palette_sha256': probe.common.registry.SOURCE_SHA256,
            'source_pins': source_pins, 'source_archive_pins': archive_pins,
            'air_observation_sha256': hashlib.sha256(observation_raw).hexdigest(), 'air_encoding': encoding,
            'acceptance': derive.ACCEPTANCE}
    plan.update(foreground_policy)
    save('plan.json', plan)
    if not args.execute:
        print(json.dumps({'prepared': True, 'ranges': len(ranges), 'planned_states': args.count,
                          'plan': str(output / 'plan.json')}))
        return 0
    session_file, owner, session = probe.common.owned_session()
    supervisor._session.load_session(session_file, owner, live=True)
    if not session.get('ready'):
        raise ValueError('The exact collection owner is not ready')
    report = {'schema': 1, 'method': METHOD, 'completed': False, 'launches': 0,
              'owner': owner, 'identity': {key: session[key] for key in ('id', 'game_pid', 'game_identity')},
              'segments': [], 'checks': [], 'cleanup_errors': [], 'world_qualified': False,
              'world_observations': [], 'acceptance': derive.ACCEPTANCE}
    report.update(foreground_policy)
    started = time.monotonic()
    deadline = started + args.max_seconds
    child, child_identity, current_path, current = None, None, None, None
    def checkpoint():
        save('report.json', report)
    def guard():
        if any(supervisor._session.process_identity(session[key + '_pid']) != session[key + '_identity']
               for key in ('game', 'mcdk')):
            raise RuntimeError('Exact managed game or MCDK creation identity changed')
        value = supervisor._window.background_guard_state(session['game_pid'], Path(session['game_executable']).name)
        report['checks'].append({'at_seconds': time.monotonic() - started, 'guard': value})
        if not supervisor.scaffold_guard_satisfied(value, session['game_pid'], require_window=True):
            raise RuntimeError('Existing owner is not a guarded background game')
        verify_pins(output, source_pins, archive_pins)
    try:
        guard()
        for path, expected in supervisor.PINS.items():
            if supervisor.digest(path) != expected:
                raise ValueError('Reviewed background binary pin differs: ' + str(path))
        near_server = supervisor.world.SERVER.replace('ground[1]+19', 'ground[1]+3')
        if near_server == supervisor.world.SERVER:
            raise ValueError('Near-read world admission template changed')
        with probe.common.Client(timeout=10) as client:
            world_deadline = min(started + 45, deadline - 130)
            stable, previous = 0, None
            while time.monotonic() < world_deadline:
                guard()
                cli = supervisor.return_value(client.call('execute_code', {'code': supervisor.world.CLIENT,
                    'is_client': True, 'direct_return': True}))
                srv = supervisor.return_value(client.call('execute_code', {'code': near_server,
                    'is_client': False, 'direct_return': True}))
                admitted = supervisor.physical_ready(cli, srv)
                foot = srv.get('foot') if isinstance(srv, dict) else None
                stable = stable + 1 if admitted and (previous is None or all(abs(a - b) <= .125
                    for a, b in zip(foot, previous))) else 0
                previous = foot if admitted else None
                report['world_observations'].append({'client': cli, 'server': srv,
                                                     'admitted': admitted, 'stable_samples': stable})
                checkpoint()
                if stable >= 3:
                    report['world_qualified'] = True
                    break
                time.sleep(.5)
        if not report['world_qualified']:
            raise RuntimeError('Actual UiInit, render ticks, loaded ground and stable feet did not qualify')
        guard()
        report['capture'] = supervisor.capture(session_file, owner, output / 'world.png', supervisor.WGC)
        env = os.environ.copy()
        env.update(MCDEV_SESSION_FILE=session_file, MCDEV_OWNER=owner, MCDEV_MCP_URL=session['mcp_url'])
        for selected in ranges:
            guard()
            if deadline - time.monotonic() < 100 + CLEANUP_SECONDS:
                raise TimeoutError('Collection budget preserves cleanup; next segment was not dispatched')
            current = None
            stem = 'segment-%05d' % selected['start_index']
            current_path = output / (stem + '.json')
            command = [sys.executable, '-X', 'utf8', str(ROOT / 'tools/probe_scaffold_runtime_catalogue.py'),
                       str(current_path), '--fresh-owned-flow-allowed', '--air-observation', str(output / 'air-observation.json'),
                       '--start-index', str(selected['start_index']), '--count', str(selected['count'])]
            with (output / (stem + '-stdout.txt')).open('wb') as stdout, (output / (stem + '-stderr.txt')).open('wb') as stderr:
                child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                child_identity = supervisor._session.process_identity(child.pid)
                child_started = time.monotonic()
                child_deadline = min(child_started + 110, deadline - CLEANUP_SECONDS)
                while child.poll() is None:
                    guard()
                    checkpoint()
                    if time.monotonic() >= child_deadline:
                        raise TimeoutError('Bounded native segment budget reached')
                    time.sleep(.5)
            current = json.loads(current_path.read_bytes())
            rows = validate_owned_segment(current, session, source)
            if child.returncode or current['range'] != [selected['start_index'], selected['start_index'] + selected['count']]:
                raise RuntimeError('Native segment failed or measured another range; original receipt retained')
            report['segments'].append({'path': current_path.name, 'sha256': supervisor.digest(current_path),
                                       'range': current['range'], 'observed_states': len(rows),
                                       'elapsed_seconds': time.monotonic() - child_started})
            checkpoint()
        full = args.start_index == 0 and args.count == len(probe.dump_states())
        report['capabilities'] = derive.capabilities(completed_reports(output, report['segments']), require_full=full)
        report['completed'] = True
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
    finally:
        try:
            if child and child.poll() is None:
                supervisor._session.terminate_owned(child.pid, child_identity)
                child.wait(timeout=5)
            if current_path and current_path.is_file():
                current = json.loads(current_path.read_bytes())
                report['last_segment'] = {'path': current_path.name, 'sha256': supervisor.digest(current_path)}
                identity = current.get('identity', {})
                expected = {'session_id': session['id'], 'owner': owner, 'game_pid': session['game_pid'],
                            'game_identity': session['game_identity']}
                if current.get('restored') is not True and all(identity.get(key) == value for key, value in expected.items()):
                    guard()
                    with probe.common.Client(timeout=10) as client:
                        restored = probe.common.run(client, probe.restore_payload(identity))
                    report['supervisor_restore'] = restored
                    if restored.get('restored') is not True:
                        report['cleanup_errors'].append('Native segment restoration was not verified')
                elif current.get('restored') is not True:
                    report['cleanup_errors'].append('Exact failed segment identity unavailable; owner must retire world')
        except Exception as error:
            report['cleanup_errors'].append('Final native segment cleanup: ' + repr(error))
        try:
            guard()
        except Exception as error:
            report['cleanup_errors'].append('Final owner or source check: ' + repr(error))
        report['elapsed_seconds'] = time.monotonic() - started
        report['game_retirement'] = 'left_to_exact_managed_owner'
        if report['cleanup_errors']:
            report['completed'] = False
        checkpoint()
    print(json.dumps({key: report.get(key) for key in ('completed', 'error', 'cleanup_errors', 'elapsed_seconds')}))
    return 0 if report['completed'] and not report['cleanup_errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
