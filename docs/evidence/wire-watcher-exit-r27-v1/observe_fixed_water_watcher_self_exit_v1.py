"""Passive retained handle only; no signal, termination, restart or watcher edit."""
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import session_reader_v3 as reader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import _identity, _kernel, process_identity


def write_new(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, indent=2) + '\n').encode('ascii'))


def main():
    folder = HERE / 'launch-v7-fixed-water'
    output = folder / 'watcher-self-exit-v1.json'
    binding_output = folder / 'watcher-self-exit-binding-v1.json'
    assert not output.exists() and not binding_output.exists()
    events = []
    stop = reader.read_json(folder / 'stop.json', events)
    exact = reader.read_json(folder / 'exact-exit.json', events)
    binding = reader.read_json(folder / 'watch-binding.json', events)
    launch = reader.read_json(folder / 'launch.json', events)
    assert launch['owner'] == 'wire-r27-fixed-water-v1'
    assert stop['ordinary_returncode'] == 0 and not stop['still_live']
    assert exact['completed'] and all(value['state'] == 'exited' for value in exact['processes'].values())
    assert process_identity(launch['game_pid']) is None and process_identity(launch['mcdk_pid']) is None
    assert binding['watcher_sha256'] == reader.WATCHER_SHA
    assert binding['reader_sha256'] == reader.READER_SHA and binding['status_io_sha256'] == reader.STATUS_IO_SHA
    pid, identity = binding['watcher_pid'], binding['watcher_identity']
    assert process_identity(pid) == identity
    kernel = _kernel()
    handle = kernel.OpenProcess(0x1000 | 0x100000, False, pid)
    assert handle
    try:
        assert _identity(kernel, handle) == identity
        write_new(binding_output, {'owner': launch['owner'], 'watcher_pid': pid,
            'watcher_identity': identity, 'bound_at': datetime.now(timezone.utc).isoformat(),
            'game_live_identity': None, 'MCDK_live_identity': None,
            'passive_retained_handle': True, 'no_process_control_executed': True})
        until = datetime(2026, 10, 21, 23, 46, tzinfo=timezone.utc)
        while kernel.WaitForSingleObject(handle, 500) != 0:
            assert datetime.now(timezone.utc) < until, 'Watcher did not self-exit by 07:46; no force executed'
        code = wintypes.DWORD()
        assert kernel.GetExitCodeProcess(handle, ctypes.byref(code))
        actual_code = code.value
    finally:
        kernel.CloseHandle(handle)
    actual = {name: process_identity(pid) for name, pid in
              [('game', launch['game_pid']), ('MCDK', launch['mcdk_pid']), ('watcher', pid)]}
    assert all(value is None for value in actual.values())
    result = {'schema': 'wire-r27-fixed-water-frozen-watcher-self-exit-v1', 'owner': launch['owner'],
              'completed': True, 'watcher_pid': pid, 'watcher_identity': identity,
              'retained_handle_actual_exit_code': actual_code,
              'retained_handle_actual_exit_hex': '0x%08X' % actual_code,
              'final_actual_identities': actual, 'frozen_watch_until_utc': '2026-10-21T23:45:00+00:00',
              'observed_exit_at': datetime.now(timezone.utc).isoformat(),
              'watcher_source_or_frozen_configuration_modified': False,
              'process_signalled_or_terminated': False, 'process_restarted': False,
              'other_processes_acted_on': False, 'read_events': events}
    write_new(output, result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
