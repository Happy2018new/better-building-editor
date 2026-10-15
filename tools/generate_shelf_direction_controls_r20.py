"""Stage shelf-only engine-direction controls without changing product models."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

from generate_liquid_product_resources import merge_registry
from generate_shelf_resources_r17 import DIRECTIONS, FRONTS, body_model, write_json


def rotate_cubes_once(cubes, native_axes=False):
    """Bake a quarter turn about (-8, 8, 8), including native face UVs."""
    result = deepcopy(cubes)
    side = {'north': 'east', 'east': 'south', 'south': 'west', 'west': 'north'}
    for cube in result:
        x, y, z = cube['origin']
        width, height, depth = cube['size']
        cube['origin'] = [z - 16, y, -x - width] if native_axes else [-z - depth, y, x + 16]
        cube['size'] = [depth, height, width]
        faces = {}
        for face, record in cube['uv'].items():
            if face in ('up', 'down'):
                rotation = (record.get('rot', 0) + (90 if face == 'up' else 270)) % 360
                record.pop('rot', None)
                if rotation:
                    record['rot'] = rotation
            faces[side.get(face, face)] = record
        cube['uv'] = faces
    return result


def baked_body_model(reference, front, direction, use_ao, reverse=False, native_axes=False):
    if reverse and native_axes:
        raise ValueError('Native-axis and reverse controls are separate experiments')
    model = body_model(reference, 'oak', front, 'north')
    geometry = model['netease:block_geometry']
    suffix = '_baked_native_axes' if native_axes else ('_baked_reverse' if reverse else '_baked')
    stem = 'preview_shelf_oak_' + front + '_' + direction + suffix + ('_ao' if use_ao else '')
    geometry['description'].update(identifier='modern_projection:' + stem, use_ao=use_ao)
    bone = geometry['bones'][0]
    turns = DIRECTIONS.index(direction)
    if reverse:
        turns = -turns % 4
    for unused in range(turns):
        bone['cubes'] = rotate_cubes_once(bone['cubes'], native_axes=native_axes)
    return model


def baked_controls(reference, project, reverse=False, native_axes=False):
    blocks = {}
    for front in FRONTS:
        for direction in DIRECTIONS:
            for use_ao in (False, True):
                model = baked_body_model(reference, front, direction, use_ao, reverse, native_axes)
                identifier = model['netease:block_geometry']['description']['identifier']
                stem = identifier.split(':', 1)[1]
                write_json(project / ('resource_pack/models/netease_block/' + stem + '.json'), model)
                write_json(project / ('behavior_pack/netease_blocks/' + stem + '.json'), {
                    'format_version': '1.10.0', 'minecraft:block': {
                        'description': {'identifier': identifier, 'register_to_creative_menu': False},
                        'components': {'netease:render_layer': {'value': 'alpha'},
                                       'netease:no_crop_face_block': {},
                                       'minecraft:block_light_absorption': {'value': 0}}}})
                blocks[identifier] = {'netease_model': identifier, 'sound': 'wood'}
    merge_registry(project / 'resource_pack/blocks.json', blocks)
    return blocks


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
    parser.add_argument('--baked-rotation', action='store_true')
    parser.add_argument('--reverse-baked-rotation', action='store_true',
                        help='Add opposite-sign coordinate controls; not an SDK equivalence claim')
    parser.add_argument('--native-axis-baked-rotation', action='store_true',
                        help='Keep native face names while reversing the model X/Z transform')
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
    baked = baked_controls(reference, args.project) if args.baked_rotation else {}
    reverse = baked_controls(reference, args.project, reverse=True) if args.reverse_baked_rotation else {}
    native_axes = baked_controls(reference, args.project, native_axes=True) if args.native_axis_baked_rotation else {}
    contract = {'schema_version': 1, 'production_qualified': False,
                'control_identifiers': sorted(blocks), 'bone_ao_controls': sorted(additions),
                'baked_rotation_controls': sorted(baked),
                'reverse_baked_rotation_controls': sorted(reverse),
                'native_axis_baked_rotation_controls': sorted(native_axes),
                'baked_uv_contract': 'Native 1.13.0 rot field; up +90, down -90 per north-to-east turn.',
                'reference_sha256': hashlib.sha256(args.reference.read_bytes()).hexdigest(),
                'limits': ['Engine direction mapping and lighting require native matched captures.',
                           'No runtime routing or shelf content admission.']}
    write_json(args.project / 'shelf-direction-controls.json', contract)
    print(json.dumps({'project': str(args.project), 'direction_controls': len(blocks),
                      'bone_ao_controls': len(additions), 'baked_controls': len(baked),
                      'production_qualified': False}))


if __name__ == '__main__':
    main()
