"""Root-scheduled, single-use full shelf/support render palette observation."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CONTROL = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'.agents/skills/pyreact-debugging/scripts')]
os.environ['OPENBLAS_NUM_THREADS'] = '1'
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from prepare_shelf_render_palette_r21 import OWNER, verify
from _session import load_session, process_identity
import instances


def launcher():
    spec = importlib.util.spec_from_file_location('shelf_context_start', ROOT/'.runtime/start_shelf_baked_r21.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PROJECT = Path(json.loads((CONTROL/'frozen.json').read_bytes())['project'])
    module.OUTPUT, module.OWNER = CONTROL/'launch', OWNER
    return module


def started():
    return json.loads((CONTROL/'launch/start-summary.json').read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'start', 'capture', 'stop', 'finalize'))
    parser.add_argument('--scheduled-by-root', action='store_true')
    args = parser.parse_args()
    if args.action in ('stop', 'finalize'):
        ready = started()
        session = load_session(ready['session_file'], OWNER, live=False)
        if args.action == 'finalize':
            exact = json.loads((CONTROL/'launch/exact-exit.json').read_bytes())
            if not exact.get('completed') or any(process_identity(session[key+'_pid']) == session[key+'_identity']
                                                 for key in ('game', 'mcdk')):
                raise RuntimeError('Finalize requires both exact observed identities to have exited')
        result = instances.stop(session, force=False)
        print(json.dumps({'state': result['state'], 'force': False}))
        return
    frozen = verify(CONTROL/'frozen.json')
    if args.action == 'preflight':
        sample, games = commit_at_boundary(), launcher().live_games()
        print(json.dumps({'frozen': True, 'files': len(frozen['files']), 'files_sha256': frozen['files_sha256'],
            'commit': sample, 'live_games': games,
            'launch_admissible': not games and sample['commit_available_bytes'] >= 6*1024**3}))
        return
    if args.action == 'start':
        if not args.scheduled_by_root:
            parser.error('A root runtime grant is required')
        start = launcher()
        if start.live_games():
            raise RuntimeError('Exclusive scheduling requires zero live games')
        sys.argv = [sys.argv[0], '--launch']
        start.main()
        ready = started()
        if ready['state'] != 'ready':
            raise RuntimeError('The private game did not become ready')
        from watch_intrinsic_glint_exit_r21 import watch
        watch(Path(ready['session_file']), OWNER, CONTROL/'launch/exact-exit.json')
        return
    ready = started()
    load_session(ready['session_file'], OWNER, live=True)
    subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT/'tools/probe_shelf_render_palette_r21.py'),
        '--freeze', str(CONTROL/'frozen.json'), '--session', ready['session_file'], '--owner', OWNER,
        '--output', str(CONTROL/'captures/south-full-palette')], cwd=ROOT, check=True)
    verify(CONTROL/'frozen.json')


if __name__ == '__main__':
    main()
