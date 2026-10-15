"""Recompute pinned planar-alpha checks without changing a retained live report."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from verify_centered_snow_profiles import world_alpha, shape_metrics, save_mask
from verify_snow_plant_visibility import cross_assets, editor_cross_above_snow
from verify_debug_blueprints import write_json


def checked_mask(record):
    path = Path(record['path'])
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != record['sha256']:
        raise ValueError('Retained observed mask changed: '+str(path))
    with Image.open(path) as image:
        return image.convert('L')


def run(source, output, executable):
    if output.resolve() == source.resolve():
        raise ValueError('Derived alpha report cannot overwrite the live source report')
    raw = source.read_bytes()
    original = json.loads(raw)
    source_hash = hashlib.sha256(raw).hexdigest()
    derived = {'schema': 1, 'source_sha256': source_hash,
               'source_completed': original['completed'], 'source_passed': original['passed'],
               'scope': 'Deterministic dry-plant alpha reanalysis only; no new live acceptance',
               'original_failure_retained': True, 'mapping_selected_from_screenshots': False,
               'oracle_sha256': hashlib.sha256(Path(__file__).with_name('plant_alpha_geometry.py').read_bytes()).hexdigest(),
               'rows': []}
    for row in original['rows']:
        if row['kind'] != 'plant' or 'world' not in row:
            continue
        plant = row['plant']
        model, texture, assets = cross_assets({'game_executable': str(executable)}, plant)
        for field in ('model_sha256', 'texture_sha256'):
            if assets[field] != original['assets'][plant][field]:
                raise ValueError('Retained alpha source changed: '+plant+' '+field)
        expected = editor_cross_above_snow(row['editor_crop'], row['camera_state'],
                                         tuple(original['blueprint_case']['focus']), -1, model, texture)
        checks = {'editor_shape': shape_metrics(expected, checked_mask(row['editor_mask']))}
        expected_records = {'editor': save_mask(expected, output, plant+'_editor_expected')}
        for mode in ('full', 'missing'):
            world = row['world'][mode]
            width, height = world['screenshot']['size']
            crop = (width//4, height//4, width*3//4, height*3//4)
            expected = world_alpha(model, texture, world['pose'], (width, height), crop,
                                   original['target'], original['calibration'])
            checks[mode+'_shape'] = shape_metrics(expected, checked_mask(world['mask']))
            expected_records[mode] = save_mask(expected, output, plant+'_'+mode+'_expected')
        derived['rows'].append({'plant': plant, 'original_row_passed': row['passed'],
                                'original_shape_checks': {name: row['checks'][name] for name in checks},
                                'derived_shape_checks': checks, 'expected_masks': expected_records,
                                'assets': assets, 'derived_shapes_passed': all(check['passed'] for check in checks.values())})
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
        raise ValueError('Source report changed during deterministic reanalysis')
    derived['dry_shapes_passed'] = all(row['derived_shapes_passed'] for row in derived['rows'])
    write_json(output, derived)
    return derived


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--game-executable', required=True, type=Path)
    args = parser.parse_args()
    result = run(args.source, args.output, args.game_executable)
    for row in result['rows']:
        print(json.dumps({'plant': row['plant'], 'original_passed': row['original_row_passed'],
                          'derived_shapes_passed': row['derived_shapes_passed'],
                          'checks': {name: check['passed'] for name, check in row['derived_shape_checks'].items()}}))


if __name__ == '__main__':
    main()
