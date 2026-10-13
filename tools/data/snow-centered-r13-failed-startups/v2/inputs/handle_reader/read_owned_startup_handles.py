"""One passive, exact-process handle observation without SDK or window operations."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from types import ModuleType


def snapshot(kernel, identity_fn, pid, identity, executable):
    handle = kernel.OpenProcess(0x0400, False, pid)
    if not handle:
        return {'pid': pid, 'status': 'unavailable', 'winerror': ctypes.get_last_error()}
    try:
        current = identity_fn(kernel, handle)
        if current is None:
            return {'pid': pid, 'identity': identity, 'status': 'dead'}
        if current != identity:
            raise RuntimeError('Owned process creation identity changed')
        size = wintypes.DWORD(32768)
        name = ctypes.create_unicode_buffer(size.value)
        if not kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        if Path(name.value).resolve() != Path(executable).resolve():
            raise RuntimeError('Owned process executable changed')
        count = wintypes.DWORD()
        if not kernel.GetProcessHandleCount(handle, ctypes.byref(count)):
            raise ctypes.WinError(ctypes.get_last_error())
        after = identity_fn(kernel, handle)
        if after not in (None, identity):
            raise RuntimeError('Owned process identity changed during count')
        return {'pid': pid, 'identity': identity, 'executable': name.value,
                'handle_count': count.value, 'status': 'live' if after else 'exited_during_count'}
    finally:
        kernel.CloseHandle(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if hashlib.sha256(args.plan.read_bytes()).hexdigest() != args.plan_sha256:
        raise ValueError('Frozen plan changed')
    plan = json.loads(args.plan.read_bytes())
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(Path(plan['project']).resolve()):
        raise ValueError('Passive handle evidence must be fresh and inside owned project')
    row = plan['files']['session_api']
    payload = Path(row['path']).read_bytes()
    if hashlib.sha256(payload).hexdigest() != row['sha256']:
        raise ValueError('Frozen process identity helper changed')
    api = ModuleType('frozen_handle_identity')
    api.__file__ = row['path']
    exec(compile(payload, row['path'], 'exec'), api.__dict__)
    session = json.loads(args.session.read_bytes())
    protected = {value['pid'] for value in plan['protected_processes'].values()}
    if (session['id'] == plan['protected_session'] or session['owner'] != plan['owner'] or
            Path(session['project']).resolve() != Path(plan['project']).resolve() or
            Path(session['session_file']).resolve() != args.session.resolve() or
            any(session.get(kind + '_pid') in protected for kind in ('game', 'mcdk'))):
        raise ValueError('Handle observation session is not the owned startup')
    kernel = api._kernel()
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                 ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.GetProcessHandleCount.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetProcessHandleCount.restype = wintypes.BOOL
    result = {'schema': 1, 'captured_at': datetime.now(timezone.utc).isoformat(),
              'monotonic': time.monotonic(), 'session': session['id'], 'processes': {},
              'sdk_or_window_mutation': False, 'cause_attribution': False}
    for kind in ('game', 'mcdk'):
        expected = session['game_executable'] if kind == 'game' else session['noactivation']['mcdk']['path']
        result['processes'][kind] = snapshot(kernel, api._identity, session[kind + '_pid'],
                                              session[kind + '_identity'], expected)
    after = json.loads(args.session.read_bytes())
    if any(after.get(key) != session.get(key) for key in
           ('id', 'owner', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity', 'game_executable')):
        raise RuntimeError('Owned startup binding changed during handle observation')
    with output.open('x', encoding='ascii') as handle:
        handle.write(json.dumps(result, ensure_ascii=True, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
