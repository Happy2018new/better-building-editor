"""Bounded owner-bound runtime reads and two temporary server timer callbacks."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value
from capture_native_burst import _background, _session_binding

IDENTITY = '''import json, os, sys, time
import mod.%s.extra%sApi as api
_result = json.dumps({'runtime': api.GetMinecraftVersion(), 'pid': os.getpid(),
 'token': getattr(sys, '_pyreact_mcdk_session', None), 'now': time.time()})
'''

START = '''import json, sys, time
import mod.server.extraServerApi as api
marker = '_frame_r11_baseline_ticks'
assert not hasattr(sys, marker)
state = {'started': time.time(), 'callbacks': []}
setattr(sys, marker, state)
game = api.GetEngineCompFactory().CreateGame(api.GetLevelId())
def observed(current):
    current['callbacks'].append(time.time())
game.AddTimer(.2, lambda current=state: observed(current))
game.AddTimer(.4, lambda current=state: observed(current))
_result = json.dumps({'runtime': api.GetMinecraftVersion(), 'started': state['started']})
'''

STOP = '''import json, sys, time
marker = '_frame_r11_baseline_ticks'
state = getattr(sys, marker)
observed = {'started': state['started'], 'callbacks': list(state['callbacks']), 'now': time.time()}
delattr(sys, marker)
observed['restored'] = not hasattr(sys, marker)
_result = json.dumps(observed)
'''


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report')
    report = {'schema': 1, 'scope': 'Zero-marker native baseline runtime health only',
              'product_acceptance': False, 'fixture_mutation_attempted': False,
              'binding_verified': False, 'passed': False, 'completed': False,
              'preflight_window_verified': False,
              'timer_mutation_attempted': False, 'timer_cleanup_verified': False,
              'session_file': os.environ.get('MCDEV_SESSION_FILE'),
              'owner': os.environ.get('MCDEV_OWNER'), 'started_at': now(),
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'config_sha256': hashlib.sha256((ROOT / '.mcdev.json').read_bytes()).hexdigest(),
              'requests': []}

    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='ascii')

    class RecordedClient(Client):
        def _post(self, method, params=None, notification=False):
            request = {'jsonrpc': '2.0', 'method': method, 'params': params or {}}
            if not notification:
                request['id'] = self.counter + 1
            row = {'request': request, 'started_at': now()}
            report['requests'].append(row)
            save()
            try:
                if method == 'tools/call':
                    guard, current_window = _background(native_binding, native_window)
                    row['background_before_request'] = guard
                    row['window_before_request'] = current_window
                response = super()._post(method, params, notification)
                row['decoded_result'] = response
                return response
            except Exception as error:
                row['error'] = '%s: %s' % (type(error).__name__, error)
                raise
            finally:
                row['finished_at'] = now()
                save()

    try:
        native_binding, binaries = _session_binding(report['session_file'], report['owner'])
        report['protected_binaries'] = binaries
        guard, native_window = _background(native_binding)
        report['preflight_background'] = guard
        report['preflight_window'] = native_window
        report['preflight_window_verified'] = True
        save()
        with RecordedClient(timeout=15) as client:
            report['binding_verified'] = True

            def execute(code, is_client):
                value = return_value(client.call('execute_code', {
                    'code': code, 'is_client': is_client, 'direct_return': True}))
                return json.loads(value) if isinstance(value, str) else value

            for side, module, api_name in ((True, 'client', 'Client'), (False, 'server', 'Server')):
                identity = execute(IDENTITY % (module, api_name), side)
                report[module + '_before'] = identity
                assert identity['pid'] == client.binding['game_pid'], identity
                assert identity['token'] == client.binding['token'], identity
                save()
            assert report['client_before']['runtime'] == report['server_before']['runtime']
            report['timer_mutation_attempted'] = True
            report['timer_start'] = execute(START, False)
            save()
            time.sleep(.8)
            report['timer_stop'] = execute(STOP, False)
            report['timer_cleanup_verified'] = report['timer_stop']['restored']
            save()
            callbacks = report['timer_stop']['callbacks']
            assert len(callbacks) == 2, report['timer_stop']
            assert report['timer_start']['started'] < callbacks[0] < callbacks[1] <= report['timer_stop']['now']
            assert report['timer_cleanup_verified']
            report['client_after'] = execute(IDENTITY % ('client', 'Client'), True)
            assert report['client_after']['now'] > report['client_before']['now']
            assert report['client_after']['token'] == client.binding['token']
            report['completed'] = report['passed'] = True
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
    finally:
        report['finished_at'] = now()
        save()
    print(json.dumps({key: report[key] for key in ('binding_verified', 'completed', 'passed',
                                                 'fixture_mutation_attempted', 'timer_cleanup_verified')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
