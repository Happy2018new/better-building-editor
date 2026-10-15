"""Preserve and replay the final ordinary sword glint measurements offline."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREPARED = ROOT / '.runtime/glint-dense-r21-prepare-v1'
CAPTURE = ROOT / '.runtime/item-glint-final-r21-sword-v1'
SPARSE = ROOT / '.runtime/item-glint-final-r21-sword-v1-sparse'
DIRECTION = ROOT / '.runtime/item-glint-final-r21-sword-v1-direction'
ROUTES = ('native', 'world', 'world_missing', 'editor')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write_new(path, value):
    with path.open('x', encoding='ascii') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')


def frozen_plan():
    namespace = runpy.run_path(str(PREPARED / 'prepare.py'))
    return namespace['check_plan']()


def source_files():
    files = [path for directory in (CAPTURE, SPARSE, DIRECTION)
             for path in directory.rglob('*') if path.is_file()]
    files += [PREPARED / name for name in (
        'plan.json', 'plan-receipt.json', 'dependency-amendment.json',
        'capture-attempt.json', 'capture-budget.json', 'capture-outcome.json',
        'prepare.py', 'capture.py', 'offline_checks.py', 'install_dependencies.py')]
    return sorted(set(files))


def prepare():
    assert not (HERE / 'manifest.json').exists(), 'Never replace a result package'
    plan = frozen_plan()
    report = read(CAPTURE / 'report.json')
    sparse = read(SPARSE / 'analysis.json')
    direction = read(DIRECTION / 'analysis.json')
    outcome = read(PREPARED / 'capture-outcome.json')
    budget = read(PREPARED / 'capture-budget.json')['samples']
    assert outcome['returncode'] == 0 and outcome['completed']
    assert outcome['environment_restored'] and outcome['source_unchanged']
    assert not outcome['cleanup_errors']
    assert sha(CAPTURE / 'report.json') == direction['source_sha256'] == sparse['source_sha256']
    assert sparse['evidence_valid'] and sparse['all_bodies_passed']
    assert sparse['native_closeup']['reference_valid'] and not sparse['capture_failures']
    assert direction['direction_and_speed_accepted'] and direction['brightness_accepted']
    assert all(direction['negative_controls'].values())
    files = source_files()
    originals = {path.relative_to(ROOT).as_posix(): sha(path) for path in files}
    copies = {
        'direction-analysis.json': DIRECTION / 'analysis.json',
        'sparse-analysis.json': SPARSE / 'analysis.json',
        'capture-outcome.json': PREPARED / 'capture-outcome.json',
        'capture-attempt.json': PREPARED / 'capture-attempt.json',
        'capture-budget.json': PREPARED / 'capture-budget.json',
        'plan.json': PREPARED / 'plan.json',
        'dependency-amendment.json': PREPARED / 'dependency-amendment.json',
    }
    timeline = {}
    route_summary = {}
    image_rows = report['closeup']['captures'] + report['closeup']['native_reference']['captures']
    for route in ROUTES:
        record = report['closeup']['motion_bursts'][route]
        receipt = read(record['receipt'])
        assert sha(record['receipt']) == record['sha256']
        rows = []
        for frame in receipt['frames']:
            raw = read(frame['receipt']['path'])
            assert sha(frame['receipt']['path']) == frame['receipt']['sha256']
            rows.append({'frame_record': frame, 'raw_receipt': raw})
        timeline[route] = {'capture_receipt': receipt, 'frames': rows}
        route_summary[route] = {
            'sparse_frames': sum(row['label'].startswith(route + '_') and
                row['label'][len(route) + 1:].isdigit() for row in image_rows),
            'timeline': record['timeline'],
            'maximum_gap_ms': record['timeline']['maximum_gap_100ns'] / 10000.,
            'duration_seconds': direction['routes'][route]['duration_seconds'],
            'fit': direction['routes'][route],
            'comparison': direction['comparison'].get(route),
            'brightness': direction['brightness_comparison'].get(route),
        }
        copies['images/' + route + '_0.png'] = Path(next(
            row['capture']['path'] for row in image_rows if row['label'] == route + '_0'))
        copies['samples/' + route + '-samples.npz'] = DIRECTION / (route + '-samples.npz')
        copies['samples/' + route + '-pixel-sources.json'] = DIRECTION / (route + '-pixel-sources.json')
        copies['images/' + route + '-first-dense-crop.png'] = DIRECTION / (route + '-frames/0001.png')
    for name, source in copies.items():
        target = HERE / name
        assert not target.exists(), 'Do not overwrite retained evidence: ' + name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert sha(target) == sha(source)
    summary = {
        'schema': 1, 'scope': 'Measured ordinary diamond-sword icon glint only',
        'candidate_commit': plan['candidate_commit'], 'item_frame_glint_color_multiplier': .75,
        'candidate_shader_sha256': plan['candidate_shader_sha256'],
        'source_sha256': plan['source_sha256'], 'capture_report_sha256': sha(CAPTURE / 'report.json'),
        'direction_and_speed_accepted': direction['direction_and_speed_accepted'],
        'brightness_measurement_accepted_with_base_controls': bool(direction['brightness_accepted']
            and sparse['evidence_valid'] and sparse['all_bodies_passed']
            and sparse['native_closeup']['reference_valid'] and all(direction['negative_controls'].values())),
        'negative_controls': direction['negative_controls'], 'limits': direction['limits'],
        'routes': route_summary, 'capture_outcome': outcome,
        'budget': {'samples': len(budget), 'all_passed': all(row['commit_passed'] and row['handles_passed'] for row in budget),
            'minimum_available_commit_bytes': min(row['commit']['commit_available_bytes'] for row in budget),
            'maximum_handles': max(row['process']['handles'] for row in budget),
            'scope': 'Sparse/dense capture boundaries only, not continuous inside a burst'},
        'all_original_sparse_flags': {key: sparse.get(key) for key in (
            'evidence_valid', 'all_bodies_passed', 'all_native_bodies_passed',
            'all_native_edges_passed', 'static_pose_accepted', 'matrix_completed', 'capture_failures')},
        'not_qualified': ['Full item/aux/pose coverage', 'Special block-item glint',
            'Static pose acceptance (closeup-only has no case matrix)', 'Full product qualification'],
        'production_qualified': False,
        'analysis_policy': plan['analysis_policy'],
        'brightness_scope': 'Dynamic red/green additive amplitude; static body and saturated blue are excluded',
    }
    write_new(HERE / 'raw-timelines.json', timeline)
    write_new(HERE / 'summary.json', summary)
    retained = {path.relative_to(HERE).as_posix(): sha(path)
                for path in HERE.rglob('*') if path.is_file()}
    write_new(HERE / 'manifest.json', {'schema': 1, 'root': str(ROOT),
        'original_inputs': originals, 'retained_package_files': retained,
        'runtime_data_retained_locally': True, 'production_qualified': False})
    print(json.dumps({'prepared': True, 'original_files': len(originals),
        'retained_files': len(retained), 'game_calls': 0, 'manifest_sha256': sha(HERE / 'manifest.json')}))


def check():
    manifest = read(HERE / 'manifest.json')
    for name, expected in manifest['retained_package_files'].items():
        assert sha(HERE / name) == expected, 'Retained package changed: ' + name
    assert {path.relative_to(ROOT).as_posix() for path in source_files()} == set(manifest['original_inputs'])
    for name, expected in manifest['original_inputs'].items():
        assert sha(ROOT / name) == expected, 'Original evidence changed: ' + name
    plan = frozen_plan()
    print(json.dumps({'checked': True, 'game_calls': 0,
        'original_files': len(manifest['original_inputs']), 'source_sha256': plan['source_sha256']}))
    return plan


def analyze(output):
    plan = check()
    output = output.resolve()
    assert not output.exists(), 'Use a fresh analysis directory'
    output.mkdir(parents=True)
    values = dict(plan, sparse_output=str(output / 'sparse'), direction_output=str(output / 'direction'))
    environment = dict(os.environ, OPENBLAS_NUM_THREADS='1')
    for template in plan['analysis_argv']:
        subprocess.run([part.format(**values) for part in template], env=environment, check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check', 'analyze'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'check':
        check()
    else:
        assert args.output is not None, 'Analysis replay requires --output'
        analyze(args.output)
