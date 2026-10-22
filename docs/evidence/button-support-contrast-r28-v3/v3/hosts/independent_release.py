"""Read-only final source/process audit after the reviewed owned stop and watch close."""
from datetime import datetime, timezone
import hashlib
import json
from status_access import read_status
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROJECT = ROOT / '.runtime/projects/r28-button-support-contrast-v3'
sys.path.insert(0, str(PROJECT / '.agents/skills/pyreact-debugging/scripts'))
from _session import process_identity
from frozen_guard import verify

out = HERE / 'owned-release.json'
assert not out.exists()
manifest = verify()
stop = json.loads((HERE / 'stop/report.json').read_bytes())
watch = json.loads((HERE / 'assert-watch-close.json').read_bytes())
status = read_status(HERE / 'assert-watch/status.json')
assert stop['completed'] and stop['registry_final']['state'] == 'stopped'
assert watch['completed'] and watch['actual_exit_code'] == 0
assert not status['errors'] and not status['other_assertions']
binding = stop['binding']
identities = {key: {'pid': binding[key + '_pid'], 'expected': binding[key + '_identity'],
                   'current': process_identity(binding[key + '_pid'])}
              for key in ('game', 'mcdk')}
identities['watcher'] = {'pid': watch['pid'], 'expected': watch['expected_creation_identity'],
                         'current': process_identity(watch['pid'])}
assert all(row['current'] is None for row in identities.values()), identities
audits = {phase: json.loads((HERE / ('face-restore-' + phase + '.json')).read_bytes())
          for phase in ('after1', 'after2')}
assert all(row['completed'] and row['changed_keys'] == [] and row['source_unchanged']
           for row in audits.values())
report = {'at': datetime.now(timezone.utc).isoformat(), 'completed': True,
          'owner': binding['owner'], 'source_commit': manifest['source_commit'],
          'source_manifest_sha256': hashlib.sha256((HERE / 'source-manifest.json').read_bytes()).hexdigest(),
          'source_unchanged': True, 'registry_state': stop['registry_final']['state'],
          'independent_identities': identities, 'actual_exit_codes': stop['actual_exit_codes'],
          'normal_shutdown_qualified': stop['normal_shutdown_qualified'],
          'force_game_executed': stop['force_executed'], 'watcher_exit_code': watch['actual_exit_code'],
          'independent_restore_audits': ['after1', 'after2'], 'manual_issues_closed': 0}
out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps(report))
