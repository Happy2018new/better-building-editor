"""Fit native camera coordinates using stone corners, independently of water pixels."""
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from camera_projection import project_points
from water_native_projection import coordinates, validate_calibration

SOURCE = ROOT / '.runtime/water-r20-state-v7/calibration.json'
TARGET = SOURCE.with_name('native-calibration-fit.json')
source = json.loads(SOURCE.read_bytes())
native = source['native_projection']
validation = validate_calibration(source, native['session_binding'],
                                  native['source_contract_sha256'])
rows = []
for view in source['views']:
    reading = native['rows'][view['view'] + '_shown']['before']
    size = (view['shown']['width'], view['shown']['height'])
    projected = project_points(reading['world_points']['cube'],
        view['camera']['position'], view['pose']['target'], size, 90.)
    basis = np.asarray([(point['screenX'] - size[0] / 2.,
                         point['screenY'] - size[1] / 2.) for point in projected])
    rows.append({'view': view['view'], 'size': size,
                 'basis': basis, 'native': coordinates(reading, 'cube', size)})


def fit(chosen):
    matrix, expected = [], []
    for row in chosen:
        for xy, actual in zip(row['basis'], row['native']):
            matrix.extend(((xy[0], 1., 0.), (xy[1], 0., 1.)))
            expected.extend(actual)
    solution, residuals, rank, singular = np.linalg.lstsq(matrix, expected, rcond=None)
    scale, cx, cy = (float(value) for value in solution)
    assert rank == 3 and scale > 0.
    details = []
    for row in rows:
        error = row['basis'] * scale + np.asarray([cx, cy]) - row['native']
        details.append({'view': row['view'], 'max_absolute_pixels': float(abs(error).max()),
                        'rms_pixels': float(np.sqrt(np.mean(error ** 2)))})
    return {'fit_views': [row['view'] for row in chosen], 'scale_relative_fov90': scale,
            'vertical_fov': math.degrees(2. * math.atan(1. / scale)),
            'center_physical_pixels': [cx, cy], 'evaluation': details}


report = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
          'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'source_path': str(SOURCE), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'session_binding': native['session_binding'],
          'source_contract_sha256': native['source_contract_sha256'],
          'stone_calibration_validation': validation,
          'fit_input': '24 native stone cube corners; no water pixels or polygons',
          'physical_size': rows[0]['size'], 'reported_fov': source['reported_fov'],
          'silhouette_fov': source['vertical_fov'],
          'shared': fit(rows), 'individual': [fit([row]) for row in rows],
          'leave_one_view_out': [fit([row for row in rows if row is not held]) for held in rows]}
TARGET.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'path': str(TARGET), 'shared': report['shared'],
                  'leave_one_view_out': report['leave_one_view_out']}))
