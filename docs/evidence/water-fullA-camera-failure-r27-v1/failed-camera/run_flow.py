"""Frozen product probe with explicit versioned deferred host capture."""
import ctypes
from ctypes import wintypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
PROJECT = Path('D:\\Happy2018newの个人文件\\GitHub\\better-building-editor\\.runtime\\projects\\water-r27-merged-flow-editor-v1')
SESSION = Path(json.loads((WORK / 'launch/launch.json').read_bytes())['session_file'])
OWNER = 'water-r27-merged-fullA-v1'
STAGE = sys.argv[1] if len(sys.argv) == 2 else None
if STAGE != 'A':
    raise ValueError('Pass one stage: A, B, R, or G')
CASES = {
    'A': ('flow_east', 'flow_south', 'flow_west', 'flow_north', 'falling'),
    'B': ('wet_oak_fence', 'pool'),
    'R': ('neighbor_oak_slab', 'neighbor_oak_stairs', 'neighbor_glass_pane',
          'neighbor_stone', 'transparent_overlap'),
    'G': ('gallery',),
}[STAGE]
ROUTES = ('editor', 'full', 'missing')
OUT = WORK / 'product-v2-a-v1.json'
HANDLES = OUT.with_name(OUT.stem + '-handles.json')
RECEIPT = OUT.with_name(OUT.stem + '-host.json')


