"""Replay the uninterrupted missing-route batch without keeping decoded frames resident."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import analyze_liquid_workspace as workspace
import analyze_product_water as product
import analyze_water_acceptance_r16 as acceptance

SOURCE = ROOT / '.runtime/water-r20-state-v7/world-missing-public19.json'
TARGETS = {name: SOURCE.with_name('world-missing-public19-' + name + '.json')
           for name in ('analysis', 'product-analysis', 'native-product-analysis')}
assert not any(path.exists() for path in TARGETS.values())
raw = json.loads(SOURCE.read_bytes())
assert raw['completed'] is True and raw['restored'] is True and raw['cleanup_errors'] == []
assert raw['source_unchanged'] is True
assert raw['routes'] == ['missing'] and len(raw['cases']) == 19
original_rgb = product.rgb
with tempfile.TemporaryDirectory(prefix='water-missing-r21-') as directory:
    cache = {}

    def decoded_rgb(path):
        key = str(Path(path).resolve(strict=True))
        if key not in cache:
            target = Path(directory) / ('decoded-%d.npy' % len(cache))
            np.save(target, original_rgb(path), allow_pickle=False)
            cache[key] = target
        return np.load(cache[key], mmap_mode='r', allow_pickle=False)

    product.rgb = workspace.rgb = acceptance.rgb = decoded_rgb
    try:
        results = {
            'analysis': acceptance.replay(SOURCE),
            'product-analysis': product.analyze(SOURCE),
            'native-product-analysis': product.analyze(SOURCE, native_world_geometry=True),
        }
    finally:
        product.rgb = workspace.rgb = acceptance.rgb = original_rgb
for name, result in results.items():
    result.update(diagnostic_only=True, production_qualified=False,
                  host_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    TARGETS[name].write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='ascii')
print(json.dumps({name: {'evidence_valid': result['evidence_valid'],
    'capture_failures': result.get('capture_failures', []),
    'gates': result.get('observed_product_gates'),
    'geometry': result.get('geometry'), 'budgets': result.get('budgets')}
    for name, result in results.items()}))
