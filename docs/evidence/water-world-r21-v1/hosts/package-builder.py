"""Freeze world water diagnostics while preserving original failures and intervention."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime/water-r20-state-v7'
PACKAGE = ROOT / 'docs/evidence/water-world-r21-v1'
REPORTS = {
    'world-full-public19': 'world-full-public19.json',
    'falling-native': 'falling-native-skyward.json',
    'calibration': 'calibration.json',
}
FILES = {
    'world-full-public19-analysis.json': RUNTIME / 'world-full-public19-analysis.json',
    'world-full-public19-product-analysis.json': RUNTIME / 'world-full-public19-product-analysis.json',
    'world-full-public19-intervention.json': RUNTIME / 'world-full-public19-intervention.json',
    'capture-host-pause-initial.json': RUNTIME / 'capture-host-pause-1792079162.json',
    'native-calibration-fit.json': RUNTIME / 'native-calibration-fit.json',
    'falling-native-points.json': RUNTIME / 'falling-native-skyward-points.json',
    'falling-depth/report.json': RUNTIME / 'falling-depth-v1/report.json',
    'falling-stone-fit/report.json': RUNTIME / 'falling-stone-fit-v1/report.json',
    'falling-native-depth/report.json': RUNTIME / 'falling-native-depth-v1/report.json',
    'hosts/world-matrix.py': ROOT / '.runtime/water-r20-world-matrix.py',
    'hosts/world-parent.py': ROOT / '.runtime/water-r20-v2.py',
    'hosts/launch-parent.py': ROOT / '.runtime/water-r20.py',
    'hosts/native-calibration-fit.py': ROOT / '.runtime/water-r20-native-calibration-fit.py',
    'hosts/falling-depth.py': ROOT / '.runtime/water-r20-falling-depth.py',
    'hosts/falling-stone-fit.py': ROOT / '.runtime/water-r20-falling-stone-fit.py',
    'hosts/falling-native.py': ROOT / '.runtime/water-r20-falling-native.py',
    'hosts/falling-native-replay.py': ROOT / '.runtime/water-r20-falling-native-replay.py',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='ascii')


def captures(value):
    if isinstance(value, dict):
        if value.get('path', '').endswith('.png') and 'sha256' in value:
            yield value
        else:
            for row in value.values():
                yield from captures(row)
    elif isinstance(value, list):
        for row in value:
            yield from captures(row)


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
    assert not (output / 'manifest.json').exists()
    report_index = {}
    for name, relative in REPORTS.items():
        original = RUNTIME / relative
        report = load(original)
        copy(original, output / (name + '.json'))
        frames = list(captures(report['views'] if name == 'calibration' else report['captures']))
        for frame in frames:
            source = Path(frame['path'])
            assert sha(source) == frame['sha256']
            target = output / 'captures' / name / source.name
            copy(source, target)
            copy(source.with_suffix('.capture.json'), target.with_suffix('.capture.json'))
        report_index[name] = {'path': name + '.json', 'capture_count': len(frames)}
    for name, original in FILES.items():
        copy(original, output / name)
    for source_dir, destination in (('falling-depth-v1', 'falling-depth'),
                                  ('falling-stone-fit-v1', 'falling-stone-fit'),
                                  ('falling-native-depth-v1', 'falling-native-depth')):
        for path in sorted((RUNTIME / source_dir).glob('*.png')):
            copy(path, output / destination / path.name)
    copy(Path(__file__), output / 'hosts/package-builder.py')
    prior = ROOT / 'docs/evidence/water-ui-state-r20-v1'
    prior_manifest = load(prior / 'manifest.json')
    references = {'prior_manifest': {'path': '../water-ui-state-r20-v1/manifest.json',
                                     'sha256': sha(prior / 'manifest.json')},
        'launch_inputs': {'path': '../water-ui-state-r20-v1/launch-inputs.json',
                         'sha256': sha(prior / 'launch-inputs.json')},
        'source_archives_in_precedence_order': []}
    for archive in prior_manifest['source_archives_in_precedence_order']:
        resolved = (prior / archive['path']).resolve(strict=True)
        assert sha(resolved) == archive['sha256']
        relative = archive['path'] if archive['path'].startswith('../') else '../water-ui-state-r20-v1/' + archive['path']
        references['source_archives_in_precedence_order'].append({'path': relative, 'sha256': archive['sha256']})
    write(output / 'references.json', references)
    manifest = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
        'reports': report_index,
        'performance_without_intervention': False,
        'files': {path.relative_to(output).as_posix(): {'bytes': path.stat().st_size, 'sha256': sha(path)}
                  for path in sorted(output.rglob('*')) if path.is_file() and '__pycache__' not in path.parts}}
    write(output / 'manifest.json', manifest)
    print(json.dumps({'files': len(manifest['files']),
        'captures': sum(row['capture_count'] for row in report_index.values()),
        'bytes': sum(row['bytes'] for row in manifest['files'].values()), 'production_qualified': False}))


if __name__ == '__main__':
    main()
