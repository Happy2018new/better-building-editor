"""Supplemental fixed-source shape diagnostic; never accepts texture or alpha."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import analyze_liquid_native_write as visibility
import analyze_liquid_sides as oracle
from analyze_liquid_workspace import difference_mask, rgb

BASE = ROOT / '.runtime/liquid-native-write-r13-v4b'
SOURCE = BASE / 'original-priority.json'
geometry = json.loads((BASE / 'original-priority_geometry_plan.json').read_bytes())
source = json.loads(SOURCE.read_bytes())
# Run every original byte/capture/source/session/readback/camera gate first.
checked = visibility.analyze(SOURCE)
assert checked['status'] == 'OBSERVED' and checked['native_visibility_observed']
assert source['fixture_height_above_foot'] == 2
declarations = {row['id']: row for row in geometry['declarations']}
empty = rgb(source['captures']['native_empty_vnw']['path'])
result = {'schema': 1, 'scope': 'Post-capture fixed-source geometry diagnostic, not a predeclared new acceptance',
          'source': visibility.reference(SOURCE), 'geometry_plan': visibility.reference(BASE / 'original-priority_geometry_plan.json'),
          'diagnostic_source': visibility.reference(__file__), 'original_visibility': checked,
          'fixed_existing_limits': oracle.LIMITS,
          'blue_mask_limits': {'rgb_delta': 12, 'blue_over_green': 8, 'blue_over_red': 12},
          'cases': {}, 'side_uv_qualified': False, 'transparency_qualified': False,
          'animation_qualified': False, 'production_qualified': False}

def shape(mask, expected):
    edges = [oracle._edges(row) for row in (mask, expected)]
    expanded = [np.asarray(Image.fromarray(row).filter(ImageFilter.MaxFilter(7))) for row in edges]
    boundary = bool(all(row.any() for row in edges) and
        not (edges[0] & ~expanded[1]).any() and not (edges[1] & ~expanded[0]).any())
    return {'mask_iou': oracle.mask_iou(mask, expected),
            'all_boundary_pixels_within_3': boundary,
            'actual_pixels': int(mask.sum()), 'expected_pixels': int(expected.sum())}

for label, identity in visibility.SOURCES.items():
    declaration = declarations['native_palette_' + label]
    projection = declaration['projection']
    builtin = oracle.builtin_geometry(identity)
    selected = visibility.visibility_masks(identity, projection)['water_envelope']
    expected = oracle.projected_mask(builtin, projection) & selected
    masks, row = {}, {'source_candidate_heights': [surface['heights'] for surface in builtin['surfaces']], 'routes': {}}
    for route in visibility.ROUTES:
        image = rgb(source['captures'][route + '_' + label]['path'])
        blue = (image[..., 2] > image[..., 1] + 8) & (image[..., 2] > image[..., 0] + 12)
        mask = difference_mask(image, empty, selected, 12) & blue
        masks[route] = mask
        row['routes'][route] = shape(mask, expected)
    row['native_palette_vs_direct'] = shape(masks['native_palette'], masks['native_direct'])
    row['native_direct_vs_full'] = shape(masks['native_direct'], masks['full'])
    result['cases'][label] = row

output = BASE / 'fixed-source-shape-diagnostic.json'
assert not output.exists(), 'Fresh immutable supplement required'
output.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
print(json.dumps(result['cases']))
