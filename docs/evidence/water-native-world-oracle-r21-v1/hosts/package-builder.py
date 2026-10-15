"""Freeze additional native analysis while referring to the original world pixels."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'docs/evidence/water-native-world-oracle-r21-v1'
WORLD = ROOT / 'docs/evidence/water-world-r21-v1'
FILES = {
    'analysis.json': ROOT / '.runtime/water-r20-state-v7/world-full-public19-native-product-analysis.json',
    'analyzer/analyze_product_water.py': ROOT / 'tools/analyze_product_water.py',
    'analyzer/water_native_projection.py': ROOT / 'tools/water_native_projection.py',
    'tests/test_product_water_analysis.py': ROOT / 'tests/test_product_water_analysis.py',
    'tests/test_water_native_projection.py': ROOT / 'tests/test_water_native_projection.py',
    'hosts/native-matrix.py': ROOT / '.runtime/water-r21-native-matrix.py',
    'hosts/package-builder.py': Path(__file__),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not (OUTPUT / 'manifest.json').exists()
assert (OUTPUT / 'README.md').is_file() and (OUTPUT / 'verify_package.py').is_file()
for name, source in FILES.items():
    target = OUTPUT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert sha(target) == sha(source), name
    else:
        shutil.copy2(source, target)
references = {name: {'path': '../water-world-r21-v1/' + name, 'sha256': sha(WORLD / name)}
    for name in ('manifest.json', 'verify_package.py', 'references.json', 'world-full-public19.json',
                 'world-full-public19-product-analysis.json', 'calibration.json', 'native-calibration-fit.json')}
(OUTPUT / 'references.json').write_text(json.dumps(references, indent=2, sort_keys=True) + '\n', encoding='ascii')
manifest = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
    'files': {path.relative_to(OUTPUT).as_posix(): {'bytes': path.stat().st_size, 'sha256': sha(path)}
              for path in sorted(OUTPUT.rglob('*')) if path.is_file() and '__pycache__' not in path.parts}}
(OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='ascii')
print(json.dumps({'files': len(manifest['files']),
    'bytes': sum(row['bytes'] for row in manifest['files'].values()), 'production_qualified': False}))
