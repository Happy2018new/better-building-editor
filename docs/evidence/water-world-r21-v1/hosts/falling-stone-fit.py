"""Evaluate original falling pixels using the independent stone-coordinate fit."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import analyze_product_water as analysis
from camera_projection import project_points

BASE = ROOT / '.runtime/water-r20-state-v7'
SOURCE_PATH = BASE / 'world-full-public19.json'
FIT_PATH = BASE / 'native-calibration-fit.json'
OUTPUT = BASE / 'falling-stone-fit-v1'
assert not OUTPUT.exists()
source = json.loads(SOURCE_PATH.read_bytes())
fitted = json.loads(FIT_PATH.read_bytes())
assert fitted['source_contract_sha256'] == source['source_contract_sha256']
assert fitted['session_binding'] == source['session_binding']
assert fitted['source_sha256'] == source['camera_calibration']['sha256']
row = source['rows']['full_falling_wet']
wet = analysis.rgb(source['captures']['full_falling_wet']['path'])
dry = analysis.rgb(source['captures']['full_falling_dry']['path'])
size = wet.shape[1], wet.shape[0]
original = analysis.expected_mask(row, source, size)
old_project = analysis.project


def project(points, shape, row, source, size):
    world = np.asarray(points) + np.asarray(row['ready']['origin'])
    projected = project_points(world, row['camera']['position'], row['camera']['target'], size, 90.)
    basis = np.asarray([(point['screenX'] - size[0] / 2.,
                         point['screenY'] - size[1] / 2.) for point in projected])
    result = basis * fitted['shared']['scale_relative_fov90']
    result += np.asarray(fitted['shared']['center_physical_pixels'])
    return result


analysis.project = project
try:
    corrected = analysis.unoccluded_neighbor_mask(row, source, size)
finally:
    analysis.project = old_project
selected = np.asarray(Image.fromarray((original * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(17))) > 0
selected[size[1] // 2 - 6:size[1] // 2 + 6, size[0] // 2 - 6:size[0] // 2 + 6] = False
actual = analysis.difference_mask(wet, dry, selected, analysis.LIMITS['rgb_delta'])
negative = actual.copy()
negative[300:450, 890:1100] = False
report = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
    'source_report_sha256': hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest(),
    'fit_report_sha256': hashlib.sha256(FIT_PATH.read_bytes()).hexdigest(),
    'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'source_contract_sha256': source['source_contract_sha256'],
    'original': analysis.product_geometry(actual, original & selected),
    'stone_fit_support_depth': analysis.product_geometry(actual, corrected & selected),
    'blank': analysis.product_geometry(np.zeros_like(actual), corrected & selected),
    'removed_fixed_rectangle': analysis.product_geometry(negative, corrected & selected)}
OUTPUT.mkdir()
Image.fromarray(((corrected & selected) * 255).astype(np.uint8)).save(OUTPUT / 'stone-fit-depth.png')
(OUTPUT / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='ascii')
print(json.dumps(report))
