"""Dismiss only the known NEMC 3.10 disabled-skin assertion in an owned instance."""
import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import load_session, process_identity
from check_native_dialogs import assertion_dialogs


def known_disabled_skin_assertion(row):
    return all(fragment in row.get('text', '') for fragment in (
        'The disabled skin popup has been displayed but the level data has no disabled cosmetics',
        'DisabledSkinScreenController::onEntered(void)',
        'DisabledSkinScreenController.cpp @ 47'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    assert not args.receipt.exists(), 'Choose a fresh assertion receipt'
    session = load_session(str(args.session), args.owner, live=True)
    assert process_identity(session['game_pid']) == session['game_identity']
    dialogs = [row for row in assertion_dialogs() if row['pid'] == session['game_pid']]
    assert len(dialogs) == 1, dialogs
    row = dialogs[0]
    assert known_disabled_skin_assertion(row), row
    receipt = {'schema':1,'session':str(args.session),'owner':args.owner,'dialog':row,
               'game_identity':session['game_identity'],'action':'WM_COMMAND IDIGNORE',
               'no_activation':True,'known_engine_assertion':True,'dismissed':False}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    def save():
        args.receipt.write_text(json.dumps(receipt,ensure_ascii=True,indent=2)+'\n',encoding='ascii')
    save()
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user.PostMessageW.argtypes = [wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    user.PostMessageW.restype = wintypes.BOOL
    owner = wintypes.DWORD()
    assert user.GetWindowThreadProcessId(row['hwnd'],ctypes.byref(owner)) and owner.value == session['game_pid']
    assert process_identity(session['game_pid']) == session['game_identity']
    assert user.PostMessageW(row['hwnd'],0x0111,7,0), ctypes.get_last_error()
    deadline = time.monotonic()+10.
    while time.monotonic()<deadline:
        remaining = [item for item in assertion_dialogs() if item['pid']==session['game_pid']]
        if not remaining:
            receipt['dismissed']=True
            break
        time.sleep(.2)
    receipt['remaining']=remaining
    save()
    print(json.dumps(receipt,ensure_ascii=True))
    return 0 if receipt['dismissed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
