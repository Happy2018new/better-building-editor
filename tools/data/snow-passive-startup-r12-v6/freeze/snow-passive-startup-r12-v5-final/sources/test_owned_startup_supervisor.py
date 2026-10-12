"""Verify the single-launch schedule and cleanup with a simulated host clock."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import supervise_owned_startup as supervisor


class FakeHost:
    def __init__(self, project):
        self.clock = 0.0
        self.project = project
        self.pids = [101, 102, 103, 104]
        self.launches = 0
        self.launch_at = None
        self.launch_done_at = 94.0
        self.publish_at = 8.0
        self.game_created_at = 4.0
        self.sample_duration = 1.0
        self.observations = []
        self.alive = {'game': {'pid': 11, 'identity': 'game-creation'},
                      'mcdk': {'pid': 22, 'identity': 'mcdk-creation'}}
        self.mismatch = []
        self.normal_closes = False
        self.normal_seconds = 15
        self.force_stops = []
        self.restored = False
        self.launcher_stopped = False
        self.session = {'schema': 1, 'id': 'new-owned', 'owner': supervisor.OWNER, 'name': supervisor.NAME,
            'project': str(project), 'session_file': str(project / 'new-owned/session.json'),
            'artifacts': str(project / 'new-owned/artifacts'), 'game_pid': 11, 'game_identity': 'game-creation',
            'mcdk_pid': 22, 'mcdk_identity': 'mcdk-creation', 'state': 'starting', 'ready': False}
        self.ready = False
        self.fault = None
        self.capacity_reads = 0

    def now(self):
        return self.clock

    def sleep(self, seconds):
        self.clock += seconds

    def session_ids(self):
        return {supervisor.PROTECTED_SESSION, 'another-existing'}

    def active_game_pids(self):
        self.capacity_reads += 1
        return self.pids

    def prepare(self, plan, output, report):
        if self.fault == 'prepare':
            raise ValueError('Preparation source changed')

    def launch(self, plan, output):
        self.launches += 1
        self.launch_at = self.clock

    def launcher_alive(self):
        return self.launches > 0 and not self.launcher_stopped and self.clock < self.launch_done_at

    def launcher_result(self):
        return {'returncode': 0 if self.ready else 1, 'stdout': json.dumps(self.session), 'stderr': ''}

    def find_session(self, plan, initial_ids):
        if self.publish_at is None or self.clock < self.publish_at:
            return None
        session = copy.deepcopy(self.session)
        session['state'] = 'ready' if self.ready else ('failed' if self.clock >= self.launch_done_at else 'starting')
        session['ready'] = self.ready
        if self.fault == 'wrong_owner':
            session['owner'] = 'another-owner'
        if self.fault == 'protected':
            session['id'] = supervisor.PROTECTED_SESSION
        if self.fault == 'reused' and self.clock >= 50:
            session['game_identity'] = 'reused-creation'
        return session

    def game_elapsed(self, session):
        return self.clock - self.game_created_at

    def observe(self, session, plan, output, timeout):
        self.observations.append({'target': int(output.stem.split('-')[-1]), 'start': self.clock, 'timeout': timeout})
        self.clock += min(self.sample_duration, timeout)
        if self.fault == 'capture':
            return {'returncode': 1, 'error': 'blank image', 'timeout': False}
        return {'returncode': 0, 'timeout': False}

    def complete_cleanup_binding(self, session):
        return session

    def inspect_owned(self, session):
        return {'alive': copy.deepcopy(self.alive), 'mismatch': self.mismatch}

    def stop_launcher(self, timeout):
        self.launcher_stopped = True
        self.clock += min(.1, timeout)
        return {'stopped': True}

    def normal_stop(self, session, timeout):
        self.clock += min(self.normal_seconds, timeout)
        if self.normal_closes:
            self.alive = {}
        return {'returncode': 0 if self.normal_closes else 1}

    def force_stop(self, session, kind):
        self.force_stops.append({'kind': kind, 'pid': session[kind + '_pid'], 'identity': session[kind + '_identity']})
        self.clock += 1
        del self.alive[kind]
        return self.force_stops[-1]

    def restore(self, plan, output, report):
        self.restored = True
        report['marker_restored'] = True
        report['native_texture_unchanged'] = True
        if self.fault == 'restore':
            raise RuntimeError('Restoration receipt failed')


class OwnedStartupSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.plan = {'schema': 1, 'project': str(self.root), 'owner': supervisor.OWNER, 'name': supervisor.NAME,
            'max_active_games': 5, 'protected_processes': {'game': {'pid': 777, 'identity': 'protected-game'},
                'mcdk': {'pid': 888, 'identity': 'protected-mcdk'}},
            'budgets': {'total': 150, 'observation': 110, 'cleanup_reserved': 40, 'launcher_wait': 90}}
        self.host = FakeHost(self.root)

    def run_supervisor(self):
        return supervisor.supervise(self.plan, self.host, self.root / 'fresh-run')

    def test_failed_readiness_still_gets_all_passive_samples_and_one_launch(self):
        result = self.run_supervisor()
        self.assertEqual(1, result['launches'])
        self.assertEqual(1, self.host.launches)
        self.assertIs(False, result['launcher_ready'])
        self.assertEqual(list(supervisor.SAMPLES), [row['target_game_seconds'] for row in result['samples']])
        self.assertEqual(3, result['samples'][0]['late_seconds'])
        self.assertEqual([], result['samples_not_attempted'])
        self.assertIs(True, result['diagnostic_completed'])
        self.assertIs(True, result['owned_processes_dead'])
        self.assertIs(True, self.host.restored)
        self.assertLessEqual(result['run_elapsed_seconds'], 150)
        self.assertEqual(110, result['observation_finished_at_elapsed_seconds'])
        self.assertEqual(1, result['launcher_result']['returncode'])

    def test_passive_samples_continue_after_failed_launcher_exit(self):
        self.host.launch_done_at = 30
        result = self.run_supervisor()
        self.assertGreater(result['samples'][-1]['started_at_elapsed_seconds'], result['launcher_finished_at_elapsed_seconds'])
        self.assertEqual(1, self.host.launches)

    def test_samples_never_overlap_or_repeat_after_capture_failure(self):
        self.host.sample_duration = 15
        self.host.fault = 'capture'
        result = self.run_supervisor()
        targets = [row['target'] for row in self.host.observations]
        self.assertEqual(len(set(targets)), len(targets))
        self.assertEqual(1, self.host.launches)
        for previous, current in zip(result['samples'], result['samples'][1:]):
            self.assertLessEqual(previous['finished_at_elapsed_seconds'], current['started_at_elapsed_seconds'])
        self.assertLessEqual(result['observation_finished_at_elapsed_seconds'], 110)
        self.assertLessEqual(result['run_elapsed_seconds'], 150)

    def test_final_sample_is_clamped_to_the_fixed_parent_observation_deadline(self):
        observe = self.host.observe
        def final_slow_sample(session, plan, output, timeout):
            self.host.sample_duration = 15 if output.stem == 'startup-105' else 1
            return observe(session, plan, output, timeout)
        self.host.observe = final_slow_sample
        result = self.run_supervisor()
        final = result['samples'][-1]
        self.assertEqual(105, final['target_game_seconds'])
        self.assertEqual(109, final['started_at_elapsed_seconds'])
        self.assertEqual(1, final['timeout_seconds'])
        self.assertEqual(110, final['finished_at_elapsed_seconds'])
        self.assertEqual(110, result['observation_finished_at_elapsed_seconds'])
        self.assertLessEqual(result['run_elapsed_seconds'], 150)

    def test_preparation_does_not_shift_the_parent_deadline(self):
        def prepare(plan, output, report):
            self.host.clock += 17.5
        self.host.prepare = prepare
        result = self.run_supervisor()
        self.assertEqual(17.5, result['prepared_at_elapsed_seconds'])
        self.assertEqual(110, result['observation_finished_at_elapsed_seconds'])
        self.assertLessEqual(result['run_elapsed_seconds'], 150)

    def test_five_existing_games_prevents_any_launch(self):
        self.host.pids.append(105)
        result = self.run_supervisor()
        self.assertEqual(0, self.host.launches)
        self.assertEqual(0, result['launches'])
        self.assertIn('slot unavailable', result['error'])
        self.assertEqual([], self.host.force_stops)

    def test_capacity_change_after_preparation_prevents_launch(self):
        def capacity():
            self.host.capacity_reads += 1
            return list(range(5 if self.host.capacity_reads > 1 else 4))
        self.host.active_game_pids = capacity
        result = self.run_supervisor()
        self.assertEqual(0, self.host.launches)
        self.assertEqual(0, result['launches'])
        self.assertIn('capacity changed', result['error'])

    def test_capacity_checks_retain_excluded_rows_at_every_phase(self):
        original = self.host.active_game_pids
        def counted():
            pids = original()
            self.host.capacity_evidence = {'active_pids': list(pids), 'excluded_pids': [900],
                'uncertain_pids': [], 'rows': [{'pid': 900, 'status': 'excluded_terminated_cim_object'}]}
            return pids
        self.host.active_game_pids = counted
        result = self.run_supervisor()
        self.assertEqual(['before_preparation', 'immediately_before_launch', 'after_game_publication'],
                         [row['phase'] for row in result['capacity_checks']])
        self.assertTrue(all(row['excluded_pids'] == [900] for row in result['capacity_checks']))
        self.assertEqual(self.host.pids, result['active_game_pids_prelaunch'])

    def test_uncertain_prelaunch_capacity_preserves_evidence_and_claims_no_launch(self):
        original = self.host.active_game_pids
        def counted():
            pids = original()
            if self.host.capacity_reads > 1:
                self.host.capacity_evidence = {'uncertain_pids': [900], 'rows': [
                    {'pid': 900, 'status': 'uninspectable_or_uncertain'}]}
                raise RuntimeError('Cannot verify candidate game liveness; capacity check refused')
            return pids
        self.host.active_game_pids = counted
        result = self.run_supervisor()
        self.assertEqual(0, result['launches'])
        self.assertEqual(0, self.host.launches)
        self.assertEqual([], self.host.force_stops)
        self.assertEqual([900], result['capacity_checks'][0]['uncertain_pids'])
        self.assertEqual('immediately_before_launch', result['capacity_checks'][0]['phase'])
        self.assertIs(True, self.host.restored)

    def test_excess_games_after_launch_stops_only_this_owned_pair(self):
        def capacity():
            self.host.capacity_reads += 1
            return list(range(6 if self.host.capacity_reads > 2 else 4))
        self.host.active_game_pids = capacity
        result = self.run_supervisor()
        self.assertEqual(1, self.host.launches)
        self.assertIn('exceeded five', result['error'])
        self.assertEqual([11, 22], [row['pid'] for row in self.host.force_stops])
        self.assertEqual([], self.host.observations)

    def test_evidence_outside_owned_project_is_refused_before_launch(self):
        with self.assertRaisesRegex(ValueError, 'inside its owned project'):
            supervisor.supervise(self.plan, self.host, self.root.parent / 'outside-owned-startup')
        self.assertEqual(0, self.host.launches)

    def test_preparation_failure_restores_bytes_without_launch(self):
        self.host.fault = 'prepare'
        result = self.run_supervisor()
        self.assertEqual(0, self.host.launches)
        self.assertIs(True, self.host.restored)
        self.assertIn('Preparation source changed', result['error'])

    def test_wrong_owner_and_protected_session_are_never_observed_or_stopped(self):
        for fault in ('wrong_owner', 'protected'):
            with self.subTest(fault=fault):
                self.host = FakeHost(self.root)
                self.host.fault = fault
                result = supervisor.supervise(self.plan, self.host, self.root / fault)
                self.assertIn('not the newly launched', result['error'])
                self.assertEqual([], self.host.observations)
                self.assertEqual([], self.host.force_stops)

    def test_identity_rebinding_stops_sampling_and_refuses_wrong_identity(self):
        self.host.fault = 'reused'
        self.host.mismatch = ['game']
        result = self.run_supervisor()
        self.assertIn('binding changed', result['error'])
        self.assertEqual([], self.host.force_stops)
        self.assertTrue(any('cleanup refused' in error for error in result['cleanup_errors']))

    def test_new_session_aliasing_protected_pid_is_never_observed_or_stopped(self):
        self.host.session['game_pid'] = 777
        result = self.run_supervisor()
        self.assertIn('protected process PID', result['error'])
        self.assertEqual([], self.host.observations)
        self.assertEqual([], self.host.force_stops)

    def test_hanging_launcher_is_stopped_before_owned_process_cleanup(self):
        self.host.launch_done_at = 1000
        result = self.run_supervisor()
        self.assertIs(True, self.host.launcher_stopped)
        self.assertIs(True, result['owned_processes_dead'])
        self.assertLessEqual(result['run_elapsed_seconds'], 150)

    def test_missing_manifest_still_stops_the_owned_launcher(self):
        self.host.publish_at = None
        self.host.launch_done_at = 1000
        result = self.run_supervisor()
        self.assertIs(True, self.host.launcher_stopped)
        self.assertEqual([], self.host.observations)
        self.assertEqual([], self.host.force_stops)
        self.assertTrue(any('cleanup remains unknown' in error for error in result['cleanup_errors']))
        self.assertIs(False, result['diagnostic_completed'])

    def test_graceful_close_does_not_force_stop(self):
        self.host.normal_closes = True
        result = self.run_supervisor()
        self.assertEqual([], self.host.force_stops)
        self.assertNotIn('force_stop_after_inspection', result)
        self.assertIs(True, result['owned_processes_dead'])

    def test_force_cleanup_carries_only_owned_pid_creation_pairs(self):
        result = self.run_supervisor()
        self.assertEqual([{'kind': 'game', 'pid': 11, 'identity': 'game-creation'},
                          {'kind': 'mcdk', 'pid': 22, 'identity': 'mcdk-creation'}], self.host.force_stops)
        self.assertEqual(self.host.force_stops, result['force_stop_after_inspection']['results'])

    def test_ready_state_does_not_implicitly_run_health_or_matrix(self):
        self.host.ready = True
        self.host.launch_done_at = 60
        result = self.run_supervisor()
        self.assertIs(True, result['launcher_ready'])
        self.assertIs(False, result['ready_health_started'])
        self.assertIs(False, result['matrix_started'])
        self.assertIs(False, result['production_acceptance'])

    def test_late_game_creation_leaves_unattempted_samples_explicit(self):
        self.host.game_created_at = 80
        result = self.run_supervisor()
        self.assertEqual([30, 45, 60, 75, 90, 105], result['samples_not_attempted'])
        self.assertLessEqual(result['run_elapsed_seconds'], 150)

    def test_restoration_failure_cannot_claim_completion(self):
        self.host.fault = 'restore'
        result = self.run_supervisor()
        self.assertIs(False, result['diagnostic_completed'])
        self.assertTrue(any('Restoration receipt failed' in error for error in result['cleanup_errors']))

    def test_existing_output_is_never_reused(self):
        target = self.root / 'fresh-run'
        target.mkdir()
        with self.assertRaisesRegex(ValueError, 'fresh'):
            self.run_supervisor()
        self.assertEqual(0, self.host.launches)


class StartupHostCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.host = supervisor.WindowsHost.__new__(supervisor.WindowsHost)
        self.host.handles, self.host.marker = [], None
        self.session = {'mcdk_pid': 22, 'mcdk_identity': 'owned-mcdk',
                        'game_executable': str(self.root / 'Minecraft.Windows.exe')}

    def test_unpublished_child_is_bound_for_cleanup_without_manifest_mutation(self):
        import observe_owned_startup
        current = {'alive': {'mcdk': {'pid': 22, 'identity': 'owned-mcdk'}}, 'mismatch': []}
        response = SimpleNamespace(returncode=0, stdout=b'11', stderr=b'')
        actual = {'identity': 'owned-game', 'executable': self.session['game_executable']}
        with mock.patch.object(self.host, 'inspect_owned', return_value=current), \
             mock.patch.object(supervisor.subprocess, 'run', return_value=response) as command, \
             mock.patch.object(observe_owned_startup, 'WindowsHost') as observer_host:
            observer_host.return_value.inspect_process.return_value = actual
            bound = self.host.complete_cleanup_binding(self.session)
        self.assertNotIn('game_pid', self.session)
        self.assertEqual(11, bound['game_pid'])
        self.assertEqual('owned-game', bound['game_identity'])
        self.assertIs(True, bound['unpublished_game_recovered_for_cleanup_only'])
        self.assertIn('ParentProcessId=22', command.call_args.args[0][-1])
        self.assertEqual(3, command.call_args.kwargs['timeout'])

    def test_reused_mcdk_does_not_enumerate_or_bind_children(self):
        with mock.patch.object(self.host, 'inspect_owned', return_value={'alive': {}, 'mismatch': ['mcdk']}), \
             mock.patch.object(supervisor.subprocess, 'run') as command:
            self.assertEqual(self.session, self.host.complete_cleanup_binding(self.session))
        command.assert_not_called()

    def test_ambiguous_or_wrong_executable_children_are_not_cleanup_targets(self):
        import observe_owned_startup
        current = {'alive': {'mcdk': {'pid': 22, 'identity': 'owned-mcdk'}}, 'mismatch': []}
        for stdout, expected in ((b'[11,12]', 'Multiple unpublished'), (b'11', 'executable is not')):
            with self.subTest(stdout=stdout), \
                 mock.patch.object(self.host, 'inspect_owned', return_value=current), \
                 mock.patch.object(supervisor.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=stdout)), \
                 mock.patch.object(observe_owned_startup, 'WindowsHost') as observer_host:
                observer_host.return_value.inspect_process.return_value = {'identity': 'creation',
                    'executable': str(self.root / 'another/Minecraft.Windows.exe')}
                with self.assertRaisesRegex(RuntimeError, expected):
                    self.host.complete_cleanup_binding(self.session)

    def test_marker_drift_retains_new_bytes_but_restores_other_owned_files(self):
        native = self.root / 'native.png'
        native.write_bytes(b'original native bytes')
        target = self.root / 'target.py'
        target.write_bytes(b'installed approved source')
        backup = self.root / 'backup.py'
        backup.write_bytes(b'original source')
        marker = self.root / 'flower_rose.png'
        marker.write_bytes(b'externally changed marker')
        self.host.marker = {'target': str(marker), 'before_hex': None, 'candidate_sha256': 'reviewed-candidate'}
        plan = {'files': {'native_texture': {'path': str(native), 'sha256': supervisor.sha(native)}}}
        report = {'marker_candidate_sha256': 'reviewed-candidate', 'backup': [
            {'target': str(target), 'backup': str(backup), 'sha256': supervisor.sha(backup),
             'installed_sha256': supervisor.sha(target)}]}
        with self.assertRaisesRegex(RuntimeError, 'Marker target changed'):
            self.host.restore(plan, self.root, report)
        self.assertEqual(b'externally changed marker', marker.read_bytes())
        self.assertEqual(b'original source', target.read_bytes())
        self.assertIs(True, report['backup'][0]['restored'])

    def test_external_runtime_source_edit_is_preserved(self):
        native = self.root / 'native.png'
        native.write_bytes(b'original native bytes')
        target = self.root / 'target.py'
        target.write_bytes(b'external user edit')
        backup = self.root / 'backup.py'
        backup.write_bytes(b'original source')
        plan = {'files': {'native_texture': {'path': str(native), 'sha256': supervisor.sha(native)}}}
        report = {'backup': [{'target': str(target), 'backup': str(backup),
                             'sha256': supervisor.sha(backup), 'installed_sha256': 'previous-installed-sha'}]}
        with self.assertRaisesRegex(RuntimeError, 'changed externally'):
            self.host.restore(plan, self.root, report)
        self.assertEqual(b'external user edit', target.read_bytes())


class StartupCaptureLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.host = supervisor.WindowsHost.__new__(supervisor.WindowsHost)
        source = supervisor.ROOT / 'tools/observe_owned_startup.py'
        dpi_source = supervisor.ROOT / 'tools/diagnose_window_dpi.py'
        self.helper = self.root / 'single-wgc.exe'
        self.helper.write_bytes(b'Offline fake helper; never executed')
        self.plan = {'owner': supervisor.OWNER, 'project': str(self.root), 'files': {
            'observer': {'path': str(source), 'sha256': supervisor.sha(source)},
            'dpi_helper': {'path': str(dpi_source), 'sha256': supervisor.sha(dpi_source)},
            'capture': {'path': str(self.helper)}}}
        self.session_file = self.root / 'session.json'
        self.session = {'schema': 1, 'id': 'owned-session', 'owner': supervisor.OWNER,
            'project': str(self.root), 'session_file': str(self.session_file), 'state': 'starting',
            'log': str(self.root / 'mcdk.log'), 'game_pid': 11, 'game_identity': 'owned-game',
            'mcdk_pid': 22, 'mcdk_identity': 'owned-mcdk',
            'game_executable': str(self.root / 'Minecraft.Windows.exe'),
            'noactivation': {'requested': True, 'mcdk': {'path': str(self.root / 'mcdk.exe')}}}
        self.session_file.write_text(json.dumps(self.session), encoding='utf8')

    def test_capture_timeout_kills_and_reaps_the_only_child_before_failed_receipt(self):
        observer = self.host.observer_adapter(self.plan)
        processes = {self.session[kind + '_pid']: {
            'identity': self.session[kind + '_identity'],
            'executable': self.session['game_executable'] if kind == 'game'
            else self.session['noactivation']['mcdk']['path']} for kind in ('game', 'mcdk')}
        guard = {'background_safe': True, 'window_noactivate': True, 'foreground': {'pid': 999},
            'windows': [{'hwnd': 600, 'pid': 11, 'process': 'Minecraft.Windows.exe',
                'width': 640, 'height': 360, 'noactivate': True, 'minimized': False}]}
        events = []
        child = mock.MagicMock()
        child.__enter__.return_value = child

        def communicate(*args, **kwargs):
            if kwargs.get('timeout') is not None:
                events.append('timeout')
                raise supervisor.subprocess.TimeoutExpired([str(self.helper)], kwargs['timeout'])
            events.append('reaped')
            return '', 'capture timed out'

        child.communicate.side_effect = communicate
        child.kill.side_effect = lambda: events.append('kill')
        output = self.root / 'timeout.png'
        with mock.patch.object(self.host, 'observer_adapter', return_value=observer), \
             mock.patch.object(observer, 'CAPTURE_EXECUTABLE', self.helper), \
             mock.patch.object(observer, 'CAPTURE_SHA256', supervisor.sha(self.helper)), \
             mock.patch.object(observer.WindowsHost, '__init__', return_value=None), \
             mock.patch.object(observer.WindowsHost, 'inspect_process', side_effect=processes.get), \
             mock.patch.object(observer.WindowsHost, 'guard', return_value=guard), \
             mock.patch.object(observer.WindowsHost, 'tcp_rows', return_value=[]), \
             mock.patch.object(supervisor.subprocess, '_mswindows', True), \
             mock.patch.object(supervisor.subprocess, 'Popen', return_value=child) as popen:
            result = self.host.observe(self.session, self.plan, output, 2)
        self.assertEqual(['timeout', 'kill', 'reaped'], events)
        child.kill.assert_called_once_with()
        self.assertEqual(2, child.communicate.call_count)
        child.communicate.assert_called_with()
        popen.assert_called_once()
        self.assertEqual([str(self.helper.resolve()), '600', '11', 'owned-game', str(output.resolve())],
                         popen.call_args.args[0])
        self.assertEqual(supervisor.subprocess.CREATE_NO_WINDOW, popen.call_args.kwargs['creationflags'])
        self.assertGreater(child.communicate.call_args_list[0].kwargs['timeout'], 0)
        self.assertLessEqual(child.communicate.call_args_list[0].kwargs['timeout'], 2)
        receipt = json.loads(output.with_suffix('.startup.json').read_bytes())
        self.assertIs(True, result['timeout'])
        self.assertEqual(1, result['returncode'])
        self.assertIs(True, result['observer_in_process'])
        self.assertIs(True, result['capture_child_direct'])
        self.assertEqual('physical_per_monitor_v2', result['window_geometry_space'])
        self.assertEqual(receipt, json.loads(result['stdout']))
        self.assertIs(False, receipt['ok'])
        self.assertIs(True, receipt['timeout'])
        self.assertIn('TimeoutExpired:', receipt['error'])
        self.assertIs(True, receipt['background_only'])
        self.assertIs(False, receipt['game_input_or_window_mutation_attempted'])
        self.assertIs(False, output.exists())

    def test_changed_reviewed_source_is_refused_without_any_child(self):
        self.plan['files']['observer']['sha256'] = 'changed-source'
        with mock.patch.object(supervisor.subprocess, 'Popen') as popen:
            result = self.host.observe(self.session, self.plan, self.root / 'refused.png', 2)
        popen.assert_not_called()
        self.assertEqual(1, result['returncode'])
        self.assertIs(False, result['timeout'])
        self.assertIn('Reviewed startup observer source changed', result['error'])

    def test_changed_physical_dpi_helper_is_refused_without_any_child(self):
        self.plan['files']['dpi_helper']['sha256'] = 'changed-dpi-helper'
        with mock.patch.object(supervisor.subprocess, 'Popen') as popen:
            result = self.host.observe(self.session, self.plan, self.root / 'refused-dpi.png', 2)
        popen.assert_not_called()
        self.assertEqual(1, result['returncode'])
        self.assertIn('Reviewed physical DPI helper source changed', result['error'])

    def test_guard_reads_physical_dimensions_then_restores_callers_context(self):
        observer = self.host.observer_adapter(self.plan)
        dpi = observer.dpi_geometry
        api = SimpleNamespace(context=123)
        api.current = lambda: api.context
        api.equal = lambda first, second: first == second
        def set_context(context):
            previous = api.context
            api.context = context
            return previous
        api.set = set_context
        def guard(pid, name):
            self.assertEqual(11, pid)
            self.assertEqual('Minecraft.Windows.exe', name)
            self.assertEqual(dpi.PER_MONITOR_V2, api.context)
            return {'windows': [{'width': 1994, 'height': 1105}]}
        host = observer.WindowsHost.__new__(observer.WindowsHost)
        host.window_api = SimpleNamespace(background_guard_state=guard)
        with mock.patch.object(dpi, 'DpiApi', return_value=api):
            result = host.guard(self.session)
        self.assertEqual([{'width': 1994, 'height': 1105}], result['windows'])
        self.assertEqual(123, api.context)

    def test_unavailable_physical_context_cannot_return_guard_geometry(self):
        observer = self.host.observer_adapter(self.plan)
        api = SimpleNamespace(current=lambda: 123, set=lambda context: None)
        host = observer.WindowsHost.__new__(observer.WindowsHost)
        host.window_api = SimpleNamespace(background_guard_state=mock.Mock())
        with mock.patch.object(observer.dpi_geometry, 'DpiApi', return_value=api):
            with self.assertRaisesRegex(RuntimeError, 'Could not enter physical'):
                host.guard(self.session)
        host.window_api.background_guard_state.assert_not_called()


class StartupLiveCapacityTests(unittest.TestCase):
    def setUp(self):
        self.host = supervisor.WindowsHost.__new__(supervisor.WindowsHost)
        self.host.identity = mock.Mock()
        self.host.terminate = mock.Mock()

    def candidates(self, rows):
        response = SimpleNamespace(returncode=0, stdout=json.dumps(rows).encode('utf8'), stderr=b'')
        return mock.patch.object(supervisor.subprocess, 'run', return_value=response)

    def test_terminated_cim_objects_are_retained_and_do_not_count_as_live(self):
        exited = [{'ProcessId': pid, 'ThreadCount': 0, 'HandleCount': 0,
                   'ExecutablePath': None, 'WorkingSetSize': 32768} for pid in range(100, 117)]
        live = [{'ProcessId': pid, 'ThreadCount': 68, 'HandleCount': 1200,
                 'ExecutablePath': 'Minecraft.Windows.exe', 'WorkingSetSize': 1000000000}
                for pid in (11, 22)]
        self.host.identity.side_effect = lambda pid: {11: 'game-11', 22: 'game-22'}.get(pid)
        with self.candidates(exited + live) as command:
            self.assertEqual([11, 22], self.host.active_game_pids())
        self.assertEqual([mock.call(row['ProcessId']) for row in exited + live], self.host.identity.call_args_list)
        self.assertEqual(list(range(100, 117)), self.host.capacity_evidence['excluded_pids'])
        self.assertEqual(19, len(self.host.capacity_evidence['rows']))
        self.assertEqual([], self.host.capacity_evidence['uncertain_pids'])
        self.assertIs(False, self.host.capacity_evidence['process_mutation_attempted'])
        self.host.terminate.assert_not_called()
        self.assertIn('ThreadCount,HandleCount,ExecutablePath', command.call_args.args[0][-1])

    def test_live_identity_counts_even_when_cim_fields_look_terminated(self):
        self.host.identity.return_value = 'verified-creation'
        with self.candidates([{'ProcessId': 11, 'ThreadCount': 0, 'HandleCount': 0, 'ExecutablePath': None}]):
            self.assertEqual([11], self.host.active_game_pids())
        self.assertEqual('verified_live', self.host.capacity_evidence['rows'][0]['status'])
        self.assertEqual('verified-creation', self.host.capacity_evidence['rows'][0]['identity'])

    def test_live_looking_or_missing_cim_fields_with_no_identity_refuse_capacity(self):
        self.host.identity.return_value = None
        for row in ({'ProcessId': 11, 'ThreadCount': 68, 'HandleCount': 1200, 'ExecutablePath': None},
                    {'ProcessId': 11}):
            with self.subTest(row=row), self.candidates([row]):
                with self.assertRaisesRegex(RuntimeError, 'capacity check refused'):
                    self.host.active_game_pids()
            self.assertEqual([11], self.host.capacity_evidence['uncertain_pids'])
            self.assertEqual([], self.host.capacity_evidence['excluded_pids'])
            self.assertEqual('uninspectable_or_uncertain', self.host.capacity_evidence['rows'][0]['status'])
        self.host.terminate.assert_not_called()

    def test_liveness_inspection_error_is_retained_and_refused(self):
        self.host.identity.side_effect = OSError('GetProcessTimes failed')
        with self.candidates([{'ProcessId': 11, 'ThreadCount': 0, 'HandleCount': 0, 'ExecutablePath': None}]):
            with self.assertRaisesRegex(RuntimeError, 'capacity check refused'):
                self.host.active_game_pids()
        self.assertEqual('GetProcessTimes failed', self.host.capacity_evidence['rows'][0]['inspection_error'])
        self.assertEqual([11], self.host.capacity_evidence['uncertain_pids'])
        self.host.terminate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
