"""Run and audit the six fungus heights absent from the R7 boundary evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from verify_snow_catalogue_visuals import ROOT, VISUAL_CASE
from verify_debug_blueprints import write_json
from _session import load_session


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path):
    return {'path': str(path.resolve()), 'sha256': digest(path)}


def freeze(output):
    if output.exists():
        raise ValueError('Frozen source output must be fresh')
    paths = sorted(path for directory in ('behavior_pack', 'resource_pack', 'tools/data')
                   for path in (ROOT/directory).rglob('*')
                   if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc')
    paths.extend(ROOT/'tools'/name for name in
                 ('verify_snow_catalogue_visuals.py', 'verify_fungus_remaining_matrix.py',
                  'verify_snow_plant_visibility.py', 'capture_native_window.py'))
    value = {'schema': 1, 'project': str(ROOT),
             'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
             'hashes_sha256': {path.relative_to(ROOT).as_posix(): digest(path) for path in paths}}
    write_json(output, value)
    return record(output)


def source_errors(frozen):
    return [name for name, expected in frozen['hashes_sha256'].items()
            if not (ROOT/name).is_file() or digest(ROOT/name) != expected]


def run(output, frozen_path, calibration_path):
    if output.exists():
        raise ValueError('Matrix output must be fresh')
    session = load_session(live=True)
    if Path(session['project']).resolve() != ROOT:
        raise ValueError('The owned session belongs to a different project')
    frozen = json.loads(frozen_path.read_bytes())
    if Path(frozen['project']).resolve() != ROOT or source_errors(frozen):
        raise ValueError('Frozen project source changed before capture')
    matrix = {'schema': 1, 'profile': 'fungus_remaining', 'completed': False,
              'restored': False, 'passed': False, 'rows': [],
              'session_file': session['session_file'], 'owner': session['owner'],
              'game_pid': session['game_pid'], 'frozen_source': record(frozen_path),
              'calibration': record(calibration_path), 'profile_case': VISUAL_CASE['fungus_remaining'],
              'limits': {'native_recall': .75, 'native_precision': .75,
                         'native_edge_tolerance_pixels': 3},
              'scope': 'R7 boundary rows plus this independent remaining-height matrix may cover all eight; other plants and positions remain pending'}
    write_json(output, matrix)
    for plant, heights in VISUAL_CASE['fungus_remaining']['heights'].items():
        for view in ('public', 'right'):
            changed = source_errors(frozen)
            if changed:
                matrix['source_errors'] = changed
                write_json(output, matrix)
                raise ValueError('Frozen source changed between matrix rows')
            report_path = output.with_name(output.stem+'_'+plant+'_'+view+'.json')
            if report_path.exists():
                raise ValueError('Matrix case output must be fresh')
            command = [sys.executable, '-X', 'utf8', str(ROOT/'tools/verify_snow_catalogue_visuals.py'),
                       str(report_path), '--camera-calibration', str(calibration_path),
                       '--plant', plant, '--view', view, '--fungus-remaining', '--native-resolution',
                       '--near-player', '--fixture-lift-y', '16', '--timeout', '90']
            for height in heights:
                command.extend(('--height', str(height)))
            completed = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, encoding='utf8')
            row = {'plant': plant, 'view': view, 'returncode': completed.returncode,
                   'stderr': completed.stderr, 'stdout_tail': completed.stdout[-4000:]}
            if report_path.is_file():
                row.update(record(report_path))
                report = json.loads(report_path.read_bytes())
                row.update({key: report.get(key, False) for key in ('completed', 'restored', 'passed')})
                row['cleanup_errors'] = report.get('cleanup_errors', [])
            matrix['rows'].append(row)
            write_json(output, matrix)
            print(json.dumps({key: row.get(key) for key in ('plant', 'view', 'returncode', 'completed', 'restored', 'passed')}), flush=True)
            if not row.get('completed') or not row.get('restored') or row['cleanup_errors']:
                break
        else:
            continue
        break
    matrix['source_errors'] = source_errors(frozen)
    matrix['source_assets_stable'] = not matrix['source_errors']
    matrix['completed'] = len(matrix['rows']) == 4 and all(row.get('completed') for row in matrix['rows'])
    matrix['restored'] = bool(matrix['rows']) and all(row.get('restored') for row in matrix['rows'])
    matrix['passed'] = matrix['completed'] and matrix['restored'] and matrix['source_assets_stable'] and all(row.get('passed') for row in matrix['rows'])
    write_json(output, matrix)
    return matrix


def captures(value):
    if isinstance(value, dict):
        if all(key in value for key in ('path', 'sha256', 'capture')):
            yield value
        for child in value.values():
            yield from captures(child)
    elif isinstance(value, list):
        for child in value:
            yield from captures(child)


def audit(matrix_path, output):
    from audit_static_plant_matrix import audit as audit_background_captures
    return audit_background_captures(matrix_path, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--frozen-source', type=Path)
    parser.add_argument('--camera-calibration', type=Path)
    parser.add_argument('--audit', type=Path)
    args = parser.parse_args()
    if args.freeze:
        result = freeze(args.output)
    elif args.audit:
        result = audit(args.audit, args.output)
    else:
        if args.frozen_source is None or args.camera_calibration is None:
            parser.error('Live matrix requires --frozen-source and --camera-calibration')
        result = run(args.output, args.frozen_source, args.camera_calibration)
    print(json.dumps(result, ensure_ascii=True), flush=True)
    return 0 if result.get('passed', result.get('integrity_passed', True)) else 1


if __name__ == '__main__':
    sys.exit(main())
