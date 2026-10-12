"""Bind frozen diagnostic rail rows to an owned build and replay current edits."""
import argparse
import hashlib
import json
from pathlib import Path

from verify_neighbor_actions_native import ROOT, START, STATUS, RESTORE, compare_local, plans
from verify_debug_blueprints import write_json

BUILD_SHA256 = '67880328996b2895fa7e80712de3dc90d5b6ced26ac10ce67fb49d2e1a51f31f'
RECORDS = (
    ('native_neighbor_actions_r11_nemc_3.9.0.401155.json', plans()),
    ('native_neighbor_actions_r11_axes_nemc_3.9.0.401155.json',
     plans(('rail',), ('rotate_y90', 'mirror_x'),
           ('rail_corner', 'golden_rail_corner', 'rail_slope', 'golden_rail_slope'))))


def record(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def pack():
    rows, session = [], None
    for filename, selected in RECORDS:
        path = ROOT / 'tools/data' / filename
        report = json.loads(path.read_bytes())
        owned = json.loads(Path(report['session_file']).read_bytes())
        if (owned['owner'] != report['owner'] or Path(owned['project']).resolve() != ROOT
                or not owned['noactivation']['background_safe'] or not owned['noactivation']['window_noactivate']):
            raise ValueError('Frozen action evidence does not bind to the guarded owned project')
        if session is not None and owned['id'] != session['id']:
            raise ValueError('Frozen action reports came from different owned sessions')
        session = owned
        replay = compare_local(report, selected)
        if not replay['all_matched']:
            raise ValueError('Current local edits differ from frozen native action states')
        rows.append({'evidence': record(path), 'rows': len(replay['rows']),
                     'original_differing_rows': sum(not row['matched'] for row in report['comparison']['rows']),
                     'current_replay': replay,
                     'public_native_payload_sha256': hashlib.sha256((START % selected).encode('utf8')).hexdigest()})
    executable = record(session['game_executable'])
    if executable['sha256'] != BUILD_SHA256 or Path(session['game_executable']).parent.name != '3.9.0.401155':
        raise ValueError('Owned native build bytes differ from the observed NEMC executable')
    guard = session['noactivation']
    return {'schema': 1, 'scope': 'Diagnostic native state replay; no image or survival acceptance.',
            'acceptance': {'editor': 'pending', 'full': 'pending', 'missing': 'pending'},
            'provenance_scope': 'Retrospective owned launch/build and reproducible payload binding; original reports unchanged.',
            'session': {'id': session['id'], 'owner': session['owner'],
                        'game_pid': session['game_pid'], 'game_identity': session['game_identity'],
                        'game_executable': executable,
                        'noactivation': dict((key, guard[key]) for key in
                                             ('dll', 'mcdk', 'background_safe', 'window_noactivate'))},
            'source': record(ROOT / 'behavior_pack/modern_projection/projection/debug_action_blueprints.py'),
            'status_payload_sha256': hashlib.sha256(STATUS.encode('utf8')).hexdigest(),
            'restore_payload_sha256': hashlib.sha256(RESTORE.encode('utf8')).hexdigest(),
            'reports': rows, 'native_rows': sum(row['rows'] for row in rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Existing evidence must not be overwritten')
    report = pack()
    write_json(args.output, report)
    print(json.dumps({'native_rows': report['native_rows'], 'current_replay_all_matched': True}))


if __name__ == '__main__':
    main()
