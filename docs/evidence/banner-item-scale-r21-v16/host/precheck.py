"""Read-only v14 identity/version/config checks, after exact handles are retained."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.runtime/banner-scale-control-r21'))
import run

assert len(sys.argv) == 2
SESSION = Path(sys.argv[1])
run.validate_inputs()
import host
host.validate()
host.resources()
session = run.load_session(SESSION, run.OWNER, live=True)
assert Path(session['project']).resolve() == run.PROJECT.resolve()
assert all(run.process_identity(session[key + '_pid']) == session[key + '_identity']
           for key in ('game', 'mcdk'))
reloads = run.prepare.read(SESSION.parent / '.mcdev.json')
assert all(reloads[key] is False for key in run.prepare.RELOADS)
assert session['noactivation']['requested'] is True
assert session['noactivation']['agent_activation_allowed'] is False
assert session['noactivation']['window_noactivate'] is True
exact = run.prepare.read(run.OUTPUT / 'runtime-launch/exact-exit.json')
assert not exact['completed']
assert all(exact['processes'][key]['state'] == 'live' and
           exact['processes'][key]['identity'] == session[key + '_identity']
           for key in ('game', 'mcdk'))
os.environ.update(MCDEV_SESSION_FILE=str(SESSION), MCDEV_OWNER=run.OWNER,
                  MCDEV_ALLOW_USER_FOREGROUND='1')
record = {'at': datetime.now(timezone.utc).isoformat(), 'owner': run.OWNER,
    'session': session['id'], 'game_pid': session['game_pid'],
    'game_identity': session['game_identity'], 'mcdk_pid': session['mcdk_pid'],
    'mcdk_identity': session['mcdk_identity'], 'mutations': False,
    'exact_handles_retained_before_this_probe': True,
    'reloads': {key: reloads[key] for key in run.prepare.RELOADS}, 'versions': {}}
try:
    with run.Client(timeout=30) as connection:
        for side in ('client', 'server'):
            code = "import mod.%s.extra%sApi as api\n_result = api.GetMinecraftVersion()" % (side, side.title())
            version = run.return_value(connection.call('execute_code', {
                'code': code, 'is_client': side == 'client', 'direct_return': True}))
            record['versions'][side] = version
            assert version == '1.21.130.0', version
    record['passed'] = True
except BaseException as error:
    record['error'] = {'type': type(error).__name__, 'message': str(error)}
    raise
finally:
    run.prepare.save(run.OUTPUT / 'runtime-version-config-check.json', record)
print(json.dumps(record))
