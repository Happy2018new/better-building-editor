"""Counterexamples for fixed preparation that cannot hide a measured stall."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import capture_native_burst as burst
import capture_native_burst_deferred as deferred
import capture_native_burst_startup as startup
import test_capture_native_burst as fixtures


class StartupBurstTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.NativeBurstWrapperTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.manifest = self.fixture.manifest
        n, f = self.manifest, self.fixture
        n.update(schema=3, mode=startup.MODE, capture_protocol=startup.PROTOCOL,
                 preparation_policy='fixed_1500ms_before_prescheduled_full_measurement',
                 preparation_duration_ms=1500, preparation_start_qpc_100ns=1000000,
                 preparation_fixed_end_qpc_100ns=16000000, preparation_actual_end_qpc_100ns=16000010,
                 preparation_selection_cutoff_qpc_100ns=15500000,
                 preparation_idle_tail_ms=50, preparation_future_wait_limit_ms=50,
                 preparation_frame_count=2, preparation_first_last_raw_bytes=96,
                 preparation_png_policy='native_first_and_last_only_all_selected_frame_metadata',
                 planned_duration_ms=3200, max_frames=240, max_gap_ms=150,
                 request_qpc_100ns=16000000, planned_end_qpc_100ns=48000000,
                 finished_qpc_100ns=48300000, encoding_policy=deferred.POLICY,
                 sampling_policy='latest_available_at_bounded_intervals', sampling_interval_ms=70,
                 raw_buffer_limit_bytes=deferred.RAW_LIMIT, encoder_reserve_bytes=deferred.ENCODER_RESERVE,
                 total_buffer_limit_bytes=deferred.TOTAL_LIMIT, single_bitmap_limit_bytes=deferred.SINGLE_LIMIT,
                 buffer_frame_limit=64, capture_finished_qpc_100ns=48000100,
                 encoding_started_qpc_100ns=48000200, encoding_finished_qpc_100ns=48200000,
                 capture_span_100ns=32000100, total_span_100ns=32300000,
                 capture_final_window_state=f.state(48000100), encoding_start_window_state=f.state(48000200),
                 final_window_state=f.state(48200000))
        n['preparation_frames'] = [dict(sequence=i,frame_qpc_100ns=t,observed_qpc_100ns=t+10,
            initial_observed_qpc_100ns=t+10,
            future_timestamp_wait=dict(requested=False,deadline_qpc_100ns=0,elapsed_100ns=0,outcome='not_requested',guards=[]),
            width=4,height=3,bitmap_stride_bytes=16,retained_bitmap_bytes=48,first_png_source=i==1,
            before=f.state(t-10),after_readback=f.state(t+20))
            for i,t in enumerate((2000000,15000000),1)]
        n['preparation_polls'] = [dict(sequence=i, before=copy.deepcopy(frame['before']),
            selection_returned_qpc_100ns=frame['initial_observed_qpc_100ns']-1,
            initial_observed_qpc_100ns=frame['initial_observed_qpc_100ns'],
            has_frame=True, frame_sequence=i, frame_qpc_100ns=frame['frame_qpc_100ns'])
            for i,frame in enumerate(n['preparation_frames'],1)]
        n['preparation_poll_count'] = 2
        n['preparation_wait_guard_count'] = 0
        n['preparation_wait_guards'] = []
        n['preparation_tail_guards'] = [f.state(15500000),f.state(16000010)]
        n['preparation_tail_guard_count'] = 2
        self.timestamps = list(range(16500000,47700001,800000))
        self.measurement(self.timestamps)
        original_emit = f.emit
        self.png_missing = None
        self.png_bad = None

        def emit(output):
            raw = original_emit(output)
            for name in startup.PNG_NAMES:
                if name != self.png_missing:
                    (output / name).write_bytes(fixtures.png_bytes(width=5 if name==self.png_bad else 4))
            return raw
        f.emit = emit

    def measurement(self,timestamps):
        frames=[]
        previous=16000000
        for index,timestamp in enumerate(timestamps,1):
            delta=timestamp-previous
            frame=self.fixture.frame(index,timestamp,timestamp+100,delta)
            frame['initial_timestamp_assessment'].update(error='',gap_exceeded=delta>1500000)
            frame.update(request_qpc_100ns=16000000,encoding_policy=deferred.POLICY,
                         bitmap_stride_bytes=16,retained_bitmap_bytes=48,
                         capture_last_window_state=copy.deepcopy(frame['after_readback']),
                         before_png_encode=self.fixture.state(48000300+index*1000),
                         before_png_write=self.fixture.state(48000400+index*1000),
                         after_png_write=self.fixture.state(48000500+index*1000),gap_exceeded=delta>1500000)
            frame['last_window_state']=copy.deepcopy(frame['after_png_write'])
            frames.append(frame);previous=timestamp
        n=self.manifest
        maximum=max([x['delta_from_previous_or_request_100ns'] for x in frames]+[48000000-timestamps[-1]])
        n.update(frames=frames,attempted_frames=len(frames),valid_frames=len(frames),rejected_frames=0,
                 frame_arrival_events=len(frames)+2,first_frame_qpc_100ns=timestamps[0],last_frame_qpc_100ns=timestamps[-1],
                 start_gap_100ns=timestamps[0]-16000000,tail_gap_100ns=48000000-timestamps[-1],
                 tail_gap_exceeded=48000000-timestamps[-1]>1500000,maximum_gap_100ns=maximum,
                 peak_raw_buffer_bytes=len(frames)*48,peak_buffered_frames=len(frames),
                 peak_accounted_buffer_bytes=len(frames)*48+deferred.ENCODER_RESERVE,
                 preparation_combined_peak_raw_bytes=len(frames)*48+96,
                 temporal_complete=maximum<=1500000,ok=maximum<=1500000)

    def capture(self):return self.fixture.capture(duration_ms=3200,max_frames=240,max_gap_ms=150)
    def failure(self,pattern):return self.fixture.failure(pattern,duration_ms=3200,max_frames=240,max_gap_ms=150)

    def test_fixed_preparation_preserves_complete_measured_window(self):
        r=self.capture()
        self.assertTrue(r['ok'])
        self.assertEqual(2,r['validated_preparation']['preparation_frames'])
        self.assertEqual(40,len(r['frames']))
        self.assertEqual(2,len(r['auxiliary_artifacts']))
        self.assertFalse(r['validated_preparation']['adaptive_window_selection'])

    def test_old_reader_rejects_new_mode(self):
        r=self.capture()
        with self.assertRaisesRegex(ValueError,'mode'):
            deferred.validate_native_deferred(copy.deepcopy(r),r['instance'],r['window'],json.dumps(r['native_manifest']).encode())

    def test_unknown_protocol_rejected(self):
        self.manifest['capture_protocol']='guess_a_good_window';self.failure('capture protocol')
    def test_unversioned_mode_rejected(self):
        self.manifest['mode']='persistent_burst';self.failure('Startup mode')
    def test_boundary_cannot_shift_to_after_an_observed_stall(self):
        self.manifest['preparation_start_qpc_100ns']+=1;self.failure('fixed boundary')
    def test_fixed_end_alias_cannot_move(self):
        self.manifest['preparation_fixed_end_qpc_100ns']+=1;self.failure('fixed end alias')
    def test_missing_preparation_frame_rejected(self):
        self.manifest['preparation_frames'].pop();self.failure('2..256')
    def test_preparation_count_cannot_hide_omitted_metadata(self):
        self.manifest['preparation_frame_count']=3;self.failure('preparation count')
    def test_preparation_source_cannot_belong_to_measured_window(self):
        self.manifest['preparation_frames'][-1]['frame_qpc_100ns']=16000000;self.failure('preparation source')
    def test_preparation_guard_cannot_waive_noactivate(self):
        self.manifest['preparation_frames'][0]['before']['window_noactivate_style']=False;self.failure('window_noactivate_style')
    def test_preparation_guard_must_be_chronological(self):
        self.manifest['preparation_frames'][1]['before']['observed_qpc_100ns']=1000001;self.failure('guard chain')
    def test_raw_preparation_budget_is_not_raised(self):
        self.manifest['preparation_combined_peak_raw_bytes']=deferred.RAW_LIMIT+1;self.failure('combined raw peak')
    def test_first_last_reservation_cannot_be_understated(self):
        self.manifest['preparation_first_last_raw_bytes']=48;self.failure('first/last raw bytes')
    def test_preparation_png_is_required(self):
        self.png_missing=startup.PNG_NAMES[0];self.failure('Artifact is missing')
    def test_preparation_png_must_be_native_size(self):
        self.png_bad=startup.PNG_NAMES[1];self.failure('PNG')
    def test_mid_measurement_stall_is_not_covered_by_preparation(self):
        self.measurement(self.timestamps[:10]+self.timestamps[11:]);self.failure('uncovered start, interior or tail gap')
    def test_tail_stall_is_not_covered_by_preparation(self):
        self.measurement(self.timestamps[:-9]);self.failure('uncovered start, interior or tail gap')
    def test_full_measurement_cannot_be_shortened(self):
        self.manifest['planned_end_qpc_100ns']-=1;self.failure('complete measurement end')

    def test_flow_replay_rehashes_retained_preparation_png(self):
        from analyze_product_water_flow import burst_frames
        capture = self.capture()
        images, times = burst_frames(capture)
        self.assertEqual((40, 40), (len(images), len(times)))
        from PIL import Image
        path = Path(capture['auxiliary_artifacts'][0]['path'])
        with Image.open(path) as original:
            changed = original.convert('RGB')
        changed.putpixel((0, 0), (1, 2, 3))
        changed.save(path)
        with self.assertRaisesRegex(ValueError, 'retained preparation artifacts'):
            burst_frames(capture)

    def future_preparation(self):
        frame=self.manifest['preparation_frames'][1]
        frame['before']=self.fixture.state(14999900)
        frame['initial_observed_qpc_100ns']=14999950
        frame['future_timestamp_wait']=dict(requested=True,deadline_qpc_100ns=15499950,
            elapsed_100ns=60,outcome='eligible',guards=[self.fixture.state(15000010)])
        poll=self.manifest['preparation_polls'][1]
        poll.update(before=copy.deepcopy(frame['before']),selection_returned_qpc_100ns=14999949,
                    initial_observed_qpc_100ns=14999950)
        self.manifest['preparation_wait_guard_count'] = 1
        self.manifest['preparation_wait_guards'] = [dict(sequence=1,frame_sequence=2,
            guard=copy.deepcopy(frame['future_timestamp_wait']['guards'][0]))]
        return frame

    def test_preparation_waits_only_for_its_own_source_with_bounded_guards(self):
        self.future_preparation()
        capture=self.capture()
        self.assertEqual(1,capture['validated_preparation']['future_waited_preparation_frames'])
        self.assertEqual(15500000,capture['validated_preparation']['fixed_acquisition_cutoff_qpc_100ns'])

    def test_future_preparation_source_cannot_be_accepted_before_observation(self):
        self.manifest['preparation_frames'][1]['frame_qpc_100ns']=15000011
        self.failure('preparation source is future')

    def test_preparation_future_initial_observation_cannot_be_relabelled(self):
        frame=self.future_preparation();frame['initial_observed_qpc_100ns']=15000010
        self.failure('wait eligibility')

    def test_preparation_future_wait_needs_every_declared_guard(self):
        frame=self.future_preparation();frame['future_timestamp_wait']['guards']=[]
        self.failure('wait exceeded budget')

    def test_preparation_future_wait_deadline_cannot_shift(self):
        frame=self.future_preparation();frame['future_timestamp_wait']['deadline_qpc_100ns']=16000000
        self.failure('wait deadline')

    def test_preparation_future_wait_cannot_exceed_50ms(self):
        frame=self.future_preparation();frame['initial_observed_qpc_100ns']=14499999
        frame['before']=self.fixture.state(14499990)
        self.failure('offset exceeds fixed 50ms')

    def test_preparation_future_wait_guard_cannot_lose_noactivate(self):
        frame=self.future_preparation();frame['future_timestamp_wait']['guards'][0]['window_noactivate_style']=False
        self.failure('window_noactivate_style')

    def test_preparation_future_wait_cannot_omit_final_observation_guard(self):
        frame=self.future_preparation();frame['future_timestamp_wait']['guards'][0]['observed_qpc_100ns']-=1
        self.failure('final preparation future guard')

    def test_preparation_cutoff_is_fixed_50ms_before_measurement(self):
        self.manifest['preparation_selection_cutoff_qpc_100ns']+=1
        self.failure('1450ms acquisition cutoff')

    def test_selected_poll_crossing_cutoff_is_rejected(self):
        self.manifest['preparation_polls'][1]['selection_returned_qpc_100ns']=15500000
        self.failure('poll return before fixed cutoff')

    def test_selected_frame_cannot_be_omitted_from_poll_records(self):
        self.manifest['preparation_polls'][1].update(has_frame=False,frame_sequence=0,frame_qpc_100ns=0)
        self.failure('metadata coverage')

    def test_selected_poll_cannot_be_omitted_from_frame_metadata(self):
        self.manifest['preparation_polls'][1]['frame_qpc_100ns']+=1
        self.failure('selected poll source')

    def test_fixed_idle_tail_guards_are_required(self):
        self.manifest['preparation_tail_guards']=[]
        self.failure('idle tail guards')

    def test_fixed_idle_tail_guard_cannot_be_omitted(self):
        self.manifest['preparation_tail_guards'].pop(0)
        self.failure('idle tail guard count')

    def test_fixed_idle_tail_must_reach_original_boundary(self):
        self.manifest['preparation_tail_guards'][-1]['observed_qpc_100ns']=15999999
        self.failure('idle tail final guard')

    def test_fixed_idle_tail_cannot_move_actual_end_past_its_final_guard(self):
        self.manifest['preparation_actual_end_qpc_100ns']+=1
        self.failure('idle tail final guard')

    def test_fixed_idle_tail_noactivate_cannot_be_waived(self):
        self.manifest['preparation_tail_guards'][0]['window_noactivate_style']=False
        self.failure('window_noactivate_style')

    def test_intermediate_preparation_future_guard_cannot_be_silently_omitted(self):
        frame=self.future_preparation()
        early=self.fixture.state(14999980)
        original=copy.deepcopy(frame['future_timestamp_wait']['guards'][0])
        self.manifest['preparation_wait_guards']=[dict(sequence=1,frame_sequence=2,guard=early),
            dict(sequence=2,frame_sequence=2,guard=original)]
        self.manifest['preparation_wait_guard_count']=2
        self.failure('complete preparation wait guard count')

    def test_preparation_and_measurement_combined_budget_is_enforced(self):
        for frame in self.manifest['preparation_frames']:
            frame.update(bitmap_stride_bytes=4*1024*1024,retained_bitmap_bytes=12*1024*1024)
        self.manifest.update(preparation_first_last_raw_bytes=24*1024*1024,
            peak_raw_buffer_bytes=430*1024*1024,preparation_combined_peak_raw_bytes=454*1024*1024)
        self.failure('exceed the unchanged memory cap')

    def test_empty_preparation_polls_remain_bound_between_selected_frames(self):
        empty=dict(sequence=2,before=self.fixture.state(3000000),
            selection_returned_qpc_100ns=3000001,initial_observed_qpc_100ns=3000002,
            has_frame=False,frame_sequence=0,frame_qpc_100ns=0)
        self.manifest['preparation_polls'].insert(1,empty)
        self.manifest['preparation_polls'][2]['sequence']=3
        self.manifest['preparation_poll_count']=3
        self.assertEqual(3,self.capture()['validated_preparation']['preparation_polls'])

    def test_missing_preparation_poll_is_rejected(self):
        self.manifest['preparation_polls'].pop(0)
        self.failure('polls are missing')


if __name__=='__main__':unittest.main()
