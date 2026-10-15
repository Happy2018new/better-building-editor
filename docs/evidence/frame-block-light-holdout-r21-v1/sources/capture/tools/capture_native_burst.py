"""Capture a bounded, owner-bound native WGC burst without activating the game."""
import argparse
from contextlib import contextmanager
import ctypes
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
import _session
import _window
from _session import load_session
from _window import _find_game_window, background_guard_state, user_foreground_allowed

MAX_JSON_BYTES = 64 * 1024 * 1024
MAX_PNG_BYTES = 136 * 1024 * 1024
MAX_PIXELS = 33554432
NOACTIVATE = 0x08000000
TIMESTAMP_ERRORS = frozenset(('frame_not_after_request', 'frame_not_strictly_monotonic',
                             'frame_timestamp_in_future', 'frame_delivery_too_old',
                             'frame_after_planned_interval'))


class CaptureError(RuntimeError):
    def __init__(self, report):
        self.report = report
        super().__init__(report['error'])


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _integer(value, label, minimum=0, maximum=None):
    _require(type(value) is int and value >= minimum and
             (maximum is None or value <= maximum), label + ' is outside its integer range')
    return value


def _equal(actual, expected, label):
    _require(type(actual) is type(expected) and actual == expected, label + ' mismatch')
    if isinstance(expected, dict):
        for key, value in expected.items():
            _equal(actual[key], value, label + '.' + str(key))
    elif isinstance(expected, list):
        for index, value in enumerate(expected):
            _equal(actual[index], value, '%s[%d]' % (label, index))


def _expected_hash(value):
    _require(isinstance(value, str) and len(value) == 64 and
             all(char in '0123456789abcdefABCDEF' for char in value),
             'An explicit expected SHA256 is required')
    return value.lower()


def _linked(path):
    return path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())


def _binary_record(path, expected):
    expected = _expected_hash(expected)
    path = Path(path).resolve(strict=True)
    _require(path.is_file(), 'Binary is not a regular file: ' + str(path))
    record = {'path': str(path), 'sha256': sha256(path)}
    _equal(record['sha256'], expected, 'Binary SHA256')
    return record


def _host_sources():
    paths = [Path(__file__), Path(_session.__file__), Path(_window.__file__)]
    paths += [ROOT / 'tools/native_wgc' / name for name in
              ('burst_main.cpp', 'burst_window_capture.cpp', 'burst_window_capture.h',
               'CMakeLists.txt', 'main.cpp', 'window_capture.cpp', 'window_capture.h')]
    return {str(path.resolve()): sha256(path) for path in paths}


def _session_binding(session_file, owner, allow_foreground=False):
    _require(isinstance(owner, str) and bool(owner.strip()), 'An explicit session owner is required')
    path = Path(session_file).resolve(strict=True)
    session = load_session(path, owner, live=True)
    _require(isinstance(session, dict), 'An owner-bound managed session is required')
    _equal(session.get('schema'), 1, 'Session schema')
    _equal(session.get('owner'), owner, 'Session owner')
    _equal(session.get('state'), 'ready', 'Session state')
    _require(Path(session.get('session_file', '')).resolve() == path, 'Session file binding changed')
    _require(Path(session.get('project', '')).resolve(strict=True) == ROOT.resolve(),
             'Session belongs to a different project')
    for prefix in ('game', 'mcdk'):
        _integer(session.get(prefix + '_pid'), prefix + ' PID', 1, 0xffffffff)
        identity = session.get(prefix + '_identity')
        _require(isinstance(identity, str) and identity.isascii() and identity.isdecimal() and
                 0 < int(identity) <= 0xffffffffffffffff, prefix + ' creation identity is invalid')
    for key in ('id', 'game_executable', 'mcp_url'):
        _require(isinstance(session.get(key), str) and bool(session[key]), 'Missing session ' + key)
    protection = session.get('noactivation')
    _require(isinstance(protection, dict) and protection.get('schema') == 1 and
             all(protection.get(key) is True for key in
                 ('requested', 'background_safe', 'window_noactivate')),
             'Capture requires a verified protected background session')
    protected_binaries = {}
    for key in ('mcdk', 'dll'):
        source = protection.get(key)
        _require(isinstance(source, dict), 'Missing protected ' + key + ' binary binding')
        protected_binaries[key] = _binary_record(source.get('path'), source.get('sha256'))
    keys = ('id', 'owner', 'state', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity',
            'game_executable', 'mcp_url', 'noactivation')
    binding = json.loads(json.dumps({key: session[key] for key in keys}))
    binding.update(session_file=str(path), project=str(ROOT.resolve()))
    if allow_foreground:
        binding['user_foreground_allowed'] = True
    return binding, protected_binaries


