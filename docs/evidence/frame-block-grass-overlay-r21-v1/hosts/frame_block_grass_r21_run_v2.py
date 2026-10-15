"""Apply a separate host-environment and effective-process census amendment."""
import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / '.runtime/frame-block-grass-overlay-r21-control-v1'
AMENDMENT = CONTROL / 'runtime-amendment-v2.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_launcher():
    amendment = json.loads(AMENDMENT.read_bytes())
    assert amendment['original_plan_sha256'] == sha(CONTROL / 'plan.json')
    assert amendment['environment_override'] == {'OPENBLAS_NUM_THREADS': '1'}
    assert os.environ['OPENBLAS_NUM_THREADS'] == '1'
    for relative, expected in amendment['files'].items():
        assert sha(ROOT / relative) == expected, relative
    spec = importlib.util.spec_from_file_location('grass_r21_original_launcher',
        ROOT / '.runtime/frame_block_grass_r21_run.py')
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    frozen = launcher.plan()
    assert frozen['phase_policy']['minimum_start_commit_gib'] == 9
    assert frozen['phase_policy']['runtime_commit_reserve_gib'] == 6
    assert frozen['source_sha256'] == amendment['source_sha256']
    assert frozen['capture_host_sha256'] == amendment['unchanged_capture_host_sha256']
    return launcher, amendment


def effective_games(rows, identity):
    raw, effective, exited_shells = [], [], []
    for source in rows:
        row = dict(source)
        row['process_identity'] = identity(row['ProcessId'])
        row['effective_live_engine'] = (row.get('HandleCount') != 0
            or row.get('ThreadCount') != 0 or row['process_identity'] is not None)
        raw.append(row)
        (effective if row['effective_live_engine'] else exited_shells).append(row)
    return raw, effective, exited_shells


def preflight(launcher, amendment):
    frozen = launcher.plan()
    command = ("@(Get-CimInstance Win32_Process -Filter \"Name='Minecraft.Windows.exe'\" | "
        "Select-Object ProcessId,CreationDate,ThreadCount,HandleCount)|ConvertTo-Json -Compress")
    census = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
        check=True, capture_output=True, encoding='utf-8-sig', timeout=15,
        creationflags=subprocess.CREATE_NO_WINDOW)
    rows = json.loads(census.stdout.strip() or '[]')
    rows = rows if isinstance(rows, list) else [rows]
    raw, games, shells = effective_games(rows, launcher.process_identity)
    own = []
    for path in launcher.registry_dir().glob('*/session.json'):
        session = json.loads(path.read_bytes())
        if (session.get('owner') == launcher.OWNER and session.get('game_pid') and session.get('game_identity')
                and launcher.process_identity(session['game_pid']) == session.get('game_identity')):
            own.append(session['id'])
    commit = launcher.commit_at_boundary()
    return {'schema': 2, 'read_only': True, 'owner': launcher.OWNER,
        'source_sha256': frozen['source_sha256'], 'runtime_amendment_sha256': sha(AMENDMENT),
        'external_observer_validated': True, 'environment_override': amendment['environment_override'],
        'raw_game_rows': raw, 'raw_game_count': len(raw), 'games': games,
        'effective_game_count': len(games), 'excluded_exited_cim_shells': shells,
        'same_owner_live': own, 'commit': commit,
        'minimum_start_commit_gib': 9., 'runtime_commit_reserve_gib': 6.,
        'passed': not own and len(games) < 2 and commit['commit_available_bytes'] >= 9 * 1024 ** 3}


def invocation(launcher, action, phase):
    name = ('launch' if action == 'start' else phase) + '-runtime-amendment-v2.json'
    launcher.save(name, {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'action': action, 'phase': phase, 'scheduled_by_root': True,
        'runtime_amendment_sha256': sha(AMENDMENT), 'launcher_wrapper_sha256': sha(Path(__file__)),
        'environment_override': {'OPENBLAS_NUM_THREADS': os.environ['OPENBLAS_NUM_THREADS']},
        'child_inheritance': 'Original launcher start, exact observer and capture host inherit this process environment',
        'frozen_host_or_dependency_mutated': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('check', 'preflight', 'start', 'capture', 'review'))
    parser.add_argument('--phase', choices=('front', 'left75', 'right75'))
    parser.add_argument('--scheduled-by-root', action='store_true')
    parser.add_argument('--front-review', type=Path)
    parser.add_argument('--first-image-reviewed-by-root', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    launcher, amendment = load_launcher()
    launcher.preflight = lambda: preflight(launcher, amendment)
    if args.action == 'check':
        print(json.dumps({'read_only': True, 'started': False,
            'source_sha256': amendment['source_sha256'], 'runtime_amendment_sha256': sha(AMENDMENT),
            'environment_override': amendment['environment_override'], 'frozen_inputs_unchanged': True,
            'production_qualified': False, 'appearance_accepted': False}))
    elif args.action == 'preflight':
        print(json.dumps(preflight(launcher, amendment)))
    elif args.action == 'review':
        if args.phase is None or args.output is None:
            parser.error('review requires --phase and a fresh --output')
        return subprocess.call([sys.executable, '-B', '-X', 'utf8',
            str(ROOT / '.runtime/frame_block_grass_r21_review.py'), '--phase', args.phase,
            '--output', str(args.output)], env=dict(os.environ), creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        assert args.scheduled_by_root, 'Root must explicitly schedule this runtime window'
        if args.action == 'capture' and args.phase is None:
            parser.error('capture requires --phase')
        invocation(launcher, args.action, args.phase)
        if args.action == 'start':
            print(json.dumps(launcher.start(True)))
        else:
            return launcher.capture(args.phase, True, args.front_review, args.first_image_reviewed_by_root)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
