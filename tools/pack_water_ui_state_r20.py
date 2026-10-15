"""Freeze water UI state diagnostics without exporting launch credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'docs/evidence/water-ui-state-r20-v1'
REPORTS = {
    'root-positive': '.runtime/water-root-cross-r20-v1/report.json',
    'v6-cold': '.runtime/water-r20-prime-v6/cold-water/report.json',
    'v6-primed': '.runtime/water-r20-prime-v6/primed-water/report.json',
    'v6-primed16': '.runtime/water-r20-prime-v6/primed16-water/report.json',
    'v6-portal16': '.runtime/water-r20-prime-v6/portal-prime16/report.json',
    'v6-matched-pose': '.runtime/water-r20-prime-v6/matched-pose.json',
    'v6-entity': '.runtime/water-r20-prime-v6/same-doll-entity.json',
    'v7-splash-invalid': '.runtime/water-r20-state-v7/cold-water/report.json',
    'v7-ready': '.runtime/water-r20-state-v7/ready-water/report.json',
    'v7-parameters': '.runtime/water-r20-state-v7/call-parameters.json',
    'v7-editor-pool': '.runtime/water-r20-state-v7/editor-pool.json',
}
FILES = {
    'launch-inputs.json': '.runtime/water-r20-state-v7/launch-inputs.json',
    'resource-delta.zip': '.runtime/water-r20-prime-v6/resource-delta.zip',
    'resource-plan.json': '.runtime/water-r20-prime-v6/plan.json',
    'launch-plan.json': '.runtime/water-r20-state-v7/plan.json',
    'launch-mcdev.json': '.runtime/water-r20-state-v7/launch-mcdev.json',
    'previous-mcdev.json': '.runtime/water-r20-state-v7/previous-mcdev.json',
    'v7-editor-pool-analysis.json': '.runtime/water-r20-state-v7/editor-pool-analysis.json',
    'timing-granular-v2.json': '.runtime/water-r20-state-v7/granular-timing-v2.json',
    'timing-thread-unsupported-v3.json': '.runtime/water-r20-state-v7/granular-timing-thread-v3.json',
    'timing-world-v1.json': '.runtime/water-r20-state-v7/granular-world-v1.json',
    'timing-world-detail-v2.json': '.runtime/water-r20-state-v7/granular-world-detail-v2.json',
    'v2-core-timing-and-state.json': '.runtime/water-r20-final-v2/frozen-core.json',
    'v2-core-analysis.json': '.runtime/water-r20-final-v2/frozen-core-analysis.json',
    'hosts/cross-session.py': '.runtime/water-r20-cross-session.py',
    'hosts/matched-pose.py': '.runtime/water-r20-pose-control.py',
    'hosts/entity-control.py': '.runtime/water-r20-entity-control.py',
    'hosts/native-parameters.py': '.runtime/water-r20-state-v7.py',
    'hosts/granular-current-v3.py': '.runtime/water-r20-granular.py',
    'hosts/world-granular-v2.py': '.runtime/water-r20-world-granular.py',
    'hosts/resource-freeze.py': '.runtime/water-r20-prime-freeze.py',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def captures(value):
    if isinstance(value, dict):
        if value.get('path', '').endswith('.png') and 'sha256' in value:
            yield value
        else:
            for row in value.values():
                for capture in captures(row):
                    yield capture
    elif isinstance(value, list):
        for row in value:
            for capture in captures(row):
                yield capture


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert sha(source) == sha(target), 'Refusing to replace frozen bytes: ' + str(target)
    else:
        shutil.copy2(source, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=PACKAGE)
    args = parser.parse_args()
    output = args.output.resolve()
    assert (output / 'README.md').is_file() and (output / 'verify_package.py').is_file()
    report_index = {}
    for name, original in REPORTS.items():
        path = ROOT / original
        report = json.loads(path.read_bytes())
        copy(path, output / (name + '.json'))
        frame_rows = list(captures(report['captures']))
        for frame in frame_rows:
            source = Path(frame['path'])
            assert sha(source) == frame['sha256']
            destination = output / 'captures' / name / source.name
            copy(source, destination)
            copy(source.with_suffix('.capture.json'), destination.with_suffix('.capture.json'))
        report_index[name] = {'path': name + '.json', 'capture_count': len(frame_rows)}
    for name, original in FILES.items():
        copy(ROOT / original, output / name)
    source_package = ROOT / 'docs/evidence/water-native-side-r20-v1'
    prior = json.loads((source_package / 'manifest.json').read_bytes())
    archives = [
        {'path': '../water-final-r19-world-v1/launch-inputs.zip',
         'sha256': prior['base_source_archive']['sha256']},
        {'path': '../water-native-side-r20-v1/launch-input-delta.zip',
         'sha256': sha(source_package / 'launch-input-delta.zip')},
        {'path': 'resource-delta.zip', 'sha256': sha(output / 'resource-delta.zip')},
    ]
    manifest = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
        'source_archives_in_precedence_order': archives, 'reports': report_index,
        'invalid_target_scene_reports': ['v7-splash-invalid'],
        'v2_core_capture_bytes_included': False,
        'unsupported_cpu_fields': 'timing-thread-unsupported-v3.json: thread_cpu_supported=false',
        'files': {path.relative_to(output).as_posix(): {'bytes': path.stat().st_size,
            'sha256': sha(path)} for path in sorted(output.rglob('*'))
            if path.is_file() and path.name != 'manifest.json' and '__pycache__' not in path.parts}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='ascii')
    print(json.dumps({'package': str(output), 'files': len(manifest['files']),
        'captures': sum(row['capture_count'] for row in report_index.values()),
        'bytes': sum(row['bytes'] for row in manifest['files'].values()),
        'production_qualified': False}))


if __name__ == '__main__':
    main()
