"""Freeze the completed missing-world water batch and its offline analyses."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime/water-r20-state-v7'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists(), 'Refusing to replace frozen bytes: ' + str(target)
    shutil.copy2(source, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/evidence/water-missing-world-r21-v1')
    args = parser.parse_args()
    output = args.output.resolve()
    assert (output / 'README.md').is_file() and (output / 'verify_package.py').is_file()
    assert not (output / 'manifest.json').exists()
    source = read(RUNTIME / 'world-missing-public19.json')
    assert all(source[key] is True for key in ('completed', 'restored', 'source_unchanged'))
    assert source['cleanup_errors'] == [] and source['routes'] == ['missing']
    for name in ('world-missing-public19.json', 'world-missing-public19-execution.json',
                 'world-missing-public19-analysis.json', 'world-missing-public19-product-analysis.json',
                 'world-missing-public19-native-product-analysis.json', 'stop-execution.json',
                 'stop-attempt1-execution.json', 'exit-observation.json', 'exit-wer/Report.wer'):
        copy(RUNTIME / name, output / name)
    for frame in source['captures'].values():
        path = Path(frame['path'])
        assert sha(path) == frame['sha256']
        copy(path, output / 'captures' / path.name)
        copy(path.with_suffix('.capture.json'), output / 'captures' / path.with_suffix('.capture.json').name)
    for name in ('analyze_product_water.py', 'water_native_projection.py',
                 'analyze_water_acceptance_r16.py', 'analyze_liquid_workspace.py'):
        copy(ROOT / 'tools' / name, output / 'analyzer' / name)
    for name, source_path in {
        'world-matrix.py': ROOT / '.runtime/water-r20-world-matrix.py',
        'world-parent.py': ROOT / '.runtime/water-r20-v2.py',
        'offline-replay.py': ROOT / '.runtime/water-r21-missing-replay.py',
        'package-builder.py': Path(__file__),
    }.items():
        copy(source_path, output / 'hosts' / name)
    references = {}
    for name, relative in {
        'world_manifest': '../water-world-r21-v1/manifest.json',
        'world_references': '../water-world-r21-v1/references.json',
        'calibration': '../water-world-r21-v1/calibration.json',
        'launch_inputs': '../water-ui-state-r20-v1/launch-inputs.json',
    }.items():
        references[name] = {'path': relative, 'sha256': sha(output / relative)}
    (output / 'references.json').write_text(json.dumps(references, indent=2, sort_keys=True) + '\n', encoding='ascii')
    manifest = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
        'capture_host_suspensions': [], 'game_suspensions': [], 'window_actions': [],
        'routes': source['routes'], 'cases': source['cases'], 'captures': len(source['captures']),
        'files': {path.relative_to(output).as_posix(): {'bytes': path.stat().st_size, 'sha256': sha(path)}
                  for path in sorted(output.rglob('*')) if path.is_file() and '__pycache__' not in path.parts}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='ascii')
    print(json.dumps({'files': len(manifest['files']), 'captures': manifest['captures'],
        'bytes': sum(row['bytes'] for row in manifest['files'].values()), 'production_qualified': False}))


if __name__ == '__main__':
    main()
