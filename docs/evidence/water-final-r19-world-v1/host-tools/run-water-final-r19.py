"""Owner-bound final-source water runs with native evidence instrumentation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path('D:/bbe-r18-water-production')
OUTPUT = Path(os.environ.get('MCDEV_WATER_FINAL_OUTPUT', str(ROOT / '.runtime/water-final-r19-v1')))
OWNER = 'water-final-r19'
INSTANCES = ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'
CAPTURE = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
MCDK = ROOT / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
DLL = ROOT / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'


def save(name, value):
    (OUTPUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='ascii')


def launch():
    if (OUTPUT / 'start.json').exists():
        raise ValueError('The final launch receipt already exists')
    command = [sys.executable, '-X', 'utf8', str(INSTANCES), 'start', '--project', str(PROJECT),
        '--owner', OWNER, '--name', OUTPUT.name, '--preset', 'ui', '--mcdk', str(MCDK),
        '--noactivate-dll', str(DLL), '--noactivate-sha256',
        '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93',
        '--noactivate-mcdk-sha256', 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9',
        '--wait', os.environ.get('MCDEV_WATER_START_WAIT', '90')]
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf8')
    save('launch-command.json', {'argv': command, 'returncode': result.returncode,
                                'stdout': result.stdout, 'stderr': result.stderr})
    bound = json.loads(result.stdout)
    save('start.json', bound)
    if result.returncode:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return result.returncode
    print(json.dumps({key: bound[key] for key in ('ready', 'game_pid', 'mcdk_pid', 'id')}), flush=True)
    return 0


def run(mode):
    bound = json.loads((OUTPUT / 'start.json').read_bytes())
    os.environ.update(MCDEV_SESSION_FILE=bound['session_file'], MCDEV_OWNER=OWNER)
    sys.path.insert(0, str(PROJECT / 'tools'))
    if mode == 'workspace-ready':
        import probe_product_water as probe
        from mcdk import return_value
        observations = []
        started = time.monotonic()
        with probe.base.Client(timeout=30) as client:
            while True:
                ready = return_value(client.call('execute_code', {'code':
                    "import mod.client.extraClientApi as api\n"
                    "owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')\n"
                    "_result=owner is not None and owner.session is not None",
                    'is_client': True, 'direct_return': True}))
                metrics = probe.workspace.transport.metrics(bound['session_file'], OWNER)
                observations.append({'elapsed_seconds': time.monotonic() - started,
                                     'workspace_ready': ready, 'metrics': metrics})
                save('workspace-ready.json', observations)
                if metrics['handles'] >= 250000:
                    raise RuntimeError('Native handle budget reached before workspace readiness')
                if ready is True or ready == 'True':
                    return 0
                if time.monotonic() - started >= 60.:
                    raise TimeoutError('Business workspace did not initialize')
                time.sleep(.25)
    if mode == 'calibration':
        import verify_camera_projection as calibration
        from capture_native_window import capture

        def guarded_capture(self, label, tree=None):
            target = OUTPUT / ('calibration_' + label + '.png')
            result = capture(bound['session_file'], OWNER, target, CAPTURE)
            result['size'] = [result['width'], result['height']]
            return result

        calibration.SignCheck.capture = guarded_capture
        sys.argv = ['verify_camera_projection.py', str(OUTPUT / 'calibration.json'),
                    '--native-resolution', '--skyward-tilted', '--fixture-lift-y', '64']
        return calibration.main()
    if mode in ('status', 'stop'):
        command = [sys.executable, '-X', 'utf8', str(INSTANCES), mode,
                   '--session', bound['session_file'], '--owner', OWNER]
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf8')
        save(mode + '.json', {'argv': command, 'returncode': result.returncode,
                             'stdout': result.stdout, 'stderr': result.stderr})
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return result.returncode
    import probe_product_water as probe
    output = OUTPUT / (mode + '.json')
    if mode == 'editor':
        import diagnose_water_editor_r19 as diagnostic
        original = probe.base.capture
        readbacks = {}

        def native_capture(*args, **kwargs):
            with probe.base.Client(timeout=30) as client:
                check = probe.blueprints.BlueprintCheck(client, output, 30.)
                readbacks[args[2].name] = check.run(diagnostic.STATE)
            save('editor-native-readbacks.json', readbacks)
            return original(*args, **kwargs)

        probe.base.capture = native_capture
    sys.argv = ['probe_product_water.py', '--session', bound['session_file'], '--owner', OWNER,
        '--capture-exe', str(CAPTURE), '--launch-inputs', str(OUTPUT / 'launch-inputs.json'),
        '--output', str(output), '--frozen', '--visibility-controls', '--opaque-side-controls',
        '--alpha-controls', '--measure-budgets', '--max-seconds', '600']
    if mode == 'editor':
        sys.argv += ['--route', 'editor']
        for name in ('source', 'low', 'flow_east', 'flow_south', 'flow_west',
                     'flow_north', 'pool', 'falling', 'wet_oak_fence'):
            sys.argv += ['--case', name]
    else:
        sys.argv += ['--route', 'full', '--route', 'missing', '--case', 'pool',
                     '--camera-calibration', str(OUTPUT / 'calibration.json'),
                     '--world-fixture-lift-y', '64', '--world-view-scale', '.5',
                     '--pool-view-scale', '.5']
    return probe.main()


if __name__ == '__main__':
    if sys.argv[1] == 'world-batch':
        OUTPUT.mkdir(parents=True, exist_ok=True)
        phases = {'completed': False, 'production_qualified': False}
        try:
            for phase in ('launch', 'workspace-ready', 'calibration', 'world'):
                result = subprocess.run([sys.executable, '-X', 'utf8', str(Path(__file__).resolve()), phase],
                                        capture_output=True, text=True, encoding='utf8')
                save(phase + '-execution.json', {'returncode': result.returncode,
                                               'stdout': result.stdout, 'stderr': result.stderr})
                phases[phase] = result.returncode == 0
                save('batch.json', phases)
                print(json.dumps({'phase': phase, 'returncode': result.returncode}), flush=True)
                if result.returncode:
                    raise RuntimeError('Bounded world batch failed: ' + phase)
            phases['completed'] = True
        finally:
            if (OUTPUT / 'start.json').exists():
                result = subprocess.run([sys.executable, '-X', 'utf8', str(Path(__file__).resolve()), 'stop'],
                                        capture_output=True, text=True, encoding='utf8')
                phases['stop_returncode'] = result.returncode
            save('batch.json', phases)
    else:
        raise SystemExit(launch() if sys.argv[1] == 'launch' else run(sys.argv[1]))
