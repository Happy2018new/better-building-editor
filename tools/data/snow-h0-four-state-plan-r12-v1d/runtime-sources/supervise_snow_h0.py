"""One coordinated h0 cold control, bounded work through T190 and cleanup through T240."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import os
import sys
from types import ModuleType

import supervise_owned_startup as startup
from verify_snow_h0_phase import run_phase

ROOT = Path(__file__).resolve().parents[1]
TOTAL = 240
WORK = 190
RESERVATION = 83
APPLICATION_READINESS = {'maximum_wait_seconds': 20, 'query_timeout_seconds': 1,
                         'query_interval_seconds': 1, 'maximum_queries': 20,
                         'capture_wait_seconds': 5,
                         'required': ['owner', 'session', 'bridge', 'session.ready', 'bridge.session', 'hud'],
                         'existing_uiinit_only': True, 'manual_initialization': False,
                         'first_sdk_capture_retained': True, 'first_application_capture_replaced': False}
COPY_TARGETS = startup.COPY_TARGETS


def validate_plan(path, expected_sha):
    if startup.sha(path) != expected_sha:
        raise ValueError('Frozen h0 plan changed')
    plan = json.loads(Path(path).read_bytes())
    if (plan.get('schema') != 1 or plan.get('status') != 'reviewed_finite_h0_control'
            or Path(plan.get('project', '')).resolve() != ROOT
            or plan.get('owner') not in ('snow-r12-h0-native', 'snow-r12-h0-alpha')
            or plan.get('texture_condition') not in ('native_original', 'native_alpha_preserved')
            or plan.get('budgets') != {'total': TOTAL, 'work': WORK, 'cleanup_reserved': 50, 'launcher_wait': 90}
            or plan.get('post_ready_reservation_seconds') != RESERVATION
            or plan.get('application_readiness') != APPLICATION_READINESS
            or plan.get('target') != [6, -48, 6] or plan.get('support') != [6, -49, 6]
            or plan.get('projection_origin') != [5, -49, 5]
            or plan.get('public_camera_offset') != [-2., .15, -2.5]
            or plan.get('max_launches') != 1 or plan.get('max_active_games') != 5
            or plan.get('movement_normalization') is not False or plan.get('retry_or_relaunch') is not False):
        raise ValueError('H0 scope or finite bounds changed')
    if plan.get('actual_camera_contract') != {'GetForward_required': True, 'minimum_forward_cosine_exclusive': 0,
            'render_event_source': 'GameRenderTickEvent', 'minimum_render_events_before_capture': 2,
            'minimum_render_events_after_restore': 2, 'camera_restore_wait_seconds': 5,
            'camera_saved_journal_cleared_only_after_verified_readback': True, 'yaw_search_allowed': False}:
        raise ValueError('H0 actual camera and render-event restoration contract changed')
    if plan.get('protected_session') != startup.PROTECTED_SESSION:
        raise ValueError('Protected session changed')
    for row in plan['files'].values():
        if startup.sha(row['path']) != row['sha256']:
            raise ValueError('Frozen h0 input changed: ' + row['path'])
    expected = json.loads(Path(plan['files']['project_source']['path']).read_bytes())['files']
    actual = {path.relative_to(ROOT).as_posix(): startup.sha(path)
              for name in ('behavior_pack', 'resource_pack') for path in (ROOT / name).rglob('*') if path.is_file()}
    if actual != expected:
        raise ValueError('H0 behavior/resource inventory changed')
    if (plan['files']['adapter']['path'] != str(Path(__file__).resolve()) or
            Path(plan['files']['phase']['path']).resolve() != ROOT / 'tools/verify_snow_h0_phase.py'):
        raise ValueError('H0 plan belongs to another adapter')
    config = json.loads(Path(plan['files']['config']['path']).read_bytes())
    for key, value in (('world_type', 2), ('world_seed', 0), ('game_mode', 1),
                       ('do_daylight_cycle', False), ('do_weather_cycle', False)):
        if config.get(key) != value:
            raise ValueError('H0 fixed private world config changed')
    if any(config.get(key) is not False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                'auto_hot_reload_shaders', 'auto_hot_reload_materials', 'auto_hot_reload_particles')):
        raise ValueError('H0 hot reload must remain disabled')
    if plan['handle_health'] != {'sample_interval_seconds': 15, 'max_samples': 18,
             'absolute_game_handle_limit': 100000, 'pre_ready_growth_observation_only': True,
             'post_ready_growth_baseline_required': True, 'consecutive_intervals': 2,
             'minimum_delta_each': 5000, 'minimum_handles_per_second_each': 200}:
        raise ValueError('H0 prospective handle stop rule changed')
    return plan


def healthy_frame(row):
    if row.get('returncode') != 0 or not row.get('stdout'):
        return False
    value = json.loads(row['stdout'])
    return (value.get('ok') is True and value.get('reliable') is True
            and value.get('state_before') == value.get('state_after') == 'ready'
            and value.get('tcp', {}).get('owned_established_pair_observed') is True
            and (value.get('pixels', {}).get('width'), value.get('pixels', {}).get('height')) == (1994, 1105))


def rapid_growth(previous, current, elapsed):
    if elapsed <= 0:
        raise ValueError('Passive handle interval must increase')
    return current - previous >= 5000 and (current - previous) / elapsed >= 200


class WindowsHost(startup.WindowsHost):
    def application_ready(self, session, plan, deadline):
        module = ModuleType('frozen_h0_readiness_client')
        module.__file__ = plan['files']['mcdk_client']['path']
        exec(compile(Path(module.__file__).read_bytes(), module.__file__, 'exec'), module.__dict__)
        previous = {key: os.environ.get(key) for key in ('MCDEV_SESSION_FILE', 'MCDEV_OWNER', 'MCDEV_MCP_URL')}
        os.environ.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=session['owner'], MCDEV_MCP_URL=session['mcp_url'])
        host = self

        class ReadinessClient(module.Client):
            def _post(self, *args, **kwargs):
                self.timeout = min(1., deadline - host.now())
                if self.timeout <= 0:
                    raise TimeoutError('Application readiness query deadline exhausted')
                return super()._post(*args, **kwargs)

            def close(self):
                self.timeout = max(.001, min(.2, deadline - host.now()))
                super().close()

        try:
            with ReadinessClient(timeout=1) as client:
                value = module.return_value(client.call('execute_code', {'code': '''import json
import mod.client.extraClientApi as api
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
session=getattr(owner,'session',None) if owner is not None else None
bridge=getattr(owner,'bridge',None) if owner is not None else None
session_ready=getattr(session,'ready',False) is True
bridge_session_matches=bridge is not None and getattr(bridge,'session',None) is session
hud_present=owner is not None and getattr(owner,'hud',None) is not None
_result=json.dumps({'owner_present':owner is not None,'session_present':session is not None,
 'bridge_present':bridge is not None,'session_ready':session_ready,
 'bridge_session_matches':bridge_session_matches,'hud_present':hud_present,
 'initialized':owner is not None and session is not None and bridge is not None and session_ready and bridge_session_matches and hud_present,
 'runtime_version':api.GetMinecraftVersion()})
''', 'is_client': True, 'direct_return': True}))
                return json.loads(value) if isinstance(value, str) else value
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def normal_stop(self, session, timeout):
        command = [sys.executable, '-X', 'utf8', str(ROOT / COPY_TARGETS[0]), 'stop',
                   '--session', session['session_file'], '--owner', session['owner']]
        try:
            value = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                   encoding='utf8', timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
            return {'returncode': value.returncode, 'stdout': value.stdout, 'stderr': value.stderr, 'timeout': False}
        except subprocess.TimeoutExpired as error:
            return {'timeout': True, 'error': str(error)}

    def prepare(self, plan, output, report):
        if plan['texture_condition'] == 'native_alpha_preserved':
            return super().prepare(plan, output, report)
        marker = ROOT / 'resource_pack/textures/blocks/flower_rose.png'
        if marker.exists():
            raise ValueError('Original cold condition requires own flower override absence')
        for target, key in zip(COPY_TARGETS, ('instances', 'mcdk_client', 'config')):
            target = ROOT / target
            backup = output / ('original-' + target.name)
            shutil.copyfile(target, backup)
            report['backup'].append({'target': str(target), 'backup': str(backup), 'sha256': startup.sha(backup)})
            shutil.copyfile(plan['files'][key]['path'], target)
            report['backup'][-1]['installed_sha256'] = startup.sha(target)
        report.update(marker_installation_attempted=False, marker_original_absence=True,
                      native_texture_sha256=startup.sha(plan['files']['native_texture']['path']))

    def restore(self, plan, output, report):
        super().restore(plan, output, report)
        if plan['texture_condition'] == 'native_original':
            report['marker_restored'] = not (ROOT / 'resource_pack/textures/blocks/flower_rose.png').exists()
            if not report['marker_restored']:
                raise ValueError('Original condition own texture slot gained external bytes')

    def handle_sample(self, session):
        from read_owned_startup_handles import snapshot
        from _session import _kernel, _identity
        import ctypes
        from ctypes import wintypes
        kernel = _kernel()
        kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                     ctypes.POINTER(wintypes.DWORD)]
        kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel.GetProcessHandleCount.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetProcessHandleCount.restype = wintypes.BOOL
        return {kind: snapshot(kernel, _identity, session[kind + '_pid'], session[kind + '_identity'],
                session['game_executable'] if kind == 'game' else session['noactivation']['mcdk']['path'])
                for kind in ('game', 'mcdk')}


def supervise(plan, host, output, phase=run_phase):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError('H0 evidence must use a fresh owned project directory')
    output.mkdir(parents=True)
    receipt = output / 'supervisor.json'
    started = host.now()
    work_deadline, deadline = started + WORK, started + TOTAL
    report = {'schema': 1, 'owner': plan['owner'], 'name': plan['name'], 'launches': 0,
              'budgets': plan['budgets'], 'backup': [], 'samples': [], 'cleanup_errors': [],
              'handle_samples': [], 'handle_rule_triggered': False, 'resource_health_accepted': False,
              'matrix_started': False, 'production_acceptance': False,
              'started_at': datetime.now(timezone.utc).isoformat()}
    session, initial = None, set()
    first_scheduled = False
    first_ready = False
    application_ready = False
    application_gate_deadline = None
    capacity_checked = False
    consecutive = {'game': 0, 'mcdk': 0}

    def health():
        if session is None or not session.get('game_pid') or not session.get('mcdk_pid'):
            return
        if report['handle_rule_triggered']:
            raise RuntimeError('Persistent rapid owned handle growth; own cleanup required')
        rows = report['handle_samples']
        current_time = host.now()
        ready = session.get('state') == 'ready' and session.get('ready') is True
        first_ready_baseline = ready and not any(row['ready'] for row in rows)
        if rows and current_time - rows[-1]['monotonic'] < 15 and not first_ready_baseline:
            return
        if len(rows) >= 18:
            return
        value = {'monotonic': current_time, 'elapsed_seconds': current_time - started,
                 'captured_at': datetime.now(timezone.utc).isoformat(), 'processes': host.handle_sample(session),
                 'ready': ready, 'post_ready_baseline': first_ready_baseline,
                 'sdk_or_window_mutation': False, 'cause_attribution': False}
        for kind in ('game', 'mcdk'):
            row = value['processes'][kind]
            if row['status'] != 'live':
                raise RuntimeError('Owned process handle observation is no longer live: ' + kind)
            qualifies = bool(ready and rows and rows[-1]['ready'] and
                             rapid_growth(rows[-1]['processes'][kind]['handle_count'],
                                          row['handle_count'], current_time - rows[-1]['monotonic']))
            consecutive[kind] = consecutive[kind] + 1 if qualifies else 0
            row['qualifying_interval'] = qualifies
            row['consecutive_qualifying_intervals'] = consecutive[kind]
            row['pre_ready_growth_observation_only'] = not ready
        rows.append(value)
        save_path = output / ('handles-%02d.json' % len(rows))
        startup.save(save_path, value)
        absolute = value['processes']['game']['handle_count'] >= 100000
        report['handle_rule_triggered'] = absolute or any(count >= 2 for count in consecutive.values())
        report['handle_stop_reason'] = ('absolute_game_handles_at_least_100000' if absolute else
                                       'persistent_post_ready_growth' if report['handle_rule_triggered'] else None)
        startup.save(receipt, report)
        if report['handle_rule_triggered']:
            raise RuntimeError('Persistent rapid owned handle growth; own cleanup required')

    try:
        initial = host.session_ids()
        report['active_game_pids_before'] = startup.capacity_pids(host, report, 'before_preparation')
        if len(report['active_game_pids_before']) >= 5:
            raise RuntimeError('H0 coordinated game slot is unavailable')
        host.prepare(plan, output, report)
        report['active_game_pids_prelaunch'] = startup.capacity_pids(host, report, 'immediately_before_launch')
        if len(report['active_game_pids_prelaunch']) >= 5 or host.now() >= work_deadline:
            raise RuntimeError('H0 capacity/deadline gate refused launch')
        report['launches'] = 1
        host.launch(plan, output)
        report['launcher_started_at_elapsed_seconds'] = host.now() - started
        while host.now() < work_deadline:
            found = host.find_session(plan, initial)
            if found:
                startup.validate_binding(found, plan, initial)
                if session and any(found.get(key) != session.get(key) for key in
                        ('id', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity') if session.get(key) is not None):
                    raise RuntimeError('H0 owned session binding changed')
                session = found
                report['session'] = {key: session.get(key) for key in ('id', 'session_file', 'owner', 'project',
                                     'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')}
                if session.get('game_pid') and session.get('mcdk_pid'):
                    if not capacity_checked:
                        report['active_game_pids_after'] = startup.capacity_pids(host, report, 'after_game_publication')
                        capacity_checked = True
                        if len(report['active_game_pids_after']) > 5:
                            raise RuntimeError('More than five games after owned h0 publication')
                    health()
                    if not first_scheduled and host.game_elapsed(session) >= 1:
                        first_scheduled = True
                        report['first_scheduled_sample_locked'] = True
                        startup.save(receipt, report)
                        row = host.observe(session, plan, output / 'startup-first-scheduled.png',
                                           max(.001, min(5., work_deadline - host.now())))
                        report['samples'].append(dict(row, label='first_scheduled', game_elapsed=host.game_elapsed(session)))
                    if session.get('state') == 'ready' and session.get('ready') is True and not first_ready:
                        first_ready = True
                        report['first_post_ready_sample_locked'] = True
                        startup.save(receipt, report)
                        row = host.observe(session, plan, output / 'startup-first-ready.png',
                                           max(.001, min(5., work_deadline - host.now())))
                        report['samples'].append(dict(row, label='first_post_ready', game_elapsed=host.game_elapsed(session)))
                        report['first_post_sdk_ready_machine_checks_passed'] = healthy_frame(row)
                        report['first_post_sdk_ready_world_pixels_accepted'] = False
                        application_gate_deadline = min(work_deadline - RESERVATION - 5, host.now() + 20)
            if not host.launcher_alive():
                if 'launcher_result' not in report:
                    report['launcher_result'] = host.launcher_result()
                    report['launcher_finished_at_elapsed_seconds'] = host.now() - started
                ready = json.loads(report['launcher_result']['stdout']) if report['launcher_result'].get('stdout') else {}
                if report['launcher_result']['returncode'] != 0 or ready.get('ready') is not True:
                    raise RuntimeError('H0 cold launcher did not finish ready')
                if first_ready and not application_ready:
                    if (host.now() >= application_gate_deadline or
                            len(report.get('application_readiness_reads', [])) >= 20):
                        raise TimeoutError('Modern projection UiInit readiness did not complete within reserved budget')
                    health()
                    semantic = host.application_ready(session, plan, application_gate_deadline)
                    report.setdefault('application_readiness_reads', []).append(dict(semantic, elapsed_seconds=host.now() - started))
                    if semantic['initialized']:
                        application_ready = True
                        report['first_application_ready_sample_locked'] = True
                        startup.save(receipt, report)
                        row = host.observe(session, plan, output / 'startup-first-application-ready.png',
                                           max(.001, min(5., work_deadline - RESERVATION - host.now())))
                        report['samples'].append(dict(row, label='first_application_ready', game_elapsed=host.game_elapsed(session)))
                        report['first_application_ready_machine_checks_passed'] = healthy_frame(row)
                        report['first_application_ready_world_pixels_accepted'] = False
                        report['first_application_ready_world_pixels_require_visual_review'] = True
                        if not report['first_application_ready_machine_checks_passed']:
                            raise RuntimeError('First application-ready frame failed; replacement refused')
                    else:
                        host.sleep(min(.8, max(0, application_gate_deadline - host.now())))
                if application_ready and report['first_application_ready_machine_checks_passed']:
                    if work_deadline - host.now() < RESERVATION:
                        raise TimeoutError('H0 ready frame left less than 83 seconds for the matrix')
                    health()
                    report['matrix_started'] = True
                    startup.save(receipt, report)
                    report['matrix'] = phase(plan, host, session, output, work_deadline, deadline - 30, health)
                    report['cleanup_errors'].extend(report['matrix']['cleanup_errors'])
                    if not report['matrix']['completed']:
                        raise RuntimeError('H0 finite phase did not complete: ' + report['matrix'].get('error', 'unknown'))
                    break
            startup.save(receipt, report)
            host.sleep(min(.2, max(0, work_deadline - host.now())))
        if not report.get('matrix', {}).get('completed'):
            raise TimeoutError('H0 matrix did not complete before the work deadline')
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        if session is None and report['launches']:
            try:
                session = host.find_session(plan, initial)
            except Exception as error:
                report['cleanup_errors'].append('Owned session discovery: ' + str(error))
        if report['launches']:
            try:
                startup.cleanup_owned(session, plan, host, deadline, report)
            except Exception as error:
                report['cleanup_errors'].append('Owned process cleanup: ' + str(error))
        try:
            host.restore(plan, output, report)
        except Exception as error:
            report['cleanup_errors'].append('Host byte restoration: ' + str(error))
        report['run_elapsed_seconds'] = host.now() - started
        report['deadline_exceeded'] = report['run_elapsed_seconds'] > TOTAL
        report['diagnostic_completed'] = bool(report.get('matrix', {}).get('completed') and
                report.get('owned_processes_dead') and not report['cleanup_errors'] and
                not report['deadline_exceeded'] and 'error' not in report)
        startup.save(receipt, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    plan = validate_plan(args.plan, args.plan_sha256)
    if not args.run:
        print(json.dumps({'review_only': True, 'new_launches': 0, 'plan_sha256': args.plan_sha256}))
        return 0
    report = supervise(plan, WindowsHost(), args.output)
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report['diagnostic_completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