@contextmanager
def _physical_dpi_context():
    api = ctypes.WinDLL('user32', use_last_error=True).SetThreadDpiAwarenessContext
    api.argtypes = [ctypes.c_void_p]
    api.restype = ctypes.c_void_p
    previous = api(ctypes.c_void_p(-4))
    if not previous:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        if not api(previous):
            raise ctypes.WinError(ctypes.get_last_error())


def _background(binding, expected_window=None, report=None, label='before'):
    with _physical_dpi_context():
        guard = background_guard_state(binding['game_pid'], Path(binding['game_executable']).name)
    if report is not None:
        report['background_' + label] = guard
    _require(isinstance(guard, dict), 'Independent background observation is unavailable')
    _require(guard.get('window_noactivate') is True,
             'Independent background/noactivation guard failed')
    foreground = guard.get('foreground')
    _require(isinstance(foreground, dict) and type(foreground.get('pid')) is int and
             foreground['pid'] >= 0 and type(foreground.get('hwnd')) is int and
             foreground['hwnd'] >= 0, 'Independent foreground observation is invalid')
    background = foreground['pid'] != binding['game_pid']
    _equal(guard.get('background_safe'), background, 'Independent actual background status')
    _require(background or binding.get('user_foreground_allowed') is True, 'Owned game is foreground')
    windows = guard.get('windows')
    _require(isinstance(windows, list) and bool(windows), 'Owned game has no visible window')
    _require(all(isinstance(window, dict) and window.get('pid') == binding['game_pid'] and
                 window.get('noactivate') is True for window in windows),
             'Owned window background protection changed')
    window = _find_game_window(windows, pid=binding['game_pid'],
                               process_name=Path(binding['game_executable']).name)
    _require(window is not None and window.get('minimized') is False,
             'Owned game is unavailable or minimized')
    for key in ('hwnd', 'width', 'height'):
        _integer(window.get(key), 'Window ' + key, 1)
    for key in ('x', 'y'):
        _require(type(window.get(key)) is int, 'Window coordinate is invalid')
    _require(window['width'] * window['height'] <= MAX_PIXELS, 'Client pixel limit exceeded')
    if expected_window is not None:
        for key in ('hwnd', 'pid', 'x', 'y', 'width', 'height'):
            _equal(window.get(key), expected_window.get(key), 'Independent window ' + key)
    return guard, window


def _json_document(raw):
    _require(0 < len(raw) <= MAX_JSON_BYTES, 'JSON evidence payload size is invalid')

    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, 'Duplicate JSON field: ' + key)
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError('Non-finite JSON value: ' + value)

    return json.loads(raw.decode('utf8'), object_pairs_hook=unique, parse_constant=invalid_constant)


