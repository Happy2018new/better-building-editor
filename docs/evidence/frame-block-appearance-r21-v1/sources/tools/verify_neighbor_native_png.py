"""Run neighbor visual suites with a preserved, hash-recorded native PNG helper."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time


def restore_owned_window(session, background_only=False):
    if background_only:
        return {'pid': session['game_pid'], 'background_only': True,
                'restored': False, 'activation_attempted': False}
    from _window import _activate_window
    from release_owned_game_focus import owned_game_hwnd
    hwnd = owned_game_hwnd(session)
    assert _activate_window(hwnd), 'Cannot restore owned game window'
    time.sleep(2.)
    return {'pid': session['game_pid'], 'hwnd': hwnd, 'restored': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=('dripstone', 'static', 'extended', 'botanical'), required=True)
    parser.add_argument('--capture-helper', type=Path, required=True,
                        help='Checkpointed verify_sign_visuals.py exporting SignCheck')
    parser.add_argument('--background-only', action='store_true', default=True,
                        help='Do not activate the game, send input or repair blank background captures')
    options, remaining = parser.parse_known_args()
    if not remaining or remaining[0].startswith('-'):
        parser.error('Supply the output JSON first, followed by the visual suite options')
    helper = options.capture_helper.resolve(strict=True)
    payload = helper.read_bytes()
    spec = importlib.util.spec_from_file_location('neighbor_png_capture_helper', helper)
    module = importlib.util.module_from_spec(spec)
    exec(compile(payload, str(helper), 'exec'), module.__dict__)
    if options.suite == 'dripstone':
        import verify_dripstone_world_visuals as suite
    elif options.suite == 'extended':
        import verify_extended_neighbor_world_visuals as suite
    elif options.suite == 'botanical':
        import verify_botanical_neighbor_world_visuals as suite
    else:
        import verify_static_neighbor_world_visuals as suite
    from verify_debug_blueprints import INSTALL_PROBE, write_json
    world = suite.world

    class NativePngNeighborCheck(module.SignCheck):
        def __init__(self, client, output, timeout):
            arguments = {'native_resolution': True}
            if options.background_only:
                arguments['background_only'] = True
            module.SignCheck.__init__(self, client, output, timeout, **arguments)
            self._neighbor_capture_counts = {}

        def capture(self, label, tree=None):
            count = self._neighbor_capture_counts.get(label, 0) + 1
            self._neighbor_capture_counts[label] = count
            identity = label if count == 1 else label + '_capture%d' % count
            return module.SignCheck.capture(self, identity, tree)

        def run(self, code):
            result = module.SignCheck.run(self, code)
            if code == INSTALL_PROBE:
                self.refresh()
            return result

    world.BlueprintCheck = NativePngNeighborCheck
    import sys
    sys.argv = [sys.argv[0]] + remaining
    output = Path(remaining[0])
    helper_snapshot = output.with_name(output.stem + '_capture_helper.py')
    helper_snapshot.parent.mkdir(parents=True, exist_ok=True)
    helper_snapshot.write_bytes(payload)
    managed_live = bool(os.environ.get('MCDEV_SESSION_FILE')) and '--replay' not in remaining
    activation = None
    if managed_live:
        from _session import desktop_lock, load_session
        session = load_session(live=True)
        with desktop_lock():
            # Minimized Minecraft windows can have a zero-size client area.
            activation = restore_owned_window(session, options.background_only)
    try:
        exit_code = world.main()
    finally:
        focus_release = None
        if managed_live and not options.background_only:
            from release_owned_game_focus import main as release_focus
            try:
                focus_release = release_focus()
            except Exception as error:
                focus_release = {'error': '%s: %s' % (type(error).__name__, error)}
        if output.is_file():
            report = json.loads(output.read_text(encoding='utf8'))
            report['native_png_capture_helper'] = {
                'path': str(helper), 'sha256': hashlib.sha256(payload).hexdigest(),
                'snapshot': str(helper_snapshot.resolve()),
                'class': 'SignCheck', 'native_resolution': True,
                'desktop_ownership': 'Caller must hold run_live_check.py desktop lock.'}
            report['owned_window_activation'] = activation
            report['background_only'] = options.background_only
            report['owned_focus_release'] = focus_release
            if focus_release and 'error' in focus_release:
                report['passed'] = False
            write_json(output, report)
    return 1 if focus_release and 'error' in focus_release else exit_code


if __name__ == '__main__':
    raise SystemExit(main())
