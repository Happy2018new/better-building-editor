"""Read exact owned process exit state without terminating anything."""
import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import load_session, process_identity, _kernel
parser = argparse.ArgumentParser()
parser.add_argument('--session', required=True)
parser.add_argument('--owner', required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
data = load_session(args.session, args.owner)
kernel = _kernel()
rows = []
for kind in ('game', 'mcdk'):
    pid = data[kind + '_pid']
    expected = data[kind + '_identity']
    handle = kernel.OpenProcess(0x1000, False, pid)
    row = {'kind': kind, 'pid': pid, 'expected_identity': expected,
           'live_identity': process_identity(pid), 'handle_available': bool(handle)}
    if handle:
        try:
            times = [wintypes.FILETIME() for _ in range(4)]
            code = wintypes.DWORD()
            assert kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in times))
            row['creation_identity'] = str((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime)
            assert row['creation_identity'] == expected
            assert kernel.GetExitCodeProcess(handle, ctypes.byref(code))
            row['exit_code'] = code.value
            row['exit_code_hex'] = '0x%08X' % code.value
        finally:
            kernel.CloseHandle(handle)
    rows.append(row)
receipt = {'owner': args.owner, 'session_file': args.session,
           'mutations': False, 'processes': rows,
           'log_path': data.get('log')}
args.output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='ascii')
print(json.dumps(receipt))
