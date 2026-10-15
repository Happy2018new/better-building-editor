"""Revalidate a timed-out owned startup without relaunching the game."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from instances import (ReadinessClient, background_guard_state, file_lock,
                       foreground_policy_satisfied, load_session, return_value,
                       verify_startup_endpoint, write_json)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
    with file_lock(args.session.parent / 'session.lock'):
        data = load_session(str(args.session), args.owner, live=False)
        assert data['state'] == 'failed' and data.get('readiness_deadline_reached')
        assert data.get('startup_endpoint_discovered')
        verify_startup_endpoint(data)
        with ReadinessClient(data, time.monotonic() + 20.) as client:
            environment = return_value(client.call('execute_code', {
                'code': "import os\n_result={'pid':os.getpid(),'appdata':os.environ.get('APPDATA')}",
                'is_client': True, 'direct_return': True}))
            assert environment == {'pid': data['game_pid'], 'appdata': data['appdata']}, environment
            for side in (True, False):
                token = return_value(client.call('execute_code', {
                    'code': "import sys\n_result=getattr(sys,'_pyreact_mcdk_session',None)",
                    'is_client': side, 'direct_return': True}))
                assert token == data['token'], 'Runtime session marker mismatch'
        verify_startup_endpoint(data)
        guard = background_guard_state(data['game_pid'], Path(data['game_executable']).name)
        assert foreground_policy_satisfied(guard, data['game_pid'])
        assert guard['window_noactivate']
        receipt = {'schema': 1, 'owner': args.owner, 'session': str(args.session),
                   'previous_state': data['state'], 'game_pid': data['game_pid'],
                   'game_identity': data['game_identity'], 'environment': environment,
                   'both_runtime_markers_verified': True, 'guard': guard,
                   'no_business_mutation': True}
        write_json(args.output / 'report.json', receipt)
        data.update(state='ready', ready=True, late_startup_receipt=str(args.output / 'report.json'))
        write_json(args.session, data)
        print(json.dumps(receipt, ensure_ascii=True))


if __name__ == '__main__':
    main()
