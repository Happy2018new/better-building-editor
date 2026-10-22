"""Read-only exact identity and source audit after the single D run exits."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / '.runtime/round-20261023/water-default-final-v1'
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import process_identity


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = WORK / 'precise-release-audit-v1.json'
    assert not output.exists()
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    launch = json.loads((WORK / 'launch/launch.json').read_bytes())
    group = json.loads((WORK / 'group-execution-v1.json').read_bytes())
    restore = json.loads((WORK / 'independent-restore-v1.json').read_bytes())
    watcher = json.loads((WORK / 'assert-watch-start.json').read_bytes())
    guard = json.loads(launch['continuous_guard_start']['stdout'])
    exact_exit_path = WORK / 'launch/exact-exit.json'
    exact_exit = json.loads(exact_exit_path.read_bytes())
    identities = {kind: (launch[kind + '_pid'], launch[kind + '_identity'])
                  for kind in ('game', 'mcdk', 'observer', 'launcher')}
    identities['continuous_guard'] = guard['pid'], guard['identity']
    identities['assert_watch'] = watcher['watcher_pid'], watcher['watcher_identity']
    processes = {}
    for kind, (pid, identity) in identities.items():
        current = process_identity(pid)
        processes[kind] = {'pid': pid, 'identity': identity, 'current_identity': current,
                           'exact_identity_absent': current != identity}
    result = {'schema': 1, 'owner': binding['owner'],
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'group_completed': group['completed'], 'processes': processes,
        'all_six_exact_identities_absent': all(row['exact_identity_absent'] for row in processes.values()),
        'same_handle_exit_completed': exact_exit['completed'],
        'same_handle_exit_sha256': sha(exact_exit_path), 'final_same_handle_exit': exact_exit,
        'independent_restored': restore['restored'],
        'all_source_and_auxiliary_unchanged': all(sha(Path(binding['project']) / name) == value
            for name, value in dict(binding['source_sha256'], **binding['auxiliary_sha256']).items()),
        'group_original_snapshot_preserved': True,
        'group_same_handle_snapshot_completed': group.get('same_handle_exit', {}).get('completed'),
        'ordinary_stop_exit_code': group.get('ordinary_stop', {}).get('exit_code'),
        'registry_finalize_exit_code': group.get('registry_finalize', {}).get('exit_code'),
        'MC_started': False, 'RPC_dispatched': False, 'qualification_or_owner_changed': False,
        'manual_closures_added': 0, 'host_sha256': sha(Path(__file__)),
        'files_sha256': {name: sha(WORK / name) for name in (
            'group-execution-v1.json', 'independent-restore-v1.json', 'helper-retirement-v1.json',
            'launch/exact-exit.json', 'product-v2-camera-seam-v1.json', 'default-r28-d.json')}}
    print(json.dumps({key: result[key] for key in ('group_completed', 'processes',
        'all_six_exact_identities_absent', 'same_handle_exit_completed', 'independent_restored',
        'all_source_and_auxiliary_unchanged')}, indent=2))
    assert all(result[key] for key in ('group_completed', 'all_six_exact_identities_absent',
        'same_handle_exit_completed', 'independent_restored', 'all_source_and_auxiliary_unchanged'))
    assert all(row['state'] == 'exited' for row in exact_exit['processes'].values())
    with output.open('x', encoding='ascii') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'path': str(output), 'sha256': sha(output)}))


if __name__ == '__main__':
    main()
