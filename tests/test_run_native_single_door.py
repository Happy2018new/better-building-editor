"""Finite door supervision restores launch inputs and stops only bound identities."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import run_native_single_door as runner


class NativeSingleDoorSupervisorTests(unittest.TestCase):
    def supervised(self, launch_ready=True, probe_timeout=False, normal_stop_fails=False,
                   corrupt_receipt=False, emergency_fails=False, unpublished_game=False, external_edit=False,
                   missing_parent=False, launch_seconds=0, collision=False, partial_install=None,
                   lost_launch_reply=False, all_child_timeouts=False, launch_journal_failure=False):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder).resolve()
            project, shared, registry = base / '.runtime/door', base / 'shared', base / 'registry'
            scripts = project / '.agents/skills/pyreact-debugging/scripts'
            scripts.mkdir(parents=True)
            (project / 'tools').mkdir()
            registry.mkdir()
            session_path = registry / 'owned/session.json'
            session_path.parent.mkdir()
            original = b'original\r\n'
            used = b'approved\n'
            (scripts / 'instances.py').write_bytes(original)
            (scripts / 'mcdk.py').write_bytes(original)
            for path in (shared / '.agents/skills/pyreact-debugging/scripts/instances.py',
                         shared / '.agents/skills/pyreact-debugging/scripts/mcdk.py',
                         shared / '.runtime/r11-native/.mcdev.json',
                         shared / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe',
                         shared / '.runtime/worktree-archive-r7/p0-integration/files/.runtime/native_focus_guard-final-r7/native_focus_guard.dll',
                         project / 'tools/probe_native_single_door.py',
                         project / 'tools/native_single_door_load_preflight.py',
                         project / 'tools/capture_native_state_transform_shapes.py', scripts / '_session.py'):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(used)
            session = {'id': 'owned', 'name': 'test', 'owner': 'owner', 'project': str(project),
                       'session_file': str(session_path), 'ready': launch_ready,
                       'game_pid': 1, 'game_identity': '200', 'mcdk_pid': 2, 'mcdk_identity': '100',
                       'game_executable': str(project / 'Minecraft.Windows.exe'),
                       'noactivation': {'mcdk': {'path': str(shared / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe')}}}
            identities = {1: '200', 2: '100', 99: 'other-game'}
            if missing_parent:
                identities[2] = None
            if unpublished_game:
                del session['game_pid'], session['game_identity']
            if collision:
                session_path.write_bytes(json.dumps(session).encode('utf8'))
            prior_session_bytes = session_path.read_bytes() if collision else None
            prior_identities = identities.copy()
            commands = []
            now = [0.]
            launch_stdout = json.dumps(session, indent=2).replace('\n', '\r\n') + '\r\n'
            def bounded(command, timeout):
                self.assertGreater(timeout, 0)
                commands.append(command)
                response = {'returncode': 0, 'stdout': '', 'stderr': '', 'timeout': False}
                if command[0] == 'powershell':
                    response['stdout'] = '[99]'
                elif 'start' in command:
                    now[0] += launch_seconds
                    session_path.write_text(json.dumps(session), encoding='utf8')
                    (session_path.parent / '.mcdev.json').write_bytes(used)
                    response.update(returncode=0 if launch_ready else 1, stdout=launch_stdout,
                                    stdout_base64=base64.b64encode(launch_stdout.encode('utf8')).decode('ascii'))
                    if lost_launch_reply:
                        response.update(returncode=1, stdout='', stdout_base64='')
                    if external_edit:
                        (scripts / 'mcdk.py').write_bytes(b'external script edit')
                        (project / '.mcdev.json').write_bytes(b'external config edit')
                elif any('probe_native_single_door.py' in item for item in command):
                    output = Path(command[4])
                    output.write_text(json.dumps({'completed': not probe_timeout, 'restored': not probe_timeout,
                        'mutation_attempted': True, 'data_replication_verified': not probe_timeout,
                        'physical_orientation_accepted': False}), encoding='utf8')
                    if corrupt_receipt:
                        output.write_bytes(b'{partial')
                    response.update(returncode=1 if probe_timeout else 0, timeout=probe_timeout)
                elif '--cleanup-session' in command:
                    if emergency_fails:
                        raise RuntimeError('cleanup transport unavailable')
                    Path(command[-1]).write_text(json.dumps({'restored': True}), encoding='utf8')
                elif 'stop' in command:
                    self.assertEqual(str(session_path), command[command.index('--session') + 1])
                    self.assertEqual('owner', command[command.index('--owner') + 1])
                    if all_child_timeouts or normal_stop_fails and '--force' not in command:
                        response['returncode'] = 1
                    else:
                        identities[1] = identities[2] = None
                        session.update(state='stopped', ready=False)
                        session_path.write_text(json.dumps(session), encoding='utf8')
                if all_child_timeouts and command[0] != 'powershell' and 'start' not in command:
                    now[0] += timeout
                    response.update(returncode=-1, timeout=True)
                return response
            session_module = ModuleType('_session')
            session_module.registry_dir = lambda: registry
            session_module.process_identity = lambda pid: identities.get(pid)
            def terminate_owned(pid, identity):
                self.assertEqual(identity, identities[pid])
                identities[pid] = None
            session_module.terminate_owned = terminate_owned
            def inspect(pid):
                if not identities.get(pid):
                    return None
                return {'identity': identities[pid], 'executable': session['game_executable'] if pid == 1 else
                        session['noactivation']['mcdk']['path']}
            approved_sha = hashlib.sha256(used).hexdigest()
            original_copyfile = runner.shutil.copyfile
            original_save = runner.save
            failed_journal = [False]
            def save(path, report):
                if (launch_journal_failure and not failed_journal[0] and report['phases'] and
                        report['phases'][-1]['label'] == 'launch'):
                    failed_journal[0] = True
                    session_path.write_bytes(launch_stdout.encode('utf8'))
                    raise OSError('launch intent journal unavailable')
                return original_save(path, report)
            def copyfile(source, target):
                if (partial_install and Path(source).name.endswith('-used') and
                        Path(target) in (scripts / partial_install, project / partial_install)):
                    Path(target).write_bytes(b'owned partial copy')
                    raise OSError('launch input copy interrupted')
                return original_copyfile(source, target)
            with mock.patch.object(runner, 'ROOT', project), mock.patch.object(runner, 'SCRIPTS', scripts), \
                 mock.patch.object(runner, 'MCDK_SHA', approved_sha), mock.patch.object(runner, 'GUARD_SHA', approved_sha), \
                 mock.patch.object(runner, 'PROBE_SHA', approved_sha), \
                 mock.patch.object(runner, 'LOAD_PREFLIGHT_SHA', approved_sha), \
                 mock.patch.object(runner, 'SHAPE_HELPERS_SHA', approved_sha), \
                 mock.patch.object(runner, 'SESSION_LOADER_SHA', approved_sha), \
                 mock.patch.object(runner, 'COPY_HASHES', (approved_sha,) * 3), \
                 mock.patch.object(runner, 'bounded', side_effect=bounded), \
                 mock.patch.object(runner, 'save', side_effect=save), \
                 mock.patch.object(runner.shutil, 'copyfile', side_effect=copyfile), \
                 mock.patch.object(runner, 'inspect_process', side_effect=inspect), \
                 mock.patch.object(runner.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout=b'1')), \
                 mock.patch.object(runner.time, 'monotonic', side_effect=lambda: now[0]), \
                 mock.patch.dict(sys.modules, {'_session': session_module}):
                directory = project / '.runtime/run'
                code = runner.run(directory, shared, 'owner', 'test')
            report = json.loads((directory / 'supervisor.json').read_bytes())
            self.assertEqual(original, (scripts / 'instances.py').read_bytes())
            self.assertEqual(b'external script edit' if external_edit else original, (scripts / 'mcdk.py').read_bytes())
            if external_edit:
                self.assertEqual(b'external config edit', (project / '.mcdev.json').read_bytes())
            else:
                self.assertFalse((project / '.mcdev.json').exists())
            self.assertEqual('other-game', identities[99])
            self.assertEqual(not external_edit, all(row['restored'] for row in report['inputs']))
            if collision or partial_install or launch_journal_failure:
                self.assertEqual(0, report['launches'])
                self.assertEqual(['launch'] if launch_journal_failure else [],
                                 [row['label'] for row in report['phases']])
                self.assertFalse(any('start' in command or 'stop' in command for command in commands))
                self.assertEqual(prior_identities, identities)
                self.assertNotIn('session', report)
                if collision:
                    self.assertEqual(prior_session_bytes, session_path.read_bytes())
                if launch_journal_failure:
                    self.assertEqual(launch_stdout.encode('utf8'), session_path.read_bytes())
                return code, report
            if lost_launch_reply:
                self.assertFalse((directory / 'launch-original.json').exists())
            else:
                self.assertEqual(launch_stdout.encode('utf8'), (directory / 'launch-original.json').read_bytes())
            self.assertEqual(not (all_child_timeouts or unpublished_game and missing_parent),
                             report['owned_processes_absent'])
            self.assertEqual(1, sum('start' in command for command in commands))
            self.assertEqual('120', next(command for command in commands if 'start' in command)[-1])
            for command in commands:
                if '--work-seconds' in command:
                    self.assertGreaterEqual(float(command[-1]), runner.PROBE_WORK_SECONDS)
            return code, report

    def test_preexisting_owner_name_collision_never_launches_or_stops_prior_session(self):
        code, report = self.supervised(collision=True)
        self.assertEqual(1, code)
        self.assertIn('requires a fresh session', report['error'])
        self.assertEqual('owned', report['registry_before'][0]['id'])
        self.assertEqual([], report['cleanup_errors'])

    def test_partial_install_restores_existing_and_absent_inputs_without_launch(self):
        for target in ('instances.py', '.mcdev.json'):
            with self.subTest(target=target):
                code, report = self.supervised(partial_install=target)
                self.assertEqual(1, code)
                self.assertIn('launch input copy interrupted', report['error'])
                self.assertEqual([], report['cleanup_errors'])
                row = report['inputs'][-1]
                self.assertTrue(row['installation_attempted'])
                self.assertTrue(row['owned_target_observed'])
                self.assertFalse(row['installed'])
                self.assertTrue(row['restored'])

    def test_failed_launch_intent_journal_does_not_claim_attempt_or_recover_new_session(self):
        code, report = self.supervised(launch_journal_failure=True)
        self.assertEqual(1, code)
        self.assertIn('launch intent journal unavailable', report['error'])
        self.assertEqual([], report['cleanup_errors'])

    def test_lost_launch_reply_recovers_only_new_owned_registry_session(self):
        code, report = self.supervised(lost_launch_reply=True)
        self.assertEqual(1, code)
        self.assertEqual(1, report['launches'])
        self.assertTrue(report['session_recovered_after_launch_attempt'])
        self.assertEqual(['launch', 'normal_stop'], [row['label'] for row in report['phases']])
        self.assertEqual([], report['registry_before'])

    def test_all_cleanup_child_timeouts_do_not_add_reap_wait_beyond_total_budget(self):
        code, report = self.supervised(launch_seconds=87, probe_timeout=True, all_child_timeouts=True)
        self.assertEqual(1, code)
        self.assertEqual(['launch', 'probe', 'emergency_cleanup', 'normal_stop', 'force_stop'],
                         [row['label'] for row in report['phases']])
        self.assertEqual(232, report['elapsed_seconds'])
        self.assertTrue(report['within_total_limit'])
        self.assertFalse(report['owned_processes_absent'])
        self.assertEqual(3, report['child_reap_reserve_seconds'])

    def test_registry_recovery_excludes_prior_paths_and_prior_ids_and_refuses_ambiguity(self):
        with tempfile.TemporaryDirectory() as folder:
            registry = Path(folder).resolve()
            def store(directory, session_id):
                path = registry / directory / 'session.json'
                path.parent.mkdir()
                data = {'id': session_id, 'name': 'test', 'owner': 'owner', 'project': str(runner.ROOT)}
                path.write_text(json.dumps(data), encoding='utf8')
                return path, data
            prior_path, _ = store('old-file', 'changed-id')
            store('new-file-old-id', 'prior-id')
            paths, ids = {prior_path.resolve()}, {'prior-id'}
            self.assertIsNone(runner.recover_new_session(registry, 'owner', 'test', paths, ids))
            _, owned = store('new-owned', 'new-id')
            self.assertEqual(owned, runner.recover_new_session(registry, 'owner', 'test', paths, ids))
            store('other-new-owned', 'second-new-id')
            with self.assertRaisesRegex(ValueError, 'Multiple new owned session candidates'):
                runner.recover_new_session(registry, 'owner', 'test', paths, ids)

    def test_failed_readiness_never_runs_probe_and_restores_absent_config(self):
        code, report = self.supervised(launch_ready=False)
        self.assertEqual(1, code)
        self.assertEqual(['launch', 'normal_stop'], [row['label'] for row in report['phases']])
        self.assertFalse(report['diagnosis']['mutation_attempted'])

    def test_probe_timeout_preserves_failure_and_attempts_cleanup_before_owned_force_stop(self):
        code, report = self.supervised(probe_timeout=True, normal_stop_fails=True)
        self.assertEqual(1, code)
        self.assertEqual(['launch', 'probe', 'emergency_cleanup', 'normal_stop', 'force_stop'],
                         [row['label'] for row in report['phases']])
        self.assertEqual(['game', 'mcdk'], report['inspected_live_owned_kinds'])
        self.assertFalse(report['ok'])
        self.assertFalse(report['diagnosis']['physical_orientation_accepted'])

    def test_success_remains_replication_only_and_stops_its_session(self):
        code, report = self.supervised()
        self.assertEqual(0, code)
        self.assertTrue(report['ok'])
        self.assertEqual(240, report['total_limit_seconds'])
        self.assertEqual(200, report['work_limit_seconds'])
        self.assertFalse(report['physical_orientation_accepted'])
        self.assertTrue(report['diagnosis']['data_replication_verified'])

    def test_late_launch_cannot_consume_required_full_probe_cleanup_reserve(self):
        code, report = self.supervised(launch_seconds=130)
        self.assertEqual(1, code)
        self.assertEqual(['launch', 'normal_stop'], [row['label'] for row in report['phases']])
        self.assertIn('Insufficient full load/fixture/cleanup reserve', report['error'])
        self.assertFalse(report['diagnosis']['mutation_attempted'])
        self.assertEqual(65, report['probe_work_seconds'])

    def test_probe_start_and_child_reap_reserves_fit_complete_minimum_probe_work(self):
        code, report = self.supervised(launch_seconds=123)
        self.assertEqual(0, code)
        self.assertEqual(72, report['probe_work_seconds'])
        phase = next(row for row in report['phases'] if row['label'] == 'probe')
        self.assertEqual(77, phase['timeout_seconds'])
        self.assertEqual(phase['timeout_seconds'], report['probe_work_seconds'] +
                         runner.PROBE_START_RESERVE_SECONDS + runner.CHILD_REAP_RESERVE_SECONDS)

    def test_corrupt_probe_receipt_cannot_skip_owned_stop(self):
        code, report = self.supervised(corrupt_receipt=True)
        self.assertEqual(1, code)
        self.assertEqual(['launch', 'probe', 'emergency_cleanup', 'normal_stop'],
                         [row['label'] for row in report['phases']])
        self.assertTrue(any('Diagnostic receipt' in error for error in report['cleanup_errors']))

    def test_emergency_cleanup_failure_cannot_skip_owned_force_stop(self):
        code, report = self.supervised(probe_timeout=True, normal_stop_fails=True, emergency_fails=True)
        self.assertEqual(1, code)
        self.assertEqual(['launch', 'probe', 'emergency_cleanup', 'normal_stop', 'force_stop'],
                         [row['label'] for row in report['phases']])
        self.assertTrue(any('Emergency fixture cleanup' in error for error in report['cleanup_errors']))

    def test_unpublished_game_is_stopped_with_recovered_identity_only(self):
        code, report = self.supervised(launch_ready=False, normal_stop_fails=True, unpublished_game=True)
        self.assertEqual(1, code)
        self.assertTrue(report['session']['unpublished_game_recovered_for_cleanup_only'])
        self.assertEqual((1, '200'), (report['session']['game_pid'], report['session']['game_identity']))
        self.assertEqual(['game', 'mcdk'], [row['kind'] for row in report['recovered_force_stop']])
        self.assertEqual([], report['cleanup_errors'])

    def test_external_input_edits_are_retained_and_restoration_refusals_recorded(self):
        code, report = self.supervised(launch_ready=False, external_edit=True)
        self.assertEqual(1, code)
        self.assertEqual(2, len(report['cleanup_errors']))
        self.assertEqual(2, sum('restoration_refused' in row for row in report['inputs']))

    def test_missing_unpublished_parent_cannot_certify_owned_process_absence(self):
        code, report = self.supervised(launch_ready=False, unpublished_game=True, missing_parent=True)
        self.assertEqual(1, code)
        self.assertFalse(report['owned_processes_absent'])
        self.assertTrue(any('binding unresolved' in error for error in report['cleanup_errors']))

    def test_cleanup_recovery_refuses_reused_parent_wrong_path_and_multiple_live_children(self):
        session = {'mcdk_pid': 2, 'mcdk_identity': '100', 'game_executable': str(Path('game.exe').resolve()),
                   'noactivation': {'mcdk': {'path': str(Path('mcdk.exe').resolve())}}}
        parent = {'identity': '100', 'executable': session['noactivation']['mcdk']['path']}
        with mock.patch.object(runner, 'inspect_process', return_value=dict(parent, identity='101')), \
             mock.patch.object(runner.subprocess, 'run') as query:
            self.assertEqual(session, runner.complete_cleanup_binding(session))
            query.assert_not_called()
        for candidates, actual, message in ((b'1', {'identity': '200', 'executable': 'wrong.exe'}, 'path/creation'),
                (b'[1,3]', {'identity': '200', 'executable': session['game_executable']}, 'Multiple live')):
            with self.subTest(message=message), \
                 mock.patch.object(runner.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout=candidates)), \
                 mock.patch.object(runner, 'inspect_process', side_effect=lambda pid: parent if pid == 2 else actual):
                with self.assertRaisesRegex(RuntimeError, message):
                    runner.complete_cleanup_binding(session)

    def test_dead_cim_child_entries_cannot_make_cleanup_binding_ambiguous(self):
        session = {'mcdk_pid': 2, 'mcdk_identity': '100', 'game_executable': str(Path('game.exe').resolve()),
                   'noactivation': {'mcdk': {'path': str(Path('mcdk.exe').resolve())}}}
        values = {2: {'identity': '100', 'executable': session['noactivation']['mcdk']['path']},
                  1: {'identity': '200', 'executable': session['game_executable']}}
        with mock.patch.object(runner.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout=b'[1,19]')) as query, \
             mock.patch.object(runner, 'inspect_process', side_effect=values.get):
            recovered = runner.complete_cleanup_binding(session)
        self.assertEqual(1, recovered['game_pid'])
        self.assertNotIn('game_pid', session)
        self.assertIn('ParentProcessId=2', query.call_args.args[0][-1])
        self.assertEqual(3, query.call_args.kwargs['timeout'])

    def test_bounded_capture_preserves_exact_stdout_and_stderr_bytes(self):
        result = runner.bounded([sys.executable, '-c',
            "import os; os.write(1, b'{\"ready\":false}\\r\\n'); os.write(2, b'error\\r\\n')"], 5)
        self.assertEqual(0, result['returncode'])
        self.assertEqual(b'{"ready":false}\r\n', base64.b64decode(result['stdout_base64']))
        self.assertEqual(b'error\r\n', base64.b64decode(result['stderr_base64']))
        self.assertEqual('{"ready":false}\r\n', result['stdout'])

    def test_bounded_child_reap_uses_remaining_absolute_phase_budget(self):
        now = [0.]
        process = mock.Mock(returncode=-1)
        waits = []
        def communicate(timeout):
            waits.append(timeout)
            now[0] += timeout
            if len(waits) == 1:
                raise runner.subprocess.TimeoutExpired(['child'], timeout)
            return b'partial output', b'error'
        process.communicate.side_effect = communicate
        def spawn(*args, **kwargs):
            now[0] += 1
            return process
        with mock.patch.object(runner.subprocess, 'Popen', side_effect=spawn), \
             mock.patch.object(runner.time, 'monotonic', side_effect=lambda: now[0]):
            result = runner.bounded(['child'], 8)
        self.assertEqual([4, 3], waits)
        self.assertEqual(8, now[0])
        process.kill.assert_called_once_with()
        self.assertTrue(result['timeout'])
        self.assertEqual(b'partial output', base64.b64decode(result['stdout_base64']))

    def test_child_not_spawned_without_full_reap_reserve(self):
        with mock.patch.object(runner.subprocess, 'Popen') as spawn:
            with self.assertRaisesRegex(TimeoutError, 'termination/reap reserve'):
                runner.bounded(['child'], runner.CHILD_REAP_RESERVE_SECONDS)
        spawn.assert_not_called()


class LaunchInputOwnershipTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.target = self.directory / 'target.py'
        self.used = self.directory / 'used.py'
        self.original = self.directory / 'original.py'
        self.used.write_bytes(b'approved bytes')
        self.original.write_bytes(b'original bytes')
        self.target.write_bytes(self.original.read_bytes())
        self.row = {'target': str(self.target), 'used': str(self.used), 'original': str(self.original),
                    'originally_present': True, 'used_sha256': runner.sha(self.used),
                    'original_sha256': runner.sha(self.original)}
        self.journal = []

    def progress(self):
        self.journal.append(self.row.copy())

    def partial(self, source, target):
        Path(target).write_bytes(b'owned partial')
        raise OSError('copy interrupted')

    def test_partial_copy_journals_intent_before_mutation_and_restores_exact_bytes(self):
        with mock.patch.object(runner.shutil, 'copyfile', side_effect=self.partial):
            with self.assertRaisesRegex(OSError, 'copy interrupted'):
                runner.install_input(self.row, self.progress)
        self.assertTrue(self.journal[0]['installation_attempted'])
        self.assertFalse(self.journal[0]['owned_target_observed'])
        self.assertTrue(self.journal[-1]['owned_target_observed'])
        self.assertFalse(self.row['installed'])
        self.assertEqual([], runner.restore_inputs([self.row]))
        self.assertEqual(b'original bytes', self.target.read_bytes())

    def test_failed_owned_snapshot_preserves_copy_error_and_refuses_restoration(self):
        with mock.patch.object(runner.shutil, 'copyfile', side_effect=self.partial), \
             mock.patch.object(runner, 'snapshot_sha', side_effect=OSError('snapshot unreadable')):
            with self.assertRaisesRegex(OSError, 'copy interrupted'):
                runner.install_input(self.row, self.progress)
        self.assertIn('snapshot unreadable', self.row['target_observation_error'])
        self.assertIn('copy interrupted', self.row['installation_error'])
        errors = runner.restore_inputs([self.row])
        self.assertIn('could not be observed', errors[0])
        self.assertFalse(self.row['restored'])
        self.assertEqual(b'owned partial', self.target.read_bytes())

    def test_external_drift_after_partial_copy_is_preserved(self):
        with mock.patch.object(runner.shutil, 'copyfile', side_effect=self.partial):
            with self.assertRaises(OSError):
                runner.install_input(self.row, self.progress)
        self.target.write_bytes(b'external edit')
        errors = runner.restore_inputs([self.row])
        self.assertIn('changed externally', errors[0])
        self.assertFalse(self.row['restored'])
        self.assertEqual(b'external edit', self.target.read_bytes())

    def test_failed_copy_with_observed_absence_restores_original(self):
        def removed(source, target):
            Path(target).unlink()
            raise OSError('copy removed target')
        with mock.patch.object(runner.shutil, 'copyfile', side_effect=removed):
            with self.assertRaises(OSError):
                runner.install_input(self.row, self.progress)
        self.assertIsNone(self.row['owned_target_sha256'])
        self.assertTrue(self.row['owned_target_observed'])
        self.assertEqual([], runner.restore_inputs([self.row]))
        self.assertEqual(b'original bytes', self.target.read_bytes())

    def test_staged_hash_drift_cannot_mutate_target(self):
        self.used.write_bytes(b'changed shared source staged after initial check')
        with mock.patch.object(runner.shutil, 'copyfile') as copyfile:
            with self.assertRaisesRegex(ValueError, 'Staged approved source hash changed'):
                runner.install_input(self.row, self.progress)
        copyfile.assert_not_called()
        self.assertNotIn('installation_attempted', self.row)
        self.assertEqual([], runner.restore_inputs([self.row]))
        self.assertEqual(b'original bytes', self.target.read_bytes())


if __name__ == '__main__':
    unittest.main()
