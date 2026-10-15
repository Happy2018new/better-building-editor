"""Take one passive host snapshot of an owned, live game before readiness."""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import time

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
SHARED_ROOT = ROOT.parents[1] if ROOT.parent.name == '.runtime' else ROOT
CAPTURE_EXECUTABLE = SHARED_ROOT / ('.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/'
                                    '.runtime/native_wgc/build/Release/native_wgc_capture.exe')
CAPTURE_SHA256 = 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
PERMITTED_STATES = frozenset(('starting', 'failed', 'ready'))
MINIMUM_CLIENT_SIZE = (640, 360)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_bound_session(path, owner, project):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    session = json.loads(raw)
    if session.get('schema') != 1 or Path(session.get('session_file', '')).resolve() != path:
        raise ValueError('Invalid startup session manifest')
    if not owner or session.get('owner') != owner:
        raise ValueError('Instance owner mismatch')
    if Path(session.get('project', '')).resolve() != Path(project).resolve(strict=True):
        raise ValueError('Instance project mismatch')
    if session.get('state') not in PERMITTED_STATES:
        raise ValueError('Startup observation does not permit state: ' + str(session.get('state')))
    if not session.get('noactivation', {}).get('requested'):
        raise ValueError('Session did not request the noactivation guard')
    return session, {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def validate_processes(session, inspect):
    observed = {}
    for kind in ('mcdk', 'game'):
        pid, identity = session.get(kind + '_pid'), session.get(kind + '_identity')
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 or not identity:
            raise ValueError('Missing startup identity: ' + kind)
        current = inspect(pid)
        if current is None:
            raise RuntimeError('Owned process is dead or unavailable: ' + kind)
        if str(current['identity']) != str(identity):
            raise RuntimeError('Owned process creation identity changed: ' + kind)
        expected = (session['game_executable'] if kind == 'game'
                    else session.get('noactivation', {}).get('mcdk', {}).get('path'))
        if not expected or Path(current['executable']).resolve() != Path(expected).resolve():
            raise RuntimeError('Owned process executable changed: ' + kind)
        observed[kind] = {'pid': pid, 'identity': str(identity), 'executable': current['executable']}
    return observed


def guarded_window(session, guard):
    if not guard.get('background_safe') or guard.get('foreground', {}).get('pid') == session['game_pid']:
        raise RuntimeError('Owned game is foreground; no activation fallback')
    windows = guard.get('windows', [])
    if not windows or not guard.get('window_noactivate'):
        raise RuntimeError('Owned game has no visible nonactivating window')
    matches = [window for window in windows
               if window.get('pid') == session['game_pid']
               and window.get('process', '').lower() == Path(session['game_executable']).name.lower()]
    if len(matches) != len(windows):
        raise RuntimeError('Current window ownership changed')
    window = max(matches, key=lambda item: item['width'] * item['height'])
    if not window.get('hwnd') or not window.get('noactivate'):
        raise RuntimeError('Current window lost the noactivation guard')
    if window.get('minimized'):
        raise RuntimeError('Owned game is minimized; no restoration fallback')
    if window['width'] < MINIMUM_CLIENT_SIZE[0] or window['height'] < MINIMUM_CLIENT_SIZE[1]:
        raise RuntimeError('Owned client dimensions are below the startup capture limit')
    return window


def ipc_port_evidence(session):
    expected = Path(session['session_file']).resolve().parent / 'mcdk.log'
    if Path(session.get('log', '')).resolve() != expected:
        raise ValueError('Startup log is not bound to this session')
    if not expected.is_file():
        return {'port': None, 'reason': 'Owned listener log is not available yet'}
    raw = expected.read_bytes()
    ports = {int(value) for value in re.findall(
        rb'\[MCDK\] IPC Bridge listening on port (\d+)', raw)}
    if len(ports) > 1 or any(not 1 <= port <= 65535 for port in ports):
        raise ValueError('Owned log has ambiguous IPC listener ports')
    return {'port': next(iter(ports), None), 'log_sha256': hashlib.sha256(raw).hexdigest(),
            'log_bytes': len(raw), 'actual_child_environment_recorded': False,
            'source': 'MCDK listener log; not a game getenv observation'}


def decode_tcp_table(raw):
    if len(raw) < 4:
        raise ValueError('Truncated IPv4 TCP table')
    count = struct.unpack_from('<I', raw)[0]
    if count > (len(raw) - 4) // 24:
        raise ValueError('Truncated IPv4 TCP rows')
    rows = []
    for index in range(count):
        state, local, local_port, remote, remote_port, pid = struct.unpack_from('<6I', raw, 4 + index * 24)
        rows.append({'state': state, 'pid': pid,
                     'local_address': str(ipaddress.IPv4Address(local.to_bytes(4, 'little'))),
                     'local_port': int.from_bytes(local_port.to_bytes(4, 'little')[:2], 'big'),
                     'remote_address': str(ipaddress.IPv4Address(remote.to_bytes(4, 'little'))),
                     'remote_port': int.from_bytes(remote_port.to_bytes(4, 'little')[:2], 'big')})
    return rows


def owned_tcp_evidence(rows, session, port):
    relevant = [] if port is None else [row for row in rows
        if row['pid'] in (session['game_pid'], session['mcdk_pid'])
        and (row['local_port'] == port or row['remote_port'] == port)]
    listener = any(row['pid'] == session['mcdk_pid'] and row['state'] == 2
                   and row['local_address'] == '127.0.0.1' and row['local_port'] == port
                   for row in relevant)
    game = [row for row in relevant if row['pid'] == session['game_pid'] and row['state'] == 5
            and row['local_address'] == '127.0.0.1' and row['remote_address'] == '127.0.0.1'
            and row['remote_port'] == port]
    paired = any(row['pid'] == session['mcdk_pid'] and row['state'] == 5
                 and row['local_address'] == '127.0.0.1' and row['remote_address'] == '127.0.0.1'
                 and row['local_port'] == port and row['remote_port'] == client['local_port']
                 for client in game for row in relevant)
    return {'ipv4_rows': relevant, 'owned_listener_observed': listener,
            'owned_established_pair_observed': paired, 'passive_table_only': True,
            'private_ipc_connection_attempted': False,
            'limits': 'An OS established pair is not an SDK-ready result; polling can miss transient connections.'}


class WindowsHost:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('Passive startup observation requires Windows')
        sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
        import _session
        import _window
        self.session_api, self.window_api = _session, _window

    def inspect_process(self, pid):
        from ctypes import wintypes
        kernel = self.session_api._kernel()
        kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                     wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            identity = self.session_api._identity(kernel, handle)
            if identity is None:
                return None
            size = wintypes.DWORD(32768)
            path = ctypes.create_unicode_buffer(size.value)
            if not kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
                raise ctypes.WinError(ctypes.get_last_error())
            return {'identity': identity, 'executable': path.value}
        finally:
            kernel.CloseHandle(handle)

    def guard(self, session):
        return self.window_api.background_guard_state(session['game_pid'], Path(session['game_executable']).name)

    def tcp_rows(self):
        from ctypes import wintypes
        library = ctypes.WinDLL('iphlpapi', use_last_error=True)
        query = library.GetExtendedTcpTable
        query.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
                          wintypes.ULONG, ctypes.c_int, wintypes.ULONG]
        query.restype = wintypes.DWORD
        size = wintypes.DWORD()
        result = query(None, ctypes.byref(size), True, 2, 5, 0)
        if result not in (0, 122):
            raise OSError(result, 'GetExtendedTcpTable size query failed')
        for _ in range(3):
            buffer = ctypes.create_string_buffer(size.value)
            result = query(buffer, ctypes.byref(size), True, 2, 5, 0)
            if result == 0:
                return decode_tcp_table(buffer.raw[:size.value])
            if result != 122:
                raise OSError(result, 'GetExtendedTcpTable failed')
        raise RuntimeError('IPv4 TCP table changed during all bounded reads')

    def capture(self, command, timeout):
        return subprocess.run(command, capture_output=True, text=True, encoding='utf8', timeout=timeout,
                              creationflags=subprocess.CREATE_NO_WINDOW)


