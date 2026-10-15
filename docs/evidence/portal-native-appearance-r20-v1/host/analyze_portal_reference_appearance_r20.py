"""Measure absolute native/candidate portal pixels without phase or exposure fits."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def surface_values(image, camera, face):
    points = dict(camera['face_points'])[face]
    if not all(point['isInScreen'] for point in points):
        raise ValueError('The measured portal face must be completely on screen')
    mask = Image.new('L', image.size)
    ImageDraw.Draw(mask).polygon([(point['screenX'], point['screenY']) for point in points], fill=255)
    interior = np.asarray(mask.filter(ImageFilter.MinFilter(11))) != 0
    if int(interior.sum()) < 100:
        raise ValueError('The measured portal face is not resolved')
    return np.asarray(image.convert('RGB'))[interior]


def absolute_statistics(values):
    rgb = np.asarray(values, dtype=np.float64)
    luminance = rgb @ np.asarray((.2126, .7152, .0722))
    cyan = ((rgb[:, 1] > rgb[:, 0]+4.) & (rgb[:, 2] > rgb[:, 0]+4.) &
            (rgb.max(axis=1)-rgb.min(axis=1) > 8.))
    magenta = ((rgb[:, 0] > rgb[:, 1]*1.3+20.) & (rgb[:, 2] > rgb[:, 1]+10.))
    return {'interior_pixels': len(rgb), 'rgb_mean': rgb.mean(axis=0).tolist(),
            'luminance_mean': float(luminance.mean()),
            'luminance_p50_p95_p99': np.percentile(luminance, (50., 95., 99.)).tolist(),
            'luminance_max': float(luminance.max()),
            'nonblack_pixels': int(np.sum(rgb.max(axis=1) > 8.)),
            'nonblack_ratio': float(np.mean(rgb.max(axis=1) > 8.)),
            'cyan_star_pixels': int(cyan.sum()), 'cyan_star_ratio': float(cyan.mean()),
            'magenta_contamination_pixels': int(magenta.sum()),
            'magenta_contamination_ratio': float(magenta.mean()),
            'excluded_pixels': 0}


def analyze(report_path):
    report = json.loads(report_path.read_bytes())
    if not all(report.get(key) for key in ('completed', 'restored', 'source_unchanged', 'project_source_unchanged')):
        raise ValueError('Absolute appearance analysis requires a completed and restored bound run')
    result = {'source_report_sha256': sha(report_path), 'pairs': {}}
    for family, face in (('end_gateway', 'north'), ('end_portal', 'top')):
        for view in ('front', 'oblique'):
            keys = {kind: family+'_'+kind+'_'+view for kind in ('candidate', 'native')}
            if not any(key in report['captures'] for key in keys.values()):
                continue
            rows = {kind: report['captures'][key] for kind, key in keys.items()}
            first, second = rows['candidate']['camera'], rows['native']['camera']
            if any(np.max(np.abs(np.asarray(first[key])-np.asarray(second[key]))) > .002
                   for key in ('position', 'rotation')):
                raise ValueError('Native/candidate cameras disagree')
            if first['face_points'] != second['face_points']:
                raise ValueError('Native/candidate face footprints disagree')
            measured = {}
            for kind, row in rows.items():
                capture = row['capture']
                frame = capture['frame']
                if not (capture['ok'] and capture['reliable'] and capture['foreground_unchanged'] and
                        not capture['agent_activation_allowed'] and
                        frame['frame_qpc_100ns'] > frame['request_qpc_100ns']):
                    raise ValueError('A bound image failed the fresh, non-activating WGC gate')
                path = report_path.parent / Path(capture['path']).name
                if sha(path) != capture['sha256']:
                    raise ValueError('A bound portal image changed')
                with Image.open(path) as image:
                    values = surface_values(image, row['camera'], face)
                measured[kind] = dict(absolute_statistics(values), capture_sha256=sha(path))
            if any(rows['candidate']['capture'][key] != rows['native']['capture'][key]
                   for key in ('owner', 'game_pid', 'game_identity')):
                raise ValueError('Native/candidate process ownership disagrees')
            ratios = {key: (measured['candidate'][key]/measured['native'][key]
                            if measured['native'][key] else None)
                      for key in ('luminance_mean', 'cyan_star_ratio', 'nonblack_ratio')}
            result['pairs'][family+'_'+view] = {'face': face, 'statistics': measured,
                                                'candidate_to_native_ratios': ratios}
    if not result['pairs']:
        raise ValueError('The report has no complete appearance pairs')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = {'schema': 1, 'qualification': False, 'pixel_acceptance': False,
              'host_sha256': sha(Path(__file__)), 'reports': [analyze(path) for path in args.report],
              'phase_or_exposure_fit': False, 'particle_pixels_removed': False,
              'cyan_star_rule': 'G > R+4 and B > R+4 and max(RGB)-min(RGB) > 8',
              'nonblack_rule': 'max(RGB) > 8',
              'luminance_rule': '0.2126 R + 0.7152 G + 0.0722 B, raw RGB bytes',
              'limits': ['Finite faces only; native beams and exterior particles are outside these masks.',
                         'Any magenta contamination remains in the raw brightness statistics.',
                         'A fresh pair samples different animation phases; no pixelwise equivalence is asserted.',
                         'Absolute measurements are evidence, not an automatic renderer qualification.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='ascii', newline='\n')
    print(json.dumps({'pairs': [key for row in result['reports'] for key in row['pairs']],
                      'phase_or_exposure_fit': False, 'qualification': False}))


if __name__ == '__main__':
    main()
