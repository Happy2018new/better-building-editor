"""Compare declared side texel centers to frozen artwork without fitting geometry."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path('D:/bbe-r18-water-production')
OUTPUT = ROOT / '.runtime/water-final-r19-world-v4'
sys.path.insert(0, str(PROJECT / 'tools'))
from analyze_product_water import rgb
from analyze_water_acceptance_r16 import repetition
from diagnose_water_texel_centers_r17 import sample

source = json.loads((OUTPUT / 'world.json').read_bytes())
row = source['extra_rows']['full_pool_wet_side_opaque']
image = rgb(source['captures']['full_pool_wet_side_opaque']['path'])
shapes = {tuple(shape['position']): shape for shape in row['ready']['shapes']
          if shape['texture'] == 'flowing_water_grey' and shape['faces'] & 30}
texture = rgb(PROJECT / 'resource_pack/textures/models/modern_projection/liquid/flowing_water_grey.png')
expected = texture[5:13, 2:14].astype(float)
sheet = Image.new('RGB', (720, 320), 'white')
draw = ImageDraw.Draw(sheet)
results = {'diagnostic_only': True, 'product_admission_performed': False,
           'physical_grid_fitted': False, 'rows': {}}
for index, (name, face, positions) in enumerate((
        ('south', 2, ((3, 3, 4), (4, 3, 4))), ('east', 4, ((4, 3, 3), (4, 3, 4))))):
    observed = [sample(image, shapes[pos], face, row, source)[0] for pos in positions]
    for column, (label, values) in enumerate((('expected grey', expected),
                                             ('cell one', observed[0]), ('cell two', observed[1]))):
        tile = Image.fromarray(np.uint8(np.clip(values, 0, 255))).resize((216, 120), Image.Resampling.NEAREST)
        sheet.paste(tile, (column * 240 + 5, index * 160 + 27))
        draw.text((column * 240 + 5, index * 160 + 7), name + ' ' + label, fill='black')
    results['rows'][name] = {'cell_pair': repetition(*observed), 'cells': []}
    for pos, values in zip(positions, observed):
        results['rows'][name]['cells'].append({'position': pos,
            'expected_grey_correlation': repetition(expected, values)['correlation'],
            'expected_grey_horizontal_mirrored_correlation': repetition(expected[:, ::-1], values)['correlation'],
            'expected_grey_vertical_mirrored_correlation': repetition(expected[::-1], values)['correlation'],
            'samples': values.tolist()})
sheet.save(OUTPUT / 'side-texel-samples.png')
(OUTPUT / 'side-texel-artwork.json').write_text(json.dumps(results, indent=2) + '\n', encoding='ascii')
print(json.dumps({key: {'pair_correlation': value['cell_pair']['correlation'],
                       'artwork_correlations': [cell['expected_grey_correlation'] for cell in value['cells']]}
                  for key, value in results['rows'].items()}))
