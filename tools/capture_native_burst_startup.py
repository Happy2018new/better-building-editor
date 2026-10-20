"""Fail-closed replay of a fixed preparation followed by a complete measured WGC burst.

Preparation cannot move the measurement origin, cover a measured gap, or raise
the existing memory caps. Only its first/last PNGs are retained; every selected
preparation frame has a native timestamp and full before/after window guards.
"""
from pathlib import Path

from capture_native_burst import (
    MAX_JSON_BYTES, MAX_PNG_BYTES, _artifact, _equal, _integer, _json_document,
    _png_evidence, _require, _window_state,
)
from capture_native_burst_deferred import (
    ENCODER_RESERVE, RAW_LIMIT, SINGLE_LIMIT, TOTAL_LIMIT, validate_native_deferred,
)

PROTOCOL = 'fixed_startup_preparation_v2'
MODE = 'persistent_burst_fixed_startup_v2'
PREPARATION_MS = 1500
MEASUREMENT_MS = 3200
PREPARATION_FRAME_LIMIT = 256
PNG_NAMES = ('preparation-first.png', 'preparation-last.png')
WAIT_LIMIT = 50 * 10000
GUARD_LIMIT = 128


def _preparation_wait(frame, source, observed, before, cutoff, boundary, binding, window, baseline):
    initial = _integer(frame.get('initial_observed_qpc_100ns'), 'Startup initial preparation observation', before, cutoff - 1)
    _require(initial <= observed and source <= observed,
             'Startup preparation source is future or observation moved backwards')
    wait = frame.get('future_timestamp_wait')
    _require(isinstance(wait, dict), 'Startup preparation future wait is missing')
    requested = source > initial
    _require(not requested or source - initial <= WAIT_LIMIT,
             'Startup preparation future offset exceeds fixed 50ms')
    deadline = min(initial + WAIT_LIMIT, boundary) if requested else 0
    _equal(wait.get('requested'), requested, 'Startup preparation wait eligibility')
    _equal(wait.get('deadline_qpc_100ns'), deadline, 'Startup preparation wait deadline')
    _equal(wait.get('elapsed_100ns'), observed - initial if requested else 0, 'Startup preparation wait elapsed')
    guards = wait.get('guards')
    _require(isinstance(guards, list) and len(guards) <= GUARD_LIMIT,
             'Startup preparation future guards are missing or unbounded')
    if requested:
        _equal(wait.get('outcome'), 'eligible', 'Startup preparation wait outcome')
        _require(bool(guards) and source <= observed <= deadline,
                 'Startup preparation wait exceeded budget or stayed future')
        previous = initial
        for guard in guards:
            at = _window_state(guard, binding, window, baseline)
            _require(previous <= at <= observed, 'Startup preparation future guard chronology')
            previous = at
        _equal(previous, observed, 'Startup final preparation future guard')
    else:
        _equal(wait.get('outcome'), 'not_requested', 'Startup unrequested preparation wait outcome')
        _equal(guards, [], 'Startup unrequested preparation wait guards')
        _equal(observed, initial, 'Startup unrequested wait changed observation')
    return requested


