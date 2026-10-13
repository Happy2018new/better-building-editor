"""One reviewed startup, passive samples, and cleanup within a 150-second budget."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
OWNER = 'snow-r12-passive'
NAME = 'snow-passive-alpha-slot-r12-v1'
PROTECTED_SESSION = '773c643b5cf344918e04d8b4eef2657a'
TOTAL_SECONDS = 150
OBSERVATION_SECONDS = 110
LAUNCHER_WAIT_SECONDS = 90
SAMPLES = (1, 15, 30, 45, 60, 75, 90, 105)
COPY_TARGETS = ('.agents/skills/pyreact-debugging/scripts/instances.py',
                '.agents/skills/pyreact-debugging/scripts/mcdk.py', '.mcdev.json')
CAPTURE_HELPER_SHA256 = 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, document):
    temporary = Path(path).with_suffix('.tmp')
    temporary.write_text(json.dumps(document, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    temporary.replace(path)


def validate_plan(path, expected_sha):
    path = Path(path).resolve(strict=True)
    if sha(path) != expected_sha:
        raise ValueError('Reviewed startup plan SHA-256 changed')
    plan = json.loads(path.read_bytes())
    if (plan.get('schema') != 1 or plan.get('owner') != OWNER or plan.get('name') != NAME
            or Path(plan.get('project', '')).resolve() != ROOT
            or plan.get('protected_session') != PROTECTED_SESSION
            or plan.get('budgets') != {'total': 150, 'observation': 110, 'cleanup_reserved': 40, 'launcher_wait': 90}
            or plan.get('sample_seconds') != list(SAMPLES) or plan.get('max_launches') != 1
            or plan.get('max_active_games') != 5 or plan.get('matrix_included') is not False):
        raise ValueError('Startup plan scope or fixed bounds changed')
    for record in plan['files'].values():
        if sha(record['path']) != record['sha256']:
            raise ValueError('Reviewed startup source or binary changed: ' + record['path'])
    inventory = json.loads(Path(plan['files']['project_source']['path']).read_bytes())
    current = {path.relative_to(ROOT).as_posix(): sha(path)
               for kind in ('behavior_pack', 'resource_pack') for path in (ROOT / kind).rglob('*')
               if path.is_file()}
    if current != inventory['files']:
        raise ValueError('Frozen behavior/resource source tree changed before launch')
    if plan['files']['supervisor']['path'] != str(Path(__file__).resolve()):
        raise ValueError('Startup plan belongs to another supervisor source')
    if plan.get('texture_condition') != 'native_alpha_preserved':
        raise ValueError('This reviewed startup supports the frozen native-alpha condition only')
    config = json.loads(Path(plan['files']['config']['path']).read_bytes())
    for key, value in (('world_type', 2), ('world_seed', 0), ('game_mode', 1),
                       ('do_daylight_cycle', False), ('do_weather_cycle', False)):
        if config.get(key) != value:
            raise ValueError('Private flat creative config changed: ' + key)
    for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui', 'auto_hot_reload_shaders',
                'auto_hot_reload_materials', 'auto_hot_reload_particles'):
        if config.get(key) is not False:
            raise ValueError('Startup hot reload must be disabled: ' + key)
    return plan


def validate_binding(session, plan, initial_ids):
    if (session.get('id') in initial_ids or session.get('id') == PROTECTED_SESSION
            or session.get('owner') != plan['owner'] or session.get('name') != plan['name']
            or Path(session.get('project', '')).resolve() != Path(plan['project']).resolve()):
        raise ValueError('Startup session is not the newly launched owned project')
    protected_pids = {row['pid'] for row in plan['protected_processes'].values()}
    if any(session.get(kind + '_pid') in protected_pids for kind in ('game', 'mcdk')):
        raise ValueError('Startup session aliases a protected process PID')
    if session.get('state') not in ('starting', 'failed', 'ready'):
        raise ValueError('Startup session state is not observable')
    for kind in ('game', 'mcdk'):
        if session.get(kind + '_pid') and not session.get(kind + '_identity'):
            raise ValueError('Missing creation identity for owned ' + kind)
    return session


def remaining(deadline, host, maximum):
    return max(0, min(maximum, deadline - host.now()))


def capacity_pids(host, report, phase):
    try:
        return host.active_game_pids()
    finally:
        evidence = getattr(host, 'capacity_evidence', None)
        if evidence is not None:
            report.setdefault('capacity_checks', []).append(dict(evidence, phase=phase))


def cleanup_owned(session, plan, host, deadline, report):
    if host.launcher_alive():
        report['launcher_stop'] = host.stop_launcher(remaining(deadline, host, 1))
    if session is None:
        report['cleanup_errors'].append('No owned session was published; process cleanup remains unknown')
        return
    validate_binding(session, plan, set())
    session = host.complete_cleanup_binding(session, remaining(deadline, host, 3))
    validate_binding(session, plan, set())
    inspection = host.inspect_owned(session)
    report['cleanup_inspection_before'] = inspection
    if inspection.get('mismatch'):
        report['cleanup_errors'].append('Owned identity/executable changed; cleanup refused')
        return
    if inspection['alive']:
        timeout = remaining(deadline, host, 15)
        if timeout > 0:
            report['normal_stop'] = host.normal_stop(session, timeout)
        inspection = host.inspect_owned(session)
        report['cleanup_inspection_after_normal'] = inspection
        if inspection.get('mismatch'):
            report['cleanup_errors'].append('Owned identity/executable changed after normal close; force cleanup refused')
            return
        if inspection['alive']:
            report['force_stop_after_inspection'] = {'identities': inspection['alive'], 'results': []}
            for kind in ('game', 'mcdk'):
                timeout = remaining(deadline, host, 5)
                if kind in inspection['alive'] and timeout > 0:
                    report['force_stop_after_inspection']['results'].append(host.force_stop(session, kind, timeout))
    final = host.inspect_owned(session)
    report['cleanup_inspection_final'] = final
    report['owned_processes_dead'] = not final['alive'] and not final.get('mismatch')
    if not report['owned_processes_dead']:
        report['cleanup_errors'].append('Owned processes were not confirmed dead within the deadline')


def supervise(plan, host, output):
    output = Path(output).resolve()
    if not output.is_relative_to(Path(plan['project']).resolve()):
        raise ValueError('Startup supervisor evidence must stay inside its owned project')
    if output.exists():
        raise ValueError('Startup supervisor output must be fresh')
    output.mkdir(parents=True)
    receipt = output / 'supervisor.json'
    started = host.now()
    deadline, observation_deadline = started + TOTAL_SECONDS, started + OBSERVATION_SECONDS
    report = {'schema': 1, 'owner': plan['owner'], 'name': plan['name'], 'production_acceptance': False,
        'launches': 0, 'samples': [], 'cleanup_errors': [], 'backup': [], 'budgets': plan['budgets'],
        'matrix_started': False, 'ready_health_started': False, 'launcher_ready': False,
        'first_scheduled_sample_target': None, 'first_post_ready_sample_target': None,
        'protected_session': PROTECTED_SESSION, 'started_at': datetime.now(timezone.utc).isoformat()}
    session, initial_ids = None, set()
    attempted, exited, capacity_checked = set(), False, False
    try:
        initial_ids = host.session_ids()
        report['active_game_pids_before'] = capacity_pids(host, report, 'before_preparation')
        if len(report['active_game_pids_before']) >= plan['max_active_games']:
            raise RuntimeError('Five active games already exist; startup slot unavailable')
        host.prepare(plan, output, report)
        report['prepared_at_elapsed_seconds'] = host.now() - started
        save(receipt, report)
        if remaining(observation_deadline, host, 1) <= 0:
            raise TimeoutError('Startup preparation exhausted the observation budget')
        report['active_game_pids_prelaunch'] = capacity_pids(host, report, 'immediately_before_launch')
        if len(report['active_game_pids_prelaunch']) >= plan['max_active_games']:
            raise RuntimeError('Startup capacity changed before launch')
        if remaining(observation_deadline, host, 1) <= 0:
            raise TimeoutError('Prelaunch capacity check exhausted the observation budget; launch refused')
        report['launches'] = 1
        host.launch(plan, output)
        report['launcher_started_at_elapsed_seconds'] = host.now() - started
        save(receipt, report)
        while host.now() < observation_deadline:
            found = host.find_session(plan, initial_ids)
            if found is not None:
                validate_binding(found, plan, initial_ids)
                if session is not None and any(found.get(key) != session.get(key) for key in
                        ('id', 'mcdk_pid', 'mcdk_identity', 'game_pid', 'game_identity')
                        if session.get(key) is not None):
                    raise RuntimeError('Owned startup session binding changed')
                session = found
                report['session'] = {key: session.get(key) for key in ('id', 'session_file', 'artifacts',
                    'owner', 'project', 'state', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')}
                if session.get('ready') is True and session.get('state') == 'ready':
                    report['launcher_ready'] = True
            if not host.launcher_alive() and not exited:
                report['launcher_result'] = host.launcher_result()
                report['launcher_finished_at_elapsed_seconds'] = host.now() - started
                exited = True
            if session and session.get('game_pid') and session.get('mcdk_pid'):
                if not capacity_checked:
                    report['active_game_pids_after'] = capacity_pids(host, report, 'after_game_publication')
                    capacity_checked = True
                    if len(report['active_game_pids_after']) > plan['max_active_games']:
                        raise RuntimeError('Active game count exceeded five after the owned launch; own cleanup required')
                game_elapsed = host.game_elapsed(session)
                due = next((target for target in SAMPLES if target not in attempted and game_elapsed >= target), None)
                if due is not None:
                    attempted.add(due)
                    timeout = remaining(observation_deadline, host, 15)
                    row = {'target_game_seconds': due, 'observed_game_seconds': game_elapsed,
                           'late_seconds': max(0, game_elapsed - due), 'timeout_seconds': timeout,
                           'session_state_at_sample': session.get('state'),
                           'session_ready_at_sample': session.get('ready') is True,
                           'started_at_elapsed_seconds': host.now() - started}
                    if report['first_scheduled_sample_target'] is None:
                        report['first_scheduled_sample_target'] = due
                    if (report['first_post_ready_sample_target'] is None and session.get('state') == 'ready'
                            and session.get('ready') is True):
                        report['first_post_ready_sample_target'] = due
                    report['samples'].append(row)
                    save(receipt, report)
                    if timeout < 1:
                        row['skipped'] = 'Insufficient remaining observation time'
                    else:
                        row.update(host.observe(session, plan, output / ('startup-%03d.png' % due), timeout))
                    row['finished_at_elapsed_seconds'] = host.now() - started
                    save(receipt, report)
                    continue
            host.sleep(min(.25, max(0, observation_deadline - host.now())))
        report['samples_not_attempted'] = [target for target in SAMPLES if target not in attempted]
        report['observation_finished_at_elapsed_seconds'] = host.now() - started
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
    finally:
        if session is None and report['launches']:
            try:
                session = host.find_session(plan, initial_ids)
                if session:
                    validate_binding(session, plan, initial_ids)
            except Exception as error:
                report['cleanup_errors'].append('Session discovery: ' + str(error))
        if report['launches']:
            try:
                cleanup_owned(session, plan, host, deadline, report)
            except Exception as error:
                report['cleanup_errors'].append('Owned process cleanup: ' + str(error))
        try:
            host.restore(plan, output, report)
        except Exception as error:
            report['cleanup_errors'].append('Original byte restoration: ' + str(error))
        report['run_elapsed_seconds'] = host.now() - started
        report['deadline_exceeded'] = report['run_elapsed_seconds'] > TOTAL_SECONDS
        report['diagnostic_completed'] = (report['launches'] == 1 and report.get('owned_processes_dead', False)
            and not report['cleanup_errors'] and not report['deadline_exceeded'] and 'error' not in report)
        save(receipt, report)
    return report


class WindowsHost:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('Owned startup supervision requires Windows')
        self.launcher = None
        self.handles = []
        self.marker = None
        sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
        from _session import registry_dir, process_identity, terminate_owned
        self.registry = registry_dir()
        self.identity, self.terminate = process_identity, terminate_owned

    now = staticmethod(time.monotonic)
    sleep = staticmethod(time.sleep)

    def session_ids(self):
        return {path.parent.name for path in self.registry.glob('*/session.json')}

    def active_game_pids(self):
        self.capacity_evidence = {'source': 'CIM candidates verified by _session.process_identity',
            'live_check': 'GetExitCodeProcess == STILL_ACTIVE (259) plus creation identity',
            'rows': [], 'active_pids': [], 'excluded_pids': [], 'uncertain_pids': [],
            'process_mutation_attempted': False}
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
            "@(Get-CimInstance Win32_Process -Filter \"Name='Minecraft.Windows.exe'\" | "
            "Select-Object ProcessId,ThreadCount,HandleCount,ExecutablePath,WorkingSetSize) "
            "| ConvertTo-Json -Compress"],
            capture_output=True, timeout=8, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise RuntimeError('Could not count active games: ' + result.stderr.decode('utf8', 'replace'))
        value = json.loads(result.stdout.decode('utf-8-sig') or '[]')
        candidates = value if isinstance(value, list) else [value]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise RuntimeError('Invalid CIM game candidate row')
            pid = candidate.get('ProcessId')
            if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
                raise RuntimeError('Invalid CIM game candidate PID')
            row = {'pid': pid, 'thread_count': candidate.get('ThreadCount'),
                'handle_count': candidate.get('HandleCount'), 'executable': candidate.get('ExecutablePath'),
                'working_set_bytes': candidate.get('WorkingSetSize'), 'identity': None}
            self.capacity_evidence['rows'].append(row)
            try:
                row['identity'] = self.identity(pid)
            except OSError as error:
                row['inspection_error'] = str(error)
            if row['identity'] is not None:
                row['status'] = 'verified_live'
                self.capacity_evidence['active_pids'].append(pid)
            elif (row['thread_count'] == 0 and row['handle_count'] == 0 and not row['executable']
                    and 'inspection_error' not in row):
                row['status'] = 'excluded_terminated_cim_object'
                self.capacity_evidence['excluded_pids'].append(pid)
            else:
                row['status'] = 'uninspectable_or_uncertain'
                self.capacity_evidence['uncertain_pids'].append(pid)
        if self.capacity_evidence['uncertain_pids']:
            raise RuntimeError('Cannot verify candidate game liveness; capacity check refused: ' +
                               str(self.capacity_evidence['uncertain_pids']))
        return self.capacity_evidence['active_pids']

    def prepare(self, plan, output, report):
        for target, key in zip(COPY_TARGETS, ('instances', 'mcdk_client', 'config')):
            target = ROOT / target
            if sha(plan['files'][key]['path']) != plan['files'][key]['sha256']:
                raise ValueError('Reviewed preparation source changed: ' + key)
            backup = output / ('original-' + target.name)
            shutil.copyfile(target, backup)
            report['backup'].append({'target': str(target), 'backup': str(backup), 'sha256': sha(backup)})
            shutil.copyfile(plan['files'][key]['path'], target)
            report['backup'][-1]['installed_sha256'] = sha(target)
        from PIL import Image
        target = ROOT / 'resource_pack/textures/blocks/flower_rose.png'
        for key in ('native_texture', 'alpha_candidate'):
            if sha(plan['files'][key]['path']) != plan['files'][key]['sha256']:
                raise ValueError('Reviewed texture source changed: ' + key)
        self.marker = {'target': str(target), 'before_hex': target.read_bytes().hex() if target.exists() else None,
                       'candidate_sha256': plan['files']['alpha_candidate']['sha256']}
        with Image.open(plan['files']['native_texture']['path']) as native, \
                Image.open(plan['files']['alpha_candidate']['path']) as candidate:
            if native.convert('RGBA').getchannel('A').tobytes() != candidate.convert('RGBA').getchannel('A').tobytes():
                raise ValueError('Frozen marker does not preserve original native alpha')
        save(output / 'marker-restore.json', self.marker)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.install_marker(plan['files']['alpha_candidate']['path'], output, report)
        report['native_texture_sha256'] = sha(plan['files']['native_texture']['path'])

    def install_marker(self, source, output, report):
        target = Path(self.marker['target'])
        self.marker.update(installation_attempted=True, owned_target_observed=False)
        report['marker_installation_attempted'] = True
        save(output / 'marker-restore.json', self.marker)
        try:
            shutil.copyfile(source, target)
            report['marker_candidate_sha256'] = sha(target)
        finally:
            self.marker['owned_target_sha256'] = sha(target) if target.exists() else None
            self.marker['owned_target_observed'] = True
            save(output / 'marker-restore.json', self.marker)

    def launch(self, plan, output):
        command = [sys.executable, '-X', 'utf8', str(ROOT / COPY_TARGETS[0]), 'start',
            '--project', str(ROOT), '--owner', plan['owner'], '--name', plan['name'],
            '--mcdk', plan['files']['mcdk_binary']['path'], '--noactivate-dll', plan['files']['guard']['path'],
            '--noactivate-sha256', plan['files']['guard']['sha256'],
            '--noactivate-mcdk-sha256', plan['files']['mcdk_binary']['sha256'], '--wait', '90']
        for filename in ('launcher.stdout', 'launcher.stderr'):
            self.handles.append((output / filename).open('wb'))
        self.launcher = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
            stdout=self.handles[0], stderr=self.handles[1], creationflags=subprocess.CREATE_NO_WINDOW)
        self.launcher_identity = self.identity(self.launcher.pid)
        self.launch_command = command

    def complete_cleanup_binding(self, session, timeout=3):
        if session.get('game_pid') or not session.get('mcdk_pid'):
            return session
        current = self.inspect_owned(session)
        if current['mismatch'] or 'mcdk' not in current['alive']:
            return session
        if timeout <= 0:
            raise TimeoutError('Cleanup deadline reached before unpublished child discovery')
        command = ("@(Get-CimInstance Win32_Process -Filter 'ParentProcessId=%d' | "
                   "Where-Object Name -eq 'Minecraft.Windows.exe' | Select-Object -ExpandProperty ProcessId) "
                   "| ConvertTo-Json -Compress") % session['mcdk_pid']
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command], capture_output=True,
                                timeout=min(3, timeout), creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise RuntimeError('Unpublished owned game discovery failed')
        values = json.loads(result.stdout.decode('utf-8-sig') or '[]')
        values = values if isinstance(values, list) else [values]
        if len(values) > 1:
            raise RuntimeError('Multiple unpublished games belong to the owned MCDK; cleanup requires inspection')
        if not values:
            return session
        from observe_owned_startup import WindowsHost as ObserverHost
        actual = ObserverHost().inspect_process(values[0])
        if actual is None or Path(actual['executable']).resolve() != Path(session['game_executable']).resolve():
            raise RuntimeError('Unpublished game executable is not the owned expected game')
        return dict(session, game_pid=values[0], game_identity=actual['identity'],
                    unpublished_game_recovered_for_cleanup_only=True)

    def find_session(self, plan, initial_ids):
        candidates = []
        for path in self.registry.glob('*/session.json'):
            if path.parent.name in initial_ids or path.parent.name == PROTECTED_SESSION:
                continue
            data = json.loads(path.read_bytes())
            if data.get('owner') == plan['owner'] and data.get('name') == plan['name']:
                candidates.append(data)
        if len(candidates) > 1:
            raise RuntimeError('Multiple new startup sessions match this owner/name')
        return candidates[0] if candidates else None

    def launcher_alive(self):
        return self.launcher is not None and self.launcher.poll() is None

    def launcher_result(self):
        for handle in self.handles:
            handle.flush()
        return {'returncode': self.launcher.poll(), 'command': self.launch_command,
                'stdout': Path(self.handles[0].name).read_text(encoding='utf8'),
                'stderr': Path(self.handles[1].name).read_text(encoding='utf8')}

    def game_elapsed(self, session):
        current_filetime = time.time_ns() // 100 + 116444736000000000
        return (current_filetime - int(session['game_identity'])) / 10000000.0

    def observer_adapter(self, plan):
        path = Path(plan['files']['observer']['path']).resolve(strict=True)
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != plan['files']['observer']['sha256']:
            raise ValueError('Reviewed startup observer source changed')
        module = ModuleType('reviewed_owned_startup_observer')
        module.__file__ = str(path)
        exec(compile(payload, str(path), 'exec'), module.__dict__)
        capture = plan['files']['capture']
        capture_path = Path(capture['path']).resolve(strict=True)
        if (capture.get('sha256') != CAPTURE_HELPER_SHA256 or
                sha(capture_path) != CAPTURE_HELPER_SHA256):
            raise ValueError('Reviewed capture helper differs from approved single-WGC bytes')
        # The frozen plan owns the exact helper path. A short worktree need not
        # contain the shared runtime archive at the observer's default ROOT.
        module.CAPTURE_EXECUTABLE = capture_path
        module.CAPTURE_SHA256 = CAPTURE_HELPER_SHA256
        dpi_path = Path(plan['files']['dpi_helper']['path']).resolve(strict=True)
        dpi_payload = dpi_path.read_bytes()
        if hashlib.sha256(dpi_payload).hexdigest() != plan['files']['dpi_helper']['sha256']:
            raise ValueError('Reviewed physical DPI helper source changed')
        dpi = ModuleType('reviewed_owned_startup_dpi')
        dpi.__file__ = str(dpi_path)
        exec(compile(dpi_payload, str(dpi_path), 'exec'), dpi.__dict__)
        module.dpi_geometry = dpi

        class PhysicalObserverHost(module.WindowsHost):
            def guard(self, session):
                with dpi.physical_dpi_context():
                    return super().guard(session)

        module.WindowsHost = PhysicalObserverHost
        return module

    def observe(self, session, plan, output, timeout):
        started = self.now()
        try:
            observer = self.observer_adapter(plan)
        except ValueError as error:
            return {'returncode': 1, 'timeout': False, 'error': str(error)}
        budget = timeout - (self.now() - started)
        if budget <= 0:
            return {'returncode': 1, 'timeout': True, 'error': 'Startup observer loading exhausted the sample budget'}
        # The observer's bounded run() now owns the WGC helper as a direct child.
        report = observer.observe(session['session_file'], plan['owner'], plan['project'], output,
                                  Path(plan['files']['capture']['path']), budget)
        return {'returncode': 0 if report['ok'] else 1, 'stdout': json.dumps(report, ensure_ascii=True),
                'stderr': '', 'observer_receipt': str(output.with_suffix('.startup.json')),
                'timeout': report['timeout'], 'observer_in_process': True, 'capture_child_direct': True,
                'window_geometry_space': 'physical_per_monitor_v2'}

    def inspect_owned(self, session):
        from observe_owned_startup import WindowsHost as ObserverHost
        host, alive, mismatch = ObserverHost(), {}, []
        for kind in ('game', 'mcdk'):
            pid, expected = session.get(kind + '_pid'), session.get(kind + '_identity')
            if not pid:
                continue
            actual = host.inspect_process(pid)
            if actual is None:
                continue
            executable = session['game_executable'] if kind == 'game' else session['noactivation']['mcdk']['path']
            if actual['identity'] != expected or Path(actual['executable']).resolve() != Path(executable).resolve():
                mismatch.append(kind)
            else:
                alive[kind] = {'pid': pid, 'identity': expected, 'executable': executable}
        return {'alive': alive, 'mismatch': mismatch}

    def terminate_within(self, pid, identity, deadline):
        import _session
        kernel = _session._kernel()
        handle = kernel.OpenProcess(0x1000 | 0x1 | 0x100000, False, int(pid))
        if not handle:
            return {'handle_unavailable': True}
        try:
            current = _session._identity(kernel, handle)
            if current is None:
                return {'already_dead': True}
            if current != identity:
                raise RuntimeError('Process identity changed; refusing to stop pid %s' % pid)
            if self.now() >= deadline:
                raise TimeoutError('Cleanup deadline reached before owned termination')
            if not kernel.TerminateProcess(handle, 1):
                raise OSError('TerminateProcess failed')
            wait_ms = max(0, int(min(5, max(0, deadline - self.now())) * 1000))
            waited = kernel.WaitForSingleObject(handle, wait_ms)
            return {'wait_ms': wait_ms, 'wait_result': waited, 'timeout': waited == 258}
        finally:
            kernel.CloseHandle(handle)

    def stop_launcher(self, timeout):
        deadline = self.now() + timeout
        termination = None
        if self.launcher_identity and self.identity(self.launcher.pid) == self.launcher_identity:
            termination = self.terminate_within(self.launcher.pid, self.launcher_identity, deadline)
        try:
            self.launcher.wait(timeout=max(0, deadline - self.now()))
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
        return dict(self.launcher_result(), timeout=timed_out, termination=termination)

    def normal_stop(self, session, timeout):
        command = [sys.executable, '-X', 'utf8', str(ROOT / COPY_TARGETS[0]), 'stop',
                   '--session', session['session_file'], '--owner', OWNER]
        try:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf8',
                timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
            return {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr, 'timeout': False}
        except subprocess.TimeoutExpired as error:
            return {'timeout': True, 'error': str(error)}

    def force_stop(self, session, kind, timeout=5):
        termination = self.terminate_within(session[kind + '_pid'], session[kind + '_identity'], self.now() + timeout)
        return {'kind': kind, 'pid': session[kind + '_pid'], 'identity': session[kind + '_identity'],
                'termination': termination}

    def restore(self, plan, output, report):
        for handle in self.handles:
            handle.close()
        errors = []
        if self.marker is not None and (report.get('marker_candidate_sha256') or report.get('marker_installation_attempted')):
            target = Path(self.marker['target'])
            try:
                if self.marker.get('installation_attempted') and not self.marker.get('owned_target_observed'):
                    raise ValueError('Marker install target could not be observed; restoration refused')
                expected = self.marker.get('owned_target_sha256', self.marker['candidate_sha256'])
                current = sha(target) if target.exists() else None
                if current != expected:
                    raise ValueError('Marker target changed; original-byte restoration refused')
                if self.marker['before_hex'] is None:
                    if target.exists():
                        target.unlink()
                else:
                    target.write_bytes(bytes.fromhex(self.marker['before_hex']))
                report['marker_restored'] = (target.read_bytes().hex() == self.marker['before_hex']
                    if target.exists() else self.marker['before_hex'] is None)
            except Exception as error:
                errors.append(str(error))
        for row in report['backup']:
            try:
                if sha(row['backup']) != row['sha256']:
                    raise ValueError('Original-byte backup changed: ' + row['backup'])
                if row.get('installed_sha256') and sha(row['target']) != row['installed_sha256']:
                    raise ValueError('Runtime source target changed externally; restoration refused: ' + row['target'])
                shutil.copyfile(row['backup'], row['target'])
                row['restored'] = sha(row['target']) == row['sha256']
                if not row['restored']:
                    raise ValueError('Original bytes were not restored: ' + row['target'])
            except Exception as error:
                errors.append(str(error))
        report['native_texture_unchanged'] = sha(plan['files']['native_texture']['path']) == plan['files']['native_texture']['sha256']
        if not report['native_texture_unchanged']:
            errors.append('Installed original native texture changed')
        if errors:
            raise RuntimeError('; '.join(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    plan = validate_plan(args.plan, args.plan_sha256)
    if not args.run:
        print(json.dumps({'review_only': True, 'plan_sha256': sha(args.plan), 'native_launches': 0}))
        return 0
    report = supervise(plan, WindowsHost(), args.output)
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report['diagnostic_completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
