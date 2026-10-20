"""Counterexamples for separate capture and deferred PNG timelines."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import capture_native_burst as burst
import capture_native_burst_deferred as deferred
import test_capture_native_burst as fixtures


class DeferredBurstTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.NativeBurstWrapperTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.manifest = self.fixture.manifest
        self.manifest.update(
            schema=3, planned_duration_ms=700, max_gap_ms=150,
            planned_end_qpc_100ns=8000000, finished_qpc_100ns=8020000,
            encoding_policy=deferred.POLICY,
            sampling_policy='latest_available_at_bounded_intervals', sampling_interval_ms=70,
            raw_buffer_limit_bytes=deferred.RAW_LIMIT, encoder_reserve_bytes=deferred.ENCODER_RESERVE,
            total_buffer_limit_bytes=deferred.TOTAL_LIMIT, single_bitmap_limit_bytes=deferred.SINGLE_LIMIT,
            buffer_frame_limit=64, peak_raw_buffer_bytes=384, peak_buffered_frames=8,
            peak_accounted_buffer_bytes=384 + deferred.ENCODER_RESERVE,
            capture_finished_qpc_100ns=8000100, encoding_started_qpc_100ns=8000200,
            encoding_finished_qpc_100ns=8010000, capture_span_100ns=7000100, total_span_100ns=7020000,
            capture_final_window_state=self.fixture.state(8000100),
            encoding_start_window_state=self.fixture.state(8000200),
            final_window_state=self.fixture.state(8010000),
            attempted_frames=8, valid_frames=8, rejected_frames=0, frame_arrival_events=8,
            first_frame_qpc_100ns=1500000, last_frame_qpc_100ns=7100000,
            start_gap_100ns=500000, tail_gap_100ns=900000, maximum_gap_100ns=900000,
        )
        frames = []
        for index, timestamp in enumerate(range(1500000, 7100001, 800000), 1):
            delta = 500000 if index == 1 else 800000
            frame = self.fixture.frame(index, timestamp, timestamp + 100, delta)
            frame['initial_timestamp_assessment']['error'] = ''
            frame.update(
                encoding_policy=deferred.POLICY, bitmap_stride_bytes=16, retained_bitmap_bytes=48,
                capture_last_window_state=copy.deepcopy(frame['after_readback']),
                before_png_encode=self.fixture.state(8000300 + index * 1000),
                before_png_write=self.fixture.state(8000400 + index * 1000),
                after_png_write=self.fixture.state(8000500 + index * 1000),
            )
            frame['last_window_state'] = copy.deepcopy(frame['after_png_write'])
            frames.append(frame)
        self.manifest['frames'] = frames

    def capture(self):
        return self.fixture.capture(duration_ms=700, max_gap_ms=150)

    def failure(self, pattern):
        return self.fixture.failure(pattern, duration_ms=700, max_gap_ms=150)

    def test_two_real_timelines_replay_independently_through_flow_reader(self):
        report = self.capture()
        self.assertTrue(report['ok'])
        self.assertGreater(report['validated_encoding']['total_span_100ns'],
                           report['validated_encoding']['capture_span_100ns'])
        replay = copy.deepcopy(report)
        burst._validate_native(replay, report['instance'], report['window'],
                               json.dumps(report['native_manifest']).encode('ascii'))
        self.assertEqual(report['validated_encoding'], replay['validated_encoding'])
        from analyze_product_water_flow import burst_frames
        images, timestamps = burst_frames(report)
        self.assertEqual(8, len(images))
        self.assertEqual([frame['frame_qpc_100ns'] for frame in self.manifest['frames']], timestamps)

    def test_encoding_cannot_begin_inside_capture_phase(self):
        self.manifest['frames'][0]['before_png_encode']['observed_qpc_100ns'] = 7000000
        self.failure('encoding guard chain or phase barrier')

    def test_capture_chain_cannot_be_waived_by_deferred_encoding(self):
        self.manifest['frames'][1]['before']['observed_qpc_100ns'] = 1200000
        self.failure('guard timestamps moved backwards')

    def test_encoding_chain_cannot_move_backwards_between_frames(self):
        self.manifest['frames'][1]['before_png_encode']['observed_qpc_100ns'] = 8000200
        self.failure('encoding guard chain or phase barrier')

    def test_capture_phase_cannot_end_before_last_readback(self):
        self.manifest['capture_finished_qpc_100ns'] = 7000000
        self.failure('capture phase finish')

    def test_encoding_phase_cannot_fake_a_shorter_total_span(self):
        self.manifest['total_span_100ns'] = self.manifest['capture_span_100ns']
        self.failure('total span')

    def test_guards_remain_mandatory_during_later_encoding(self):
        self.manifest['frames'][3]['before_png_write']['minimized'] = True
        self.failure('minimized')

    def test_frame_memory_accounting_requires_real_stride_and_height(self):
        self.manifest['frames'][3]['retained_bitmap_bytes'] = 47
        self.failure('stride/height')

    def test_declared_peak_cannot_understate_retained_raw_memory(self):
        self.manifest['peak_raw_buffer_bytes'] = 383
        self.failure('peak raw bytes')

    def test_memory_and_frame_caps_cannot_be_raised(self):
        self.manifest['total_buffer_limit_bytes'] += 1
        self.failure('total_buffer_limit_bytes')

    def test_bitmap_cannot_exceed_single_frame_limit(self):
        self.manifest['frames'][0]['bitmap_stride_bytes'] = deferred.SINGLE_LIMIT
        self.manifest['frames'][0]['retained_bitmap_bytes'] = deferred.SINGLE_LIMIT * 3
        self.failure('bitmap bytes')

    def test_unknown_policy_and_legacy_schema_cannot_select_relaxed_reader(self):
        self.manifest['schema'] = 1
        self.failure('schema')

    def test_unknown_encoding_policy_is_rejected(self):
        self.manifest['encoding_policy'] = 'unverified_future_policy'
        self.failure('encoding policy')

    def test_phase_guard_thread_identity_must_match_capture_baseline(self):
        self.manifest['encoding_start_window_state']['thread_id'] += 1
        self.failure('thread')

    def test_user_foreground_requires_explicit_matching_policy_and_actual_guard_status(self):
        os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
        self.manifest.update(schema=4, background_only=False, foreground_policy='allow_user_foreground',
                             user_foreground_allowed=True, agent_activation_allowed=False)

        def actual_background_status(value):
            if isinstance(value, dict):
                if 'observed_qpc_100ns' in value and 'foreground_pid' in value:
                    value['background_safe'] = value['foreground_pid'] != 123
                for child in value.values():
                    actual_background_status(child)
            elif isinstance(value, list):
                for child in value:
                    actual_background_status(child)

        state = self.manifest['frames'][3]['before_png_encode']
        state.update(foreground_pid=123, foreground_hwnd=42)
        actual_background_status(self.manifest)
        self.assertTrue(self.capture()['ok'])

    def test_receipt_content_is_still_bound_to_native_manifest(self):
        original = self.fixture.emit

        def altered(directory):
            raw = original(directory)
            path = directory / self.manifest['frames'][0]['receipt']
            value = json.loads(path.read_bytes())
            value['bitmap_stride_bytes'] += 4
            path.write_text(json.dumps(value), encoding='ascii')
            return raw

        self.fixture.emit = altered
        self.failure('Manifest/individual receipt')

    def test_pngs_are_rehashed_again_during_independent_analysis(self):
        report = self.capture()
        path = Path(report['frames'][0]['png']['path'])
        path.write_bytes(fixtures.png_bytes(blank=True))
        from analyze_product_water_flow import burst_frames
        with self.assertRaises(ValueError):
            burst_frames(report)


if __name__ == '__main__':
    unittest.main()
