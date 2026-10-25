"""Read-only R29 closeout; writes only its new receipt, never calls an SDK."""
import argparse
from datetime import datetime, timezone, timedelta
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / '.runtime/round-20261026/validation-v7'
PRODUCT = 'dcf34132ce8e33284066efe66b9693ff89dc675a'
SHANGHAI = timezone(timedelta(hours=8))
sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args, cwd=ROOT):
    result = subprocess.run(args, cwd=cwd, capture_output=True, timeout=45,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf8', 'replace'))
    return result.stdout.decode('utf-8-sig').strip()


def powershell(source):
    return json.loads(command(['powershell.exe', '-NoProfile', '-Command', source]))


def repository(path, branch, head):
    row = {'branch': command(['git', 'branch', '--show-current'], path),
           'head': command(['git', 'rev-parse', 'HEAD'], path),
           'tracked_status': command(['git', 'status', '--porcelain=v1',
                                      '--untracked-files=no'], path)}
    row['expected_branch_and_head'] = row['branch'] == branch and row['head'] == head
    row['tracked_clean'] = not row['tracked_status']
    assert row['expected_branch_and_head'] and row['tracked_clean'], row
    return row


def audit():
    result = {'schema': 1, 'started_at': datetime.now(SHANGHAI).isoformat(),
              'product_source_commit': PRODUCT, 'read_only_except_new_receipt': True,
              'game_connection_or_input': False, 'session_configs_read': False,
              'process_or_window_mutation': False, 'MC_launch_performed': False,
              'SDK_or_RPC_called': False, 'tests_rerun': False,
              'hibernation_execution_observed': False}
    result['repositories'] = {
        'better-building-editor': repository(ROOT, 'dev',
            '08bb6bad461bbfe0532de762f19d860818a4a93b'),
        'nemc-block-states': repository(ROOT.parent / 'nemc-block-states', 'main',
            '58534dc5956848b4e6e5bcba97ad7112e2802388'),
        'nemc-block-renderer': repository(ROOT.parent / 'nemc-block-renderer', 'main',
            'ca1035615410db75aeaffdd7e8f3feb73ae6c0f0')}
    assert not command(['git', 'diff', PRODUCT, 'HEAD', '--',
                        'behavior_pack', 'resource_pack'])
    index_dir = ROOT / 'docs/evidence/r29-final-cpu-v8'
    index = json.loads((index_dir / 'index.json').read_bytes())
    reference = next(row for row in index['references']
                     if row['path'] == 'cpu-v8/before.json')
    obj = index['objects'][reference['sha256']]
    compressed = (index_dir / obj['file']).read_bytes()
    assert hashlib.sha256(compressed).hexdigest() == obj['stored_sha256']
    raw = gzip.decompress(compressed)
    assert len(raw) == reference['bytes']
    assert hashlib.sha256(raw).hexdigest() == reference['sha256']
    before = json.loads(raw)
    expected = {key: value for key, value in before.items()
                if key.startswith(('behavior_pack/', 'resource_pack/'))}
    paths = [path for pack in ('behavior_pack', 'resource_pack')
             for path in (ROOT / pack).rglob('*')
             if path.is_file() and '__pycache__' not in path.parts
             and path.suffix not in ('.pyc', '.pyo')]
    actual = {path.relative_to(ROOT).as_posix(): sha(path) for path in paths}
    assert actual == expected
    result['runtime'] = {'files': len(actual),
                         'bytes': sum(path.stat().st_size for path in paths),
                         'CPU_v8_runtime_names_and_sha_equal': True,
                         'git_product_delta_since_dcf': False}
    provenance = json.loads((ROOT / '.runtime/lib-dcf-r29-v1/provenance.json').read_bytes())
    metadata = {name: {'sha256': sha(ROOT / name), 'expected_sha256': digest}
                for name, digest in provenance['metadata_preserved'].items()}
    assert len(metadata) == 3
    assert all(row['sha256'] == row['expected_sha256'] for row in metadata.values())
    result['three_water_metadata_files'] = metadata
    prepared = json.loads((ROOT / '.runtime/round-20261026/root-final-preparation-review-v1.json').read_bytes())
    bindings = {name: sha(HOST / name)
                for name in prepared['projection']['binding_sha256']}
    assert bindings == prepared['projection']['binding_sha256']
    result['v7_binding_sha256'] = bindings
    spec = importlib.util.spec_from_file_location('r29_closeout_frozen_guard',
                                                  HOST / 'frozen_guard.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    frozen = guard.verify()
    assert frozen['source_commit'] == PRODUCT
    result['v7_frozen_guard_passed'] = True
    sys.path.insert(0, str(HOST))
    import instance_admission
    census = instance_admission.census()
    result['OS_MC_count'] = {
        'recorded_at': census['recorded_at'],
        'actual_live_mc_count': census['actual_live_mc_count'],
        'instance_count_qualified': census['instance_count_qualified'],
        'categories': {key: len(rows) for key, rows in census['categories'].items()},
        'scope': 'OS process identity and count only; no game/session access'}
    markers = [str(ROOT / '.runtime/round-20261026'),
               str(ROOT / '.runtime/projects/r29-transform-cold-v7'),
               'r29-transform-cold-v7']
    # Only matched metadata leaves PowerShell; all foreign command lines are discarded.
    query = r"""
$ErrorActionPreference='Stop'
$rows=@(Get-CimInstance Win32_Process)
$excluded=@([int]$PID, AUDIT_PID)
$next=AUDIT_PID
while ($next -gt 0) {
  $row=$rows | Where-Object { [int]$_.ProcessId -eq $next } | Select-Object -First 1
  if ($null -eq $row) { break }
  $next=[int]$row.ParentProcessId
  if ($excluded -contains $next) { break }
  $excluded+= $next
}
$markers=ConvertFrom-Json 'MARKERS_JSON'
$owned=@($rows | Where-Object {
  if ($excluded -contains [int]$_.ProcessId) { return $false }
  $line=([string]$_.CommandLine).Replace('/','\').ToLowerInvariant()
  foreach ($marker in $markers) {
    if ($line.Contains($marker.Replace('/','\').ToLowerInvariant())) { return $true }
  }
  return $false
} | ForEach-Object {
  [ordered]@{pid=[int]$_.ProcessId;name=$_.Name;
    creation_utc=$(if ($null -ne $_.CreationDate) {$_.CreationDate.ToUniversalTime().ToString('o')} else {$null})}
})
ConvertTo-Json -InputObject $owned -Compress
"""
    query = query.replace('AUDIT_PID', str(os.getpid())).replace(
        'MARKERS_JSON', json.dumps(markers).replace("'", "''"))
    own = powershell(query)
    assert isinstance(own, list)
    result['owned_process_audit'] = {
        'matched_count': len(own), 'matched_metadata': own,
        'scope': 'Exact v7 owner/project and round host paths; query wrappers and ancestors excluded',
        'external_command_lines_copied': False,
        'limitation': 'Cannot attribute unmarked inherited or stdin-only processes; combine with existing no-launch receipts.'}
    assert not own, own
    result['v7_absent_artifacts'] = {
        name: not (HOST / name).exists() for name in
        ('launch/report.json', 'assert-watch-start.json', 'feature-smoke', 'stop/report.json')}
    assert all(result['v7_absent_artifacts'].values())
    task = powershell(r"""
$ErrorActionPreference='Stop'
$task=Get-ScheduledTask -TaskName 'Codex-BBE-R29-Hibernate-20261026'
$info=$task | Get-ScheduledTaskInfo
[ordered]@{recorded_at=(Get-Date -Format o);name=$task.TaskName;state=[string]$task.State;
 enabled=$task.Settings.Enabled;next_run=$info.NextRunTime.ToString('o');
 last_run=$info.LastRunTime.ToString('o');last_result=$info.LastTaskResult;
 start_when_available=$task.Settings.StartWhenAvailable;wake_to_run=$task.Settings.WakeToRun;
 disallow_on_battery=$task.Settings.DisallowStartIfOnBatteries;
 stop_on_battery=$task.Settings.StopIfGoingOnBatteries;
 actions=@($task.Actions | Select-Object Execute,Arguments);
 triggers=@($task.Triggers | Select-Object StartBoundary,Enabled)} | ConvertTo-Json -Depth 5
""")
    assert task['state'] == 'Ready' and task['enabled'] is True
    assert datetime.fromisoformat(task['next_run']) == datetime(2026, 10, 26, 8, tzinfo=SHANGHAI)
    assert task['start_when_available'] is False and task['wake_to_run'] is True
    assert not task['disallow_on_battery'] and not task['stop_on_battery']
    assert len(task['actions']) == 1
    assert task['actions'][0]['Arguments'] == '/h'
    assert task['actions'][0]['Execute'].replace('\\', '/').lower() == 'c:/windows/system32/shutdown.exe'
    assert len(task['triggers']) == 1 and task['triggers'][0]['Enabled']
    result['hibernation_task'] = task
    result['completed_at'] = datetime.now(SHANGHAI).isoformat()
    result['passed'] = True
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Closeout receipt must be new'
    result = audit()
    args.output.write_text(json.dumps(result, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps(result, ensure_ascii=True, indent=2))
