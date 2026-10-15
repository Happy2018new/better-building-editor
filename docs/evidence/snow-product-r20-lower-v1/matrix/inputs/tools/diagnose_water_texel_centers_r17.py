"""Sample predeclared physical water-side texel centers without fitting screenshots."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates

from analyze_product_water import project, rgb
from analyze_water_acceptance_r16 import repetition


def sample(image, shape, face, row, source):
    # Frozen point-filter artwork maps u and (1-height) into centers 0.5..15.5.
    horizontal, vertical = np.meshgrid(np.arange(2, 14) / 15., np.arange(5, 13) / 15.)
    height = 1. - vertical
    x, y, z = shape['position']
    if face == 2:
        points = [(x + 1. - u, y + h, z + 1.) for u, h in zip(horizontal.ravel(), height.ravel())]
    elif face == 4:
        points = [(x + 1., y + h, z + u) for u, h in zip(horizontal.ravel(), height.ravel())]
    else:
        raise ValueError('Declared south/east sides only')
    coordinates = np.asarray(project(points, shape, row, source, (image.shape[1], image.shape[0])))
    if (not np.isfinite(coordinates).all() or np.any(coordinates < 1) or
            np.any(coordinates[:, 0] > image.shape[1] - 2) or
            np.any(coordinates[:, 1] > image.shape[0] - 2)):
        raise ValueError('Physical texel centers leave the native viewport')
    values = np.stack([map_coordinates(image[:, :, channel].astype(float),
        (coordinates[:, 1] - .5, coordinates[:, 0] - .5), order=1, mode='nearest')
        for channel in range(3)], axis=1)
    return values.reshape(horizontal.shape + (3,)), coordinates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose fresh diagnostic evidence')
    source = json.loads(args.source.read_bytes())
    result = {'schema': 1, 'diagnostic_only': True, 'product_admission_performed': False,
        'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'grid': {'horizontal_texels': list(range(2, 14)), 'vertical_texels': list(range(5, 13)),
                 'pixel_mapping': 'u*15+0.5; (1-height)*15+0.5; point texture filter'},
        'rows': {}}
    for route in source['routes']:
        label = route + '_pool_wet'
        if label not in source['rows']:
            continue
        phase = label + '_side_opaque'
        row = source['extra_rows'][phase]
        image = rgb(source['captures'][phase]['path'])
        shapes = {tuple(shape['position']): shape for shape in row['ready']['shapes']
                  if shape['texture'] == 'flowing_water_grey' and shape['faces'] & 30}
        for face, positions in ((2, ((3, 3, 4), (4, 3, 4))), (4, ((4, 3, 3), (4, 3, 4)))):
            key = label + '_' + ('south' if face == 2 else 'east')
            try:
                observed = [sample(image, shapes[pos], face, row, source) for pos in positions]
                first, second = [value[0] for value in observed]
                measured = repetition(first, second)
                measured.update(negative_mirrored=repetition(first, second[:, ::-1]),
                    negative_wrong_phase=repetition(first, np.roll(second, 4, axis=1)),
                    sample_viewport_bounds=[[[float(points[:, i].min()), float(points[:, i].max())]
                                            for i in (0, 1)] for values, points in observed])
                result['rows'][key] = measured
            except ValueError as error:
                result['rows'][key] = {'passed': False, 'error': str(error)}
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps(result['rows']))


if __name__ == '__main__':
    main()
