"""Run a frozen snow suite in one owner-bound background game."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import load_session
from probe_product_water import snapshot_digest, snapshot_sources


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--launch-inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--phase', choices=('ready', 'calibrate', 'matrix'), required=True)
    parser.add_argument('--camera-calibration', type=Path)
    parser.add_argument('--plant', action='append')
    parser.add_argument('--height', type=int, choices=range(8), action='append')
    args = parser.parse_args()
    session = load_session(args.session, args.owner, live=True)
    project = args.project.resolve(strict=True)
    assert Path(session['project']).resolve() == project
    args.output.mkdir(parents=True, exist_ok=False)
    launch = json.loads(args.launch_inputs.read_bytes())
    sources = snapshot_sources(project)
    assert sources == launch['files'], 'Cold project changed after launch'
    record = {'schema': 1, 'phase': args.phase, 'completed': False,
              'session': {key: session[key] for key in ('owner', 'session_file', 'game_pid',
                  'game_identity', 'mcdk_pid', 'mcdk_identity')},
              'project': str(project), 'source_contract_sha256': snapshot_digest(sources),
              'files': sources, 'agent_activation_allowed': False,
              'source_unchanged': False, 'production_qualification_changed': False}
    frozen = args.output / 'inputs'
    frozen.mkdir()
    shutil.copyfile(__file__, frozen / Path(__file__).name)
    shutil.copyfile(args.launch_inputs, frozen / 'launch-inputs.json')
    for folder in ('tools', '.agents/skills/pyreact-debugging/scripts'):
        destination = frozen / folder
        destination.mkdir(parents=True, exist_ok=True)
        for source in (project / folder).glob('*.py'):
            shutil.copyfile(source, destination / source.name)
    wgc = project / '.runtime/native_wgc/build/Release/native_wgc_capture.exe'
    env = dict(os.environ, MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=args.owner,
               MCDEV_MCP_URL=session['mcp_url'], MCDEV_GAME_PID=str(session['game_pid']),
               MCDEV_ALLOW_USER_FOREGROUND='1', MCDEV_NATIVE_CAPTURE_EXE=str(wgc),
               MCDEV_NATIVE_CAPTURE_HELPER=str(project / 'tools/capture_native_window.py'))
    if args.phase == 'ready':
        command = [sys.executable, '-X', 'utf8', str(project / 'tools/capture_native_window.py'),
                   '--output', str(args.output.resolve() / 'ready.png')]
    elif args.phase == 'calibrate':
        command = [sys.executable, '-X', 'utf8', str(project / 'tools/verify_camera_projection.py'),
                   str(args.output.resolve() / 'report.json'), '--native-resolution',
                   '--skyward-tilted', '--fixture-lift-y', '24', '--native-api',
                   '--native-capture-exe', str(wgc)]
    else:
        assert args.camera_calibration is not None
        command = [sys.executable, '-X', 'utf8', str(project / 'tools/verify_centered_snow_profiles.py'),
                   str(args.output.resolve() / 'report.json'), '--camera-calibration',
                   str(args.camera_calibration.resolve(strict=True))]
        for name in args.plant or ():
            command += ['--plant', name]
        for height in args.height or ():
            command += ['--height', str(height)]
    record['command'] = command
    write(args.output / 'receipt.json', record)
    started = time.monotonic()
    try:
        with (args.output / 'stdout.txt').open('w', encoding='utf8') as stdout, \
                (args.output / 'stderr.txt').open('w', encoding='utf8') as stderr:
            process = subprocess.run(command, cwd=project, env=env, stdout=stdout, stderr=stderr)
        record.update(returncode=process.returncode, completed=True)
    finally:
        record['elapsed_seconds'] = time.monotonic() - started
        record['source_unchanged'] = snapshot_sources(project) == sources
        record['input_file_sha256'] = {path.relative_to(frozen).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                                       for path in sorted(frozen.rglob('*')) if path.is_file()}
        write(args.output / 'receipt.json', record)
    print(json.dumps({key: record[key] for key in ('phase', 'completed', 'returncode', 'source_unchanged', 'elapsed_seconds')}))
    return process.returncode


if __name__ == '__main__':
    raise SystemExit(main())
