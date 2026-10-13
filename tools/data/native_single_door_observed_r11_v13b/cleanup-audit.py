"""Independently inspect owned process identities and restored launch bytes."""
from datetime import datetime, timezone
import ctypes
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
sys.path.insert(0, str(ROOT / 'tools'))
from _session import process_identity
from run_native_single_door import save, snapshot_sha

directory = Path(__file__).resolve().parent
supervisor = json.loads((directory / 'supervisor.json').read_bytes())
probe = json.loads((directory / 'probe.json').read_bytes())
session = supervisor['session']
frame = json.loads((Path.home() / '.pyreact-debug/instances/773c643b5cf344918e04d8b4eef2657a/session.json').read_bytes())
user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.GetForegroundWindow.restype = ctypes.c_void_p
user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
foreground_window = user32.GetForegroundWindow()
foreground_pid = ctypes.c_uint32()
user32.GetWindowThreadProcessId(foreground_window, ctypes.byref(foreground_pid))
before = probe['noactivation']['foreground']
audit = {'verified_at': datetime.now(timezone.utc).isoformat(),
         'inspection': 'GetProcessTimes and GetExitCodeProcess from independently opened process handles',
         'native_calls': 0, 'sdk_calls': 0, 'input_calls': 0,
         'owned_processes': {kind: {'pid': session[kind + '_pid'],
              'expected_identity': session[kind + '_identity'],
              'observed_identity': process_identity(session[kind + '_pid'])}
              for kind in ('game', 'mcdk')},
         'frame': {'session': frame['id'], 'pid': frame['game_pid'],
                   'expected_identity': frame['game_identity'],
                   'observed_identity': process_identity(frame['game_pid']), 'sdk_or_input_called': False},
         'foreground': {'hwnd': foreground_window, 'pid': foreground_pid.value,
                        'identity': process_identity(foreground_pid.value), 'before': before},
         'inputs': [{'target': row['target'], 'originally_present': row['originally_present'],
                     'expected_sha256': row.get('original_sha256'),
                     'observed_sha256': snapshot_sha(Path(row['target'])),
                     'restored_at_supervisor_exit': row['restored']} for row in supervisor['inputs']],
         'fixture': {'restored': probe['restored'], 'player_unchanged': probe['cleanup']['player_unchanged'],
                     'cleanup_errors': probe['cleanup']['errors'],
                     'client_reserved_air_cells': len(probe['client_after_cleanup']['rows']),
                     'reserve_coordinates_in_world_bounds': all(-64 <= pos[1] < 320 for pos in probe['reserved'])}}
audit['owned_processes_independently_absent'] = all(row['observed_identity'] is None
                                                  for row in audit['owned_processes'].values())
audit['frame_identity_unchanged'] = audit['frame']['expected_identity'] == audit['frame']['observed_identity']
audit['foreground_unchanged'] = (foreground_window == before['hwnd'] and foreground_pid.value == before['pid'] and
                                audit['foreground']['identity'] == before['identity'])
audit['launch_inputs_restored'] = all(row['observed_sha256'] == row['expected_sha256']
                                     for row in audit['inputs'])
save(directory / 'cleanup-audit.json', audit)
print(json.dumps(audit, ensure_ascii=True))