def _artifact(directory, name, limit):
    _require(isinstance(name, str) and Path(name).name == name and
             name not in ('', '.', '..'), 'Artifact path must be a direct child')
    path = directory / name
    _require(not _linked(path) and path.is_file() and path.resolve().parent == directory,
             'Artifact is missing, linked or outside output: ' + name)
    _require(0 < path.stat().st_size <= limit, 'Artifact size is invalid: ' + name)
    raw = path.read_bytes()
    _require(0 < len(raw) <= limit, 'Artifact changed while reading: ' + name)
    return raw, {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def _rectangle(value, label):
    _require(isinstance(value, list) and len(value) == 4 and
             all(type(axis) is int for axis in value) and
             value[2] > value[0] and value[3] > value[1], label + ' is invalid')
    return value


def _window_state(state, binding, window, baseline=None):
    _require(isinstance(state, dict), 'Native window guard snapshot is missing')
    for key, value in (('hwnd', window['hwnd']), ('pid', binding['game_pid']),
                       ('creation_time', binding['game_identity'])):
        _equal(state.get(key), value, 'Native window ' + key)
    for key in ('process_live', 'window_valid', 'visible', 'geometry_valid', 'window_noactivate_style'):
        _equal(state.get(key), True, 'Native window ' + key)
    for key in ('minimized', 'cloaked'):
        _equal(state.get(key), False, 'Native window ' + key)
    _integer(state.get('thread_id'), 'Native window thread', 1)
    style = _integer(state.get('extended_style'), 'Native window style', 0, 0xffffffff)
    _require(bool(style & NOACTIVATE), 'Native window lost WS_EX_NOACTIVATE')
    foreground_pid = _integer(state.get('foreground_pid'), 'Native foreground PID')
    background = foreground_pid != binding['game_pid']
    _require(background or binding.get('user_foreground_allowed') is True,
             'Native guard observed foreground game')
    if binding.get('user_foreground_allowed') is True:
        _equal(state.get('background_safe'), background, 'Native actual background status')
    _integer(state.get('foreground_hwnd'), 'Native foreground HWND')
    observed = _integer(state.get('observed_qpc_100ns'), 'Native guard observation', 1)
    client = _rectangle(state.get('client_rect_screen'), 'Native client rectangle')
    _equal(client, [window['x'], window['y'], window['x'] + window['width'],
                    window['y'] + window['height']], 'Physical native client rectangle')
    frame = _rectangle(state.get('dwm_frame_rect'), 'Native DWM rectangle')
    _require(frame[0] <= client[0] and frame[1] <= client[1] and
             frame[2] >= client[2] and frame[3] >= client[3] and
             (frame[2] - frame[0]) * (frame[3] - frame[1]) <= MAX_PIXELS,
             'Native client crop is outside the bounded DWM frame')
    if baseline is not None:
        for key in ('thread_id', 'client_rect_screen', 'dwm_frame_rect'):
            _equal(state.get(key), baseline.get(key), 'Native stable window ' + key)
        _require(observed >= baseline['observed_qpc_100ns'], 'Native guard timestamp moved backwards')
    return observed


def _png_evidence(raw, evidence, width, height):
    _require(raw.startswith(b'\x89PNG\r\n\x1a\n') and
             raw.endswith(b'\x00\x00\x00\x00IEND\xaeB\x60\x82'),
             'PNG signature, termination or trailing data is invalid')
    with Image.open(BytesIO(raw)) as image:
        _require(image.format == 'PNG' and image.mode == 'RGB' and image.n_frames == 1 and
                 image.size == (width, height), 'PNG encoding or native dimensions mismatch')
        image.verify()
    with Image.open(BytesIO(raw)) as image:
        image.load()
        variance = ImageStat.Stat(image).var
    evidence.update(width=width, height=height, mode='RGB', variance=variance)
    _require(max(variance) > 1., 'Native PNG is blank; activation fallback is disabled')


def _timestamp_error(frame, observed, request, previous, deadline):
    return ('frame_not_after_request' if frame <= request else
            'frame_not_strictly_monotonic' if frame <= previous else
            'frame_timestamp_in_future' if frame > observed else
            'frame_delivery_too_old' if observed - frame > 10000000 else
            'frame_after_planned_interval' if frame > deadline else '')


def _validate_timestamp_wait(record, binding, window, baseline, request, previous, deadline, max_gap):
    initial = record.get('initial_timestamp_assessment')
    wait = record.get('future_timestamp_wait')
    _require(isinstance(initial, dict) and isinstance(wait, dict), 'Frame initial/wait assessment is missing')
    frame, observed = record['frame_qpc_100ns'], record['observed_qpc_100ns']
    initial_observed = _integer(initial.get('observed_qpc_100ns'), 'Initial frame observation', request)
    initial_error = _timestamp_error(frame, initial_observed, request, previous, deadline)
    _equal(initial.get('error'), initial_error, 'Initial timestamp policy')
    _equal(initial.get('frame_age_100ns'), initial_observed - frame, 'Initial frame age')
    _equal(initial.get('delta_from_previous_or_request_100ns'), frame - previous, 'Initial frame interval')
    _equal(initial.get('gap_exceeded'), not initial_error and frame - previous > max_gap, 'Initial frame gap')
    requested = (initial_error == 'frame_timestamp_in_future' and frame <= deadline and
                 frame - initial_observed <= 500000)
    wait_deadline = min(initial_observed + 500000, deadline) if requested else 0
    _equal(wait.get('requested'), requested, 'Future timestamp wait eligibility')
    _equal(wait.get('deadline_qpc_100ns'), wait_deadline, 'Future timestamp wait deadline')
    _equal(wait.get('elapsed_100ns'), observed - initial_observed if requested else 0, 'Actual future wait')
    guards = wait.get('guards')
    _require(isinstance(guards, list) and len(guards) <= 128, 'Future wait guards are unbounded or missing')
    _require(record['before']['observed_qpc_100ns'] <= initial_observed <= observed,
             'Initial/final frame observations moved backwards')
    if requested:
        _equal(wait.get('outcome'), 'eligible', 'Future timestamp wait outcome')
        _require(bool(guards) and frame <= observed <= wait_deadline,
                 'Future timestamp waited past its budget or never became eligible')
        previous_guard = initial_observed
        for state in guards:
            guarded = _window_state(state, binding, window, baseline)
            _require(previous_guard <= guarded <= observed, 'Future wait guard timestamps moved backwards')
            previous_guard = guarded
        _equal(previous_guard, observed, 'Final future wait QPC observation')
    else:
        _equal(wait.get('outcome'), 'not_requested', 'Unrequested future wait outcome')
        _equal(guards, [], 'Unrequested future wait guards')
        _equal(observed, initial_observed, 'Unrequested wait changed frame observation')
    return {'waited': requested, 'initial_future_offset_100ns': max(0, frame - initial_observed),
            'elapsed_100ns': wait['elapsed_100ns'], 'guard_observations': len(guards)}


def _validate_native(report, binding, window, stdout):
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
    for key, value in (('schema', 2 if allow_foreground else 1), ('backend', 'Windows.Graphics.Capture'),
                       ('mode', 'persistent_burst'), ('clock', 'compositor_system_relative_qpc_100ns'),
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
    max_gap = report['request']['max_gap_ms'] * 10000
    baseline = native.get('baseline')
    _require(_window_state(baseline, binding, window) <= request, 'Native baseline is after request')
    records = native.get('frames')
    _require(isinstance(records, list) and len(records) <= report['request']['max_frames'] * 4 + 64,
             'Native frame attempts are unbounded or invalid')
    expected_files = {'manifest.json'}
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
        last_time = _window_state(record.get('last_window_state'), binding, window, baseline)
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
            guard_times = [_window_state(record.get(key), binding, window, baseline) for key in
                           ('before', 'after_readback', 'before_png_write', 'after_png_write')]
            _require(last_guard <= guard_times[0] <= observed <= guard_times[1] <=
                     guard_times[2] <= guard_times[3], 'Native per-frame guard timestamps moved backwards')
            _equal(record.get('last_window_state'), record.get('after_png_write'), 'Final frame guard')
            accepted.append(frame)
            gaps.append(delta)
        else:
            _equal(record.get('png'), None, 'Rejected timestamp PNG')
            if record['error'] == 'frame_after_planned_interval':
                _require(sequence == len(records), 'Frames follow the terminal postinterval receipt')
        last_guard = last_time
    _equal({path.name for path in directory.iterdir()}, expected_files, 'Native artifact inventory')
    final_guard = _window_state(native.get('final_window_state'), binding, window, baseline)
    _require(last_guard <= final_guard <= finished, 'Native final guard timestamp is invalid')
    valid_count = len(accepted)
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


def _failure(report, phase, error):
    report['errors'].append({'phase': phase, 'type': type(error).__name__, 'message': str(error)})


def _check(report, phase, callback):
    try:
        callback()
    except Exception as error:
        _failure(report, phase, error)


def _run_helper(report, command):
    timeout = report['request']['planned_duration_ms'] / 1000. + 15.
    report['helper_timeout_seconds'] = timeout
    report['helper_command'] = command
    helper = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    report['helper_pid'] = helper.pid
    stdout = stderr = b''
    try:
        try:
            stdout, stderr = helper.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            report['helper_timed_out'] = True
            _failure(report, 'helper', TimeoutError('Native helper exceeded the duration + 15 second limit'))
            stdout, stderr = error.output or b'', error.stderr or b''
            # Popen.kill uses this child's retained process handle on Windows.
            helper.kill()
            stdout, stderr = helper.communicate(timeout=5)
            report['own_helper_terminated'] = True
    finally:
        if helper.poll() is None:
            helper.kill()
            helper.wait(timeout=5)
            report['own_helper_terminated'] = True
        report['helper_returncode'] = helper.poll()
        report['helper_stderr'] = stderr.decode('utf8', 'replace')
        report['helper_stdout'] = {'bytes': len(stdout), 'sha256': hashlib.sha256(stdout).hexdigest()}
        if report['helper_timed_out'] or report['helper_returncode'] != 0:
            report['helper_stdout']['text'] = stdout.decode('utf8', 'replace')
    if report['helper_returncode'] != 0:
        _failure(report, 'helper', RuntimeError('Native helper exited with code %s' % report['helper_returncode']))
    return stdout


def _inventory(report):
    directory = Path(report['output_directory'])
    if not directory.exists():
        report['artifacts'] = []
        return
    _require(not _linked(directory) and directory.is_dir(), 'Output became a linked or invalid directory')
    entries = list(directory.iterdir())
    _require(len(entries) <= report['request']['max_frames'] * 8 + 129, 'Too many output artifacts')
    artifacts = report['artifacts'] = []
    for path in sorted(entries):
        limit = MAX_JSON_BYTES if path.suffix == '.json' else MAX_PNG_BYTES
        raw, record = _artifact(directory, path.name, limit)
        artifacts.append(record)
        if report['errors'] and path.name.endswith('.capture.json'):
            try:
                record['receipt'] = _json_document(raw)
            except (ValueError, UnicodeError) as error:
                record['receipt_error'] = str(error)
    if not report['errors']:
        bound = {report['native_manifest_file']['path']: report['native_manifest_file']['sha256']}
        for frame in report['frames']:
            for key in ('receipt', 'png'):
                if frame[key] is not None:
                    bound[frame[key]['path']] = frame[key]['sha256']
        _equal({record['path']: record['sha256'] for record in artifacts}, bound,
               'Final artifact SHA256 binding')


def _write_report(handle, report):
    handle.seek(0)
    json.dump(report, handle, ensure_ascii=True, indent=2)
    handle.write('\n')
    handle.truncate()
    handle.flush()
    os.fsync(handle.fileno())


def capture(session_file, owner, output, executable, expected_sha256,
            duration_ms=1000, max_frames=180, max_gap_ms=150):
    allow_foreground = user_foreground_allowed()
    output = Path(output).absolute()
    _require(not output.exists() and not _linked(output), 'Choose a fresh native output directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    output = output.parent.resolve() / output.name
    report_path = output.with_name(output.name + '.capture.json')
    _require(not report_path.exists() and not _linked(report_path), 'Choose a fresh wrapper receipt')
    report = {'schema': 2 if allow_foreground else 1, 'ok': False, 'reliable': False, 'capture_valid': False,
              'temporal_complete': False, 'background_only': not allow_foreground, 'activation_fallback': False,
              'native_resolution': True, 'pixel_acceptance': False, 'animation_acceptance': False,
              'source_frame_loss_known': False, 'backend': 'Windows.Graphics.Capture',
              'mode': 'persistent_burst', 'output_directory': str(output),
              'wrapper_receipt': str(report_path), 'started_at': datetime.now(timezone.utc).isoformat(),
              'request': {'planned_duration_ms': duration_ms, 'max_frames': max_frames, 'max_gap_ms': max_gap_ms},
              'helper_timed_out': False, 'own_helper_terminated': False, 'errors': []}
    if allow_foreground:
        report.update(foreground_policy='allow_user_foreground', user_foreground_allowed=True,
                      agent_activation_allowed=False)
    started = time.perf_counter()
    with report_path.open('x', encoding='ascii') as receipt:
        _write_report(receipt, report)
        phase = 'preflight'
        try:
            _integer(duration_ms, 'Duration milliseconds', 50, 60000)
            _integer(max_frames, 'Frame cap', 1, 1800)
            _integer(max_gap_ms, 'Maximum gap milliseconds', 1, 5000)
            report['helper'] = _binary_record(executable, expected_sha256)
            report['expected_helper_sha256'] = _expected_hash(expected_sha256)
            report['host_sources_before'] = _host_sources()
            binding, binaries = _session_binding(session_file, owner, allow_foreground)
            report.update(instance=binding, protected_binaries_before=binaries)
            guard, window = _background(binding, report=report)
            report.update(background_before=guard, window=window)
            _equal(_binary_record(executable, expected_sha256), report['helper'], 'Prelaunch helper')
            _require(not output.exists() and not _linked(output), 'Native output appeared before launch')
            phase = 'helper'
            command = [report['helper']['path'], str(window['hwnd']), str(binding['game_pid']),
                       binding['game_identity'], str(output), str(duration_ms), str(max_frames), str(max_gap_ms)]
            if allow_foreground:
                command.append('--allow-user-foreground')
            stdout = b''
            try:
                stdout = _run_helper(report, command)
            except Exception as error:
                _failure(report, 'helper', error)

            def postflight(label):
                current, binaries_after = _session_binding(session_file, owner, allow_foreground)
                report['instance_' + label] = current
                report['protected_binaries_' + label] = binaries_after
                _equal(current, binding, 'Owner/session identity')
                guard_after, _ = _background(binding, window, report, label)
                report['background_' + label] = guard_after
                if allow_foreground:
                    report['background_safe'] = guard_after['background_safe']

            def helper_binding():
                report['helper_after'] = _binary_record(executable, expected_sha256)
                _equal(report['helper_after'], report['helper'], 'Helper identity after capture')
                report['host_sources_after'] = _host_sources()
                _equal(report['host_sources_after'], report['host_sources_before'], 'Host source hashes')

            _check(report, 'postflight', lambda: postflight('after'))
            _check(report, 'helper_binding', helper_binding)
            _check(report, 'native_evidence', lambda: _validate_native(report, binding, window, stdout))
            _check(report, 'final_session', lambda: postflight('final'))
        except Exception as error:
            _failure(report, phase, error)
        finally:
            _check(report, 'artifact_inventory', lambda: _inventory(report))
            if report['errors']:
                report['error'] = '; '.join('%s: %s' % (error['phase'], error['message'])
                                            for error in report['errors'])
            else:
                report['ok'] = report['reliable'] = report['capture_valid'] = report['temporal_complete'] = True
            report.update(finished_at=datetime.now(timezone.utc).isoformat(),
                          elapsed_seconds=time.perf_counter() - started)
            _write_report(receipt, report)
    if not report['ok']:
        raise CaptureError(report)
    return report


def summary(report):
    result = {key: report[key] for key in ('ok', 'capture_valid', 'temporal_complete',
                                          'animation_acceptance', 'wrapper_receipt', 'output_directory')}
    timeline = report.get('validated_timeline', {})
    result.update({key: value for key, value in timeline.items() if key != 'temporal_complete'})
    if 'temporal_complete' in timeline:
        result['validated_timeline_temporal_complete'] = timeline['temporal_complete']
    result['helper_returncode'] = report.get('helper_returncode')
    result['helper_timed_out'] = report['helper_timed_out']
    if report.get('error'):
        result['error'] = report['error']
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--executable', required=True, type=Path)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--duration-ms', type=int, default=1000)
    parser.add_argument('--max-frames', type=int, default=180)
    parser.add_argument('--max-gap-ms', type=int, default=150)
    args = parser.parse_args(argv)
    if os.name != 'nt':
        parser.error('Native WGC burst capture requires Windows')
    try:
        report = capture(args.session, args.owner, args.output, args.executable,
                         args.expected_sha256, args.duration_ms, args.max_frames, args.max_gap_ms)
    except CaptureError as error:
        print(json.dumps(summary(error.report), ensure_ascii=True))
        return 1
    except (OSError, ValueError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=True))
        return 1
    print(json.dumps(summary(report), ensure_ascii=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
