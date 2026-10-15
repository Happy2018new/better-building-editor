"""One explicit operation in an exact-owned, root-scheduled banner session."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import load_session, process_identity
from mcdk import Client, return_value
import prepare

OWNER, PROJECT, OUTPUT = prepare.OWNER, prepare.PROJECT, prepare.OUTPUT


def validate_inputs():
    return prepare.verify(emit=False)


def call(args):
    plan = validate_inputs()
    session = load_session(args.session, OWNER, live=True)
    assert Path(session['project']).resolve() == PROJECT.resolve()
    assert all(process_identity(session[key + '_pid']) == session[key + '_identity']
               for key in ('game', 'mcdk'))
    import host
    host.validate()
    ready = host.bound(live=True)
    assert ready['id'] == session['id']
    assert not (host.CONTROL / 'stop-request.json').exists()
    exact = prepare.read(host.CONTROL / 'exact-exit.json')
    assert not exact['completed']
    for key in ('game', 'mcdk'):
        assert exact['processes'][key]['state'] == 'live'
        assert exact['processes'][key]['identity'] == session[key + '_identity']
    if args.action not in ('inspect', 'restore', 'absent'):
        proof = prepare.read(OUTPUT / 'runtime-version-config-check.json')
        assert proof['passed'] and proof['session'] == session['id']
        assert all(proof[key + '_identity'] == session[key + '_identity'] for key in ('game', 'mcdk'))
        host.resources()
    os.environ.update(MCDEV_SESSION_FILE=str(args.session), MCDEV_OWNER=OWNER,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    actors_path = OUTPUT / ('actors-' + args.phase + '.json')
    receipts = OUTPUT / 'runtime-receipts'
    receipts.mkdir(exist_ok=True)
    client_restores = [prepare.read(path) for path in receipts.glob('*-' + args.phase + '-client-restore.json')]
    client_restored = any(row.get('result', {}).get('restored') or
                          row.get('result', {}).get('already_restored') for row in client_restores)
    if args.server and args.action in ('restore', 'absent'):
        assert client_restored, 'Restore client controls, bindings and models before server actors'
    if args.server and args.action == 'journal':
        assert not actors_path.exists(), 'Do not recreate a completed phase'
    actors = prepare.read(actors_path) if actors_path.exists() else {}
    config = {'pose': args.pose}
    code = 'ACTION = %r\nPHASE = %r\nLABELS = %r\nACTORS = %r\nMODELS = %r\nPOSES = %r\nCONFIG = %r\nINPUTS = %r\n' % (
        args.action, args.phase, plan['phases'][args.phase], actors, plan['host_models'],
        plan['poses'], config, prepare.read(OUTPUT / 'inputs.json'))
    code += (HERE / ('server.py' if args.server else 'client.py')).read_text(encoding='ascii')
    number = max([int(path.name.split('-', 1)[0]) for path in receipts.glob('[0-9][0-9][0-9]-*.json')] + [0]) + 1
    receipt = receipts / ('%03d-%s-%s-%s.json' % (
        number, args.phase, 'server' if args.server else 'client', args.action))
    record = {'at': datetime.now(timezone.utc).isoformat(), 'owner': OWNER,
        'phase': args.phase, 'action': args.action, 'source_sha256': plan['source_sha256'],
        'game_pid': session['game_pid'], 'game_identity': session['game_identity'],
        'mcdk_pid': session['mcdk_pid'], 'mcdk_identity': session['mcdk_identity'],
        'code': code, 'code_sha256': hashlib.sha256(code.encode('ascii')).hexdigest()}
    try:
        with Client(timeout=30) as connection:
            result = return_value(connection.call('execute_code', {'code': code,
                'is_client': not args.server, 'direct_return': True}))
        result = json.loads(result) if isinstance(result, str) else result
        record['result'] = result
        if args.server and args.action == 'journal':
            prepare.save(actors_path, result['actors'])
        if args.server and args.action == 'absent' and result.get('journal_removed'):
            prepare.save(OUTPUT / (args.phase + '-restored.json'), {'phase': args.phase,
                'actors_absent': True, 'server_receipt': str(receipt), 'client_restored': True})
    except BaseException as error:
        record['error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        prepare.save(receipt, record)
    print(json.dumps({'receipt': str(receipt), 'result': result}, ensure_ascii=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('journal', 'setup', 'mount', 'bind', 'scale', 'pose', 'inspect', 'restore', 'absent'))
    parser.add_argument('--phase', choices=('banner',), default='banner')
    parser.add_argument('--pose', choices=tuple(prepare.POSES), default='yaw90')
    parser.add_argument('--server', action='store_true')
    parser.add_argument('--session', type=Path, required=True)
    args = parser.parse_args()
    assert args.action in ('inspect', 'restore') or args.server == (args.action in ('journal', 'absent'))
    call(args)
