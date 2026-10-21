"""Offline controls of actual unknown-modal and watcher-health decisions."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
from unittest.mock import patch

import modal_guard as target


class Function:
    def __init__(self, call):
        self.call = call

    def __call__(self, *args):
        return self.call(*args)


def main():
    checks = []
    known_text = ('The disabled skin popup has been displayed but the level data has no disabled cosmetics '
                  'DisabledSkinScreenController::onEntered(void) DisabledSkinScreenController.cpp @ 47')
    windows = [{'hwnd': 10, 'pid': 123}]
    assertion = {'hwnd': 10, 'pid': 123, 'text': known_text}
    config = {'class': '#32770', 'owner': 0, 'enabled': True}

    def read_class(hwnd, buffer, capacity):
        buffer.value = config['class']
        return len(buffer.value)

    user = NS(GetClassNameW=Function(read_class),
              GetWindow=Function(lambda *args: config['owner']),
              IsWindowEnabled=Function(lambda *args: config['enabled']))
    with patch.object(target.ctypes, 'WinDLL', return_value=user), \
            patch.object(target._window, '_list_windows_windows', return_value=windows), \
            patch.object(target, 'assertion_dialogs', return_value=[assertion]):
        assert not target.unknown_modal_windows(123)
        checks.append({'name': 'exact_known_assertion_allowed_for_watcher', 'passed': True})
        assertion['text'] = 'Unrelated engine assertion'
        assert len(target.unknown_modal_windows(123)) == 1
        checks.append({'name': 'unknown_assertion_stops', 'passed': True})
        assert not target.unknown_modal_windows(456)
        checks.append({'name': 'other_pid_untouched', 'passed': True})
        config.update({'class': 'UnknownCustomModal', 'owner': 20, 'enabled': False})
        assert len(target.unknown_modal_windows(123)) == 1
        checks.append({'name': 'disabled_owner_custom_modal_stops', 'passed': True})
        config.update({'class': 'MinecraftWindow', 'owner': 0, 'enabled': True})
        assert not target.unknown_modal_windows(123)
        checks.append({'name': 'ordinary_game_window_allowed', 'passed': True})
    with tempfile.TemporaryDirectory(prefix='water-modal-offline-') as temporary:
        work = Path(temporary)
        directory = work / 'assert-watch'
        directory.mkdir()
        path = directory / 'status.json'
        base = {'owners': ['exact-owner'], 'errors': [], 'other_assertions': [],
                'checked_at': datetime.now(timezone.utc).isoformat()}
        with patch.object(target, 'unknown_modal_windows', return_value=[]):
            assert target.assertion_status_breach(work, 'exact-owner', 123)
            checks.append({'name': 'missing_status_stops', 'passed': True})
            for name, change, accepted in (
                ('healthy_exact_owner', {}, True),
                ('wrong_owner', {'owners': ['other-owner']}, False),
                ('watcher_error', {'errors': ['failed recovery']}, False),
                ('other_assertion_recorded', {'other_assertions': [{}]}, False),
                ('stale_status', {'checked_at': (datetime.now(timezone.utc)-timedelta(seconds=9)).isoformat()}, False),
                ('future_status', {'checked_at': (datetime.now(timezone.utc)+timedelta(seconds=3)).isoformat()}, False),
            ):
                path.write_text(json.dumps(dict(base, **change)), encoding='utf-8')
                assert (target.assertion_status_breach(work, 'exact-owner', 123) is None) == accepted
                checks.append({'name': name, 'passed': True})
    result = {'schema': 1, 'offline_only': True, 'MC_started': False,
              'all_passed': True, 'checks': checks,
              'limitations': ['Injected Windows readers verify actual modal decisions; no real dialog was opened or dismissed.']}
    path = Path(__file__).with_name('modal-guard-offline-controls-v1.json')
    with path.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({'passed': True, 'controls': len(checks), 'path': str(path)}))


if __name__ == '__main__':
    main()
