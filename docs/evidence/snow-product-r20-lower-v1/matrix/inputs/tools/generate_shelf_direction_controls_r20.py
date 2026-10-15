"""Stage shelf-only engine-direction controls without changing product models."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

from generate_liquid_product_resources import merge_registry
from generate_shelf_resources_r17 import FRONTS, body_model, write_json


def direction_controls(reference, project):
    blocks = {}
    for front in FRONTS:
        for use_ao in (False, True):
            stem = 'preview_shelf_oak_' + front + '_directional' + ('_ao' if use_ao else '')
            identifier = 'modern_projection:' + stem
            model = body_model(reference, 'oak', front, 'north')
            geometry = model['netease:block_geometry']
            geometry['description'].update(identifier=identifier, use_ao=use_ao)
            write_json(project / ('resource_pack/models/netease_block/' + stem + '.json'), model)
            write_json(project / ('behavior_pack/netease_blocks/' + stem + '.json'), {
                'format_version': '1.10.0', 'minecraft:block': {
                    'description': {'identifier': identifier, 'register_to_creative_menu': False},
                    'components': {'netease:render_layer': {'value': 'alpha'},
                                   'netease:no_crop_face_block': {},
                                   'minecraft:block_light_absorption': {'value': 0},
                                   'netease:face_directional': {'type': 'direction'}}}})
            blocks[identifier] = {'netease_model': identifier, 'sound': 'wood'}
    merge_registry(project / 'resource_pack/blocks.json', blocks)
    return blocks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-project', type=Path, required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    args = parser.parse_args()
    args.project.mkdir(parents=True, exist_ok=False)
    for folder in ('behavior_pack', 'resource_pack'):
        shutil.copytree(args.source_project / folder, args.project / folder,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
    configuration = json.loads((args.source_project / '.mcdev.json').read_bytes())
    for family in ('mods', 'ui', 'shaders', 'materials'):
        configuration['auto_hot_reload_' + family] = False
    write_json(args.project / '.mcdev.json', configuration)
    reference = json.loads(args.reference.read_bytes())
    blocks = direction_controls(reference, args.project)
    # Preserve the earlier bone-rotation AO controls for matched comparisons.
    additions = {}
    for front in FRONTS:
        for direction in ('north', 'east', 'south', 'west'):
            stem = 'preview_shelf_oak_' + front + '_' + direction
            path = args.project / ('resource_pack/models/netease_block/' + stem + '.json')
            model = json.loads(path.read_bytes())
            identifier = 'modern_projection:' + stem + '_ao'
            model['netease:block_geometry']['description'].update(identifier=identifier, use_ao=True)
            write_json(path.with_name(stem + '_ao.json'), model)
            path = args.project / ('behavior_pack/netease_blocks/' + stem + '.json')
            block = deepcopy(json.loads(path.read_bytes()))
            block['minecraft:block']['description']['identifier'] = identifier
            write_json(path.with_name(stem + '_ao.json'), block)
            additions[identifier] = {'netease_model': identifier, 'sound': 'wood'}
    merge_registry(args.project / 'resource_pack/blocks.json', additions)
    contract = {'schema_version': 1, 'production_qualified': False,
                'control_identifiers': sorted(blocks), 'bone_ao_controls': sorted(additions),
                'reference_sha256': hashlib.sha256(args.reference.read_bytes()).hexdigest(),
                'limits': ['Engine direction mapping and lighting require native matched captures.',
                           'No runtime routing or shelf content admission.']}
    write_json(args.project / 'shelf-direction-controls.json', contract)
    print(json.dumps({'project': str(args.project), 'direction_controls': len(blocks),
                      'bone_ao_controls': len(additions), 'production_qualified': False}))


if __name__ == '__main__':
    main()