def _preparation_poll_and_tail(native, frames, begin, cutoff, boundary, actual_end, binding, window, baseline):
    polls = native.get('preparation_polls')
    _require(isinstance(polls, list) and 2 <= len(polls) <= 1024,
             'Startup preparation polls are missing or unbounded')
    _equal(native.get('preparation_poll_count'), len(polls), 'Startup preparation poll count')
    previous, selected = begin, 0
    for sequence, poll in enumerate(polls, 1):
        _require(isinstance(poll, dict), 'Startup preparation poll must be an object')
        _equal(poll.get('sequence'), sequence, 'Startup preparation poll sequence')
        before = _window_state(poll.get('before'), binding, window, baseline)
        returned = _integer(poll.get('selection_returned_qpc_100ns'), 'Startup poll return before fixed cutoff', before, cutoff - 1)
        initial = _integer(poll.get('initial_observed_qpc_100ns'), 'Startup poll observation before fixed cutoff', returned, cutoff - 1)
        _require(previous <= before, 'Startup preparation poll chronology moved backwards')
        has_frame = poll.get('has_frame')
        _require(type(has_frame) is bool, 'Startup poll frame flag must be boolean')
        if has_frame:
            selected += 1
            _require(selected <= len(frames), 'Startup poll omits selected preparation metadata')
            frame = frames[selected - 1]
            _equal(poll.get('frame_sequence'), selected, 'Startup selected poll frame sequence')
            _equal(poll.get('frame_qpc_100ns'), frame['frame_qpc_100ns'], 'Startup selected poll source')
            _equal(initial, frame['initial_observed_qpc_100ns'], 'Startup selected poll observation')
            _equal(poll.get('before'), frame.get('before'), 'Startup selected poll guard')
            previous = frame['after_readback']['observed_qpc_100ns']
        else:
            _equal(poll.get('frame_sequence'), 0, 'Startup empty poll frame sequence')
            _equal(poll.get('frame_qpc_100ns'), 0, 'Startup empty poll frame source')
            previous = initial
    _equal(selected, len(frames), 'Startup selected preparation metadata coverage')
    expected_wait_guards = [dict(sequence=sequence, frame_sequence=frame['sequence'], guard=guard)
        for sequence, (frame, guard) in enumerate(
            ((frame, guard) for frame in frames for guard in frame['future_timestamp_wait']['guards']), 1)]
    _equal(native.get('preparation_wait_guard_count'), len(expected_wait_guards),
           'Startup complete preparation wait guard count')
    _equal(native.get('preparation_wait_guards'), expected_wait_guards,
           'Startup complete preparation wait guard stream')
    tail = native.get('preparation_tail_guards')
    _require(isinstance(tail, list) and 1 <= len(tail) <= GUARD_LIMIT,
             'Startup fixed idle tail guards are missing or unbounded')
    _equal(native.get('preparation_tail_guard_count'), len(tail), 'Startup fixed idle tail guard count')
    for index, guard in enumerate(tail):
        at = _window_state(guard, binding, window, baseline)
        _require(max(previous, cutoff) <= at <= actual_end, 'Startup fixed idle tail chronology')
        _require(index == len(tail) - 1 or at < boundary,
                 'Startup idle tail continued beyond fixed boundary')
        previous = at
    _equal(previous, actual_end, 'Startup fixed idle tail final guard')
    _require(previous >= boundary, 'Startup fixed idle tail ended early')
    return len(polls), len(tail)


