"""Let the owned diagnostic finish normal close through its repeated modal."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'.agents/skills/pyreact-debugging/scripts')]
from _session import load_session, process_identity
from _window import _list_windows
from check_native_dialogs import assertion_dialogs

control = ROOT/'.runtime/shelf-mesh-inputs-r21-start-v1'
ready = json.loads((control/'start-summary.json').read_bytes())
session = load_session(ready['session_file'], 'root-shelf-r20-mesh-inputs-v1', live=True)
user = ctypes.WinDLL('user32', use_last_error=True)
user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user.PostMessageW.restype = wintypes.BOOL
result = {'normal_close_only': True, 'agent_activation': False, 'events': []}
deadline = time.monotonic()+30.
while time.monotonic() < deadline and len(result['events']) < 32:
    if process_identity(session['game_pid']) != session['game_identity']:
        break
    for row in _list_windows():
        if row['pid'] == session['game_pid'] and 'assert' not in row['title'].lower():
            user.PostMessageW(row['hwnd'], 0x0010, 0, 0)
    dialogs = [row for row in assertion_dialogs() if row['pid'] == session['game_pid']]
    for row in dialogs:
        if not all(value in row.get('text', '') for value in (
                'Mesh missing vertex field NORMAL required by shader. Skipping draw.',
                'mce::ShaderBase::checkVertexFormat', 'ShaderBase.cpp @ 118')):
            raise RuntimeError('Different modal; no dismissal sent: '+repr(row))
        assert process_identity(session['game_pid']) == session['game_identity']
        sent = bool(user.PostMessageW(row['hwnd'], 0x0111, 7, 0))
        result['events'].append({'dialog': row, 'action': 'WM_COMMAND IDIGNORE', 'sent': sent})
    (control/'normal-close-modal-drain.json').write_text(
        json.dumps(result, indent=2)+'\n', encoding='ascii')
    time.sleep(.1)
result['remaining_game_identity'] = process_identity(session['game_pid'])
(control/'normal-close-modal-drain.json').write_text(
    json.dumps(result, indent=2)+'\n', encoding='ascii')
print(json.dumps({'dismissals': len(result['events']), 'remaining_game_identity': result['remaining_game_identity']}))
