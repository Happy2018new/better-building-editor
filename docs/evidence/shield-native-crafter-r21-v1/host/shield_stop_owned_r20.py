"""Stop only a validated owned session and print a compact nonsecret receipt."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
import instances
from _session import load_session, process_identity

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--session', required=True)
parser.add_argument('--owner', required=True)
parser.add_argument('--normal-only', action='store_true')
args = parser.parse_args()
data = load_session(args.session, args.owner)
forced = False
try:
    result = instances.stop(data, False)
except RuntimeError as exc:
    assert 'Game has not closed' in str(exc), str(exc)
    if args.normal_only:
        print(json.dumps({'owner': args.owner, 'session_file': args.session,
                          'normal_stop_completed': False,
                          'forced': False, 'error': str(exc)}))
        raise SystemExit(2)
    data = load_session(args.session, args.owner)
    result = instances.stop(data, True)
    forced = True
alive = dict((name, process_identity(result[name + '_pid']) == result[name + '_identity'])
             for name in ('game', 'mcdk'))
assert result['state'] == 'stopped' and not any(alive.values())
receipt = {'owner': args.owner, 'session_file': args.session, 'state': result['state'],
           'game_pid': result['game_pid'], 'game_identity': result['game_identity'],
           'mcdk_pid': result['mcdk_pid'], 'mcdk_identity': result['mcdk_identity'],
           'forced_after_normal_stop': forced, 'process_alive': alive}
print(json.dumps(receipt))
