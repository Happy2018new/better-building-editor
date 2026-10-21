"""D cold default routes and same-session camera, never assigning a candidate."""
import ctypes
from ctypes import wintypes
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
PROJECT = Path('D:\\Happy2018newの个人文件\\GitHub\\better-building-editor\\.runtime\\projects\\water-r25-final41-v2')
OWNER = 'water-r27-final41-size720-v2'
STAGE = sys.argv[1] if len(sys.argv) == 2 else None
if STAGE not in ('camera', 'D'):
    raise ValueError('Pass camera or D')


def main():
    launch = json.loads((WORK / 'launch/launch.json').read_bytes())
    assert launch['ready'] is True and launch['owner'] == OWNER
    session = launch['session_file']
    os.environ.update(MCDEV_SESSION_FILE=session, MCDEV_OWNER=OWNER,
                      OPENBLAS_NUM_THREADS='1', MCDEV_ALLOW_USER_FOREGROUND='0')
    sys.path.insert(0, str(PROJECT / 'tools'))
    import probe_product_water as probe
    import capture_native_window
    from _session import load_session, process_identity
    capture_native_window.ROOT = ROOT
    binding = load_session(session, OWNER, live=True)
    assert Path(binding['project']).resolve() == PROJECT.resolve()
    initial = probe.snapshot_sources(PROJECT)
    inputs = json.loads((WORK / 'product-v2-launch-inputs.json').read_bytes())
    assert initial == inputs['source_sha256']
    output = WORK / ('product-v2-camera-native-v1.json' if STAGE == 'camera' else 'default-r25-d.json')
    handles_path = output.with_name(output.stem + '-handles.json')
    receipt_path = output.with_name(output.stem + '-host.json')
    assert not any(path.exists() for path in (output, handles_path, receipt_path))
    rows = []
    receipt = {'schema': 1, 'stage': STAGE, 'owner': OWNER,
        'session_id': binding['id'], 'game_pid': binding['game_pid'],
        'game_identity': binding['game_identity'], 'mcdk_pid': binding['mcdk_pid'],
        'mcdk_identity': binding['mcdk_identity'],
        'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_contract_sha256': inputs['source_contract_sha256'],
        'profile_assignment_performed': False, 'gate_mutation_performed': False,
        'maximum_handles': 250000, 'rapid_step_growth_limit': 10000,
        'capture_helper_sources_root': str(ROOT / 'tools/native_wgc'),
        'started_at': time.time(), 'completed': False}
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessHandleCount.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)

    def count_mcdk():
        assert process_identity(binding['mcdk_pid']) == binding['mcdk_identity']
        handle = kernel.OpenProcess(0x1000, False, binding['mcdk_pid'])
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            count = wintypes.DWORD()
            if not kernel.GetProcessHandleCount(handle, ctypes.byref(count)):
                raise ctypes.WinError(ctypes.get_last_error())
            return count.value
        finally:
            kernel.CloseHandle(handle)

    def save():
        handles_path.write_text(json.dumps({'schema': 1, 'samples': rows}, indent=2) + '\n', 'utf8')
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', 'utf8')

    def sample(label, enforce=True):
        row = dict(probe.workspace.transport.metrics(session, OWNER), label=label,
                   sampled_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'), mcdk_handles=count_mcdk())
        rows.append(row)
        save()
        if enforce and (row['handles'] >= 250000 or row['mcdk_handles'] >= 250000 or
            len(rows) > 1 and any(row[key] - rows[-2][key] >= 10000 for key in ('handles', 'mcdk_handles'))):
            raise RuntimeError('Fixed D handle guard reached at ' + label)
        return row

    original_capture = capture_native_window.capture
    state = {'row': None, 'captures': 0}
    def tracked_capture(session_arg, owner, path, executable):
        label = Path(path).stem
        sample(label + '_before_wgc')
        result = original_capture(session_arg, owner, path, executable)
        sample(label + '_after_wgc')
        state['captures'] += 1
        return result
    capture_native_window.capture = tracked_capture
    probe.base.capture = tracked_capture
    original_run = probe.blueprints.BlueprintCheck.run
    def tracked_run(check, code):
        is_load = 'identity,control,pose=' in code and 'source_document(identity,control)' in code
        result = original_run(check, code)
        if is_load:
            state['row'] = result['case'] + '_' + result['control']
            row = sample(state['row'] + '_loaded')
            print(json.dumps({'row_loaded': state['row'], 'handles': row['handles']}), flush=True)
        return result
    probe.blueprints.BlueprintCheck.run = tracked_run
    original_base_run = probe.base.run
    def attested_base_run(client, code, server=False):
        result = original_base_run(client, code, server)
        if STAGE == 'D' and server and code == probe.base.NEAR_PLAYER:
            observed = original_base_run(client, '''import json,sys
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
factory=api.GetEngineCompFactory()
origin=tuple(saved['origin'])
platform=(origin[0]-4,origin[1]-1,origin[2]-4)
_result=json.dumps({'before_foot':saved['foot_before'],
 'actual_foot':factory.CreatePos(saved['player']).GetFootPos(),
 'fixture_origin':origin,'platform':platform,
 'actual_platform':factory.CreateBlockInfo(saved['player']).GetBlockNew(platform,saved['dimension'])})
''', True)
            receipt['world_isolation_readback'] = observed
            save()
            assert observed['actual_foot'][1] - observed['before_foot'][1] >= 64
            assert observed['fixture_origin'][1] - observed['before_foot'][1] >= 64
            assert observed['actual_platform']['name'] == 'minecraft:stone'
        return result
    probe.base.run = attested_base_run
    helper = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
    assert probe.fingerprint(helper) == 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
    if STAGE == 'camera':
        tool = importlib.import_module('verify_camera_projection')
        arguments = [str(PROJECT / 'tools/verify_camera_projection.py'), str(output),
            '--native-resolution', '--native-api', '--native-capture-exe', str(helper), '--fixture-lift-y', '64']
    else:
        tool = probe
        arguments = [str(PROJECT / 'tools/probe_product_water.py'), '--session', session,
            '--owner', OWNER, '--capture-exe', str(helper), '--output', str(output),
            '--launch-inputs', str(WORK / 'product-v2-launch-inputs.json'),
            '--camera-calibration', str(WORK / 'product-v2-camera-native-v1.json'),
            '--production-default', '--extras', '--controls', 'all',
            '--world-fixture-lift-y', '64', '--world-view-scale', '.5',
            '--max-seconds', '1800', '--max-handles', '250000']
        for route in ('editor', 'full', 'missing'):
            arguments.extend(('--route', route))
        for case in ('source', 'pool', 'wet_oak_fence'):
            arguments.extend(('--case', case))
    receipt['arguments'] = arguments
    sample('before_' + STAGE)
    with probe.base.Client(timeout=30) as client:
        deadline = time.monotonic() + 60.
        while True:
            initialized = original_base_run(client, "import mod.client.extraClientApi as api\n"
                "owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')\n"
                "_result=owner is not None and owner.session is not None")
            if initialized is True or initialized == 'True':
                receipt['workspace_initialized'] = True
                save()
                break
            if time.monotonic() >= deadline:
                raise TimeoutError('Cold D business Session did not initialize')
            time.sleep(.25)
    sys.argv = arguments
    try:
        result = tool.main()
        receipt.update(exit_code=result, completed=result == 0)
        return result
    finally:
        sample('after_' + STAGE + '_cleanup', enforce=False)
        receipt.update(source_unchanged=initial == probe.snapshot_sources(PROJECT),
            elapsed_seconds=time.time() - receipt['started_at'], captures=state['captures'])
        save()


if __name__ == '__main__':
    raise SystemExit(main())
