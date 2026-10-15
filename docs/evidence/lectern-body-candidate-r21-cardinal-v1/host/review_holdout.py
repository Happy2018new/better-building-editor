"""Verify and crop frozen actual-cardinal40 evidence without fitting pixels."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


DIRECTIONS = {'south': 0, 'west': 1, 'north': 2, 'east': 3}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(report_path, output):
    report = json.loads(report_path.read_bytes())
    assert all(report.get(k) is True for k in ('completed', 'restored', 'source_unchanged'))
    assert not report['cleanup_errors']
    assert report['planned_captures'] == len(report['captures']) == 40
    expected_cases = {direction + '_' + case for direction in DIRECTIONS for case in ('empty', 'book')} | {'cyan'}
    assert set(report['cases']) == expected_cases
    assert not output.exists()
    groups = {}
    verified = {}
    image_size = None
    camera = None
    for label, row in report['cases'].items():
        is_cyan = label == 'cyan'
        is_book = label.endswith('_book')
        direction = None if is_cyan else label.split('_')[0]
        expected_material = ['minecraft:cyan_concrete', 0] if is_cyan else ['minecraft:lectern', DIRECTIONS[direction]]
        assert row['source']['target_material'] == expected_material
        assert row['source']['true_cardinal_direction'] == direction
        if not is_cyan:
            assert row['world']['states']['minecraft:cardinal_direction'] == direction
            assert row['world']['states']['powered_bit'] is False
            assert row['source']['native_body_input'] == [expected_material, {}]
        phases = ('world',) + (('body_only',) if is_book else ()) + ('full', 'missing', 'hidden')
        groups[label] = phases
        for phase in phases:
            capture_label = label + '_' + phase
            capture = report['captures'][capture_label]
            receipt = capture['receipt']
            assert receipt['ok'] and receipt['reliable']
            assert receipt['agent_activation_allowed'] is False
            assert receipt['activation_fallback'] is False
            assert receipt['foreground_unchanged'] is True
            assert capture['before'] == capture['after']
            if camera is None:
                camera = capture['before']
            assert capture['before'] == camera
            assert all(receipt[k] == report['session'][k] for k in ('owner', 'game_pid', 'game_identity'))
            if phase != 'world':
                state = row[phase]['state']
                assert state['logical_source_unchanged'] is True
                assert row[phase]['target_body_count'] == int(not is_cyan and phase != 'hidden')
                assert state['book_models'] == int(is_book and phase in ('full', 'missing'))
            picture_path = report_path.parent / Path(receipt['path']).name
            assert sha(picture_path) == receipt['sha256']
            target = camera['target_screen']
            assert target['isInScreen'] is True
            with Image.open(picture_path) as picture:
                if image_size is None:
                    image_size = picture.size
                assert picture.size == image_size
                width, height = 420, 420
                left, top = round(target['screenX'] - width / 2), round(target['screenY'] - height / 2 + 40)
                bounds = left, top, left + width, top + height
                assert left >= 0 and top >= 0 and bounds[2] <= picture.width and bounds[3] <= picture.height
                verified[capture_label] = {'crop': picture.convert('RGB').crop(bounds), 'bounds': bounds,
                    'source_sha256': receipt['sha256'], 'background_safe': receipt['background_safe']}
    output.mkdir(parents=True)
    result = {'schema': 1, 'source_report_sha256': sha(report_path), 'tool_sha256': sha(Path(__file__)),
        'verified_captures': len(verified), 'native_capture_size': image_size, 'camera': camera,
        'production_qualified': False, 'book_pixel_oracle_validated': False,
        'body_pixel_acceptance_automatic': False, 'groups': {}, 'limits': [
            'Crops retain native pixels without alignment, scaling, color normalization or fitting.',
            'World books are blank writable_book with server hasBook=1 and totalPages=0.',
            'Client palette actor is empty; no independent complete client book NBT was acquired.',
            'Native book oracle remains unvalidated; book image differences are not a product failure verdict.',
            'Unpowered cardinal bodies, support ownership and hidden boundaries need human visual review.']}
    for label, phases in groups.items():
        sheet = Image.new('RGB', (3 * 420, 2 * 444), '#252525')
        draw = ImageDraw.Draw(sheet)
        result['groups'][label] = {}
        for index, phase in enumerate(phases):
            capture_label = label + '_' + phase
            row = verified[capture_label]
            crop_path = output / (capture_label + '.png')
            row['crop'].save(crop_path)
            x, y = index % 3 * 420, index // 3 * 444
            draw.text((x + 4, y + 5), capture_label, fill='white')
            sheet.paste(row['crop'], (x, y + 24))
            result['groups'][label][phase] = {'crop_bounds': row['bounds'],
                'source_sha256': row['source_sha256'], 'crop_sha256': sha(crop_path),
                'background_safe': row['background_safe']}
        sheet_path = output / (label + '-review.png')
        sheet.save(sheet_path)
        result['groups'][label]['review_sha256'] = sha(sheet_path)
    (output / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'verified_captures': 40, 'groups': len(groups), 'output': str(output),
                      'analysis_sha256': sha(output / 'analysis.json')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    analyze(args.report.resolve(), args.output.resolve())
