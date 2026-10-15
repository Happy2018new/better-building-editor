"""Preserve the failed real-mesh vertex-format probe without acceptance."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
output = ROOT/'docs/evidence/shelf-light-inputs-r21-mesh-v1-failure'
assert not output.exists()
output.mkdir(parents=True)
paths = [
    '.runtime/shelf-mesh-inputs-r21-v1-selection',
    '.runtime/shelf-mesh-inputs-r21-start-v1',
    '.runtime/shelf-mesh-inputs-r21-compile-v1.json',
    '.runtime/start_shelf_mesh_inputs_r21.py',
    '.runtime/start_shelf_mesh_inputs_observed_r21.py',
    '.runtime/recover_shelf_missing_normal_r21.py',
    '.runtime/close_shelf_missing_normal_r21.py',
    '.runtime/disabled-skin-watch-r20-v2/status.json',
    '.runtime/projects/shelf-r21-mesh-inputs-v1/shelf-input-contract.json',
    '.runtime/projects/shelf-r21-mesh-inputs-v1/resource_pack/materials/terrain.material',
    '.runtime/projects/shelf-r21-mesh-inputs-v1/resource_pack/shaders/glsl/modern_projection_shelf_inputs.vertex',
    '.runtime/projects/shelf-r21-mesh-inputs-v1/resource_pack/shaders/glsl/modern_projection_shelf_inputs.fragment',
]
for relative in paths:
    source = ROOT/relative
    target = output/'originals'/relative.removeprefix('.runtime/')
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)
shutil.copy2(__file__, output/'package-builder.py')
report = json.loads((ROOT/paths[0]/'report.json').read_bytes())
assert report['completed'] is False and report['restored'] is False
assert len(report['captures']) == 2
exits = json.loads((ROOT/paths[1]/'exact-exit.json').read_bytes())
assert exits['completed'] is True
assert all(row['state'] == 'exited' for row in exits['processes'].values())
index = {'completed': False, 'restored': False, 'production_qualified': False,
         'flag_readback_valid': False, 'captures': len(report['captures']),
         'failure': 'Engine reports combined mesh has no NORMAL vertex field',
         'limits': ['Only native-world and empty controls were captured.',
                    'No diagnostic input or candidate appearance was captured.',
                    'Fixture cleanup was blocked by the repeated diagnostic modal.',
                    'Only the private diagnostic world remains modified.',
                    'Normal close and exact exit evidence do not establish a normal exit cause.'],
         'exact_exit': exits['processes']}
(output/'index.json').write_text(json.dumps(index, indent=2)+'\n', encoding='ascii')
(output/'README.md').write_text(
    '# Failed terrain-mesh NORMAL probe\n\n'
    'The engine rejected the real combined mesh because it did not bind NORMAL. '
    'Synthetic compilation had passed, but no diagnostic draw was obtained. '
    'The original report retains completed=false, restored=false and all cleanup errors. '
    'The exact modal was dismissed during normal close without activation; '
    'the retained handles recorded MC 0xC0000409 and MCDK 0. '
    'No force stop was used. The private fixture remains un-restored.\n\n'
    'Original capture bytes, failure report, acquisition hosts, diagnostic shaders, '
    'compile evidence, modal receipts and exact exit evidence are retained. '
    'This package grants no shader-input, lighting, item-content or production acceptance.\n',
    encoding='ascii')
manifest = {path.relative_to(output).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in output.rglob('*') if path.is_file()}
(output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='ascii')
assert all(hashlib.sha256((output/path).read_bytes()).hexdigest() == expected
           for path, expected in manifest.items())
print(json.dumps({'manifest_files': len(manifest), 'captures': 2, 'restored': False}))
