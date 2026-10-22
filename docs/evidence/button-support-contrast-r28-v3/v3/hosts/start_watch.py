"""Resume only the final owner's frozen assertion observer through today's closeout."""
from datetime import datetime, timezone
import hashlib
import json
from status_access import read_status
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWNER = 'r28-button-support-contrast-v3'
review=json.loads((HERE/'root-review-and-slot-v1.json').read_bytes())
assert review['passed']
UNTIL=review['watch_until']
cutoff=datetime.fromisoformat(review['cutoff_utc'])
assert datetime.now(timezone.utc)<cutoff<datetime.fromisoformat(UNTIL)
assert (datetime.fromisoformat(UNTIL)-cutoff).total_seconds()<=300
manifest = json.loads((HERE / 'source-manifest.json').read_bytes())
assert review['source_manifest_sha256']==hashlib.sha256((HERE/'source-manifest.json').read_bytes()).hexdigest()
from frozen_guard import verify
assert verify() == manifest
assert hashlib.sha256((HERE/'prelaunch-config.json').read_bytes()).hexdigest() == review['prelaunch_config_sha256']
host = Path(manifest['diagnostic_watcher']['path'])
host_sha = hashlib.sha256(host.read_bytes()).hexdigest()
assert host_sha == manifest['diagnostic_watcher']['sha256']
assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
           for path,digest in manifest['diagnostic_host_assets'].items())
assert datetime.now(timezone.utc) < datetime.fromisoformat(UNTIL)
output = HERE / 'assert-watch'
assert not output.exists()
assert not (HERE / 'assert-watch-start.json').exists()
command = [sys.executable, '-B', '-X', 'utf8', str(host), '--owner', OWNER,
           '--until', UNTIL, '--output', str(output), '--detach']
result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                        encoding='utf8', timeout=15)
assert result.returncode == 0, (result.stdout, result.stderr)
receipt = json.loads(result.stdout)
receipt.update(command=command, host_sha256=host_sha,
               started_at=datetime.now(timezone.utc).isoformat(),
               stdout=result.stdout, stderr=result.stderr,
               resume_wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               original_launcher_unchanged=True,
               resume_reason='New single support-color diagnostic owner; exact b70 runtime; old failed owners immutable.')
(HERE / 'assert-watch-start.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
deadline = time.monotonic() + 10
while not (output / 'status.json').exists():
    if time.monotonic() > deadline:
        raise TimeoutError('Owner assertion monitor did not publish status')
    time.sleep(.1)
status = read_status(output / 'status.json')
assert status['owners'] == [OWNER] and not status['errors'] and not status['other_assertions']
assert status['host_sha256'] == host_sha
assert (datetime.now(timezone.utc) - datetime.fromisoformat(status['checked_at'])).total_seconds() < 60
print(json.dumps(receipt))