def observe(session_file, owner, project, output, executable=CAPTURE_EXECUTABLE,
            timeout_seconds=15, host=None):
    output, executable = Path(output), Path(executable)
    receipt = output.with_suffix('.startup.json')
    if output.exists() or receipt.exists():
        raise ValueError('Startup evidence must use fresh output paths')
    if not 0 < timeout_seconds <= 15:
        raise ValueError('Single startup observation timeout must be in (0, 15] seconds')
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    report = {'schema': 1, 'scope': 'Passive host startup snapshot', 'ok': False, 'reliable': False, 'timeout': False,
              'production_acceptance': False, 'game_or_mcdk_launched': False, 'sdk_or_mcp_called': False,
              'game_input_or_window_mutation_attempted': False, 'background_only': True,
              'started_at': datetime.now(timezone.utc).isoformat(), 'timeout_seconds': timeout_seconds,
              'output': str(output.resolve()), 'permitted_states': sorted(PERMITTED_STATES)}
    try:
        session, manifest = read_bound_session(session_file, owner, project)
        report.update(manifest=manifest, session_id=session.get('id'), owner=owner,
                      project=str(Path(project).resolve()), state_before=session['state'])
        executable = executable.resolve(strict=True)
        if executable != CAPTURE_EXECUTABLE.resolve(strict=True) or sha256(executable) != CAPTURE_SHA256:
            raise ValueError('Capture helper path or SHA-256 is not the approved single-WGC helper')
        report['helper'] = {'path': str(executable), 'sha256': CAPTURE_SHA256}
        host = host if host is not None else WindowsHost()
        report['processes_before'] = validate_processes(session, host.inspect_process)
        report['ipc_port'] = ipc_port_evidence(session)
        report['tcp'] = owned_tcp_evidence(host.tcp_rows(), session, report['ipc_port']['port'])
        report['guard_before'] = host.guard(session)
        window = guarded_window(session, report['guard_before'])
        report['window'] = window
        remaining = timeout_seconds - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError('Startup observation deadline reached before capture')
        command = [str(executable), str(window['hwnd']), str(session['game_pid']),
                   str(session['game_identity']), str(output.resolve())]
        result = host.capture(command, remaining)
        report.update(helper_returncode=result.returncode, helper_stdout=result.stdout, helper_stderr=result.stderr)
        after, report['manifest_after'] = read_bound_session(session_file, owner, project)
        for key in ('id', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity', 'game_executable'):
            if after.get(key) != session.get(key):
                raise RuntimeError('Session startup binding changed during capture: ' + key)
        if after['noactivation'].get('mcdk', {}).get('path') != session['noactivation'].get('mcdk', {}).get('path'):
            raise RuntimeError('Session MCDK executable binding changed during capture')
        report['processes_after'] = validate_processes(after, host.inspect_process)
        report['state_after'] = after['state']
        report['guard_after'] = host.guard(session)
        current = guarded_window(session, report['guard_after'])
        if any(current[key] != window[key] for key in ('hwnd', 'width', 'height')):
            raise RuntimeError('Owned window or dimensions changed during capture')
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or 'Single-WGC helper failed')
        frame = json.loads(result.stdout)
        report['frame'] = frame
        if (frame.get('ok') is not True or frame.get('backend') != 'Windows.Graphics.Capture'
                or frame.get('native_resolution') is not True
                or frame['frame_qpc_100ns'] < frame['request_qpc_100ns']):
            raise RuntimeError('Single-WGC helper did not return a fresh native compositor frame')
        if (frame['width'], frame['height']) != (window['width'], window['height']):
            raise RuntimeError('Captured dimensions differ from the guarded current client')
        with Image.open(output) as image:
            if image.format != 'PNG' or image.size != (frame['width'], frame['height']):
                raise RuntimeError('Startup image encoding or dimensions changed')
            report['pixels'] = {'width': image.width, 'height': image.height,
                                'variance': ImageStat.Stat(image.convert('RGB')).var,
                                'sha256': sha256(output), 'bytes': output.stat().st_size}
        if max(report['pixels']['variance']) <= 1.0:
            raise RuntimeError('Startup image is blank; no activation fallback')
        if time.monotonic() - started > timeout_seconds:
            raise TimeoutError('Startup observation deadline exceeded')
        report['ok'] = report['reliable'] = True
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
        report['timeout'] = isinstance(error, (TimeoutError, subprocess.TimeoutExpired))
    finally:
        report.update(finished_at=datetime.now(timezone.utc).isoformat(),
                      elapsed_seconds=time.monotonic() - started)
        with receipt.open('x', encoding='ascii') as handle:
            handle.write(json.dumps(report, ensure_ascii=True, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--capture-executable', type=Path, default=CAPTURE_EXECUTABLE)
    parser.add_argument('--timeout-seconds', type=float, default=15)
    args = parser.parse_args()
    report = observe(args.session, args.owner, args.project, args.output,
                     args.capture_executable, args.timeout_seconds)
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
