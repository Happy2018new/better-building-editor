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


def post_owned_ignore(session, row, before_post, user=None,
                      identity_reader=process_identity, dialog_reader=assertion_dialogs):
    """Click only the freshly verified Ignore control of this owned assertion."""
    if not known_disabled_skin_assertion(row) or row.get('pid') != session['game_pid']:
        raise ValueError('The dialog is not the owned disabled-skin assertion')
    if identity_reader(session['game_pid']) != session['game_identity']:
        raise RuntimeError('Game process identity changed before recovery')
    fresh = [item for item in dialog_reader() if item['pid'] == session['game_pid']]
    if (len(fresh) != 1 or fresh[0]['hwnd'] != row['hwnd'] or
            not known_disabled_skin_assertion(fresh[0])):
        raise RuntimeError('The owned assertion changed or another assertion appeared')
    if user is None:
        user = ctypes.WinDLL('user32', use_last_error=True)
        signatures = {
            'GetWindowThreadProcessId': ([wintypes.HWND, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD),
            'GetDlgItem': ([wintypes.HWND, ctypes.c_int], wintypes.HWND),
            'GetDlgCtrlID': ([wintypes.HWND], ctypes.c_int),
            'GetParent': ([wintypes.HWND], wintypes.HWND),
            'GetClassNameW': ([wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            'GetWindowTextW': ([wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            'IsWindowVisible': ([wintypes.HWND], wintypes.BOOL),
            'PostMessageW': ([wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM], wintypes.BOOL),
        }
        for name, (arguments, result) in signatures.items():
            getattr(user, name).argtypes = arguments
            getattr(user, name).restype = result

    def text(window, function):
        buffer = ctypes.create_unicode_buffer(256)
        if not function(window, buffer, len(buffer)):
            raise RuntimeError('Cannot inspect assertion control')
        return buffer.value

    def belongs(window):
        pid = wintypes.DWORD()
        return (user.GetWindowThreadProcessId(window, ctypes.byref(pid)) and
                pid.value == session['game_pid'])

    def verify_target(expected_button=None):
        if identity_reader(session['game_pid']) != session['game_identity']:
            raise RuntimeError('Game process identity changed before recovery')
        fresh = [item for item in dialog_reader() if item['pid'] == session['game_pid']]
        if (len(fresh) != 1 or fresh[0]['hwnd'] != row['hwnd'] or
                not known_disabled_skin_assertion(fresh[0])):
            raise RuntimeError('The owned assertion changed or another assertion appeared')
        dialog = row['hwnd']
        button = user.GetDlgItem(dialog, 5)  # Win32 IDIGNORE; 7 is IDNO.
        if (not belongs(dialog) or not user.IsWindowVisible(dialog) or
                text(dialog, user.GetClassNameW) != '#32770' or not button or
                not belongs(button) or user.GetParent(button) != dialog or
                user.GetDlgCtrlID(button) != 5 or not user.IsWindowVisible(button) or
                text(button, user.GetClassNameW) != 'Button' or
                expected_button is not None and button != expected_button):
            raise RuntimeError('Ignore button ownership, parent, class or control ID differs')
        button_text = text(button, user.GetWindowTextW)
        if button_text.replace('&', '').strip().lower() not in (
                'ignore', 'ignore(i)', '\u5ffd\u7565', '\u5ffd\u7565(i)'):
            raise RuntimeError('Control 5 is not the expected Ignore button')
        return {'dialog_hwnd': int(dialog), 'button_hwnd': int(button),
                'control_id': 5, 'button_text': button_text,
                'action': 'BM_CLICK verified IDIGNORE', 'agent_activation': False}

    target = verify_target()
    before_post(target)
    verify_target(target['button_hwnd'])
    button = target['button_hwnd']
    if not user.PostMessageW(button, 0x00F5, 0, 0):  # BM_CLICK; no activation.
        raise ctypes.WinError(ctypes.get_last_error())
    return target


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
               'game_identity':session['game_identity'],'action':'BM_CLICK verified IDIGNORE',
               'no_activation':True,'known_engine_assertion':True,'dismissed':False}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    def save():
        args.receipt.write_text(json.dumps(receipt,ensure_ascii=True,indent=2)+'\n',encoding='ascii')
    save()
    def before_post(target):
        receipt['verified_target'] = target
        save()
    post_owned_ignore(session, row, before_post)
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
