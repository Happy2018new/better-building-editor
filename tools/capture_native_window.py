"""Capture one owner-bound game's current client frame as a background PNG."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from PIL import Image, ImageStat
from diagnose_window_dpi import physical_dpi_context as physical_window_coordinates

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'.agents/skills/pyreact-debugging/scripts'))
from _session import load_session
from _window import (_find_game_window, _list_windows_windows, user32,
                     background_guard_state, foreground_policy_satisfied, user_foreground_allowed)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def foreground():
    import ctypes
    from ctypes import wintypes
    hwnd = user32.GetForegroundWindow()
    pid = wintypes.DWORD()
    if hwnd:
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return {'hwnd': int(hwnd or 0), 'pid': int(pid.value)}


def capture_guard(session, window):
    with physical_window_coordinates():
        guard = background_guard_state(session['game_pid'], Path(session['game_executable']).name)
    # Capture receipts need only window identity, not another application's title.
    guard['foreground'] = {key: guard['foreground'][key] for key in ('hwnd', 'pid')}
    if (not foreground_policy_satisfied(guard, session['game_pid']) or
            guard.get('window_noactivate') is not True or not guard.get('windows') or
            not all(value.get('pid') == session['game_pid'] and value.get('noactivate') is True
                    for value in guard['windows'])):
        raise RuntimeError('The owned game noactivation guard is invalid')
    matches = [value for value in guard['windows'] if value.get('hwnd') == window['hwnd']]
    if (len(matches) != 1 or matches[0].get('minimized') is not False or
            any(matches[0].get(key) != window.get(key) for key in ('pid', 'width', 'height'))):
        raise RuntimeError('The owned capture window changed or is unavailable')
    return guard


def capture(session_file, owner, output, executable):
    if output.exists():
        raise ValueError('Choose a fresh PNG output: '+str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path = output.with_suffix('.capture.json')
    if report_path.exists():
        raise ValueError('Choose a fresh capture report: '+str(report_path))
    allow_foreground = user_foreground_allowed()
    report = {'schema': 3 if allow_foreground else 2, 'ok': False, 'reliable': False,
              'background_only': not allow_foreground,
              'backend': 'Windows.Graphics.Capture', 'native_resolution': True,
              'path': str(output.resolve()), 'started_at': datetime.now(timezone.utc).isoformat()}
    if allow_foreground:
        report.update(foreground_policy='allow_user_foreground', user_foreground_allowed=True,
                      agent_activation_allowed=False, activation_fallback=False, guarded_no_activation=True,
                      window_coordinate_units='physical_pixels', dpi_awareness='per_monitor_v2')
    started = time.perf_counter()
    try:
        session = load_session(session_file, owner, live=True)
        if session is None:
            raise ValueError('An owner-bound managed session is required')
        report.update(session_file=session['session_file'], owner=session['owner'],
                      game_pid=session['game_pid'], game_identity=session['game_identity'])
        if allow_foreground:
            protection = session.get('noactivation', {})
            report['noactivation_requested'] = protection.get('requested') is True
            if not report['noactivation_requested'] or protection.get('window_noactivate') is not True:
                raise RuntimeError('User foreground capture requires a protected managed session')
        if allow_foreground:
            with physical_window_coordinates():
                window = _find_game_window(_list_windows_windows(), pid=session['game_pid'],
                                          process_name=Path(session['game_executable']).name)
        else:
            window = _find_game_window(_list_windows_windows(), pid=session['game_pid'],
                                      process_name=Path(session['game_executable']).name)
        if window is None:
            raise RuntimeError('The owned game has no visible window')
        report['window'] = window
        if window['minimized']:
            raise RuntimeError('The owned game is minimized; restoration is disabled')
        executable = executable.resolve(strict=True)
        report['helper'] = {'path': str(executable), 'sha256': sha256(executable),
                            'sources': {path.name: sha256(path) for path in
                                        sorted((ROOT/'tools/native_wgc').iterdir()) if path.is_file()}}
        if allow_foreground:
            report['guard_before'] = capture_guard(session, window)
            report['foreground_before'] = report['guard_before']['foreground']
        else:
            report['foreground_before'] = foreground()
        if report['foreground_before']['pid'] == session['game_pid'] and not allow_foreground:
            raise RuntimeError('The owned game is foreground; background capture is pending')
        command = [str(executable), str(window['hwnd']), str(session['game_pid']),
                   session['game_identity'], str(output.resolve())]
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf8',
                                timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
        if allow_foreground:
            report['guard_after'] = capture_guard(session, window)
            report['foreground_after'] = report['guard_after']['foreground']
        else:
            report['foreground_after'] = foreground()
        report['foreground_unchanged'] = report['foreground_before'] == report['foreground_after']
        report['background_safe'] = report['foreground_after']['pid'] != session['game_pid']
        report.update(helper_returncode=result.returncode, helper_stderr=result.stderr)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or 'Native WGC helper failed')
        frame = json.loads(result.stdout)
        report['frame'] = frame
        if not frame['ok'] or frame['frame_qpc_100ns'] < frame['request_qpc_100ns']:
            raise RuntimeError('Capture did not return a fresh compositor frame')
        if allow_foreground and (frame['width'], frame['height']) != (window['width'], window['height']):
            raise RuntimeError('Native capture dimensions differ from the guarded client window')
        current = load_session(session_file, owner, live=True)
        if current is None or any(current.get(key) != session.get(key) for key in
                ('session_file', 'owner', 'game_pid', 'game_identity', 'game_executable')):
            raise RuntimeError('The owned game identity changed during capture')
        with Image.open(output) as image:
            if image.format != 'PNG' or image.size != (frame['width'], frame['height']):
                raise RuntimeError('Native capture encoding or dimensions changed')
            report.update(width=image.width, height=image.height,
                          variance=ImageStat.Stat(image.convert('RGB')).var,
                          sha256=sha256(output), bytes=output.stat().st_size)
        if max(report['variance']) <= 1.:
            raise RuntimeError('Native WGC background capture is blank; activation fallback is disabled')
        # Switching between other applications is ordinary background use.
        # The capture helper has no activation path; keep both observations.
        if not report['background_safe'] and not allow_foreground:
            raise RuntimeError('The owned game became foreground during capture; acceptance is pending')
        report['ok'] = report['reliable'] = True
        return report
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        report.update(finished_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.perf_counter()-started)
        report_path.write_text(json.dumps(report, ensure_ascii=True, indent=2)+'\n', encoding='utf8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session')
    parser.add_argument('--owner')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--executable', type=Path,
                        default=Path(os.environ.get('MCDEV_NATIVE_CAPTURE_EXE',
                                     str(ROOT/'.runtime/native_wgc/build/Release/native_wgc_capture.exe'))))
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('WGC capture requires Windows')
    report = capture(args.session, args.owner, args.output, args.executable)
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    main()
