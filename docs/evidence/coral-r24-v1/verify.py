"""Check the compact coral review bundle; this does not replay raw GPU evidence."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path)
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    manifest = json.loads((base / 'manifest.json').read_bytes())
    for row in manifest['files']:
        path = (base / row['path']).resolve()
        require(path.is_relative_to(base), 'Path outside bundle: ' + row['path'])
        require(path.stat().st_size == row['bytes'], 'Size mismatch: ' + row['path'])
        require(digest(path) == row['sha256'], 'Hash mismatch: ' + row['path'])
    read = lambda name: json.loads((base / name).read_bytes())
    delivery = read('delivery.json')
    binding = read('source-binding.json')
    ui, visual = read('ui-report.json'), read('visual-report.json')
    require(delivery['five_card_semantic_ui_passed'] is True, 'UI not completed')
    require(delivery['three_gallery_three_route_precheck_completed'] is True,
            'Gallery precheck not completed')
    for report in (ui, visual):
        for key in ('completed', 'restored', 'source_unchanged'):
            require(report[key] is True, 'Report failed: ' + key)
        require(report['source_contract_sha256'] == binding['source_contract_sha256'],
                'Source contract mismatch')
        require(report['manual_acceptance'] is False and report['issues_closed'] == 0,
                'Unexpected manual acceptance')
        require(report['native_mouse_clicked'] is False, 'Unexpected native mouse claim')
    identities = {'test.blocks.ordinary_plant_visibility', 'test.blocks.coral_plant_visibility',
                  'test.blocks.coral_blocks', 'test.blocks.coral_fans',
                  'test.layers.coral_plants'}
    require(len(ui['cases']) == 5 and {case['identity'] for case in ui['cases']} == identities,
            'Expected five unique UI cards')
    require(len(visual['cases']) == 3, 'Expected three galleries')
    require({case['identity'] for case in visual['cases']} ==
            {'test.blocks.coral_blocks', 'test.blocks.coral_fans', 'test.layers.coral_plants'},
            'Unexpected galleries')
    for case in visual['cases']:
        require(len(case['routes']) == 2 and {route['mode'] for route in case['routes']} ==
                {'projection_full', 'projection_missing'}, 'Expected full and missing')
    for prefix in ('ui', 'visual'):
        reviewed = read(prefix + '-reviewed.json')
        require(reviewed['source_report_sha256'] == digest(base / (prefix + '-report.json')),
                'Image review binding mismatch')
        require(reviewed['images_actually_viewed'] == (10 if prefix == 'ui' else 9),
                'Unexpected image count')
    require(visual['default_profile'] == {'style': 'java_snapshot_water_v1', 'present': True},
            'Unexpected default profile')
    require(visual['profile_assignment_performed'] is False, 'Candidate profile assigned')
    require(visual['product_gate_modified'] is False, 'Gate modified')
    require(delivery['all_owned_helpers_ended'] is True, 'Owned helpers remain')
    stop = read('stop.json')
    require(stop['active_minecraft_count'] == 0 and stop['force_executed'] is True,
            'Unexpected stop record')
    require(stop['game_exit'] == '0x00000001' and stop['mcdk_exit'] == '0x00000000',
            'Unexpected exit record')
    if args.project is not None:
        project = args.project.resolve(strict=True)
        for relative, expected in binding['source_sha256'].items():
            path = (project / relative).resolve()
            require(path.is_relative_to(project), 'Path outside project: ' + relative)
            require(digest(path) == expected, 'Project source changed: ' + relative)
    print(json.dumps({'bundle_integrity': True, 'files': len(manifest['files']),
                      'semantic_ui_cards': 5, 'galleries': 3, 'routes_per_gallery': 3,
                      'source_files_checked': len(binding['source_sha256']) if args.project else 0,
                      'native_mouse_clicked': False, 'manual_issues_closed': 0,
                      'raw_pixel_replay_performed': False}))


if __name__ == '__main__':
    main()
