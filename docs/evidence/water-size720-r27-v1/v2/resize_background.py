"""Resize the exact owned game and preserve both DPI-context readbacks."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import desktop_lock, load_session, process_identity
from _window import _list_windows
from resize_adapter import resize_exact, user32


def main():
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    launch = json.loads((WORK / 'launch/launch.json').read_bytes())
    os.environ.update(MCDEV_SESSION_FILE=launch['session_file'], MCDEV_OWNER=binding['owner'],
                      MCDEV_ALLOW_USER_FOREGROUND='0')
    session = load_session(launch['session_file'], binding['owner'], live=True)
    out = WORK / 'resize-background-v1.json'
    assert not out.exists()
    row = {'schema': 2, 'owner': binding['owner'], 'completed': False,
           'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    try:
        # Match the existing resize_window entry's process setup; exact physical reads use PMv2.
        assert user32.SetProcessDPIAware(), 'Could not set the existing resize DPI awareness'
        with desktop_lock():
            assert process_identity(session['game_pid']) == session['game_identity']
            windows = [w for w in _list_windows() if w['pid'] == session['game_pid']]
            assert len(windows) == 1, windows
            resize_exact(windows[0]['hwnd'], session['game_pid'], session['game_identity'], 1280, 720, row)
        print(json.dumps({'completed': row['completed'], 'client_size': row['physical_after']['client_size']}))
    except BaseException as error:
        row['error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        with out.open('x', encoding='utf-8') as stream:
            json.dump(row, stream, indent=2)


if __name__ == '__main__':
    main()
