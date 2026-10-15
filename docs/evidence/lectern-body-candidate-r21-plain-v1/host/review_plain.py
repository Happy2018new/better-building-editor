"""Verify and crop the owner-bound plain24 native lectern experiment."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


PHASES = ('world', 'body_only', 'full', 'missing', 'excluded', 'present')
VIEWS = ('south', 'north', 'east', 'west')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(report_path, output):
    report = json.loads(report_path.read_bytes())
    if any(report.get(key) is not True for key in ('completed', 'restored', 'source_unchanged')):
        raise ValueError('The native experiment must complete and restore unchanged sources')
    if report.get('cleanup_errors') or set(report['scenes']) != {'plain'}:
        raise ValueError('Expected the restored plain-only experiment')
    expected = {'plain_' + phase + '_' + view for phase in PHASES for view in VIEWS}
    if set(report['captures']) != expected:
        raise ValueError('Expected exactly 24 plain-scene captures')
    scene = report['scenes']['plain']
    source = scene['source']
    if (source.get('native_input_equal_for_empty_and_book') is not True or
            source.get('native_render_actor_empty') is not True):
        raise ValueError('Empty and book native body inputs require investigation')
    for phase in PHASES[1:]:
        row = scene[phase]
        expected_bodies = 0 if phase in ('excluded', 'present') else 2
        expected_books = int(phase in ('full', 'missing'))
        if row['target_body_count'] != expected_bodies:
            raise ValueError('Unexpected native body count: ' + phase)
        if (row['state']['book_models'] != expected_books or
                row['state']['logical_source_unchanged'] is not True):
            raise ValueError('Book ownership or logical source changed: ' + phase)
    if output.exists():
        raise ValueError('Choose a fresh review output')
    verified = {}
    image_size = None
    for view in VIEWS:
        camera = None
        verified[view] = {}
        for phase in PHASES:
            label = 'plain_' + phase + '_' + view
            capture = report['captures'][label]
            receipt = capture['receipt']
            if (receipt.get('ok') is not True or receipt.get('reliable') is not True or
                    receipt.get('agent_activation_allowed') is not False or
                    receipt.get('activation_fallback') is not False):
                raise ValueError('Unreliable or unprotected capture: ' + label)
            for key in ('owner', 'game_pid', 'game_identity'):
                if receipt[key] != report['session'][key]:
                    raise ValueError('Capture session identity differs: ' + label)
            for state in (capture['before'], capture['after']):
                if camera is None:
                    camera = state
                if state != camera:
                    raise ValueError('The fixed camera changed: ' + label)
            target = camera.get('target_screen')
            if target is None or target.get('isInScreen') is not True:
                raise ValueError('The native target is outside the viewport: ' + label)
            source_path = Path(receipt['path'])
            if not source_path.is_file():
                source_path = report_path.parent / source_path.name
            if sha(source_path) != receipt['sha256']:
                raise ValueError('Capture bytes changed: ' + label)
            with Image.open(source_path) as picture:
                if image_size is None:
                    image_size = picture.size
                if picture.size != image_size:
                    raise ValueError('Capture dimensions changed: ' + label)
                width, height = min(800, picture.width - 32), min(560, picture.height - 96)
                if min(width, height) < 200:
                    raise ValueError('Viewport is too small for an unscaled body review: ' + label)
                x = round(target['screenX'] - width / 2)
                y = round(target['screenY'] - height / 2 + 24)
                bounds = (x, y, x + width, y + height)
                if min(bounds) < 0 or bounds[2] > picture.width or bounds[3] > picture.height:
                    raise ValueError('Unscaled target crop leaves the viewport: ' + label)
                crop = picture.convert('RGB').crop(bounds)
            verified[view][phase] = dict(label=label, source=source_path, crop=crop,
                bounds=bounds, source_sha256=receipt['sha256'], camera=camera)
    output.mkdir(parents=True)
    result = dict(schema=1, source_report_sha256=sha(report_path),
        tool_sha256=sha(Path(__file__)), native_capture_size=image_size,
        product_qualified=False, pixel_acceptance_claimed=False, views={}, limits=[
            'Crops retain native pixels without alignment, scaling or recoloring.',
            'The paired bodies may overlap from east and west; inspect full source captures as needed.',
            'Book motion and lighting differ between world and custom book owners.',
            'No whole-image IoU or color mask is used as a native body acceptance criterion.',
            'This report checks acquisition and ownership; native pixel acceptance needs visual review.'])
    for view, rows in verified.items():
        width, height = rows['world']['crop'].size
        sheet = Image.new('RGB', (3 * width, 2 * (height + 24)), '#252525')
        draw = ImageDraw.Draw(sheet)
        result['views'][view] = {}
        for index, (phase, row) in enumerate(rows.items()):
            crop_path = output / (row['label'] + '.png')
            row['crop'].save(crop_path)
            x, y = index % 3 * width, index // 3 * (height + 24)
            draw.text((x + 4, y + 5), row['label'], fill='white')
            sheet.paste(row['crop'], (x, y + 24))
            result['views'][view][phase] = dict(source=str(row['source']),
                source_sha256=row['source_sha256'], crop_bounds=row['bounds'],
                crop_sha256=sha(crop_path), camera=row['camera'])
        sheet_path = output / (view + '-review.png')
        sheet.save(sheet_path)
        result['views'][view]['review_sha256'] = sha(sheet_path)
    (output / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps(dict(verified_captures=len(expected), output=str(output),
                         analysis_sha256=sha(output / 'analysis.json'))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    analyze(args.report.resolve(), args.output.resolve())
