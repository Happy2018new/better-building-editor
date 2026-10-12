"""Offline fault checks for the owner-bound native burst wrapper."""
import copy
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import capture_native_burst as burst


def png_bytes(width=4, height=3, blank=False):
    image = Image.new('RGB', (width, height))
    if not blank:
        image.putdata([(0, 20, 40) if (x + y) % 2 else (240, 180, 100)
                       for y in range(height) for x in range(width)])
    output = BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


class FakeHelper:
    def __init__(self, command, emit, *, returncode=0, timeout=False):
        self.pid = 987
        self.returncode = None
        self.result_code = returncode
        self.timeout = timeout
        self.killed = False
        self.communicate_timeouts = []
        self.stdout = emit(Path(command[4]))

    def communicate(self, timeout):
        self.communicate_timeouts.append(timeout)
        if self.timeout and not self.killed:
            raise subprocess.TimeoutExpired('owned-helper', timeout, output=b'partial stdout')
        self.returncode = -9 if self.killed else self.result_code
        return self.stdout, b''

    def kill(self):
        self.killed = True
        self.returncode = -9

    def poll(self):
        return self.returncode

    def wait(self, timeout):
        self.returncode = -9 if self.killed else self.result_code
        return self.returncode


class NativeBurstWrapperTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.output = self.root / 'burst'
        self.session_file = self.root / 'session.json'
        self.session_file.write_text('{}', encoding='ascii')
        self.executable = self.root / 'burst.exe'
        self.executable.write_bytes(b'test helper; never executed')
        self.expected = burst.sha256(self.executable)
        self.protection_file = self.root / 'guard.dll'
        self.protection_file.write_bytes(b'test protected launch binary')
        binary = {'path': str(self.protection_file), 'sha256': burst.sha256(self.protection_file)}
        self.session = {'schema': 1, 'id': 'owned-instance', 'owner': 'assigned-owner', 'state': 'ready',
                        'session_file': str(self.session_file), 'project': str(ROOT),
                        'game_pid': 123, 'game_identity': '456', 'mcdk_pid': 124, 'mcdk_identity': '457',
                        'game_executable': 'Minecraft.Windows.exe', 'mcp_url': 'http://localhost:1/mcp',
                        'noactivation': {'schema': 1, 'requested': True, 'background_safe': True,
                                         'window_noactivate': True, 'mcdk': binary, 'dll': binary}}
        self.window = {'hwnd': 42, 'pid': 123, 'process': 'Minecraft.Windows.exe', 'title': 'Game',
                       'x': 10, 'y': 20, 'width': 4, 'height': 3, 'minimized': False, 'noactivate': True}
        self.guard = {'background_safe': True, 'window_noactivate': True,
                      'foreground': {'hwnd': 99, 'pid': 900}, 'windows': [self.window]}
        self.helper = None
        self.manifest = self.make_manifest()
        self.emit = self.emit_manifest
        self.result_code = 0
        self.timeout = False
        self.start_patch('load_session', return_value=copy.deepcopy(self.session))
        self.start_patch('background_guard_state', return_value=copy.deepcopy(self.guard))
        self.start_patch('_physical_dpi_context', return_value=mock.MagicMock())
        self.popen = self.start_patch('subprocess.Popen', side_effect=self.popen_factory)

    def start_patch(self, name, **kwargs):
        patcher = mock.patch('capture_native_burst.' + name, **kwargs)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def popen_factory(self, command, **kwargs):
        self.helper = FakeHelper(command, self.emit, returncode=self.result_code, timeout=self.timeout)
        return self.helper

    def state(self, observed):
        return {'hwnd': 42, 'pid': 123, 'thread_id': 7, 'creation_time': '456', 'process_live': True,
                'window_valid': True, 'visible': True, 'minimized': False, 'cloaked': False,
                'geometry_valid': True, 'client_rect_screen': [10, 20, 14, 23],
                'dwm_frame_rect': [8, 18, 16, 25], 'foreground_hwnd': 99, 'foreground_pid': 900,
                'extended_style': burst.NOACTIVATE, 'window_noactivate_style': True,
                'observed_qpc_100ns': observed}

    def frame(self, sequence, timestamp, observed, delta):
        after = self.state(observed + 3)
        return {'schema': 1, 'sequence': sequence, 'receipt': 'frame_%06d.capture.json' % sequence,
                'capture_valid': True, 'timestamp_available': True, 'request_qpc_100ns': 1000000,
                'frame_qpc_100ns': timestamp, 'observed_qpc_100ns': observed,
                'frame_age_100ns': observed - timestamp, 'delta_from_previous_or_request_100ns': delta,
                'gap_exceeded': False, 'png': 'frame_%06d.png' % sequence, 'width': 4, 'height': 3,
                'error': '', 'before': self.state(observed - 1), 'after_readback': self.state(observed + 1),
                'before_png_write': self.state(observed + 2), 'after_png_write': after,
                'last_window_state': copy.deepcopy(after)}

    def make_manifest(self):
        return {'schema': 1, 'backend': 'Windows.Graphics.Capture', 'mode': 'persistent_burst',
                'clock': 'compositor_system_relative_qpc_100ns', 'background_only': True,
                'activation_fallback': False, 'native_resolution': True, 'pixel_acceptance': False,
                'ok': True, 'capture_valid': True, 'temporal_complete': True, 'owned_hwnd': 42,
                'owned_pid': 123, 'owned_creation_time': '456', 'planned_duration_ms': 100,
                'max_frames': 10, 'max_gap_ms': 40, 'max_frame_age_ms': 1000,
                'request_qpc_100ns': 1000000, 'planned_end_qpc_100ns': 2000000,
                'finished_qpc_100ns': 2000200, 'attempted_frames': 3, 'valid_frames': 3,
                'rejected_frames': 0, 'frame_arrival_events': 3, 'source_frame_loss_known': False,
                'first_frame_qpc_100ns': 1250000, 'last_frame_qpc_100ns': 1750000,
                'start_gap_100ns': 250000, 'tail_gap_100ns': 250000, 'tail_gap_exceeded': False,
                'maximum_gap_100ns': 250000, 'stop_reason': 'duration_elapsed', 'error': '',
                'baseline': self.state(999990), 'final_window_state': self.state(2000100),
                'frames': [self.frame(sequence, timestamp, timestamp + 100, 250000)
                           for sequence, timestamp in enumerate((1250000, 1500000, 1750000), 1)]}

    def emit_manifest(self, output):
        output.mkdir()
        for frame in self.manifest['frames']:
            (output / frame['receipt']).write_text(json.dumps(frame), encoding='ascii')
            if frame['png']:
                (output / frame['png']).write_bytes(png_bytes())
        raw = json.dumps(self.manifest).encode('ascii')
        (output / 'manifest.json').write_bytes(raw)
        return raw

    def capture(self, **kwargs):
        return burst.capture(self.session_file, 'assigned-owner', self.output, self.executable,
                             kwargs.pop('expected_sha256', self.expected),
                             kwargs.pop('duration_ms', 100), kwargs.pop('max_frames', 10),
                             kwargs.pop('max_gap_ms', 40), **kwargs)

    def failure(self, pattern, **kwargs):
        with self.assertRaisesRegex(burst.CaptureError, pattern) as caught:
            self.capture(**kwargs)
        report = caught.exception.report
        saved = json.loads((self.root / 'burst.capture.json').read_bytes())
        self.assertEqual(report, saved)
        self.assertFalse(report['ok'])
        self.assertFalse(report['capture_valid'])
        self.assertFalse(report['temporal_complete'])
        self.assertFalse(report['animation_acceptance'])
        return report

    def test_valid_burst_binds_each_png_and_receipt_without_animation_claim(self):
        report = self.capture()
        self.assertTrue(report['ok'])
        self.assertTrue(report['temporal_complete'])
        self.assertFalse(report['animation_acceptance'])
        self.assertFalse(report['source_frame_loss_known'])
        self.assertEqual(3, len(report['frames']))
        for frame in report['frames']:
            self.assertEqual(burst.sha256(Path(frame['png']['path'])), frame['png']['sha256'])
            self.assertEqual(burst.sha256(Path(frame['receipt']['path'])), frame['receipt']['sha256'])
        self.assertEqual([15.1], self.helper.communicate_timeouts)
        self.assertFalse(self.helper.killed)
        compact = burst.summary(report)
        self.assertNotIn('frames', compact)
        self.assertNotIn('native_manifest', compact)
        self.assertEqual(3, compact['valid_frames'])

    def test_timeout_kills_only_owned_helper_and_preserves_partial_output(self):
        def partial(output):
            output.mkdir()
            (output / 'frame_000001.png').write_bytes(png_bytes())
            (output / 'frame_000001.capture.json').write_text(json.dumps(self.manifest['frames'][0]),
                                                           encoding='ascii')
            return b'partial stdout'
        self.emit = partial
        self.timeout = True
        report = self.failure(r'duration \+ 15 second')
        self.assertTrue(self.helper.killed)
        self.assertEqual([15.1, 5], self.helper.communicate_timeouts)
        self.assertTrue(report['helper_timed_out'])
        self.assertTrue(report['own_helper_terminated'])
        self.assertEqual(2, len(report['artifacts']))
        self.assertTrue((self.output / 'frame_000001.png').is_file())
        self.popen.assert_called_once()
        self.assertIn('background_final', report)
        self.assertEqual('partial stdout', report['helper_stdout']['text'])

    def test_rejected_old_and_postinterval_frames_keep_one_to_one_receipts(self):
        old = self.frame(1, 1000000, 1000100, 0)
        old.update(capture_valid=False, png=None, error='frame_not_after_request')
        old.update({key: {} for key in ('after_readback', 'before_png_write', 'after_png_write')})
        records = [old]
        for sequence, frame in enumerate(self.manifest['frames'], 2):
            frame.update(sequence=sequence, receipt='frame_%06d.capture.json' % sequence,
                         png='frame_%06d.png' % sequence)
            records.append(frame)
        post = self.frame(5, 2000010, 2000020, 250010)
        post.update(capture_valid=False, png=None, error='frame_after_planned_interval')
        post.update({key: {} for key in ('after_readback', 'before_png_write', 'after_png_write')})
        records.append(post)
        self.manifest.update(frames=records, attempted_frames=5, rejected_frames=2, frame_arrival_events=5)
        report = self.capture()
        self.assertEqual(5, len(report['frames']))
        self.assertIsNone(report['frames'][0]['png'])
        self.assertIsNone(report['frames'][-1]['png'])
        self.assertEqual(3, report['validated_timeline']['valid_frames'])
        self.assertEqual(2, report['validated_timeline']['rejected_frames'])

    def test_incorrect_or_missing_helper_hash_fails_before_execution(self):
        for expected in ('0' * 64, None, 'abcd'):
            with self.subTest(expected=expected):
                self.output = self.root / ('bad-hash-' + str(expected))
                with self.assertRaises(burst.CaptureError) as caught:
                    self.capture(expected_sha256=expected)
                self.assertFalse(caught.exception.report['ok'])
        self.popen.assert_not_called()

    def test_owner_process_project_and_session_changes_invalidate_evidence(self):
        for field, value in (('owner', 'another-owner'), ('game_identity', '999'),
                             ('game_pid', 222), ('mcdk_identity', '998'), ('id', 'replaced'),
                             ('project', str(self.root)), ('session_file', str(self.executable))):
            with self.subTest(field=field):
                self.output = self.root / ('changed-' + field)
                changed = copy.deepcopy(self.session)
                changed[field] = value
                with mock.patch.object(burst, 'load_session', side_effect=[self.session, changed, changed]):
                    with self.assertRaises(burst.CaptureError) as caught:
                        self.capture()
                self.assertFalse(caught.exception.report['ok'])
                self.assertIn('postflight', {error['phase'] for error in caught.exception.report['errors']})

    def test_manifest_individual_receipt_mismatch_is_rejected(self):
        original = self.emit
        def mismatch(output):
            raw = original(output)
            receipt = copy.deepcopy(self.manifest['frames'][1])
            receipt['frame_qpc_100ns'] += 1
            (output / receipt['receipt']).write_text(json.dumps(receipt), encoding='ascii')
            return raw
        self.emit = mismatch
        self.failure('Manifest/individual receipt mismatch')

    def test_rejected_timestamp_still_requires_background_window_guards(self):
        frame = self.frame(4, 2000010, 2000020, 250010)
        frame.update(capture_valid=False, png=None, error='frame_after_planned_interval')
        frame['last_window_state']['foreground_pid'] = 123
        self.manifest['frames'].append(frame)
        self.manifest.update(attempted_frames=4, rejected_frames=1, frame_arrival_events=4)
        self.failure('Native guard observed foreground game')

    def test_nested_json_type_drift_is_a_receipt_mismatch(self):
        original = self.emit
        def mismatch(output):
            raw = original(output)
            receipt = copy.deepcopy(self.manifest['frames'][0])
            receipt['before']['pid'] = 123.0
            (output / receipt['receipt']).write_text(json.dumps(receipt), encoding='ascii')
            return raw
        self.emit = mismatch
        self.failure('Manifest/individual receipt.*mismatch')

    def test_background_foreground_noactivate_and_geometry_loss_are_rejected(self):
        for kind in ('foreground', 'noactivate', 'geometry', 'minimized'):
            with self.subTest(kind=kind):
                self.output = self.root / ('background-' + kind)
                changed = copy.deepcopy(self.guard)
                if kind == 'foreground':
                    changed['foreground']['pid'] = 123
                elif kind == 'noactivate':
                    changed['windows'][0]['noactivate'] = False
                elif kind == 'geometry':
                    changed['windows'][0]['width'] = 5
                else:
                    changed['windows'][0]['minimized'] = True
                with mock.patch.object(burst, 'background_guard_state',
                                       side_effect=[self.guard, changed, changed]):
                    with self.assertRaises(burst.CaptureError) as caught:
                        self.capture()
                self.assertFalse(caught.exception.report['ok'])
                self.assertTrue((self.output / 'manifest.json').exists())
                self.assertEqual(changed, caught.exception.report['background_after'])
                compact = burst.summary(caught.exception.report)
                self.assertFalse(compact['temporal_complete'])
                self.assertTrue(compact['validated_timeline_temporal_complete'])

    def test_unprotected_session_and_changed_launch_binary_fail_before_execution(self):
        changed = copy.deepcopy(self.session)
        changed['noactivation']['window_noactivate'] = False
        with mock.patch.object(burst, 'load_session', return_value=changed):
            self.failure('protected background session')
        self.output = self.root / 'changed-guard'
        self.protection_file.write_bytes(b'changed guard binary')
        with self.assertRaisesRegex(burst.CaptureError, 'Binary SHA256 mismatch'):
            self.capture()
        self.popen.assert_not_called()

    def test_code_two_and_false_completeness_cannot_be_accepted(self):
        self.result_code = 2
        self.failure('exited with code 2')
        self.output = self.root / 'incomplete'
        self.result_code = 0
        self.manifest['temporal_complete'] = False
        self.manifest['stop_reason'] = 'frame_cap_before_duration'
        with self.assertRaisesRegex(burst.CaptureError, 'Native completion'):
            self.capture()

    def test_helper_hash_change_during_capture_is_a_failed_receipt(self):
        original = self.emit
        def changed(output):
            raw = original(output)
            self.executable.write_bytes(b'changed binary after launch')
            return raw
        self.emit = changed
        self.failure('Binary SHA256 mismatch')

    def test_final_artifact_hash_change_after_png_validation_is_rejected(self):
        original = burst._validate_native
        def tampered(*args):
            original(*args)
            (self.output / 'frame_000001.png').write_bytes(png_bytes() + b'changed after validation')
        with mock.patch.object(burst, '_validate_native', side_effect=tampered):
            self.failure('Final artifact SHA256 binding mismatch')

    def test_native_window_guard_loss_is_rejected_even_if_host_guard_stays_safe(self):
        self.manifest['frames'][1]['after_png_write']['window_noactivate_style'] = False
        self.failure('Native window window_noactivate_style mismatch')

    def test_actual_png_pixels_and_dimensions_override_successful_native_flags(self):
        original = self.emit
        for kind in ('blank', 'dimension', 'not_png', 'trailing_data'):
            with self.subTest(kind=kind):
                self.output = self.root / ('png-' + kind)
                def invalid_png(output):
                    raw = original(output)
                    payload = (png_bytes(blank=True) if kind == 'blank' else
                               png_bytes(width=5) if kind == 'dimension' else
                               b'not a PNG' if kind == 'not_png' else png_bytes() + b'trailing')
                    (output / 'frame_000001.png').write_bytes(payload)
                    return raw
                self.emit = invalid_png
                with self.assertRaises(burst.CaptureError) as caught:
                    self.capture()
                self.assertFalse(caught.exception.report['ok'])
                self.assertIn('native_evidence', {error['phase'] for error in caught.exception.report['errors']})

    def test_extra_artifacts_and_receipt_traversal_are_rejected(self):
        original = self.emit
        def extra(output):
            raw = original(output)
            (output / 'orphan.png').write_bytes(png_bytes())
            return raw
        self.emit = extra
        self.failure('Native artifact inventory mismatch')
        self.output = self.root / 'traversal'
        self.manifest['frames'][0]['receipt'] = '../escaped.capture.json'
        self.emit = original
        with self.assertRaisesRegex(burst.CaptureError, 'Frame receipt name mismatch'):
            self.capture()

    def test_fresh_directory_and_receipt_are_preflighted_without_overwriting(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, 'fresh native output'):
            self.capture()
        self.output = self.root / 'receipt-exists'
        receipt = self.root / 'receipt-exists.capture.json'
        receipt.write_bytes(b'prior evidence')
        with self.assertRaisesRegex(ValueError, 'fresh wrapper receipt'):
            self.capture()
        self.assertEqual(b'prior evidence', receipt.read_bytes())
        self.popen.assert_not_called()

    def test_overlong_duration_is_refused_with_failed_receipt(self):
        self.failure('Duration milliseconds', duration_ms=60001)
        self.popen.assert_not_called()

    def test_recomputed_head_gap_and_freshness_reject_claimed_complete_burst(self):
        self.manifest['frames'][0]['frame_qpc_100ns'] = 1000000
        self.failure('Frame age mismatch|Frame timestamp policy|freshness policy')
        self.output = self.root / 'head-gap'
        self.manifest = self.make_manifest()
        self.manifest['max_gap_ms'] = 20
        with self.assertRaisesRegex(burst.CaptureError, 'Frame gap flag mismatch'):
            self.capture(max_gap_ms=20)


if __name__ == '__main__':
    unittest.main()
