"""Strict independent replay of bounded capture-then-encode WGC evidence.

The capture and PNG guard chains are separate real timelines. Neither compositor
timestamps nor post-capture encoding timestamps are rewritten for legacy readers.
"""
from pathlib import Path

from capture_native_burst import (
    MAX_JSON_BYTES, MAX_PNG_BYTES, TIMESTAMP_ERRORS, _artifact, _equal, _integer,
    _json_document, _linked, _png_evidence, _require, _timestamp_error,
    _validate_timestamp_wait, _window_state,
)

POLICY = 'deferred_after_capture_v1'
RAW_LIMIT = 448 * 1024 * 1024
ENCODER_RESERVE = 64 * 1024 * 1024
TOTAL_LIMIT = 512 * 1024 * 1024
SINGLE_LIMIT = 16 * 1024 * 1024
FRAME_LIMIT = 64


def validate_native_deferred(report, binding, window, stdout, *, expected_mode='persistent_burst', extra_artifacts=()):
    directory = Path(report['output_directory'])
    _require(not _linked(directory) and directory.is_dir() and directory.resolve() == directory,
             'Native output directory is missing or linked')
    raw, manifest_file = _artifact(directory, 'manifest.json', MAX_JSON_BYTES)
    report['native_manifest_file'] = manifest_file
    native = _json_document(raw)
    report['native_manifest'] = native
    _require(isinstance(native, dict), 'Native manifest must be an object')
    _equal(_json_document(stdout), native, 'Native stdout/manifest')
    allow_foreground = binding.get('user_foreground_allowed') is True
    for key, value in (('schema', 4 if allow_foreground else 3), ('backend', 'Windows.Graphics.Capture'),
                       ('mode', expected_mode), ('clock', 'compositor_system_relative_qpc_100ns'),
                       ('background_only', not allow_foreground), ('activation_fallback', False),
                       ('native_resolution', True), ('pixel_acceptance', False),
                       ('source_frame_loss_known', False), ('owned_hwnd', window['hwnd']),
                       ('owned_pid', binding['game_pid']), ('owned_creation_time', binding['game_identity']),
                       ('max_frame_age_ms', 1000), ('timestamp_policy', 'strict_after_bounded_qpc_wait'),
                       ('future_timestamp_wait_limit_ms', 50), ('future_timestamp_wait_guard_limit', 128)):
        _equal(native.get(key), value, 'Native manifest ' + key)
    if allow_foreground:
        for key, value in (('foreground_policy', 'allow_user_foreground'),
                           ('user_foreground_allowed', True), ('agent_activation_allowed', False)):
            _equal(native.get(key), value, 'Native manifest ' + key)
    else:
        _require('foreground_policy' not in native and 'user_foreground_allowed' not in native and
                 'agent_activation_allowed' not in native, 'Legacy native policy contains foreground opt-in')
    for key in ('planned_duration_ms', 'max_frames', 'max_gap_ms'):
        _equal(native.get(key), report['request'][key], 'Native requested ' + key)
    request = _integer(native.get('request_qpc_100ns'), 'Native request timestamp', 1)
    deadline = _integer(native.get('planned_end_qpc_100ns'), 'Native deadline', request + 1)
    _equal(deadline - request, report['request']['planned_duration_ms'] * 10000, 'Native interval')
    finished = _integer(native.get('finished_qpc_100ns'), 'Native finish timestamp', deadline)
    for key, value in (('encoding_policy', POLICY),
                       ('sampling_policy', 'latest_available_at_bounded_intervals'),
                       ('sampling_interval_ms', 70),
                       ('raw_buffer_limit_bytes', RAW_LIMIT),
                       ('encoder_reserve_bytes', ENCODER_RESERVE),
                       ('total_buffer_limit_bytes', TOTAL_LIMIT),
                       ('single_bitmap_limit_bytes', SINGLE_LIMIT),
                       ('buffer_frame_limit', FRAME_LIMIT)):
        _equal(native.get(key), value, 'Deferred manifest ' + key)
    capture_finished = _integer(native.get('capture_finished_qpc_100ns'),
                                'Deferred capture phase finish', deadline, finished)
    encoding_started = _integer(native.get('encoding_started_qpc_100ns'),
                                'Deferred encoding phase start', capture_finished, finished)
    encoding_finished = _integer(native.get('encoding_finished_qpc_100ns'),
                                 'Deferred encoding phase finish', encoding_started, finished)
    _equal(native.get('capture_span_100ns'), capture_finished - request, 'Deferred capture span')
    _equal(native.get('total_span_100ns'), finished - request, 'Deferred total span')
    _equal(_window_state(native.get('capture_final_window_state'), binding, window),
           capture_finished, 'Deferred capture-final guard')
    _equal(_window_state(native.get('encoding_start_window_state'), binding, window),
           encoding_started, 'Deferred encoding-start guard')
    last_encoding_guard = encoding_started
    raw_bytes = 0
    max_gap = report['request']['max_gap_ms'] * 10000
    baseline = native.get('baseline')
    _require(_window_state(baseline, binding, window) <= request, 'Native baseline is after request')
    _window_state(native['capture_final_window_state'], binding, window, baseline)
    _window_state(native['encoding_start_window_state'], binding, window, baseline)
    records = native.get('frames')
    _require(isinstance(records, list) and len(records) <= report['request']['max_frames'] * 4 + 64,
             'Native frame attempts are unbounded or invalid')
    expected_files = {'manifest.json'} | {Path(row['path']).name for row in extra_artifacts}
    accepted = []
    gaps = []
    waits = []
    report['frames'] = []
    last_guard = request
    for sequence, record in enumerate(records, 1):
        _require(isinstance(record, dict) and 'receipt_write_error' not in record,
                 'Native receipt write failed')
        _equal(record.get('schema'), 1, 'Frame schema')
        _equal(record.get('sequence'), sequence, 'Frame sequence')
        receipt_name = 'frame_%06d.capture.json' % sequence
        _equal(record.get('receipt'), receipt_name, 'Frame receipt name')
        receipt_raw, receipt = _artifact(directory, receipt_name, MAX_JSON_BYTES)
        evidence = {'sequence': sequence, 'receipt': receipt, 'png': None}
        report['frames'].append(evidence)
        _equal(_json_document(receipt_raw), record, 'Manifest/individual receipt')
        expected_files.add(receipt_name)
        _equal(record.get('request_qpc_100ns'), request, 'Frame request timestamp')
        _equal(record.get('timestamp_available'), True, 'Frame timestamp availability')
        frame = _integer(record.get('frame_qpc_100ns'), 'Frame timestamp')
        observed = _integer(record.get('observed_qpc_100ns'), 'Frame observation', request)
        previous = accepted[-1] if accepted else request
        age, delta = observed - frame, frame - previous
        _equal(record.get('frame_age_100ns'), age, 'Frame age')
        _equal(record.get('delta_from_previous_or_request_100ns'), delta, 'Frame interval')
        policy_error = _timestamp_error(frame, observed, request, previous, deadline)
        _require(type(record.get('capture_valid')) is bool and isinstance(record.get('error'), str),
                 'Frame validity/error is malformed')
        valid = record['capture_valid']
        _equal(record['error'], '' if valid else policy_error, 'Frame timestamp policy')
        _require(valid or record['error'] in TIMESTAMP_ERRORS, 'Native frame has a terminal capture error')
        _require(not valid or not policy_error, 'Native frame violates freshness policy')
        _equal(record.get('gap_exceeded'), valid and delta > max_gap, 'Frame gap flag')
        _equal(record.get('width'), window['width'], 'Frame native width')
        _equal(record.get('height'), window['height'], 'Frame native height')
        before_time = _window_state(record.get('before'), binding, window, baseline)
        _equal(record.get('encoding_policy'), POLICY, 'Deferred receipt policy')
        last_time = _window_state(record.get('capture_last_window_state'), binding, window, baseline)
        _require(last_time <= capture_finished, 'Deferred receipt captured after phase barrier')
        _require(last_guard <= before_time <= observed <= last_time,
                 'Native receipt guard timestamps moved backwards')
        evidence['timestamp_wait'] = _validate_timestamp_wait(
            record, binding, window, baseline, request, previous, deadline, max_gap)
        waits.append(evidence['timestamp_wait'])
        if valid:
            png_name = 'frame_%06d.png' % sequence
            _equal(record.get('png'), png_name, 'Frame PNG name')
            png_raw, png = _artifact(directory, png_name, MAX_PNG_BYTES)
            evidence['png'] = png
            _png_evidence(png_raw, png, window['width'], window['height'])
            expected_files.add(png_name)
            after_readback = _window_state(record.get('after_readback'), binding, window, baseline)
            _require(last_guard <= before_time <= observed <= after_readback <= capture_finished,
                     'Deferred capture guard chain moved backwards')
            _equal(record.get('capture_last_window_state'), record.get('after_readback'),
                   'Deferred immutable bitmap capture-final guard')
            encode_guards = [_window_state(record.get(key), binding, window, baseline) for key in
                             ('before_png_encode', 'before_png_write', 'after_png_write')]
            _require(last_encoding_guard <= encode_guards[0] <= encode_guards[1] <=
                     encode_guards[2] <= encoding_finished,
                     'Deferred encoding guard chain or phase barrier failed')
            _equal(record.get('last_window_state'), record.get('after_png_write'),
                   'Deferred final encoded-frame guard')
            last_encoding_guard = encode_guards[-1]
            stride = _integer(record.get('bitmap_stride_bytes'), 'Deferred bitmap stride',
                              window['width'] * 4, SINGLE_LIMIT)
            size = _integer(record.get('retained_bitmap_bytes'), 'Deferred bitmap bytes', 1, SINGLE_LIMIT)
            _equal(size, stride * window['height'], 'Deferred stride/height byte accounting')
            raw_bytes += size
            _require(raw_bytes <= RAW_LIMIT, 'Deferred raw queue exceeded its byte cap')
            _require(len(accepted) + 1 <= FRAME_LIMIT, 'Deferred raw queue exceeded its frame cap')
            accepted.append(frame)
            gaps.append(delta)
        else:
            _equal(record.get('last_window_state'), record.get('capture_last_window_state'),
                   'Deferred rejected-frame final guard')
            _equal(record.get('bitmap_stride_bytes'), 0, 'Rejected bitmap stride')
            _equal(record.get('retained_bitmap_bytes'), 0, 'Rejected bitmap bytes')
            _equal(record.get('png'), None, 'Rejected timestamp PNG')
            if record['error'] == 'frame_after_planned_interval':
                _require(sequence == len(records), 'Frames follow the terminal postinterval receipt')
        last_guard = last_time
    _equal({path.name for path in directory.iterdir()}, expected_files, 'Native artifact inventory')
    final_guard = _window_state(native.get('final_window_state'), binding, window, baseline)
    _require(last_guard <= capture_finished <= encoding_started <= last_encoding_guard <=
             final_guard == encoding_finished <= finished,
             'Deferred final guard or two-phase ordering is invalid')
    valid_count = len(accepted)
    _equal(native.get('peak_raw_buffer_bytes'), raw_bytes, 'Deferred peak raw bytes')
    _equal(native.get('peak_buffered_frames'), valid_count, 'Deferred peak queued frames')
    _equal(native.get('peak_accounted_buffer_bytes'), raw_bytes + ENCODER_RESERVE,
           'Deferred peak accounted bytes')
    _require(raw_bytes + ENCODER_RESERVE <= TOTAL_LIMIT, 'Deferred total buffer cap exceeded')
    report['validated_encoding'] = {'policy': POLICY, 'capture_finished_qpc_100ns': capture_finished,
                                     'encoding_started_qpc_100ns': encoding_started,
                                     'encoding_finished_qpc_100ns': encoding_finished,
                                     'capture_span_100ns': capture_finished - request,
                                     'total_span_100ns': finished - request,
                                     'peak_raw_buffer_bytes': raw_bytes,
                                     'peak_accounted_buffer_bytes': raw_bytes + ENCODER_RESERVE,
                                     'peak_buffered_frames': valid_count,
                                     'total_buffer_limit_bytes': TOTAL_LIMIT}
    _require(2 <= valid_count <= report['request']['max_frames'], 'Burst needs at least two valid frames')
    for key, value in (('attempted_frames', len(records)), ('valid_frames', valid_count),
                       ('rejected_frames', len(records) - valid_count),
                       ('first_frame_qpc_100ns', accepted[0]), ('last_frame_qpc_100ns', accepted[-1]),
                       ('start_gap_100ns', accepted[0] - request),
                       ('tail_gap_100ns', deadline - accepted[-1]),
                       ('tail_gap_exceeded', deadline - accepted[-1] > max_gap),
                       ('maximum_gap_100ns', max(gaps + [deadline - accepted[-1]]))):
        _equal(native.get(key), value, 'Native timeline ' + key)
    _integer(native.get('frame_arrival_events'), 'Frame arrival event count')
    complete = max(gaps + [deadline - accepted[-1]]) <= max_gap
    report['validated_timeline'] = {'valid_frames': valid_count, 'attempted_frames': len(records),
                                    'rejected_frames': len(records) - valid_count,
                                    'maximum_gap_100ns': max(gaps + [deadline - accepted[-1]]),
                                    'future_timestamp_waited_frames': sum(wait['waited'] for wait in waits),
                                    'maximum_initial_future_offset_100ns': max(
                                        wait['initial_future_offset_100ns'] for wait in waits),
                                    'maximum_future_wait_elapsed_100ns': max(wait['elapsed_100ns'] for wait in waits),
                                    'temporal_complete': complete}
    _require(complete, 'Native burst has an uncovered start, interior or tail gap')
    for key, value in (('ok', True), ('capture_valid', True), ('temporal_complete', True),
                       ('stop_reason', 'duration_elapsed'), ('error', '')):
        _equal(native.get(key), value, 'Native completion ' + key)

