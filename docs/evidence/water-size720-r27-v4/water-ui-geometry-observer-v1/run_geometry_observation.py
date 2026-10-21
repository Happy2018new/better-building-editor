"""Collect native hidden/visible geometry in one mount per GUI phase.

This host only observes the new diagnostic Panel wrapper. It does not award
the original production controls a geometry or water qualification.
"""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import desktop_lock, load_session, process_identity, _kernel, _identity
from _window import _list_windows
sys.path.insert(0, str(ROOT / '.runtime/round-20261022/water-size720-v3'))
from resize_adapter import resize_exact, user32
from run_size_group import available_commit
import observer_game as game
from geometry_observation import describe_snapshot


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def actor_readback(client, run):
    return run(client, '''system=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
s=system.session;b=system.bridge
_result=json.dumps({'busy':s.busy,'edit_job':s.edit_job is not None,'io_job':s.io_job is not None,
 'projection_active':s.projection_active,'world_actors':len(b.projection_entities)+int(bool(b.entity)),
 'preparing_entity':bool(b.preparing_entity)})
''')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--root-grant', required=True, type=Path)
    args = parser.parse_args()
    plan_path = WORK / 'plan-v1.json'
    plan = json.loads(plan_path.read_bytes())
    manifest_path = WORK / 'diagnostic-source-v1.json'
    manifest = json.loads(manifest_path.read_bytes())
    output = WORK / 'geometry-observation-v1.json'
    assert not output.exists(), 'Preserve every prior observation'
    assert sha(manifest_path) == plan['diagnostic_source_manifest_sha256']
    assert all(sha(WORK / name) == expected for name, expected in plan['host_code_sha256'].items())
    grant = json.loads(args.root_grant.read_bytes())
    assert grant['owner'] == plan['owner'] and grant['plan_sha256'] == sha(plan_path)
    assert grant['begin'] <= time.time() < grant['until'] - 120
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)),
                      MCDEV_OWNER=plan['owner'], MCDEV_ALLOW_USER_FOREGROUND='0')
    session = load_session(args.session, plan['owner'], live=True)
    project = Path(plan['project']).resolve(strict=True)
    assert Path(session['project']).resolve() == project
    sources = dict(manifest['source_sha256'], **manifest['auxiliary_sha256'])
    assert all(sha(project / name) == expected for name, expected in sources.items())
    sys.path.insert(0, str(project / 'tools'))
    import probe_liquid_pose_channel as base
    assert base.ROOT.resolve() == project
    assert user32.SetProcessDPIAware(), 'Resize process must become DPI aware'
    report = {'schema': 1, 'owner': plan['owner'], 'plan_sha256': sha(plan_path),
        'source_contract_sha256': manifest['source_contract_sha256'],
        'host_sha256': sha(Path(__file__)), 'started_at': time.time(),
        'completed': False, 'restored': False, 'restore_unknown': True,
        'source_unchanged': False, 'phases': [], 'resources': [], 'cleanup_errors': [],
        'scope': 'Native SDK geometry of a new diagnostic Panel wrapper only',
        'formal_A_accepted': False, 'production_admission_performed': False,
        'manual_closures_added': 0, 'screenshots_collected': 0}

    def save():
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')

    def resource(stage):
        assert time.time() < grant['until'] - 60, 'Leave time for explicit restoration'
        kernel = _kernel()
        kernel.GetProcessHandleCount.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        sample = {'stage': stage, 'at': time.time(), 'available_commit_bytes': available_commit(),
                  'processes': {}}
        for kind in ('game', 'mcdk'):
            pid, identity = session[kind + '_pid'], session[kind + '_identity']
            handle = kernel.OpenProcess(0x1000, False, pid)
            assert handle, 'Exact process cannot be opened: ' + kind
            try:
                assert _identity(kernel, handle) == identity, 'Creation identity changed: ' + kind
                count = wintypes.DWORD()
                assert kernel.GetProcessHandleCount(handle, ctypes.byref(count))
                assert _identity(kernel, handle) == identity, 'Process exited while sampling: ' + kind
                previous = next((item['processes'][kind]['handles'] for item in reversed(report['resources'])
                                 if kind in item['processes']), None)
                sample['processes'][kind] = {'pid': pid, 'identity': identity, 'handles': count.value,
                    'previous_handles': previous, 'growth': None if previous is None else count.value - previous}
            finally:
                kernel.CloseHandle(handle)
        report['resources'].append(sample)
        save()
        assert sample['available_commit_bytes'] >= plan['resource_gates']['min_available_commit_bytes'], sample
        for value in sample['processes'].values():
            assert value['handles'] < plan['resource_gates']['max_handles'], value
            assert value['growth'] is None or value['growth'] < plan['resource_gates']['max_adjacent_growth'], value

    def wait_restored(client):
        deadline = time.monotonic() + 15
        while True:
            state = base.run(client, game.CLEAN_READY)
            if state['restored']:
                return state
            if time.monotonic() >= deadline:
                raise RuntimeError('Explicit UI restoration deadline: ' + repr(state))
            time.sleep(.1)

    def clean_and_verify(client, phase):
        phase['clean_return'] = base.run(client, game.CLEAN)
        phase['clean_ready'] = wait_restored(client)
        # This second, independent readonly call is kept apart from CLEAN_READY.
        phase['independent_restore'] = base.run(client, '''from modern_projection.pyreact import navigator
_result=json.dumps({'diagnostic_marker':hasattr(sys,'_r27_water_anchor_ui'),
 'navigator_transitioning':navigator.is_transitioning,
 'navigator_top':None if navigator.top is None else navigator.top.key})
''')
        phase['actors_after'] = actor_readback(client, base.run)
        check = phase['independent_restore']
        assert phase['clean_return'] is True and phase['clean_ready']['restored']
        assert not check['diagnostic_marker'] and not check['navigator_transitioning']
        assert check['navigator_top'] in (None, 'modern_projection_workspace')
        assert not any(phase['actors_after'].values()), phase['actors_after']
        phase['restored'] = True
        save()

    def observe(client, phase, config, label):
        row = {'label': label, 'configuration': config, 'samples': [], 'completed': False}
        phase['states'].append(row)
        resource(phase['label'] + '_' + label + '_before_configure')
        row['configured'] = base.run(client, game.CONFIGURE % (config,))
        save()
        started = time.monotonic()
        deadline = started + plan['observation']['logical_ready_deadline_seconds']
        tail = None
        while True:
            snapshot = base.run(client, game.STATUS)
            sample = {'at': time.time(), 'elapsed_since_configure_seconds': time.monotonic() - started,
                      'native_snapshot': snapshot, 'description': describe_snapshot(snapshot)}
            row['samples'].append(sample)
            if snapshot.get('ready') and tail is None:
                row['first_logical_ready_sample'] = len(row['samples']) - 1
                tail = plan['observation']['samples_including_first_logical_ready']
            if tail is not None:
                tail -= 1
            save()
            if tail == 0:
                break
            if time.monotonic() >= deadline:
                row['logical_ready_deadline_reached'] = True
                break
            time.sleep(plan['observation']['sample_interval_seconds'])
        row['observed_logical_ready'] = tail is not None
        row['last_geometry_complete'] = row['samples'][-1]['description']['contract_observation_complete']
        row['completed'] = True  # Collection complete, no product pass implied.
        resource(phase['label'] + '_' + label + '_after_observation')
        save()

    opened = False
    save()
    with base.Client(timeout=30) as client:
        try:
            report['actors_before'] = actor_readback(client, base.run)
            assert not any(report['actors_before'].values()), report['actors_before']
            for stage in plan['phases']:
                phase = {'label': stage['label'], 'requested': stage, 'states': [], 'restored': False}
                report['phases'].append(phase)
                resource(stage['label'] + '_before_resize')
                phase['pre_mount_restored'] = wait_restored(client)
                with desktop_lock():
                    windows = [value for value in _list_windows() if value['pid'] == session['game_pid']]
                    assert len(windows) == 1, windows
                    resize_exact(windows[0]['hwnd'], session['game_pid'], session['game_identity'],
                                 *stage['physical_client'], phase)
                opened = True  # CLEAN is safe even if OPEN only partly completes.
                phase['opened'] = base.run(client, game.OPEN)
                assert phase['opened']['gui'] == stage['expected_integer_gui'], phase['opened']
                logical = phase['opened']['logical']
                fractions = stage['rectangle_fractions']
                rect = [fractions[index] * logical[index % 2] for index in range(4)]
                for state in plan['state_sequence']:
                    config = {'position': plan['position'], 'pose': plan['pose'], 'rect': rect,
                        'unit_fraction': plan['unit_fraction'], 'mode': state['mode'],
                        'model': 'modern_projection_r27_anchor_15', 'offset_factor': 0.}
                    observe(client, phase, config, state['label'])
                clean_and_verify(client, phase)
                opened = False
            report['completed'] = True
        except BaseException as error:
            report['error'] = {'type': type(error).__name__, 'message': str(error)}
            raise
        finally:
            if opened:
                try:
                    clean_and_verify(client, report['phases'][-1])
                except Exception as error:
                    report['cleanup_errors'].append({'step': 'explicit_UI_cleanup',
                        'type': type(error).__name__, 'message': str(error)})
            try:
                report['final_clean_ready'] = base.run(client, game.CLEAN_READY)
                report['actors_final'] = actor_readback(client, base.run)
                report['restored'] = report['final_clean_ready']['restored'] and not any(report['actors_final'].values())
                report['restore_unknown'] = False
            except Exception as error:
                report['cleanup_errors'].append({'step': 'final_readonly_restore',
                    'type': type(error).__name__, 'message': str(error)})
            try:
                report['source_unchanged'] = all(sha(project / name) == expected for name, expected in sources.items())
            except Exception as error:
                report['cleanup_errors'].append({'step': 'final_source_audit',
                    'type': type(error).__name__, 'message': str(error)})
            report['ended_at'] = time.time()
            save()
    assert report['completed'] and report['restored'] and report['source_unchanged']
    print(json.dumps({'collection_completed': True, 'phases': len(report['phases']),
        'states': sum(len(phase['states']) for phase in report['phases']),
        'restored': True, 'formal_A_accepted': False, 'production_admission_performed': False}))


if __name__ == '__main__':
    main()
