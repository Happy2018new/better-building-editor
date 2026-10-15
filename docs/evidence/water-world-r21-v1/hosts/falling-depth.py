"""Compare the original falling mask with independent opaque-support depth."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import analyze_product_water as analysis

OUTPUT = ROOT / '.runtime/water-r20-state-v7/falling-depth-v1'
assert not OUTPUT.exists()
OUTPUT.mkdir()
source_path = OUTPUT.parent / 'world-full-public19.json'
source = json.loads(source_path.read_bytes())
row = source['rows']['full_falling_wet']
wet = analysis.rgb(source['captures']['full_falling_wet']['path'])
dry = analysis.rgb(source['captures']['full_falling_dry']['path'])
size = wet.shape[1], wet.shape[0]
old = analysis.expected_mask(row, source, size)
depth = analysis.unoccluded_neighbor_mask(row, source, size)
selected = np.asarray(Image.fromarray((old * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(17))) > 0
selected[size[1] // 2 - 6:size[1] // 2 + 6, size[0] // 2 - 6:size[0] // 2 + 6] = False
old &= selected
depth &= selected
actual = analysis.difference_mask(wet, dry, selected, analysis.LIMITS['rgb_delta'])
negative = actual.copy()
negative[300:450, 890:1100] = False
report = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
          'source_report_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
          'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'analyzer_sha256': hashlib.sha256(Path(analysis.__file__).read_bytes()).hexdigest(),
          'source_contract_sha256': source['source_contract_sha256'],
          'original': analysis.product_geometry(actual, old),
          'support_depth': analysis.product_geometry(actual, depth),
          'removed_visible_water': analysis.product_geometry(negative, depth),
          'blank': analysis.product_geometry(np.zeros_like(actual), depth),
          'occluded_pixels': int(np.count_nonzero(old & ~depth)),
          'solid_boxes': list(analysis.fixture_solid_boxes(row))}
for name, mask in (('original', old), ('support-depth', depth), ('actual', actual)):
    Image.fromarray((mask * 255).astype(np.uint8)).save(OUTPUT / (name + '.png'))
(OUTPUT / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='ascii')
print(json.dumps(report))
