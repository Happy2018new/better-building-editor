"""Start the reviewed exact-owner known-assertion watcher before cold launch."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent


def main():
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    hosts = json.loads((WORK / 'prelaunch-host-binding-v1.json').read_bytes())
    for name, expected in hosts['external_host_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    assert datetime.now(timezone.utc) < datetime.fromisoformat(binding['guard_deadline_utc'])
    path = WORK / 'assert-watch-start.json'
    assert not path.exists() and not (WORK / 'assert-watch').exists()
    command = [sys.executable, '-B', '-X', 'utf8', str(ROOT / '.runtime/round-20261022/water-anchor-watcher-v5/watch_owned_disabled_skin_assert_r27_v5.py'),
               '--owner', binding['owner'], '--until', binding['guard_deadline_utc'],
               '--output', str(WORK / 'assert-watch'), '--detach']
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=15)
    result.check_returncode()
    receipt = json.loads(result.stdout)
    receipt.update(command=command, external_hosts=hosts['external_host_sha256'],
                   started_at_utc=datetime.now(timezone.utc).isoformat())
    path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    deadline = time.monotonic() + 8
    while True:
        status_path = WORK / 'assert-watch/status.json'
        if status_path.exists():
            status = json.loads(status_path.read_bytes())
            assert status['owners'] == [binding['owner']]
            assert not status['errors'] and not status['other_assertions']
            assert (datetime.now(timezone.utc) - datetime.fromisoformat(status['checked_at'])).total_seconds() < 5
            print(json.dumps(receipt))
            return
        if time.monotonic() >= deadline:
            raise RuntimeError('Exact assertion watcher did not publish fresh prelaunch status')
        time.sleep(.1)


if __name__ == '__main__':
    main()
