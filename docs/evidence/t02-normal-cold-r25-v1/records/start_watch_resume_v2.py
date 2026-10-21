"""Resume only the final owner's frozen assertion observer through today's closeout."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWNER = 'r25-t02-normal-v1'
UNTIL = '2026-10-21T13:35:00+08:00'
manifest = json.loads((HERE / 'source-manifest.json').read_bytes())
host = ROOT / 'tools/watch_owned_disabled_skin_assert_r20.py'
host_sha = hashlib.sha256(host.read_bytes()).hexdigest()
assert host_sha == manifest['host_files']['tools/watch_owned_disabled_skin_assert_r20.py']
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
               resume_reason='Work was interrupted 10:32-12:56; root assigned resumed closeout 13:35 and total 13:50, no frozen source or original host changes.')
(HERE / 'assert-watch-start.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
deadline = time.monotonic() + 10
while not (output / 'status.json').exists():
    if time.monotonic() > deadline:
        raise TimeoutError('Owner assertion monitor did not publish status')
    time.sleep(.1)
status = json.loads((output / 'status.json').read_bytes())
assert status['owners'] == [OWNER] and not status['errors']
assert (datetime.now(timezone.utc) - datetime.fromisoformat(status['checked_at'])).total_seconds() < 60
print(json.dumps(receipt))
