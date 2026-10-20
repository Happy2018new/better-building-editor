"""Generate shelf body resources for the common-palette product candidate.

No shader changes and no lighting fit are introduced.  The measured native
role map is 0=unconnected, 1=right, 2=center, 3=left while powered; unpowered
states share the unpowered front.  Runtime qualification remains separate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'behavior_pack/modern_projection'))
from projection.shelf_body import WOODS, FRONTS, DIRECTIONS, identifier
from generate_shelf_resources_r17 import ENGINE_VERSION, body_model


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='ascii', newline='\n')


def generate(project, native_data, reference_path):
    if native_data.parent.name != ENGINE_VERSION:
        raise ValueError('Shelf textures must use the declared target engine')
    reference = json.loads(reference_path.read_bytes())
    blocks_path = project/'resource_pack/blocks.json'
    terrain_path = project/'resource_pack/textures/terrain_texture.json'
    blocks, terrain = json.loads(blocks_path.read_bytes()), json.loads(terrain_path.read_bytes())
    resources, texture_sources = [], {}
    for wood in WOODS:
        texture = 'modern_projection_shelf_' + wood
        source = native_data/('resource_packs/vanilla/textures/blocks/' + wood + '_shelf.png')
        target = project/('resource_pack/textures/blocks/' + texture + '.png')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        texture_sources[wood] = hashlib.sha256(source.read_bytes()).hexdigest()
        resources.append(target.relative_to(project).as_posix())
        terrain['texture_data'][texture] = {'textures': 'textures/blocks/' + texture}
        for front in FRONTS:
            for direction in DIRECTIONS:
                name = identifier(wood, front, direction)
                stem = name.split(':', 1)[1]
                model = body_model(reference, wood, front, direction)
                model['netease:block_geometry']['description'].update(identifier=name, use_ao=True)
                model_path = project/('resource_pack/models/netease_block/' + stem + '.json')
                block_path = project/('behavior_pack/netease_blocks/' + stem + '.json')
                write_json(model_path, model)
                write_json(block_path, {'format_version': '1.10.0', 'minecraft:block': {
                    'description': {'identifier': name, 'register_to_creative_menu': False},
                    'components': {'netease:render_layer': {'value': 'alpha'},
                                   'netease:no_crop_face_block': {},
                                   'minecraft:block_light_absorption': {'value': 0}}}})
                blocks[name] = {'netease_model': name, 'sound': 'wood'}
                resources.extend((model_path.relative_to(project).as_posix(),
                                  block_path.relative_to(project).as_posix()))
    write_json(blocks_path, blocks)
    write_json(terrain_path, terrain)
    resources.extend((blocks_path.relative_to(project).as_posix(), terrain_path.relative_to(project).as_posix()))
    return {'schema_version': 1, 'engine_version': ENGINE_VERSION,
            'model_count': len(WOODS)*len(FRONTS)*len(DIRECTIONS),
            'native_ao_qualified': False, 'runtime_qualified': False,
            'reference_sha256': hashlib.sha256(reference_path.read_bytes()).hexdigest(),
            'texture_sources': texture_sources,
            'resources': {name: hashlib.sha256((project/name).read_bytes()).hexdigest()
                          for name in sorted(resources)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=ROOT)
    parser.add_argument('--native-data', type=Path, required=True)
    parser.add_argument('--reference', type=Path,
                        default=ROOT/'tools/data/shelf_body_java_1.21.9_reference.json')
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    contract = generate(args.project.resolve(), args.native_data.resolve(), args.reference.resolve())
    write_json(args.manifest, contract)
    print(json.dumps({'model_count': contract['model_count'], 'resources': len(contract['resources']),
                      'runtime_qualified': False}))


if __name__ == '__main__':
    main()
