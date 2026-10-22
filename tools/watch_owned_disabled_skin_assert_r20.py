"""Record and recover one specific engine assertion in selected owned instances."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from check_native_dialogs import assertion_dialogs
from dismiss_owned_disabled_skin_assert import known_disabled_skin_assertion, post_owned_ignore

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import load_session, process_identity, read_json, registry_dir, write_json


def assigned(owner, owners):
    return isinstance(owner, str) and any(owner == item or
        item.endswith('*') and len(item) > 1 and owner.startswith(item[:-1]) for item in owners)


def eligible(session, owners, project_root, identity_reader=process_identity):
    if not assigned(session.get('owner'), owners) or session.get('state') not in ('starting', 'ready'):
        return False
    project = Path(session.get('project', '')).resolve()
    if project == project_root or not project.is_relative_to(project_root):
        return False
    return all(session.get(key + '_identity') and
               identity_reader(session.get(key + '_pid')) == session[key + '_identity']
               for key in ('game', 'mcdk'))


def recover(session, row, receipt_path):
    if not known_disabled_skin_assertion(row) or row['pid'] != session['game_pid']:
        raise ValueError('The dialog does not match the owned disabled-skin assertion')
    receipt = {'schema_version': 1, 'owner': session['owner'], 'session_id': session['id'],
               'game_pid': session['game_pid'], 'game_identity': session['game_identity'],
               'observed_at': datetime.now().astimezone().isoformat(), 'dialog': row,
               'action': 'BM_CLICK verified IDIGNORE', 'agent_activation': False, 'dismissed': False}

    def save():
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=True, indent=2) + '\n', encoding='ascii')

    save()
    def before_post(target):
        receipt['verified_target'] = target
        save()
    post_owned_ignore(session, row, before_post)
    deadline = time.monotonic() + 5.
    while time.monotonic() < deadline:
        remaining = [item for item in assertion_dialogs()
                     if item['pid'] == session['game_pid'] and item['hwnd'] == row['hwnd']]
        if not remaining:
            receipt['dismissed'] = True
            break
        time.sleep(.1)
    receipt['completed_at'] = datetime.now().astimezone().isoformat()
    save()
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', action='append', required=True)
    parser.add_argument('--until', type=datetime.fromisoformat, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--detach', action='store_true')
    args = parser.parse_args()
    if args.until.tzinfo is None:
        parser.error('--until needs an explicit UTC offset')
    if args.detach:
        command = [sys.executable, '-X', 'utf8', str(Path(__file__).resolve())]
        command.extend(value for value in sys.argv[1:] if value != '--detach')
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        print(json.dumps({'watcher_pid': process.pid, 'watcher_identity': process_identity(process.pid),
                          'output': str(args.output), 'until': args.until.isoformat()}))
        return 0
    args.output.mkdir(parents=True, exist_ok=False)
    project_root = (ROOT / '.runtime/projects').resolve()
    attempts = set()
    recovered_sessions = set()
    status = {'schema_version': 1, 'owners': args.owner, 'until': args.until.isoformat(),
              'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'known_assert_recoveries': [], 'other_assertions': [], 'errors': []}
    while datetime.now().astimezone() < args.until:
        sessions = {}
        for manifest in registry_dir().glob('*/session.json'):
            try:
                data = read_json(manifest)
                if not assigned(data.get('owner'), args.owner):
                    continue
                data = load_session(str(manifest), data['owner'])
                if eligible(data, args.owner, project_root):
                    sessions[data['game_pid']] = data
            except (OSError, ValueError, KeyError, TypeError) as error:
                message = str(manifest) + ': ' + str(error)
                if message not in status['errors']:
                    status['errors'].append(message)
        for row in assertion_dialogs():
            session = sessions.get(row['pid'])
            if session is None:
                continue
            key = (session['id'], row['hwnd'])
            if key in attempts:
                continue
            attempts.add(key)
            if not known_disabled_skin_assertion(row):
                status['other_assertions'].append({'session_id': session['id'], 'dialog': row})
                continue
            if session['id'] in recovered_sessions:
                status['errors'].append(session['id'] + ': known assertion repeated after one recovery')
                continue
            recovered_sessions.add(session['id'])
            try:
                receipt = recover(session, row, args.output / ('recovery-' + session['id'] + '.json'))
                status['known_assert_recoveries'].append(receipt)
            except (OSError, ValueError, RuntimeError) as error:
                status['errors'].append(session['id'] + ': ' + str(error))
        status['checked_at'] = datetime.now().astimezone().isoformat()
        status['eligible_sessions'] = [{'id': value['id'], 'owner': value['owner'],
                                        'game_pid': value['game_pid']} for value in sessions.values()]
        write_json(args.output / 'status.json', status)
        if args.once:
            break
        time.sleep(1.)
    return 0 if not status['errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
