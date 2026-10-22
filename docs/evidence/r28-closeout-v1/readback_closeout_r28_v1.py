"""Read-only R28 closeout. Never stop a process or edit a session/qualification."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '.runtime/round-20261023'
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import process_identity, read_json, registry_dir


def powershell(code):
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', code],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return json.loads(result.stdout.decode('utf-8-sig')) if result.stdout.strip() else None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_state(path):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(path)] + list(args)).decode('utf8').strip()
    return {'path': str(path), 'branch': git('branch', '--show-current'), 'head': git('rev-parse', 'HEAD'),
            'tracked_status': git('status', '--porcelain=v1', '--untracked-files=no').splitlines()}


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--phase', required=True)
args = parser.parse_args()
assert not args.output.exists()
rows = []
errors = []
owned = []
live_sessions = []
for path in registry_dir().glob('*/session.json'):
    try:
        row = read_json(path)
        active = []
        for kind in ('game', 'mcdk'):
            pid, identity = row.get(kind + '_pid'), row.get(kind + '_identity')
            if pid and identity:
                current = process_identity(pid)
                if current == identity:
                    active.append({'kind': kind, 'pid': pid, 'creation_identity': current, 'live_exit_code': 259})
        safe = {'id': row.get('id'), 'owner': row.get('owner'), 'registry_state': row.get('state'),
                'exact_live_processes': active}
        rows.append(safe)
        if 'r28' in str(row.get('owner', '')).lower(): owned.append(safe)
        if active: live_sessions.append(safe)
    except Exception as error:
        errors.append({'session_directory': path.parent.name, 'type': type(error).__name__, 'message': str(error)})

# CIM can retain exited zero-resource records; a live identity is still required.
cim = powershell("@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'Minecraft.Windows.exe' } | Select-Object ProcessId,Name,HandleCount,ThreadCount,ExecutablePath) | ConvertTo-Json -Depth 3 -Compress") or []
if isinstance(cim, dict): cim = [cim]
actual_games = []
tombstones = []
unqualified_cim = []
for row in cim:
    identity = process_identity(row['ProcessId'])
    safe = {'pid': row['ProcessId'], 'name': row['Name'], 'creation_identity': identity,
            'handles': row.get('HandleCount'), 'threads': row.get('ThreadCount'),
            'executable_present': row.get('ExecutablePath') is not None}
    if identity:
        actual_games.append(safe)
    elif row.get('HandleCount') == 0 and row.get('ThreadCount') == 0 and row.get('ExecutablePath') is None:
        tombstones.append(safe)
    else:
        unqualified_cim.append(safe)

# Do not save full command lines: bridge process arguments can contain credentials.
helpers_raw = powershell("@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?[.]exe$' -and $_.CommandLine -match 'round-20261023' -and $_.CommandLine -match 'watch_owned|observer|watcher' } | Select-Object ProcessId,Name,CommandLine) | ConvertTo-Json -Depth 3 -Compress") or []
if isinstance(helpers_raw, dict): helpers_raw = [helpers_raw]
helpers = []
for row in helpers_raw:
    if row['ProcessId'] == os.getpid(): continue
    identity = process_identity(row['ProcessId'])
    if identity:
        helpers.append({'pid': row['ProcessId'], 'name': row['Name'], 'creation_identity': identity,
                        'command_line_sha256_only': sha(row['CommandLine'].encode('utf8'))})

manifest = read_json(RUN / 'final-public-cold-v4/source-manifest.json')
exact, eol, changed = [], [], []
for relative, expected in manifest['files'].items():
    path = ROOT / relative
    if not path.is_file():
        changed.append({'path': relative, 'missing': True})
        continue
    data = path.read_bytes()
    if sha(data) == expected:
        exact.append(relative)
        continue
    # Only valid UTF8 text may be compared with Git's CRLF conversion.
    is_text = False
    if b'\0' not in data:
        try:
            data.decode('utf8')
            is_text = True
        except UnicodeDecodeError:
            pass
    row = {'path': relative, 'current_raw_sha256': sha(data), 'frozen_Git_raw_sha256': expected}
    if is_text and sha(data.replace(b'\r\n', b'\n')) == expected:
        eol.append(row)
    else:
        changed.append(row)
contract = read_json(ROOT / 'tools/data/liquid_product_owner_contract_v1.json')
water_changes = []
for relative, expected in contract['source_sha256'].items():
    data = (ROOT / relative).read_bytes()
    actual = sha(data.replace(b'\r\n', b'\n'))
    if actual != expected: water_changes.append({'path': relative, 'expected': expected, 'actual': actual})

task = powershell("Get-ScheduledTask -TaskName Codex-BBE-R28-Hibernate-20261023 | Select-Object TaskName,State,@{Name='StartBoundary';Expression={$_.Triggers[0].StartBoundary}},@{Name='Execute';Expression={$_.Actions[0].Execute}},@{Name='Arguments';Expression={$_.Actions[0].Arguments}},@{Name='Enabled';Expression={$_.Settings.Enabled}},@{Name='TriggerEnabled';Expression={$_.Triggers[0].Enabled}},@{Name='StartWhenAvailable';Expression={$_.Settings.StartWhenAvailable}},@{Name='WakeToRun';Expression={$_.Settings.WakeToRun}},@{Name='DisallowStartIfOnBatteries';Expression={$_.Settings.DisallowStartIfOnBatteries}},@{Name='StopIfGoingOnBatteries';Expression={$_.Settings.StopIfGoingOnBatteries}} | ConvertTo-Json -Compress")
report = {
    'at': datetime.now(timezone.utc).isoformat(), 'phase': args.phase,
    'read_only': True, 'processes_stopped_by_this_script': 0,
    'registry_rows_checked': len(rows) + len(errors), 'registry_read_errors': errors,
    'R28_sessions': owned, 'matching_live_managed_sessions': live_sessions,
    'actual_live_MC': actual_games, 'zero_resource_CIM_tombstones': tombstones,
    'CIM_records_not_live_or_tombstone_qualified': unqualified_cim,
    'live_R28_watcher_observer_candidates': helpers,
    'frozen_b70_runtime_check': {'files': len(manifest['files']), 'exact_raw_Git_matches': len(exact),
                               'only_Git_CRLF_conversions': eol, 'other_changes': changed},
    'water_explicit_source_contract_check': {'files': len(contract['source_sha256']), 'changes': water_changes,
                                           'scope': 'Explicit contract only, not full transitive/resource/GPU closure'},
    'hibernation_task': task, 'hibernation_executed_by_this_script': False,
    'repositories': [git_state(path) for path in (ROOT, ROOT.parent / 'nemc-block-renderer', ROOT.parent / 'nemc-block-states')],
}
args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf8')
print(json.dumps({'phase': args.phase, 'actual_live_MC': len(actual_games), 'R28_sessions': len(owned),
                  'live_managed_sessions': len(live_sessions), 'watcher_observer_candidates': len(helpers),
                  'registry_errors': len(errors), 'frozen_runtime_changes': len(changed),
                  'water_contract_changes': len(water_changes),
                  'tracked_changes': [len(row['tracked_status']) for row in report['repositories']],
                  'task_ready': task['State'] == 3 and task['Enabled'] and task['TriggerEnabled'],
                  'receipt_sha256': sha(args.output.read_bytes())}))
