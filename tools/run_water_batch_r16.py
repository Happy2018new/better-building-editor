"""Launch, calibrate, capture and reclaim one bounded owned water batch."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence/water-product-r16-v1'
OWNER = 'water-product-r16'
WGC = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
CORE = ('source', 'low', 'diagonal', 'drop_north', 'pool', 'falling',
        'flow_east', 'flow_south', 'flow_west', 'flow_north', 'wet_oak_fence')
NEIGHBORS = ('wet_glass_pane', 'wet_oak_slab', 'wet_oak_stairs', 'neighbor_oak_slab',
             'neighbor_oak_stairs', 'neighbor_glass_pane', 'neighbor_stone', 'transparent_overlap')


def run(command, cwd, env, log=None):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True,
                            encoding='utf-8', errors='replace')
    if log is not None:
        log.write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError('Command failed (%s): %s' % (result.returncode, result.stderr[-3000:]))
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path('D:/bbe-r16-water-production'))
    parser.add_argument('--launch-inputs', type=Path, default=EVIDENCE / 'launch-inputs-v12.json')
    parser.add_argument('--name', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--route', action='append', choices=('editor', 'full', 'missing'), required=True)
    parser.add_argument('--batch', choices=('core', 'neighbors', 'all'))
    parser.add_argument('--case', action='append')
    parser.add_argument('--animated', action='store_true')
    parser.add_argument('--extras', action='store_true')
    parser.add_argument('--reverse', action='store_true')
    parser.add_argument('--gallery', action='store_true')
    parser.add_argument('--production-default', action='store_true')
    parser.add_argument('--native-world-geometry', action='store_true',
                        help='Record same-session native stone corners for world geometry '
                             'and native side grids for the ordinary frozen side-control matrix')
    parser.add_argument('--pool-view-scale', type=float)
    parser.add_argument('--retain', action='store_true',
                        help='Retain the owned game for sequential diagnostics after the restored batch')
    args = parser.parse_args()
    args.launch_inputs = args.launch_inputs.resolve(strict=True)
    report = EVIDENCE / (args.name + '.json')
    camera = EVIDENCE / ('camera-' + args.name + '.json')
    if report.exists() or camera.exists():
        parser.error('Choose fresh batch and camera reports')
    env = dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND='1')
    instances = ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'
    launch = [sys.executable, str(instances), 'start', '--project', str(args.project),
        '--owner', OWNER, '--name', 'water-product-r16-' + args.name, '--port', str(args.port), '--wait', '180',
        '--mcdk', str(ROOT / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'),
        '--noactivate-dll', str(ROOT / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'),
        '--noactivate-sha256', '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93',
        '--noactivate-mcdk-sha256', 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9']
    session = json.loads(run(launch, ROOT, env))
    print(json.dumps({key: session[key] for key in ('ready', 'game_pid', 'session_file')}), flush=True)
    env.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=OWNER,
        MCDEV_NATIVE_CAPTURE_HELPER=str(args.project / 'tools/capture_native_window.py'),
        MCDEV_NATIVE_CAPTURE_EXE=str(WGC))
    try:
        os.environ.update(env)
        sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
        from mcdk import Client, return_value
        with Client(timeout=30) as client:
            deadline = time.monotonic() + 60.
            while True:
                value = return_value(client.call('execute_code', {'code':
                    "import mod.client.extraClientApi as api\n"
                    "owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')\n"
                    "_result=owner is not None and owner.session is not None",
                    'is_client': True, 'direct_return': True}))
                if value is True or value == 'True':
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError('Business workspace did not initialize')
                time.sleep(.25)
        print(json.dumps({'workspace_initialized': True}), flush=True)
        if set(args.route) - {'editor'}:
            camera_command = [sys.executable, 'tools/verify_camera_projection.py', str(camera),
                              '--native-resolution', '--fixture-lift-y', '64']
            if args.native_world_geometry:
                camera_command += ['--native-api', '--native-capture-exe', str(WGC)]
            run(camera_command, args.project, env, camera.with_suffix('.log'))
            print(json.dumps({'camera_passed': json.loads(camera.read_bytes())['passed']}), flush=True)
        command = [sys.executable, 'tools/probe_product_water.py', '--session', session['session_file'],
            '--owner', OWNER, '--capture-exe', str(WGC), '--launch-inputs', str(args.launch_inputs),
            '--output', str(report), '--measure-budgets', '--world-fixture-lift-y', '64',
            '--world-view-scale', '.5', '--max-seconds', '600']
        if set(args.route) - {'editor'}:
            command += ['--camera-calibration', str(camera)]
        if args.pool_view_scale is not None:
            command += ['--pool-view-scale', str(args.pool_view_scale)]
        for route in args.route:
            command += ['--route', route]
        cases = args.case or (CORE if args.batch == 'core' else NEIGHBORS if args.batch == 'neighbors'
                             else CORE + NEIGHBORS if args.batch == 'all' else ())
        if args.gallery:
            cases = ('gallery',)
            command += ['--editor-zoom', '.9']
        for case in cases:
            command += ['--case', case]
        if args.animated or args.production_default:
            command += ['--controls', 'wet', '--extras']
            if args.animated:
                command += ['--flow-burst-exe', str(ROOT / '.runtime/native_wgc/burst-build-r14/Release/native_wgc_burst_capture.exe'),
                    '--flow-burst-sha256', '82361ce558efc40dbde5bb272cb309f6cd68fa7c79e9087a6d3089f49443c0f6']
            if args.production_default:
                command += ['--production-default']
        else:
            command += ['--frozen']
            if not args.gallery and not args.reverse and not args.extras:
                command += ['--visibility-controls', '--opaque-side-controls', '--alpha-controls']
                if args.native_world_geometry and set(args.route) - {'editor'}:
                    command += ['--native-side-projection']
        if args.extras:
            command += ['--extras']
        if args.reverse:
            command += ['--reverse-view']
        run(command, args.project, env, report.with_suffix('.log'))
        observed = json.loads(report.read_bytes())
        print(json.dumps({key: observed[key] for key in ('completed', 'restored', 'elapsed_seconds')}), flush=True)
    finally:
        if args.retain:
            print(json.dumps({'retained': True, 'game_pid': session['game_pid'],
                              'session_file': session['session_file']}), flush=True)
        else:
            stopped = subprocess.run([sys.executable, str(instances), 'stop', '--session', session['session_file'],
                '--owner', OWNER], cwd=ROOT, env=env, capture_output=True, text=True)
            print(json.dumps({'stop_returncode': stopped.returncode, 'stop_message': stopped.stderr.strip()}), flush=True)


if __name__ == '__main__':
    main()
