"""Retire only our exact auxiliary watcher after both owned game identities exit."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import _kernel, _identity, process_identity


def main():
    launch = json.loads((WORK / 'launch/launch.json').read_bytes())
    for kind in ('game', 'mcdk'):
        assert process_identity(launch[kind + '_pid']) != launch[kind + '_identity']
    started = json.loads((WORK / 'assert-watch-start.json').read_bytes())
    pid, identity = started['watcher_pid'], started['watcher_identity']
    receipt = {'schema': 1, 'pid': pid, 'identity': identity,
               'game_and_mcdk_identities_absent': True,
               'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    kernel = _kernel()
    handle = kernel.OpenProcess(0x1000 | 1 | 0x100000, False, pid)
    if handle:
        try:
            assert _identity(kernel, handle) == identity
            assert kernel.TerminateProcess(handle, 0)
            assert kernel.WaitForSingleObject(handle, 5000) == 0
            receipt['exact_helper_terminated'] = True
        finally:
            kernel.CloseHandle(handle)
    else:
        receipt['already_absent'] = True
    assert process_identity(pid) != identity
    with (WORK / 'helper-retirement-v1.json').open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
