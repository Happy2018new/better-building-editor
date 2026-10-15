"""Retain exact owned process handles and record exit codes without mutation."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from probe_intrinsic_glint_ui_r21 import load_session
from _session import _identity, _kernel


def watch(session_path, owner, output):
    if output.exists():
        raise ValueError('Exit evidence must use a fresh output path')
    session = load_session(session_path, owner, live=True)
    kernel = _kernel()
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                 wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    handles = {}
    report = {'schema': 1, 'session': session['id'], 'owner': owner,
              'opened_at': datetime.now(timezone.utc).isoformat(), 'processes': {},
              'process_or_window_mutation': False, 'completed': False}
    output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        output.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='ascii')

    try:
        for kind in ('game', 'mcdk'):
            pid, identity = session[kind + '_pid'], session[kind + '_identity']
            handle = kernel.OpenProcess(0x1000 | 0x100000, False, pid)
            if not handle:
                raise ctypes.WinError(ctypes.get_last_error())
            handles[kind] = handle
            if _identity(kernel, handle) != identity:
                raise RuntimeError('Owned process identity changed before exit observation')
            size, executable = wintypes.DWORD(32768), ctypes.create_unicode_buffer(32768)
            if not kernel.QueryFullProcessImageNameW(handle, 0, executable, ctypes.byref(size)):
                raise ctypes.WinError(ctypes.get_last_error())
            expected = (session['game_executable'] if kind == 'game'
                        else session['noactivation']['mcdk']['path'])
            if Path(executable.value).resolve() != Path(expected).resolve():
                raise RuntimeError('Owned executable changed before exit observation')
            report['processes'][kind] = {'pid': pid, 'identity': identity,
                                          'executable': executable.value, 'state': 'live'}
        save()
        print(json.dumps({'exact_process_handles_retained': report['processes'],
                          'output': str(output)}), flush=True)
        while any(row['state'] == 'live' for row in report['processes'].values()):
            for kind, handle in handles.items():
                row = report['processes'][kind]
                if row['state'] != 'live':
                    continue
                waited = kernel.WaitForSingleObject(handle, 0)
                if waited == 258:
                    continue
                if waited != 0:
                    raise ctypes.WinError(ctypes.get_last_error())
                code = wintypes.DWORD()
                if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                    raise ctypes.WinError(ctypes.get_last_error())
                row.update(state='exited', exit_code=code.value,
                           exit_code_hex='0x%08X' % code.value,
                           observed_at=datetime.now(timezone.utc).isoformat())
                save()
                print(json.dumps({'process_exited': kind, 'observation': row}), flush=True)
            if any(row['state'] == 'live' for row in report['processes'].values()):
                time.sleep(1.)
        report['completed'] = True
        save()
    finally:
        for handle in handles.values():
            kernel.CloseHandle(handle)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(watch(args.session, args.owner, args.output)))
