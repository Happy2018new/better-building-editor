"""Observe exact process handles until stop, identity exit, or bound deadline."""
from datetime import datetime, timezone
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import sys
import time

import guard_policy
from modal_guard import assertion_status_breach

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import _kernel, _identity, process_identity, load_session


def sample_process(pid, expected):
    kernel = _kernel()
    kernel.GetProcessHandleCount.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return {'pid': pid, 'identity_verified': False, 'handles': None}
    try:
        actual = _identity(kernel, handle)
        row = {'pid': pid, 'expected_identity': expected, 'observed_identity': actual,
               'identity_verified': actual == expected, 'handles': None}
        if row['identity_verified']:
            count = wintypes.DWORD()
            if not kernel.GetProcessHandleCount(handle, ctypes.byref(count)):
                raise ctypes.WinError(ctypes.get_last_error())
            row['handles'] = count.value
        return row
    finally:
        kernel.CloseHandle(handle)


def main():
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    launch = json.loads((WORK / 'launch/launch.json').read_bytes())
    session = load_session(launch['session_file'], binding['owner'], live=False)
    assert session.get('state') in ('starting', 'ready'), 'Unexpected startup state for exact-identity guard'
    for kind in ('game', 'mcdk'):
        assert session.get(kind + '_pid') and session.get(kind + '_identity')
        assert process_identity(session[kind + '_pid']) == session[kind + '_identity']
        assert launch[kind + '_pid'] == session[kind + '_pid'] and launch[kind + '_identity'] == session[kind + '_identity']
    assert Path(session['project']).resolve() == Path(binding['project']).resolve()
    remaining = guard_policy.remaining_seconds(binding['guard_deadline_utc'])
    output = WORK / 'continuous-handle-guard-v1.json'
    stop_file = WORK / 'continuous-handle-guard.stop'
    assert not output.exists() and not stop_file.exists()
    if '--detach' in sys.argv:
        process_receipt = WORK / 'continuous-handle-guard-process-v1.json'
        assert not process_receipt.exists()
        with (WORK / 'continuous-handle-guard.stdout.txt').open('xb') as stdout, \
                (WORK / 'continuous-handle-guard.stderr.txt').open('xb') as stderr:
            child = subprocess.Popen([sys.executable, '-B', '-X', 'utf8', str(Path(__file__))],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                creationflags=subprocess.CREATE_NO_WINDOW)
        row = {'pid': child.pid, 'identity': process_identity(child.pid)}
        process_receipt.write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
        start_deadline = time.monotonic() + 8
        while time.monotonic() < start_deadline:
            if output.exists():
                try:
                    data = json.loads(output.read_bytes())
                except (OSError, ValueError):
                    data = None
                if data and data.get('samples'):
                    assert all(data['samples'][0][kind]['identity_verified'] for kind in ('game', 'mcdk'))
                    assert not data.get('guard_breach')
                    assert not data.get('modal_guard_breach')
                    print(json.dumps(row | {'first_sample_verified': True}))
                    return
            if child.poll() is not None:
                raise RuntimeError('Watchdog exited before its first verified sample')
            time.sleep(.1)
        raise RuntimeError('Watchdog did not produce verified coverage; do not start capture')
    receipt = {'schema': 1, 'owner': binding['owner'], 'maximum_handles': guard_policy.MAX_HANDLES,
        'rapid_step_growth_limit': guard_policy.RAPID_GROWTH,
        'deadline_utc': binding['guard_deadline_utc'], 'samples': [], 'guard_breach': None,
        'stopped': False, 'completed': False}
    previous = None
    deadline = time.monotonic() + remaining
    try:
        while True:
            row = {'at': datetime.now(timezone.utc).isoformat(),
                   **{kind: sample_process(session[kind + '_pid'], session[kind + '_identity'])
                      for kind in ('game', 'mcdk')}}
            receipt['samples'].append(row)
            receipt['modal_guard_breach'] = assertion_status_breach(WORK, binding['owner'], session['game_pid'])
            for kind in ('game', 'mcdk'):
                current = row[kind]['handles']
                prior = previous[kind]['handles'] if previous is not None else None
                if guard_policy.handle_breach(current, prior):
                    receipt['guard_breach'] = {'kind': kind, 'handles': current, 'previous': prior}
            live = all(row[kind]['identity_verified'] for kind in ('game', 'mcdk'))
            expired = time.monotonic() >= deadline
            receipt.update(deadline_expired=expired, identity_ended=not live)
            if receipt['guard_breach'] or receipt['modal_guard_breach'] or expired:
                result = subprocess.run([sys.executable, '-B', '-X', 'utf8',
                    str(ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'),
                    'stop', '--session', launch['session_file'], '--owner', binding['owner']],
                    cwd=ROOT, capture_output=True, text=True, timeout=45)
                receipt['ordinary_stop'] = {'exit_code': result.returncode,
                    'stdout': result.stdout, 'stderr': result.stderr}
                receipt['stopped'] = result.returncode == 0
                break
            if not live or stop_file.exists():
                receipt['stop_file_observed'] = stop_file.exists()
                break
            output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
            previous = row
            time.sleep(1.)
        receipt['completed'] = True
    finally:
        output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
