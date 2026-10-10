"""Generate static skull assets from the exact installed vanilla head resource."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.static_skull import SKULL_PROXIES
from generate_shulker_proxies import behavior, netease_box_uv

SOURCE = ROOT / 'tools/data/skull_static_model_v1.json'
MOB_HEAD_SOURCES = {
    'minecraft:skeleton_skull': ('skeleton', 'textures/entity/skulls/skeleton.png'),
    'minecraft:wither_skeleton_skull': ('wither', 'textures/entity/skulls/wither_skeleton.png'),
    'minecraft:zombie_head': ('zombie', 'textures/entity/skulls/zombie.png'),
    'minecraft:creeper_head': ('creeper', 'textures/entity/skulls/creeper.png'),
}


def model(spec, material, pose):
    original = spec['geometry']['bones'][0]['cubes'][0]
    cube = deepcopy(original)
    cube['uv'] = netease_box_uv(original['uv'], original['size'])
    cube['origin'] = [-12., 0., 4.]
    pivot = [-8., 0., 8.]
    if pose.startswith('floor_'):
        rotation = [0., int(pose[6:]) * 22.5, 0.]
    else:
        facing = int(pose[5:])
        rotation = [0., {2: 0., 3: 180., 4: 270., 5: 90.}[facing], 0.]
        cube['origin'][1] += 4.
        cube['origin'][2] += 4.
        pivot[1] += 4.
    return {'format_version': '1.13.0', 'netease:block_geometry': {
        'description': {'identifier': SKULL_PROXIES[material][pose],
            'textures': ['modern_projection_static_' + material.split(':')[1]],
            'textures_descriptions': [{'width': 64, 'length': 32}], 'use_ao': True},
        'bones': [{'name': 'head', 'pivot': pivot, 'rotation': rotation, 'cubes': [cube]}]}}


def generate_source(native):
    paths = {'geometry': 'models/mobs.json', 'entity': 'entity/skull.entity.json'}
    paths.update(('texture_' + name.split(':')[1], value[1])
                 for name, value in MOB_HEAD_SOURCES.items())
    files = dict((key, native / path) for key, path in paths.items())
    entity = json.loads(files['entity'].read_text(encoding='utf8'))['minecraft:client_entity']['description']
    for name, (key, path) in MOB_HEAD_SOURCES.items():
        assert entity['geometry'][key] == 'geometry.mob_head'
        assert entity['textures'][key] == path[:-4]
    geometry = json.loads(files['geometry'].read_text(encoding='utf8'))['geometry.mob_head']
    spec = {'schema': 2, 'game_version': 'NEMC 3.9.0.401155', 'geometry': geometry,
            'paths': paths, 'sha256': dict((key, hashlib.sha256(path.read_bytes()).hexdigest())
                                         for key, path in files.items()),
            'scope': 'Vanilla mob_head closed cube; pose acceptance is separately measured against player-placed native skulls.'}
    SOURCE.write_text(json.dumps(spec, sort_keys=True, indent=2) + '\n', encoding='utf8')
    return spec


def outputs(spec):
    assert spec['schema'] == 2
    blocks_path = ROOT / 'resource_pack/blocks.json'
    atlas_path = ROOT / 'resource_pack/textures/terrain_texture.json'
    blocks = json.loads(blocks_path.read_text(encoding='utf8'))
    atlas = json.loads(atlas_path.read_text(encoding='utf8'))
    files = {}
    for material, variants in SKULL_PROXIES.items():
        texture_key = 'texture_' + material.split(':')[1]
        assert spec['paths'][texture_key] == MOB_HEAD_SOURCES[material][1]
        atlas['texture_data']['modern_projection_static_' + material.split(':')[1]] = {
            'textures': spec['paths'][texture_key][:-4]}
        for pose, identifier in variants.items():
            filename = identifier.split(':')[1] + '.json'
            files[ROOT / 'behavior_pack/netease_blocks' / filename] = behavior(identifier, 'opaque')
            files[ROOT / 'resource_pack/models/netease_block' / filename] = model(spec, material, pose)
            blocks[identifier] = {'netease_model': identifier, 'sound': 'stone'}
    files[blocks_path], files[atlas_path] = blocks, atlas
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-resource-root', type=Path)
    parser.add_argument('--refresh-source', action='store_true', help='Capture the declared named source resources')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    spec = json.loads(SOURCE.read_text(encoding='utf8')) if SOURCE.exists() else None
    if args.native_resource_root:
        if spec is None or args.refresh_source:
            spec = generate_source(args.native_resource_root)
        for key, path in spec['paths'].items():
            if hashlib.sha256((args.native_resource_root / path).read_bytes()).hexdigest() != spec['sha256'][key]:
                raise ValueError('The installed native skull source changed: ' + path)
    if spec is None:
        parser.error('Generate the versioned source using --native-resource-root')
    if args.refresh_source and not args.native_resource_root:
        parser.error('--refresh-source requires --native-resource-root')
    stale = []
    for path, data in outputs(spec).items():
        text = json.dumps(data, ensure_ascii=True, indent=2) + '\n'
        if args.check:
            if not path.exists() or path.read_text(encoding='utf8') != text:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.write_text(text, encoding='utf8')
    if stale:
        raise SystemExit('Stale skull assets: ' + ', '.join(stale))
    print('%s %d render-only mob head poses' % ('Checked' if args.check else 'Generated',
                                               sum(len(value) for value in SKULL_PROXIES.values())))


if __name__ == '__main__':
    main()
