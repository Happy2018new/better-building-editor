"""Retain post-ready coverage without clearing the earlier session-read error."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / '.agents/skills/pyreact-debugging/scripts')]
from _session import process_identity
from check_native_dialogs import assertion_dialogs

control = ROOT / '.runtime/portal-native-candidate-control-r21-v12'
watch = ROOT / '.runtime/disabled-skin-watch-portal-r21-v12/status.json'
ready = json.loads((control / 'ready-summary.json').read_bytes())
assert process_identity(55680) == '134365769130132257'
samples = []
for unused in range(2):
    sample = json.loads(watch.read_bytes())
    assert (datetime.now(timezone.utc) - datetime.fromisoformat(sample['checked_at'])).total_seconds() < 15.
    assert sample['eligible_sessions'] == [{'id': '651cb12e8cf340b2bed51b8eced0de3d',
        'owner': ready['owner'], 'game_pid': ready['game_pid']}]
    assert not sample['known_assert_recoveries'] and not sample['other_assertions']
    assert len(sample['errors']) == 1 and '[Errno 13]' in sample['errors'][0]
    assert '651cb12e8cf340b2bed51b8eced0de3d' in sample['errors'][0]
    assert all(process_identity(ready[kind + '_pid']) == ready[kind + '_identity'] for kind in ('game', 'mcdk'))
    samples.append(sample)
    time.sleep(2.)
assert samples[0]['checked_at'] < samples[1]['checked_at']
assert samples[0]['errors'] == samples[1]['errors']
dialogs = [row for row in assertion_dialogs() if row['pid'] == ready['game_pid']]
assert not dialogs
report = {'owner': ready['owner'], 'session': '651cb12e8cf340b2bed51b8eced0de3d',
          'ready': ready, 'watcher_pid': 55680, 'watcher_identity': '134365769130132257',
          'samples': samples, 'current_owned_native_assertions': dialogs,
          'read_error_cause': 'A manifest read was denied during startup; the locking process or underlying cause was not observed. Later full watcher iterations read and validate the exact session again.',
          'read_error_preserved': True, 'watcher_errors_cumulative_in_source': True,
          'subsequent_exact_session_coverage_observed': True, 'qualification': False}
output = control / 'watcher-before-capture.json'
assert not output.exists()
output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii', newline='\n')
print(json.dumps({'ready': ready, 'covered_heartbeats': [row['checked_at'] for row in samples],
                  'owned_native_assertions': dialogs, 'earlier_read_error_retained': True}))
