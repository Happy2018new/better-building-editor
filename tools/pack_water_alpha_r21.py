"""Freeze the single-launch water alpha batch for independent offline replay."""
import argparse
import ast
from importlib.metadata import version
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime/water-r21-alpha-v1'
CLONE = ROOT / '.runtime/projects/water-r20'
REPORTS = (
    'after-launch.json', 'calibration.json', 'calibration-execution.json',
    'calibration-preflight-1.json', 'calibration-restored.json', 'exit-observer.json',
    'full-alpha4.json', 'full-alpha4-execution.json', 'full-alpha4-native-analysis.json',
    'full-alpha4-original-analysis.json', 'full-alpha4-preflight-1.json',
    'full-alpha4-restored.json', 'full-alpha4-review.json', 'launch-attempt.json',
    'launch-execution.json', 'launch-inputs.json', 'launch-mcdev.json',
    'plan.json', 'plan-receipt.json', 'start.json',
    'stop-attempt-1-execution.json', 'stop-attempt-2-execution.json', 'exit-Report.wer',
)
HOSTS = {
    '.runtime/water-r21-alpha-host.py': 'hosts/water-r21-alpha-host.py',
    '.runtime/water-r21-alpha-launch.py': 'hosts/water-r21-alpha-launch.py',
    '.agents/skills/pyreact-debugging/scripts/instances.py': 'hosts/instances.py',
    '.agents/skills/pyreact-debugging/scripts/_session.py': 'hosts/_session.py',
    'tools/census_intrinsic_glint_ui_r21.py': 'hosts/census_intrinsic_glint_ui_r21.py',
    'tools/analyze_product_water.py': 'replay/tools/analyze_product_water.py',
    'tools/analyze_liquid_workspace.py': 'replay/tools/analyze_liquid_workspace.py',
    'tools/water_native_projection.py': 'replay/tools/water_native_projection.py',
}
DEPENDENCIES = (
    'tools/analyze_liquid_transparency.py', 'tools/camera_projection.py',
    'tools/water_capture_contract.py',
    'behavior_pack/modern_projection/projection/__init__.py',
    'behavior_pack/modern_projection/projection/camera.py',
    'behavior_pack/modern_projection/projection/cell.py',
    'behavior_pack/modern_projection/projection/block_registry.py',
    'behavior_pack/modern_projection/projection/block_registry_data.py',
)
ENTRYPOINTS = ('tools/probe_product_water.py', 'tools/verify_camera_projection.py',
               'tools/verify_missing_neighbor_visuals.py')
PURE_HELPERS = {
    'verify_missing_neighbor_visuals': ('hull', 'maximum', 'signal'),
    'verify_camera_projection': ('stone_signal', 'fill_enclosed_holes', 'largest_component'),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    with path.open('x', encoding='ascii') as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + '\n')


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists(), 'Refusing to replace frozen bytes: ' + str(target)
    shutil.copy2(source, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/evidence/water-alpha-r21-v1')
    output = parser.parse_args().output.resolve()
    assert (output / 'README.md').is_file() and (output / 'verify_package.py').is_file()
    assert not (output / 'manifest.json').exists()
    source, calibration = read(RUNTIME / 'full-alpha4.json'), read(RUNTIME / 'calibration.json')
    assert all(source[key] is True for key in ('completed', 'restored', 'source_unchanged'))
    assert source['cleanup_errors'] == [] and source['routes'] == ['full']
    assert len(source['captures']) == 56 and len(source['rows']) == 24
    assert calibration['completed'] and calibration['passed'] and calibration['restored']
    assert read(RUNTIME / 'full-alpha4-review.json')['evidence_valid'] is True
    for name in REPORTS:
        copy(RUNTIME / name, output / name)
    for group, frames in (
            ('full', source['captures'].values()),
            ('calibration', [view[state] for view in calibration['views'] for state in ('shown', 'hidden')])):
        for frame in frames:
            original = Path(frame['path'])
            assert sha(original) == frame['sha256']
            target = output / 'captures' / group / original.name
            copy(original, target)
            copy(original.with_suffix('.capture.json'), target.with_suffix('.capture.json'))
    plan = read(RUNTIME / 'plan.json')
    for original, target in HOSTS.items():
        assert sha(ROOT / original) == plan['host_files_sha256'][original], original
        copy(ROOT / original, output / target)
    sources = read(RUNTIME / 'launch-inputs.json')['source_sha256']
    launch_bound = {}
    for original in DEPENDENCIES:
        assert sha(ROOT / original) == sources[original], original
        target = 'replay/' + original
        copy(ROOT / original, output / target)
        launch_bound[target] = original
    for original in ENTRYPOINTS:
        assert sha(CLONE / original) == sources[original], original
        target = 'acquisition/' + original
        copy(CLONE / original, output / target)
        launch_bound[target] = original
    pure_helpers = {}
    for name, functions in PURE_HELPERS.items():
        original = 'tools/' + name + '.py'
        target = 'replay/helpers/' + name + '.py'
        definitions = []
        for base in (ROOT, CLONE):
            tree = ast.parse((base / original).read_bytes())
            definitions.append({node.name: ast.dump(node) for node in tree.body
                                if isinstance(node, ast.FunctionDef) and node.name in functions})
        assert set(definitions[0]) == set(functions) and definitions[0] == definitions[1]
        copy(ROOT / original, output / target)
        pure_helpers[name] = {'path': target, 'launch_path': 'acquisition/' + original,
                              'functions': functions}
    copy(ROOT / 'tools/watch_intrinsic_glint_exit_r21.py', output / 'hosts/watch_intrinsic_glint_exit_r21.py')
    copy(Path(__file__), output / 'hosts/package-builder.py')
    write(output / 'code-bindings.json', {'frozen_host_files': HOSTS,
        'launch_bound_files': launch_bound, 'pure_helper_files': pure_helpers})
    packages = {name: version(name) for name in ('numpy', 'Pillow', 'scipy')}
    write(output / 'replay-environment.json', {'python': sys.version, 'packages': packages})
    with (output / 'requirements.txt').open('x', encoding='ascii') as handle:
        handle.write(''.join('%s==%s\n' % pair for pair in packages.items()))
    manifest = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
        'standalone_offline_replay': True, 'capture_host_suspensions': [], 'game_suspensions': [],
        'window_actions': [], 'routes': source['routes'], 'cases': source['cases'],
        'captures': {'full': 56, 'calibration': 6},
        'source_receipts_files': len(sources), 'complete_launch_source_archive_included': False,
        'files': {path.relative_to(output).as_posix(): {'bytes': path.stat().st_size, 'sha256': sha(path)}
                  for path in sorted(output.rglob('*')) if path.is_file() and '__pycache__' not in path.parts}}
    write(output / 'manifest.json', manifest)
    print(json.dumps({'files': len(manifest['files']), 'captures': manifest['captures'],
        'bytes': sum(row['bytes'] for row in manifest['files'].values()), 'production_qualified': False}))


if __name__ == '__main__':
    main()
