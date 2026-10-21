"""One reviewed private launch/bootstrap/G/F-editor group; restore and ordinary stop."""
from datetime import datetime, timezone
import hashlib
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import process_identity



def available_commit():
    class MemoryStatus(ctypes.Structure):
        _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD)] + [
            (name, ctypes.c_ulonglong) for name in ('total_physical', 'available_physical',
             'total_pagefile', 'available_pagefile', 'total_virtual', 'available_virtual', 'available_extended')]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    memory = MemoryStatus()
    memory.length = ctypes.sizeof(memory)
    kernel.GlobalMemoryStatusEx.argtypes = (ctypes.POINTER(MemoryStatus),)
    if not kernel.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise ctypes.WinError(ctypes.get_last_error())
    return memory.available_pagefile


def main():
    assert len(sys.argv) == 1, 'One immutable full group; no retry flags'
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    project = Path(binding['project'])
    output = WORK / 'group-execution-v1.json'
    assert not output.exists(), 'Retain all previous outcomes'
    assert datetime.now(timezone.utc) < datetime.fromisoformat('2026-10-21T06:55:00+00:00')
    receipt = {'schema': 1, 'owner': binding['owner'], 'label': 'final41-editor',
               'source_contract_sha256': binding['source_contract_sha256'],
               'production_admission_performed': False, 'default_path_evidence': False,
               'started_at': time.time(), 'steps': [], 'completed': False,
               'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', MCDEV_ALLOW_USER_FOREGROUND='0')
    launch = None

    def save():
        output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')

    def command(name, filename, args=()):
        if name in ('launch', 'bootstrap', 'G', 'F-editor'):
            assert datetime.now(timezone.utc) < datetime.fromisoformat('2026-10-21T06:55:00+00:00'), 'No new experiment after 14:55'
        row = {'name': name, 'started_at': time.time(), 'arguments': [sys.executable, '-B', '-X', 'utf8', str(WORK / filename), *args]}
        row['memory_preflight'] = {'available_commit_bytes': available_commit(), 'minimum_available_commit_bytes': 6 * 1024 ** 3}
        receipt['steps'].append(row)
        save()
        assert row['memory_preflight']['available_commit_bytes'] >= 6 * 1024 ** 3, 'Below fixed 6 GiB commit headroom before ' + name
        print(json.dumps({'stage_start': name}), flush=True)
        with (WORK / (name + '.stdout.txt')).open('xb') as stdout, (WORK / (name + '.stderr.txt')).open('xb') as stderr:
            result = subprocess.run(row['arguments'], cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        row.update(exit_code=result.returncode, elapsed_seconds=time.time() - row['started_at'])
        save()
        print(json.dumps(row), flush=True)
        result.check_returncode()

    def read_restore():
        os.environ.update(MCDEV_SESSION_FILE=launch['session_file'], MCDEV_OWNER=binding['owner'], MCDEV_ALLOW_USER_FOREGROUND='0')
        sys.path.insert(0, str(project / 'tools'))
        import probe_product_water as probe
        with probe.base.Client(timeout=35) as client:
            state = probe.base.run(client, '''import json,sys
import mod.client.extraClientApi as api
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
s=owner.session;b=owner.bridge
_result=json.dumps({'session_exists':s is not None,
 'markers':[name for name in ('_blueprint_qa_saved','_blueprint_visual_saved',
 '_product_water_saved_profile','_product_water_timing','_sign_visual_hud_saved',
 '_neighbor_visual_options_saved') if hasattr(sys,name)],
 'projection_active':s.projection_active if s is not None else False,
 'busy':s.busy if s is not None else False,'edit_job':s.edit_job is not None if s is not None else False,
 'io_job':s.io_job is not None if s is not None else False,
 'world_actors':len(b.projection_entities)+int(bool(b.entity)) if b is not None else 0,
 'preparing_entity':bool(b.preparing_entity) if b is not None else False})
''')
            world = probe.base.run(client, '''import json,sys
_result=json.dumps({'markers':[name for name in ('_liquid_pose_world','_context_environment_saved') if hasattr(sys,name)]})
''', True)
        unchanged = probe.snapshot_sources(project) == binding['source_sha256']
        passed = unchanged and not state['markers'] and not world['markers'] and not any(state[k] for k in ('projection_active', 'busy', 'edit_job', 'io_job', 'world_actors', 'preparing_entity'))
        result = {'passed': passed, 'client': state, 'world': world, 'source_unchanged': unchanged,
                  'at': time.time(), 'limited_to_runtime_markers_and_actors': True}
        path = WORK / 'independent-restore-v1.json'
        with path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
        assert passed, result

    save()
    try:
        command('assert-watch-start', 'start_assert_watch.py')
        command('launch', 'launch_r25.py')
        launch = json.loads((WORK / 'launch/launch.json').read_bytes())
        command('bootstrap', 'run_candidate_bootstrap.py')
        command('G', 'run_product_v2_stages.py', ('G',))
        assert datetime.now(timezone.utc) < datetime.fromisoformat('2026-10-21T06:55:00+00:00'), 'Do not start a long batch after cutoff'
        command('F-editor', 'run_product_v2_f_editor.py')
        read_restore()
        command('retire-bootstrap-marker', 'retire_bootstrap_marker.py')
        receipt['completed'] = True
    except BaseException as error:
        receipt['error'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
        raise
    finally:
        path = WORK / 'launch/launch.json'
        if launch is None and path.exists():
            launch = json.loads(path.read_bytes())
        if launch and launch.get('session_file'):
            if not (WORK / 'independent-restore-v1.json').exists() and launch.get('ready'):
                try:
                    read_restore()
                except Exception as error:
                    receipt['independent_restore_error'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
            args = [sys.executable, '-B', '-X', 'utf8', str(ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'),
                    'stop', '--session', launch['session_file'], '--owner', binding['owner']]
            stopped = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
            receipt['ordinary_stop'] = {'exit_code': stopped.returncode, 'stdout': stopped.stdout, 'stderr': stopped.stderr}
            exact = {k: (launch.get(k + '_pid'), launch.get(k + '_identity')) for k in ('game', 'mcdk')}
            known = {k: pair for k, pair in exact.items() if pair[0] and pair[1]}
            receipt['stop_identity_inputs'] = {k: {'pid': pair[0], 'identity': pair[1], 'complete': k in known} for k, pair in exact.items()}
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline and any(process_identity(pid) == identity for pid, identity in known.values()):
                time.sleep(.25)
            absent = {k: process_identity(pid) != identity for k, (pid, identity) in known.items()}
            receipt['exact_identities_absent_after_stop'] = absent
            if len(known) == 2 and all(absent.values()) and stopped.returncode != 0:
                final = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
                receipt['registry_finalize'] = {'exit_code': final.returncode, 'stdout': final.stdout, 'stderr': final.stderr}
        receipt['elapsed_seconds'] = time.time() - receipt['started_at']
        save()
        print(json.dumps({'completed': receipt['completed'], 'elapsed_seconds': receipt['elapsed_seconds']}), flush=True)


if __name__ == '__main__':
    main()
