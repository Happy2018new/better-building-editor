"""Decode frozen native banner matrix measurements from actual WGC pixels."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence/native-render-profile-r15'
SAMPLES = {
    'standing_oblique': ('150-metrics-v5-standing-frame',
                         ((944, 432), (1125, 485), (1300, 540)), (935, 432)),
    'standing_zero': ('152-metrics-v5-zero-frame', ((705, 600),), (718, 600)),
    'wall_zoom2': ('155-metrics-v5-wall-zero-frame', ((705, 600),), (710, 565)),
    'wall_zoom1': ('157-metrics-v5-wall-zoom1-frame', ((857, 600),), (860, 582)),
}


def decode(pixel, offset):
    assert pixel[2] == 255
    return (pixel[0] * 256 + pixel[1] - offset) / (32. if offset else 64.)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = {}
    for label, (folder, points, pole) in SAMPLES.items():
        path = EVIDENCE / folder
        source = json.loads((path / 'report.json').read_text(encoding='utf8'))
        assert source['capture']['reliable'] and source['capture']['background_safe']
        assert source['before']['editor_camera'] == source['after']['editor_camera']
        assert source['before']['ready'] and not source['before']['pending']
        image_path = path / 'frame.png'
        image_sha = hashlib.sha256(image_path.read_bytes()).hexdigest()
        assert image_sha == source['capture']['sha256']
        with Image.open(image_path).convert('RGB') as image:
            colors = [image.getpixel(p) for p in points]
            pole_color = image.getpixel(pole)
        rows[label] = {'source': str(path.relative_to(ROOT)), 'image_sha256': image_sha,
                       'camera': source['before']['editor_camera'],
                       'points': points, 'pixels': colors,
                       'view_translation_plus_350': [decode(p, 32768) for p in colors],
                       'pole_point': pole, 'pole_pixel': pole_color,
                       'matrix_row_scale': decode(pole_color, 0)}
    zoom2, zoom1 = rows['wall_zoom2'], rows['wall_zoom1']
    assert zoom2['camera'] == [0., 0., 2.] and zoom1['camera'] == [0., 0., 1.]
    origin_offset = (2. * zoom1['view_translation_plus_350'][0] -
                     zoom2['view_translation_plus_350'][0])
    oblique = rows['standing_oblique']
    assert oblique['camera'] == [35., 25., 2.]
    toward_x = math.sin(math.radians(35.)) * math.cos(math.radians(25.))
    values = oblique['view_translation_plus_350']
    steps = [(values[i + 1] - values[i]) / (5. * toward_x) for i in range(2)]
    logical_scale = sum(steps) / len(steps)
    model_scale = oblique['matrix_row_scale'] / logical_scale
    assert abs(origin_offset + 100.) < .0625
    assert max(steps) - min(steps) < .0625
    assert abs(model_scale - .64) < .002
    result = {'schema': 1, 'runtime': '3.10.0.420447', 'family': 'native banner/pole',
              'observations': rows, 'camera_basis_toward_x': toward_x,
              'view_translation_zero_scale_intercept': origin_offset,
              'native_view_origin_candidate': 350. - origin_offset,
              'logical_block_scale_from_five_block_steps': steps,
              'native_model_to_block_scale_candidate': model_scale,
              'quantization': {'translation': 1. / 32., 'matrix_row_scale': 1. / 64.},
              'production_acceptance': False,
              'limits': 'Measured matrix contract only; candidate must still pass depth, cut plane and world regression.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
