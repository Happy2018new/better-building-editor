"""Analyze independently captured alpha layers without changing acceptance gates."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import ImageFilter

from flat_frame_item_visual_checks import capture_payload, checked_crops, content_mask
from verify_debug_blueprints import write_json


def layer_measure(composite, item, body, background, crop, mask, opacity=.2):
    frames = checked_crops((composite, item, body, background), crop, mask)
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
    records = {'blank': captures['blank']['0.0']['capture'],
               'item_opaque': captures['item']['1.0']['capture'],
               'composite_faded': full['alpha02']['capture'],
               'item_faded': captures['item']['0.2']['capture'],
               'body_faded': captures['body']['0.2']['capture']}
    images = {name: capture_payload(record) for name, record in records.items()}
    unused, mask = content_mask(images['item_opaque'], images['blank'], full['crop'])
    measurement = layer_measure(images['composite_faded'], images['item_faded'],
                                images['body_faded'], images['blank'], full['crop'], mask)
    result = {'schema': 1, 'completed': True, 'production_rendering_accepted': False,
              'original_report_passed': report['passed'],
              'input': str(args.input.resolve()),
              'input_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
              'measurement': measurement,
              'verified_capture_sha256': {name: record['sha256'] for name, record in records.items()}}
    write_json(args.output, result)
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
