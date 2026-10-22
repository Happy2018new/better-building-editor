"""Launch one current-source lectern/book cold clone after an explicit team resource window."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from status_access import read_status
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / '.runtime/projects/r28-button-support-contrast-v3/.agents/skills/pyreact-debugging/scripts'), str(ROOT / '.runtime/projects/r28-button-support-contrast-v3/tools')]
from _session import process_identity, registry_dir
from audit_chest_occupied_runtime import process_snapshot
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from lifecycle_helpers import handles
def fingerprint(project):
    return {path.relative_to(project).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
            for pack in ('behavior_pack','resource_pack') for path in (project/pack).rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc','.pyo')}

p = argparse.ArgumentParser()
p.add_argument('--project', type=Path, required=True)
p.add_argument('--owner', required=True)
p.add_argument('--freeze', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
args = p.parse_args()
project = args.project.resolve(strict=True)
review_path=Path(__file__).resolve().parent/'root-review-and-slot-v1.json'
review=json.loads(review_path.read_bytes())
assert review['passed'] and review['source_manifest_sha256']==hashlib.sha256(args.freeze.read_bytes()).hexdigest()
prelaunch=review_path.with_name('prelaunch-config.json')
assert hashlib.sha256(prelaunch.read_bytes()).hexdigest()==review['prelaunch_config_sha256']
assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in json.loads(prelaunch.read_bytes())['host_assets'].items())
assert datetime.now(timezone.utc)<datetime.fromisoformat(review['cutoff_utc'])
config_sha256=hashlib.sha256((project/'.mcdev.json').read_bytes()).hexdigest()
assert project.parent == ROOT / '.runtime/projects'
assert args.owner=='r28-button-support-contrast-v3'
frozen = json.loads(args.freeze.read_bytes())
from frozen_guard import verify
assert verify()==frozen
assert fingerprint(project) == frozen['files']
assert all(not json.loads((project / '.mcdev.json').read_bytes())[key] for key in
           ('auto_hot_reload_mods', 'auto_hot_reload_ui', 'auto_hot_reload_materials', 'auto_hot_reload_shaders'))
args.output.mkdir(exist_ok=False)
reader_asset=frozen['manifest_reader']
reader_path=Path(reader_asset['path'])
assert hashlib.sha256(reader_path.read_bytes()).hexdigest()==reader_asset['sha256']
spec=importlib.util.spec_from_file_location('_r27_transform_shared_manifest_reader',reader_path)
reader=importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
manifest_read_events=[]
manifest_read_errors=[]

def read_manifest(path):
    before=len(manifest_read_events)
    def transaction():
        value=reader.native_read_json(path)
        assert type(value) is dict, 'Registry manifest is not an object'
        if value.get('owner')==args.owner:
            assert Path(value['project']).resolve()==project
            assert type(value['id']) is str and value['id']
        return value
    try:
        return reader.bounded_manifest_read(transaction,manifest_read_events,str(path))
    except Exception as error:
        manifest_read_errors.append({'path':str(path),'type':type(error).__name__,
            'error':str(error),'winerror':getattr(error,'winerror',None),'errno':getattr(error,'errno',None)})
        raise
    finally:
        if len(manifest_read_events)!=before or manifest_read_errors:
            (args.output/'manifest-read-events.json').write_text(json.dumps({
                'reader':reader_asset,'events':manifest_read_events,'errors':manifest_read_errors},indent=2)+'\n',encoding='utf8')

watch = read_status(ROOT / '.runtime/round-20261023/button-support-contrast-v3/assert-watch/status.json')
assert (datetime.now(timezone.utc) - datetime.fromisoformat(watch['checked_at'])).total_seconds() < 60
assert args.owner in watch['owners']
assert watch['host_sha256']==frozen['diagnostic_watcher']['sha256']
assert not watch['errors'] and not watch['other_assertions']
memory = commit_at_boundary()
assert memory['commit_available_bytes'] >= 6 * 1024 ** 3
raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command',
    '@(Get-Process -Name Minecraft.Windows -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress'], encoding='utf8')
pids = json.loads(raw) if raw.strip() else []
pids = [pids] if isinstance(pids, int) else pids
import ctypes
from ctypes import wintypes
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
k.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)];k.CloseHandle.argtypes=[wintypes.HANDLE]
live=[];exited=[]
for pid in pids:
 identity=process_identity(pid)
 if not identity:continue
 handle=k.OpenProcess(0x1000,False,pid)
 if not handle:continue
 try:
  code=wintypes.DWORD();assert k.GetExitCodeProcess(handle,ctypes.byref(code))
  assert process_identity(pid)==identity
  row=dict(pid=pid,identity=identity,exit_code=code.value)
  (live if code.value==259 else exited).append(row)
 finally:k.CloseHandle(handle)
assert not live, ('Final transform cold run requires the explicit exclusive window',live)
assert not any(read_manifest(path).get('owner') == args.owner for path in registry_dir().glob('*/session.json'))
mcdk = ROOT / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
guard = ROOT / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
pins = {mcdk:'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9',
        guard:'04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93'}
assert all(hashlib.sha256(path.read_bytes()).hexdigest() == sha for path, sha in pins.items())
cmd = [sys.executable, '-B', '-X', 'utf8', str(project / '.agents/skills/pyreact-debugging/scripts/instances.py'),
       'start', '--project', str(project), '--owner', args.owner, '--name', args.owner,
       '--preset', 'ui', '--wait', '180', '--mcdk', str(mcdk), '--noactivate-dll', str(guard),
       '--noactivate-sha256', pins[guard], '--noactivate-mcdk-sha256', pins[mcdk]]
env = dict(os.environ, OPENBLAS_NUM_THREADS='1', MCDEV_ALLOW_USER_FOREGROUND='0')
report = dict(owner=args.owner, project=str(project), command=cmd, live_before=live,
              memory=memory, reload_config_sha256=config_sha256, exited_process_records=exited, samples=[],
              manifest_reader=reader_asset,manifest_read_events=manifest_read_events,manifest_read_errors=manifest_read_errors,
              started_at=datetime.now(timezone.utc).isoformat())
def save():
    (args.output / 'report.json').write_text(json.dumps(report, indent=2), encoding='ascii')
save()
with (args.output / 'stdout.json').open('wb') as stdout, (args.output / 'stderr.txt').open('wb') as stderr:
    child = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
                             stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    observer = None
    previous_handles = {}
    while child.poll() is None:
        found=[]
        for path in registry_dir().glob('*/session.json'):
            data=read_manifest(path)
            if data.get('owner')==args.owner:found.append((path,data))
        if found:
            assert len(found) == 1
            session_path,session=found[0]
            assert Path(session['project']).resolve() == project
            report['session_file'] = str(session_path)
            if session.get('game_identity') and process_identity(session['game_pid']) == session['game_identity']:
                row = process_snapshot(session['game_pid'])
                row['memory'] = commit_at_boundary()
                report['samples'].append(row)
                save()
                assert row['memory']['commit_available_bytes'] >= 6 * 1024 ** 3
                status = read_status(Path(__file__).resolve().parent / 'assert-watch/status.json')
                assert status['owners'] == [args.owner] and not status['errors'] and not status['other_assertions']
                assert status['host_sha256'] == frozen['diagnostic_watcher']['sha256']
                assert (datetime.now(timezone.utc) - datetime.fromisoformat(status['checked_at'])).total_seconds() < 5
                row['owned_handles'] = {}
                for key in ('game', 'mcdk'):
                    if session.get(key + '_identity') and process_identity(session[key + '_pid']) == session[key + '_identity']:
                        count = handles(session[key + '_pid'])
                        row['owned_handles'][key] = count
                        save()
                        assert count is not None and count < 250000 and count - previous_handles.get(key, count) < 10000
                        previous_handles[key] = count
                save()
                assert row['handles'] < 250000, 'Startup handle budget exceeded; preserve before owned stop'
                if observer is None:
                    obs = [sys.executable, '-B', '-X', 'utf8', str(ROOT / '.runtime/round-20261019/watch_exact_start.py'),
                           '--session', str(session_path), '--owner', args.owner, '--project', str(project),
                           '--output', str(args.output / 'exact-exit.json')]
                    with (args.output / 'observer.log').open('wb') as output:
                        observer = subprocess.Popen(obs, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
                    report['observer_pid'] = observer.pid
        time.sleep(.75)
    report['launch_exit_code'] = child.returncode
    save()
assert child.returncode == 0
result = json.loads((args.output / 'stdout.json').read_bytes())
assert result['ready'] and result['owner'] == args.owner
report.update({k: result[k] for k in ('session_file', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')})
report['source_unchanged'] = fingerprint(project) == frozen['files'] and hashlib.sha256((project/'.mcdev.json').read_bytes()).hexdigest()==config_sha256
save()
assert report['source_unchanged']
print(json.dumps({k: report[k] for k in ('owner', 'session_file', 'game_pid', 'source_unchanged')}))