def validate_native_startup(report, binding, window, stdout):
    native = _json_document(stdout)
    _require(isinstance(native, dict), 'Startup manifest must be an object')
    for key, expected in (
        ('capture_protocol', PROTOCOL), ('mode', MODE),
        ('preparation_policy', 'fixed_1500ms_before_prescheduled_full_measurement'),
        ('preparation_duration_ms', PREPARATION_MS),
        ('preparation_png_policy', 'native_first_and_last_only_all_selected_frame_metadata'),
    ):
        _equal(native.get(key), expected, 'Startup ' + key)
    _equal(report['request']['planned_duration_ms'], MEASUREMENT_MS, 'Startup full measurement duration')
    directory = Path(report['output_directory'])
    raw, manifest_file = _artifact(directory, 'manifest.json', MAX_JSON_BYTES)
    _equal(_json_document(raw), native, 'Startup stdout/manifest')
    report['native_manifest_file'] = manifest_file
    report['native_manifest'] = native
    baseline = native.get('baseline')
    baseline_time = _window_state(baseline, binding, window)
    begin = _integer(native.get('preparation_start_qpc_100ns'), 'Startup preparation origin', baseline_time)
    boundary = _integer(native.get('request_qpc_100ns'), 'Startup measurement origin', begin + 1)
    _equal(native.get('preparation_fixed_end_qpc_100ns'), boundary, 'Startup fixed end alias')
    _equal(boundary - begin, PREPARATION_MS * 10000, 'Startup fixed boundary')
    cutoff = _integer(native.get('preparation_selection_cutoff_qpc_100ns'), 'Startup fixed acquisition cutoff', begin)
    _equal(cutoff, boundary - WAIT_LIMIT, 'Startup 1450ms acquisition cutoff')
    _equal(native.get('preparation_idle_tail_ms'), 50, 'Startup fixed idle tail duration')
    _equal(native.get('preparation_future_wait_limit_ms'), 50, 'Startup fixed preparation future wait limit')
    _equal(native.get('planned_end_qpc_100ns'), boundary + MEASUREMENT_MS * 10000,
           'Startup complete measurement end')
    actual_end = _integer(native.get('preparation_actual_end_qpc_100ns'), 'Startup actual preparation end', boundary)
    frames = native.get('preparation_frames')
    _require(isinstance(frames, list) and 2 <= len(frames) <= PREPARATION_FRAME_LIMIT,
             'Startup needs 2..256 preparation frames')
    _equal(native.get('preparation_frame_count'), len(frames), 'Startup preparation count')
    last_guard, last_source = begin, begin - 1
    conservative_peak, previous_reserved = 0, 0
    sizes = []
    waited = 0
    for sequence, frame in enumerate(frames, 1):
        _require(isinstance(frame, dict), 'Startup preparation frame must be an object')
        _equal(frame.get('sequence'), sequence, 'Startup preparation sequence')
        for key in ('width', 'height'):
            _equal(frame.get(key), window[key], 'Startup preparation ' + key)
        source = _integer(frame.get('frame_qpc_100ns'), 'Startup preparation source', begin, boundary - 1)
        _require(source > last_source, 'Startup preparation source is not strictly monotonic')
        observed = _integer(frame.get('observed_qpc_100ns'), 'Startup preparation observation', begin, actual_end)
        before = _window_state(frame.get('before'), binding, window, baseline)
        after = _window_state(frame.get('after_readback'), binding, window, baseline)
        _require(last_guard <= before <= observed <= after <= actual_end,
                 'Startup preparation guard chain moved backwards')
        waited += _preparation_wait(frame, source, observed, before, cutoff, boundary, binding, window, baseline)
        _equal(frame.get('first_png_source'), sequence == 1, 'Startup first PNG source')
        stride = _integer(frame.get('bitmap_stride_bytes'), 'Startup preparation stride', window['width']*4, SINGLE_LIMIT)
        size = _integer(frame.get('retained_bitmap_bytes'), 'Startup preparation bitmap bytes', 1, SINGLE_LIMIT)
        _equal(size, stride * window['height'], 'Startup preparation stride/height')
        conservative_peak = max(conservative_peak, previous_reserved + size)
        previous_reserved = size * 2
        sizes.append(size)
        last_source, last_guard = source, after
    poll_count, tail_count = _preparation_poll_and_tail(
        native, frames, begin, cutoff, boundary, actual_end, binding, window, baseline)
    reserved = sizes[0] + sizes[-1]
    _equal(native.get('preparation_first_last_raw_bytes'), reserved, 'Startup first/last raw bytes')
    _require(all(size == sizes[0] for size in sizes), 'Startup fixed-size frame accounting changed')
    peak_measurement = _integer(native.get('peak_raw_buffer_bytes'), 'Startup measured raw bytes', 1, RAW_LIMIT)
    expected_peak = max(conservative_peak, reserved + peak_measurement)
    _equal(native.get('preparation_combined_peak_raw_bytes'), expected_peak, 'Startup combined raw peak')
    _require(expected_peak <= RAW_LIMIT and expected_peak + ENCODER_RESERVE <= TOTAL_LIMIT,
             'Startup preparation and measurement exceed the unchanged memory cap')
    measured = native.get('frames')
    _require(isinstance(measured, list) and measured, 'Startup measured frames are missing')
    _require(_window_state(measured[0].get('before'), binding, window, baseline) >= actual_end,
             'Startup measured guards precede preparation completion')
    auxiliary = []
    for name in PNG_NAMES:
        png_raw, png = _artifact(directory, name, MAX_PNG_BYTES)
        _png_evidence(png_raw, png, window['width'], window['height'])
        auxiliary.append(png)
    if 'auxiliary_artifacts' in report:
        _equal(auxiliary, report['auxiliary_artifacts'], 'Startup retained preparation artifacts')
    # Replays the original strict measured timestamps, full interval, tail, frame
    # freshness, PNGs, identities and capture/encoding barriers, with this explicit mode.
    validate_native_deferred(report, binding, window, stdout,
                             expected_mode=MODE, extra_artifacts=auxiliary)
    report['auxiliary_artifacts'] = auxiliary
    report['validated_preparation'] = {
        'protocol': PROTOCOL, 'preparation_ms': PREPARATION_MS,
        'preparation_start_qpc_100ns': begin, 'fixed_measurement_start_qpc_100ns': boundary,
        'actual_preparation_end_qpc_100ns': actual_end, 'preparation_frames': len(frames),
        'fixed_acquisition_cutoff_qpc_100ns': cutoff, 'future_waited_preparation_frames': waited,
        'preparation_polls': poll_count, 'fixed_idle_tail_guards': tail_count,
        'first_source_qpc_100ns': frames[0]['frame_qpc_100ns'],
        'last_source_qpc_100ns': frames[-1]['frame_qpc_100ns'],
        'combined_peak_raw_bytes': expected_peak, 'raw_limit_bytes': RAW_LIMIT,
        'png_policy': 'first_and_last_only', 'adaptive_window_selection': False,
    }
