"""Preserve the original minimal v6 snow lifecycle and its pure pixel inputs."""
import ast
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / '.runtime/snow-lifecycle-r20-blue-orchid-v6'
CONTROL = ROOT / '.runtime/snow-r20-v6-control'
HOST = CONTROL / 'external-host'
PROJECT = ROOT / '.runtime/projects/snow-r20-v4'
DEST = ROOT / 'docs/evidence/snow-lifecycle-r20-v6-subset-v1'


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    mapping, bindings = {}, {}

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def copy(source, relative, binding=None):
        source = source.resolve(strict=True)
        target = DEST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != source.read_bytes():
            raise ValueError('Refusing to replace package bytes: ' + str(relative))
        shutil.copyfile(source, target)
        mapping[str(source)] = target.relative_to(DEST).as_posix()
        if binding:
            bindings[relative.as_posix()] = {'source': str(source), 'sha256': digest(source), 'basis': binding}

    def walk(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    receipt = json.loads((RAW / 'receipt.json').read_bytes())
    launch = json.loads((CONTROL / 'launch-inputs.json').read_bytes())
    scope = dict(hashlib=hashlib, json=json)
    tree = ast.parse((HOST / 'tools/probe_product_water.py').read_text(encoding='utf-8-sig'))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in ('fingerprint', 'snapshot_sources', 'snapshot_digest')]
    assert len(nodes) == 3
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<frozen source inventory>', 'exec'), scope)
    sources = scope['snapshot_sources'](PROJECT)
    assert sources == launch['files'] == receipt['files']
    assert scope['snapshot_digest'](sources) == launch['source_contract_sha256'] == receipt['source_contract_sha256']
    for source in sorted(RAW.iterdir()):
        if source.is_file() and source.name not in ('replay.json', 'portable-checks.json'):
            copy(source, Path('lifecycle') / source.name)
    for name in ('ready.png', 'ready.capture.json', 'receipt.json'):
        copy(ROOT / '.runtime/snow-product-r20-ready-v6' / name, Path('ready') / name)
    for name in ('process-exits.json', 'exit-watcher.json', 'offline-closure-cleanup.json',
                 'launch-inputs.json', 'launch-preflight.json', 'launch-postflight.json',
                 'ready-summary.json', 'case-queue.json', 'frozen-plan.json',
                 'launcher-plan-amendment-v1.json'):
        copy(CONTROL / name, Path('control') / name)
    copy(HOST / 'manifest.json', Path('control/external-host-manifest.json'))
    for name in ('camera.py', 'scene.py', 'ui.py'):
        relative = 'behavior_pack/modern_projection/projection/' + name
        source = PROJECT / relative
        assert digest(source) == receipt['files'][relative]
        copy(source, Path('inputs') / name, 'Product source inventory in original wrapper receipt')
    for name in ('verify_snow_plant_visibility.py', 'verify_centered_snow_profiles.py',
                 'native_draw_response.py', 'plant_alpha_geometry.py'):
        source = RAW / 'inputs/tools' / name
        assert digest(source) == receipt['input_file_sha256']['tools/' + name]
        assert digest(source) == receipt['files']['tools/' + name]
        copy(source, Path('inputs') / name, 'Original captured acquisition input and product source inventory')
    for name in ('run_snow_scene_lifecycle_r20.py', 'probe_snow_product_r20.py'):
        source = RAW / 'inputs' / name
        assert digest(source) == receipt['input_file_sha256'][name]
        assert digest(source) == digest(HOST / 'tools' / name)
        copy(source, Path('inputs') / name, 'Original acquisition input and frozen external host')
    for name in ('analyze_snow_lifecycle_r20.py', 'analyze_snow_product_r20.py', 'probe_product_water.py'):
        copy(HOST / 'tools' / name, Path('inputs') / name, 'Frozen external host manifest')
    report = json.loads((RAW / 'report.json').read_bytes())
    for record in walk(report):
        if 'path' in record and 'sha256' in record:
            source = Path(record['path']).resolve(strict=True)
            assert digest(source) == record['sha256']
            if str(source) not in mapping:
                copy(source, Path('assets') / source.name)
    for key in ('model', 'texture'):
        source = Path(report['assets'][key]).resolve(strict=True)
        assert digest(source) == report['assets'][key + '_sha256']
        copy(source, Path('assets') / source.name)
    copy(ROOT / 'tools/verify_snow_lifecycle_subset_r20.py', Path('verify_package.py'))
    audit = {'schema': 1, 'recorded_after_exact_process_exit': True,
             'matches_launch_and_receipt': True, 'source_contract_sha256': scope['snapshot_digest'](sources),
             'files': sources, 'evidence': ['lifecycle/receipt.json', 'control/launch-inputs.json'],
             'limit': 'Hashes audit the original unchanged project; unrelated product media are not duplicated'}
    (DEST / 'control/source-audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='ascii')
    manifest = {'schema': 1, 'kind': 'snow_lifecycle_subset',
                'source_contract_sha256': scope['snapshot_digest'](sources), 'original_to_package': mapping,
                'input_bindings': bindings, 'original_completed': report['completed'],
                'original_restored': report['restored'], 'workflow_scope': 'blue_orchid h0 nine editing steps only',
                'workflow_accepted': True, 'production_accepted': False, 'full_snow_acceptance': False,
                'complete_executable_acquisition_replay': False,
                'replay_scope': 'Original native images, exact recorded masks, clocks, camera and pure geometry checks',
                'files': {}}
    for path in sorted(DEST.rglob('*')):
        if path.is_file() and path.name != 'manifest.json' and '__pycache__' not in path.parts:
            manifest['files'][path.relative_to(DEST).as_posix()] = {'sha256': digest(path), 'bytes': path.stat().st_size}
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'files': len(manifest['files']), 'bytes': sum(row['bytes'] for row in manifest['files'].values()),
                      'source_contract_sha256': scope['snapshot_digest'](sources)}))


if __name__ == '__main__':
    main()
