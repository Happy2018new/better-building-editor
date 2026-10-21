"""Read-only R27 process, Git and hibernation readback; never stop a process."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import process_identity, registry_dir

kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel.OpenProcess.restype = wintypes.HANDLE
kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel.CloseHandle.argtypes = [wintypes.HANDLE]

def current(pid, identity=None):
    if not pid:
        return None
    seen = process_identity(pid)
    if not seen or identity is not None and seen != identity:
        return None
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        code = wintypes.DWORD()
        assert kernel.GetExitCodeProcess(handle, ctypes.byref(code))
        assert process_identity(pid) == seen
        return {'pid': pid, 'identity': seen, 'exit_code': code.value, 'live': code.value == 259}
    finally:
        kernel.CloseHandle(handle)

def powershell(code):
    raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', code], encoding='utf8')
    return json.loads(raw) if raw.strip() else None

def git_state(path):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(path), *args]).decode('utf8').strip()
    return {'path': str(path), 'branch': git('branch', '--show-current'),
            'head': git('rev-parse', 'HEAD'),
            'tracked_status': git('status', '--porcelain=v1', '--untracked-files=no').splitlines()}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    owned, live, errors = [], [], []
    count = 0
    for path in registry_dir().glob('*/session.json'):
        count += 1
        try:
            row = json.loads(path.read_bytes())
            matched = []
            for kind in ('game', 'mcdk'):
                result = current(row.get(kind + '_pid'), row.get(kind + '_identity'))
                if result is not None and result['live']:
                    matched.append(dict(kind=kind, **result))
            safe = {'session_id': row.get('id'), 'owner': row.get('owner'),
                    'state': row.get('state'), 'matching_live_processes': matched}
            if matched:
                live.append(safe)
            if str(row.get('owner', '')).startswith(('water-r27-', 'books-r27-', 'wire-r27-', 'r27-')):
                owned.append(safe)
        except Exception as error:
            errors.append({'session_directory': path.parent.name,
                           'type': type(error).__name__, 'message': str(error)})
    ids = powershell('@(Get-Process -Name Minecraft.Windows -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress') or []
    if isinstance(ids, int):
        ids = [ids]
    actual_games, exited = [], []
    for pid in ids:
        row = current(pid)
        if row:
            (actual_games if row['live'] else exited).append(row)
    task = powershell("Get-ScheduledTask -TaskName Codex-BBE-R27-Hibernate-20261022 | Select-Object TaskName,State,@{Name='StartBoundary';Expression={$_.Triggers[0].StartBoundary}},@{Name='Execute';Expression={$_.Actions[0].Execute}},@{Name='Arguments';Expression={$_.Actions[0].Arguments}},@{Name='StartWhenAvailable';Expression={$_.Settings.StartWhenAvailable}},@{Name='Enabled';Expression={$_.Settings.Enabled}},@{Name='TriggerEnabled';Expression={$_.Triggers[0].Enabled}},@{Name='WakeToRun';Expression={$_.Settings.WakeToRun}},@{Name='DisallowStartIfOnBatteries';Expression={$_.Settings.DisallowStartIfOnBatteries}},@{Name='StopIfGoingOnBatteries';Expression={$_.Settings.StopIfGoingOnBatteries}} | ConvertTo-Json -Compress")
    report = {'schema': 1, 'read_at': datetime.now().astimezone().isoformat(),
              'read_only': True, 'processes_stopped_by_this_script': 0,
              'registry_rows_checked': count, 'registry_read_errors': errors,
              'R27_owned_sessions': owned, 'matching_live_managed_sessions': live,
              'actual_live_MC': actual_games, 'enumerable_exited_MC': exited,
              'hibernation_task': task,
              'repositories': [git_state(path) for path in (ROOT, ROOT.parent / 'nemc-block-renderer', ROOT.parent / 'nemc-block-states')]}
    with args.output.open('x', encoding='utf8') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({'actual_live_MC': len(actual_games), 'matching_live_managed_sessions': len(live),
                      'registry_read_errors': len(errors), 'R27_sessions_checked': len(owned),
                      'task': task, 'tracked_changes': [len(r['tracked_status']) for r in report['repositories']]}))

if __name__ == '__main__':
    main()