def main():
    if any(path.exists() for path in (OUT, HANDLES, RECEIPT)):
        raise ValueError('Use fresh immutable result paths')
    sys.path.insert(0, str(PROJECT / 'tools'))
    tool_path = PROJECT / 'tools/probe_product_water.py'
    spec = importlib.util.spec_from_file_location('product_v2_probe_water', str(tool_path))
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    import capture_native_window
    capture_native_window.ROOT = ROOT
    os.environ.update(MCDEV_SESSION_FILE=str(SESSION), MCDEV_OWNER=OWNER,
                      OPENBLAS_NUM_THREADS='1', MCDEV_ALLOW_USER_FOREGROUND='0')
    from _session import load_session, process_identity
    binding = load_session(str(SESSION), OWNER, live=True)
    assert Path(binding['project']).resolve() == PROJECT.resolve()
    initial = probe.snapshot_sources(PROJECT)
    launch = json.loads((WORK / 'product-v2-launch-inputs.json').read_bytes())
    assert initial == launch['source_sha256']
    assert probe.snapshot_digest(initial) == launch['source_contract_sha256']
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

    samples = []
    state = {'row': None, 'finished_rows': 0, 'capture_count': 0, 'burst_count': 0}
    receipt = {'schema': 1, 'stage': STAGE, 'routes': ROUTES, 'cases': CASES,
               'owner': OWNER, 'session_id': binding['id'],
               'game_pid': binding['game_pid'], 'game_identity': binding['game_identity'],
               'mcdk_pid': binding['mcdk_pid'], 'mcdk_identity': binding['mcdk_identity'],
               'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'source_contract_sha256': launch['source_contract_sha256'],
               'production_admission_performed': False, 'qualified_or_default_gate_set': False,
               'maximum_handles': 250000, 'rapid_step_growth_limit': 10000,
               'diagnostic_only': False, 'qualification_evidence': False, 'sampling_protocol_check_only': False, 'formal_A_capture_candidate': True, 'formal_A_accepted': False, 'world_A_accepted': False, 'production_admission_performed': False, 'started_at': time.time(), 'completed': False, 'ordinary_profile_no_assignment':True, 'old_qualification_reused_as_new_A':False}

    def save():
        HANDLES.write_text(json.dumps({'schema': 1, 'samples': samples}, indent=2) + '\n', 'utf8')
        RECEIPT.write_text(json.dumps(receipt, indent=2) + '\n', 'utf8')

    def sample(label, enforce=True):
        row = dict(probe.workspace.transport.metrics(str(SESSION), OWNER), label=label,
                   sampled_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'), mcdk_handles=count_mcdk())
        samples.append(row)
        save()
        if enforce and (row['handles'] >= 250000 or
                        (len(samples) > 1 and row['handles'] - samples[-2]['handles'] >= 10000)):
            raise RuntimeError('Handle guard reached at ' + label)
        return row

    from scene_policy import describe_scene
    import scene_game
    geometry=[]
    receipt['native_geometry_observations']=geometry
    active_check=[None]

    def geometry_sample(label):
        route = next((route for route in ROUTES if label.startswith(OUT.stem + '_' + route + '_')), None)
        assert route is not None, label
        if route != 'editor':
            return
        assert active_check[0] is not None
        value=original_run(active_check[0],probe.SCENE_STATE+scene_game.EXTRA_STATE)
        verdict=describe_scene(value,2,True)
        geometry.append({'label':label,'state':value,'verdict':verdict})
        save()
        assert verdict['complete'],verdict

    original_capture = probe.base.capture
    original_run = probe.blueprints.BlueprintCheck.run

    def tracked_capture(session, owner, output, executable):
        label = Path(output).stem
        geometry_sample(label + '_before_wgc')
        sample(label + '_before_wgc')
        captured = original_capture(session, owner, output, executable)
        sample(label + '_after_wgc')
        state['capture_count'] += 1
        return captured

    def tracked_run(check, code):
        active_check[0]=check
        is_load = 'identity,control,pose=' in code and 'source_document(identity,control)' in code
        if is_load and state['row']:
            row = sample(state['row'] + '_row_complete')
            state['finished_rows'] += 1
            print(json.dumps({'row_complete': state['row'], 'row_count': state['finished_rows'],
                              'captures': state['capture_count'], 'bursts': state['burst_count'],
                              'handles': row['handles'], 'mcdk_handles': row['mcdk_handles']}), flush=True)
        result = original_run(check, code)
        if is_load:
            state['row'] = result['case'] + '_' + result['control']
            sample(state['row'] + '_row_loaded')
        return result

    probe.base.capture = tracked_capture
    probe.blueprints.BlueprintCheck.run = tracked_run
    capture_exe = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
    assert probe.fingerprint(capture_exe) == 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
    arguments = [str(tool_path), '--session', str(SESSION), '--owner', OWNER,
                 '--capture-exe', str(capture_exe), '--output', str(OUT),
                 '--launch-inputs', str(WORK / 'product-v2-launch-inputs.json'),
                 '--controls', 'wet' if STAGE in ('A', 'B') else 'all',
                 '--max-seconds', '1800', '--max-handles', '250000', '--production-default']
    if STAGE != 'A':
        arguments += ['--frozen']
    arguments += ['--camera-calibration', str(WORK / 'product-v2-camera-native-v1.json'),
                  '--world-fixture-lift-y', '64', '--world-view-scale', '.5']
    if STAGE in ('A', 'B'):
        arguments += ['--extras']
    if STAGE == 'A':
        # Reviewed non-trace fixed-startup protocol; frozen product source remains unchanged.
        candidate = Path('D:\\Happy2018newの个人文件\\GitHub\\better-building-editor\\.runtime\\round-20261021\\water-startup-protocol-v2') / 'candidate/tools'
        sys.path.insert(0, str(candidate))
        import capture_native_burst
        import capture_native_burst_deferred
        import capture_native_burst_startup
        sys.path.remove(str(candidate))
        for module in (capture_native_burst, capture_native_burst_deferred, capture_native_burst_startup):
            assert Path(module.__file__).resolve().parent == candidate.resolve()
        capture_native_burst.ROOT = PROJECT
        contract_path = Path('D:\\Happy2018newの个人文件\\GitHub\\better-building-editor\\.runtime\\round-20261021\\water-startup-protocol-v2') / 'host-contract-v1.json'
        contract = json.loads(contract_path.read_bytes())
        receipt['startup_host_contract_sha256'] = probe.fingerprint(contract_path)
        receipt['startup_host_contract'] = contract

        def actual_host_sources():
            current = {path: probe.fingerprint(Path(path)) for path in contract['sources']}
            assert current == contract['sources'], 'Frozen startup host sources changed'
            for module in (capture_native_burst._session, capture_native_burst._window):
                current[str(Path(module.__file__).resolve())] = probe.fingerprint(Path(module.__file__))
            return current

        capture_native_burst._host_sources = actual_host_sources
        burst_exe = Path(contract['binary']['path'])
        burst_hash = contract['binary']['sha256']
        assert probe.fingerprint(burst_exe) == burst_hash
        original_burst = capture_native_burst.capture

        def tracked_burst(*args, **kwargs):
            label = Path(args[2]).stem
            geometry_sample(label + '_before_burst')
            sample(label + '_before_burst')
            captured = original_burst(*args, **kwargs)
            sample(label + '_after_burst')
            state['burst_count'] += 1
            return captured

        capture_native_burst.capture = tracked_burst
        arguments += ['--flow-burst-exe', str(burst_exe), '--flow-burst-sha256', burst_hash,
                      '--flow-burst-duration-ms', '3200', '--falling-skyward']
    elif STAGE == 'R':
        arguments += ['--reverse-view']
    elif STAGE == 'G':
        arguments += ['--editor-zoom', '.9']
    for route in ROUTES:
        arguments += ['--route', route]
    for case in CASES:
        arguments += ['--case', case]
    sys.argv = arguments
    receipt['arguments'] = arguments
    sample('before_' + STAGE)
    try:
        result = probe.main()
        receipt['exit_code'] = result
        receipt['completed'] = result == 0
        return result
    finally:
        if state['row']:
            sample(state['row'] + '_final_row_and_cleanup_complete', enforce=False)
        sample('after_' + STAGE + '_cleanup', enforce=False)
        receipt.update(elapsed_seconds=time.time() - receipt['started_at'],
                       source_unchanged=initial == probe.snapshot_sources(PROJECT),
                       captured=state['capture_count'], finished_rows=state['finished_rows'],
                       bursts=state['burst_count'])
        save()


if __name__ == '__main__':
    raise SystemExit(main())
