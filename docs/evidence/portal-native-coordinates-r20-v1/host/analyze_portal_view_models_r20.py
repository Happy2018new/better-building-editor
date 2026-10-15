"""Investigate v8 GPU X-coordinate readback against explicit shader models."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_portal_coordinates_r20 import decode

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--report', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
folder = args.report.parent
report = json.loads(args.report.read_bytes())
observed = {}
for kind in ('candidate', 'native'):
    row = report['captures']['end_gateway_' + kind + '_front']
    control, observed[kind] = decode(folder / ('end_gateway_' + kind + '_front.png'), row['camera'])
    assert control['control_observed']

camera = report['captures']['end_gateway_candidate_front']['camera']
assert camera == report['captures']['end_gateway_native_front']['camera']
corners = dict(camera['face_points'])['north']
world = np.asarray(dict(camera['face_world_points'])['north'], dtype=np.float64)
eye = np.asarray(camera['position'], dtype=np.float64)
equations, targets = [], []
for point, (u, v) in zip(corners, ((0., 0.), (1., 0.), (1., 1.), (0., 1.))):
    x, y = point['screenX'], point['screenY']
    equations.extend(((x, y, 1., 0., 0., 0., -u*x, -u*y),
                      (0., 0., 0., x, y, 1., -v*x, -v*y)))
    targets.extend((u, v))
transform = np.append(np.linalg.solve(equations, targets), 1.).reshape(3, 3)
models = {}
for relative in (False, True):
    for neutral, add_eye in ((0., True), (-1./255., True), (1./255., True),
                             (0., False), (-1./255., False), (1./255., False)):
        name = ('eye_relative' if relative else 'absolute') + '_' + str(neutral) + ('_add_eye' if add_eye else '_no_eye')
        normal = np.array((neutral, neutral, -1.))
        ray = world - eye if relative else world
        models[name] = []
        for index, depth in enumerate(range(0, 32, 2)):
            distance = np.floor(index*255./16.)*(32./255.)
            t = 1. - distance*float(normal @ normal) / (ray @ normal)
            position = t[:, None]*ray + (eye if add_eye else 0.)
            uv = position[:, :2]/16.
            angle = distance*np.pi*(5./7.)
            vertex_x = np.cos(angle)*uv[:, 0] - np.sin(angle)*uv[:, 1] + np.cos(angle)*distance
            first_mask, first_image = observed['candidate'][depth]
            second_mask, second_image = observed['native'][depth]
            mask = first_mask & second_mask
            py, px = np.nonzero(mask)
            mapped = transform @ np.asarray((px+.5, py+.5, np.ones(len(px))))
            u, v = mapped[:2] / mapped[2]
            # Both possible unit-square triangle diagonals are retained as controls.
            interpolated = {
                '02': np.where(u >= v,
                               (1.-u)*vertex_x[0]+(u-v)*vertex_x[1]+v*vertex_x[2],
                               (1.-v)*vertex_x[0]+u*vertex_x[2]+(v-u)*vertex_x[3]),
                '13': np.where(u+v <= 1.,
                               (1.-u-v)*vertex_x[0]+u*vertex_x[1]+v*vertex_x[3],
                               (1.-v)*vertex_x[1]+(u+v-1.)*vertex_x[2]+(1.-u)*vertex_x[3])}
            row = {'depth': depth, 'pixels': len(px), 'diagonals': {}}
            for diagonal, values in interpolated.items():
                expected = np.floor(np.mod(values, 1.)*256.).astype(int)
                compared = {}
                for kind, actual in (('candidate', first_image[mask, 0]), ('native', second_image[mask, 0])):
                    delta = (actual.astype(int)-expected+128) % 256-128
                    compared[kind] = {'exact': float(np.mean(delta == 0)),
                                      'within_one': float(np.mean(np.abs(delta) <= 1)),
                                      'abs_error_mean': float(np.mean(np.abs(delta))),
                                      'abs_error_max': int(np.max(np.abs(delta)))}
                row['diagonals'][diagonal] = compared
            models[name].append(row)

delta_rows = []
translation_rows = []
time_residuals = []
for index, depth in enumerate(range(0, 32, 2)):
    first_mask, first_image = observed['candidate'][depth]
    second_mask, second_image = observed['native'][depth]
    mask = first_mask & second_mask
    delta = (second_image[mask, :2].astype(int)-first_image[mask, :2].astype(int)+128) % 256-128
    modes = []
    for column in range(2):
        unique, counts = np.unique(delta[:, column], return_counts=True)
        mode = int(unique[np.argmax(counts)])
        residual = (delta[:, column]-mode+128) % 256-128
        modes.append({'mode': mode, 'minimum': int(delta[:, column].min()),
                      'maximum': int(delta[:, column].max()),
                      'within_one_after_phase': float(np.mean(np.abs(residual) <= 1))})
    delta_rows.append({'depth': depth, 'difference': modes})
    distance = np.floor(index*255./16.)*(32./255.)
    angle = distance*np.pi*(5./7.)
    rotation = np.asarray(((np.cos(angle), -np.sin(angle)),
                           (np.sin(angle), np.cos(angle))))
    expected_shift = rotation @ (-eye[:2]*16.)
    residual = (delta - expected_shift + 128.) % 256.-128.
    time_residuals.append(residual[:, 1])
    translation_rows.append({'depth': depth,
                             'expected_shift_texels_unwrapped': expected_shift.tolist(),
                             'x_residual_abs_max': float(np.abs(residual[:, 0]).max()),
                             'x_residual_abs_mean': float(np.abs(residual[:, 0]).mean()),
                             'time_phase_residual_min': float(residual[:, 1].min()),
                             'time_phase_residual_max': float(residual[:, 1].max())})
time_values = np.concatenate(time_residuals)
common_time_phase = float(np.median(time_values))
for row, residual in zip(translation_rows, time_residuals):
    adjusted = (residual-common_time_phase+128.) % 256.-128.
    row['y_residual_after_common_phase_abs_max'] = float(np.abs(adjusted).max())
result = {'schema': 1, 'source_report_sha256': hashlib.sha256(args.report.read_bytes()).hexdigest(),
          'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'models': models, 'raw_differences': delta_rows,
          'known_eye_translation': {'fitted_parameters_for_x': 0,
                                    'common_time_phase_texels': common_time_phase,
                                    'rows': translation_rows},
          'qualification': False, 'renderer_modified': False,
          'limits': ['CPU models investigate the bound GPU X bytes only.',
                     'Triangle diagonals and neutral-byte conventions remain explicit.',
                     'No live candidate using a corrected shader has been observed.']}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, sort_keys=True, indent=2)+'\n', encoding='ascii', newline='\n')
summary = {}
for name, rows in models.items():
    summary[name] = {kind: {'mean_abs_error': float(np.mean([r['diagonals']['02'][kind]['abs_error_mean'] for r in rows])),
                            'min_within_one': min(r['diagonals']['02'][kind]['within_one'] for r in rows)}
                     for kind in ('candidate', 'native')}
print(json.dumps({'models': summary, 'known_eye_translation': result['known_eye_translation'], 'qualification': False}))
