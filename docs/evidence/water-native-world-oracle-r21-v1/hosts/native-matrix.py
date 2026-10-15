"""Apply the opt-in native stone oracle to preserved images without running the game."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import analyze_product_water as analysis

SOURCE = ROOT / '.runtime/water-r20-state-v7/world-full-public19.json'
TARGET = SOURCE.with_name('world-full-public19-native-product-analysis.json')
assert not TARGET.exists()
original_rgb = analysis.rgb

with tempfile.TemporaryDirectory(prefix='water-native-oracle-r21-') as directory:
    cache = {}

    def decoded_rgb(path):
        key = str(Path(path).resolve(strict=True))
        if key not in cache:
            target = Path(directory) / ('decoded-%d.npy' % len(cache))
            np.save(target, original_rgb(path), allow_pickle=False)
            cache[key] = target
        return np.load(cache[key], mmap_mode='r', allow_pickle=False)

    analysis.rgb = decoded_rgb
    try:
        result = analysis.analyze(SOURCE, native_world_geometry=True)
    finally:
        analysis.rgb = original_rgb
result.update(diagnostic_only=True, production_qualified=False, performance_without_intervention=False,
              host_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
TARGET.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='ascii')
print(json.dumps({'evidence_valid': result['evidence_valid'],
    'capture_failures': result['capture_failures'], 'geometry': result['geometry'],
    'gates': result['observed_product_gates'], 'oracle': result['geometry_oracle']}))
