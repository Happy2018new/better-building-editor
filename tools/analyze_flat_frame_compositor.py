"""Analyze independently captured alpha layers without changing acceptance gates."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageFilter

from flat_frame_item_visual_checks import content_mask
from verify_debug_blueprints import write_json


def layer_measure(composite, item, body, background, crop, mask, opacity=.2):
    frames = []
    for path in (composite, item, body, background):
        with Image.open(path) as image:
            frames.append(image.convert('RGB').crop(crop))
    eligible = mask.filter(ImageFilter.MinFilter(3)).tobytes()
    energy = error = 0.
    samples = 0
    for channel in range(3):
        pixels = [frame.split()[channel].tobytes() for frame in frames]
        for actual, front, rear, blank, use in zip(*pixels, eligible):
            if not use:
                continue
            # Cancel the shared blank contribution in the two isolated layers.
            predicted = front + (1. - opacity) * (rear - blank)
            energy += (actual - blank) ** 2
            error += (actual - predicted) ** 2
            samples += 1
    residual = (error / energy) ** .5 if energy > 100 and samples >= 60 else None
    return {'diagnostic_matches_layers': residual is not None and residual <= .12,
            'relative_composition_residual': residual, 'samples': samples,
            'opacity_per_layer': opacity,
            'equal_color_two_layer_coverage': 1. - (1. - opacity) ** 2,
            'formula': 'item_faded + (1-opacity) * (body_faded - blank)',
            'scope': 'Isolated layers explain composite contrast; this does not replace the original opacity gate'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh diagnostic output')
    report = json.loads(args.input.read_text(encoding='utf8'))
    assert report['completed'] and report['restored'] and report['candidate_alpha_ownership']
    full = report['rows'][0]['item_scopes']['full']
    captures = full['alpha_ownership']['captures']
    blank = captures['blank']['0.0']['capture']['path']
    unused, mask = content_mask(captures['item']['1.0']['capture']['path'], blank, full['crop'])
    measurement = layer_measure(full['alpha02']['capture']['path'],
                                captures['item']['0.2']['capture']['path'],
                                captures['body']['0.2']['capture']['path'], blank, full['crop'], mask)
    result = {'schema': 1, 'completed': True, 'production_rendering_accepted': False,
              'original_report_passed': report['passed'],
              'input': str(args.input.resolve()),
              'input_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
              'measurement': measurement}
    write_json(args.output, result)
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
