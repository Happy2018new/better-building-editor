"""Stage shelf-body candidates from traced models and installed native artwork.

Generated assets are isolated candidates, never product routing or qualification.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw

ENGINE_VERSION = '3.10.0.420447'
WOODS = ('acacia', 'bamboo', 'birch', 'cherry', 'crimson', 'dark_oak',
         'jungle', 'mangrove', 'oak', 'pale_oak', 'spruce', 'warped')
FRONTS = ('unpowered', 'unconnected', 'left', 'center', 'right')
DIRECTIONS = ('north', 'east', 'south', 'west')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2)+'\n', encoding='ascii', newline='\n')


def shelf_cubes(reference, front):
    body = reference['models']['body']['elements']
    if (len(body) != 3 or body[0]['from'] != [0, 0, 13] or
            body[0]['to'] != [16, 16, 16]):
        raise ValueError('Shelf reference body topology changed')
    panel = reference['models'][front]['elements']
    if (len(panel) != 1 or panel[0]['from'] != [0, 4, 13] or
            panel[0]['to'] != [16, 12, 13] or set(panel[0]['faces']) != {'north'}):
        raise ValueError('Shelf reference front topology changed')
    pieces = []
    # Split the backing so its middle front can use the selected artwork;
    # this preserves the Java surface without a zero-thickness native cube.
    for low, high in ((0, 4), (4, 12), (12, 16)):
        slab = deepcopy(body[0])
        slab['from'][1], slab['to'][1] = low, high
        faces = slab['faces']
        for face in ('east', 'south', 'west'):
            left, top, right, bottom = faces[face]['uv']
            faces[face]['uv'] = [left, top+(16-high)*(bottom-top)/16.,
                                right, top+(16-low)*(bottom-top)/16.]
        if low != 0:
            del faces['down']
        if high != 16:
            del faces['up']
        if low == 4:
            faces['north'] = deepcopy(panel[0]['faces']['north'])
        pieces.append(slab)
    pieces.extend(deepcopy(body[1:]))
    cubes = []
    for element in pieces:
        low, high = element['from'], element['to']
        uv = {}
        for face, record in element['faces'].items():
            left, top, right, bottom = record['uv']
            uv[face] = {'uv': [left*2, top*2],
                        'uv_size': [(right-left)*2, (bottom-top)*2]}
        cubes.append({'origin': [low[0]-16, low[1], low[2]],
                      'size': [high[i]-low[i] for i in range(3)], 'uv': uv})
    return cubes


def body_model(reference, wood, front, direction):
    identifier = 'modern_projection:preview_shelf_'+wood+'_'+front+'_'+direction
    texture = 'modern_projection_shelf_'+wood
    return {'format_version': '1.13.0', 'netease:block_geometry': {
        'description': {'identifier': identifier, 'textures': [texture],
                        'textures_descriptions': [{'width': 32, 'length': 32}], 'use_ao': False},
        'bones': [{'name': 'shelf_body', 'pivot': [-8, 8, 8],
                   'rotation': [0, DIRECTIONS.index(direction)*90, 0],
                   'cubes': shelf_cubes(reference, front)}]}}


def generate_body(native_data, reference_path, destination, project=None):
    if destination.exists():
        raise ValueError('Choose a fresh shelf candidate output')
    reference = json.loads(reference_path.read_bytes())
    if reference.get('schema_version') != 1 or set(reference['models']) != set(('body',)+FRONTS):
        raise ValueError('Incomplete shelf model reference')
    if native_data.parent.name != ENGINE_VERSION:
        raise ValueError('Shelf artwork must come from the declared target engine')
    blocks, textures, sources = {}, {}, {}
    for wood in WOODS:
        relative = 'resource_packs/vanilla/textures/blocks/'+wood+'_shelf.png'
        source = native_data/relative
        with Image.open(source) as picture:
            if picture.size != (32, 32):
                raise ValueError('Native shelf atlas layout changed: '+wood)
        sources[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
        texture = 'modern_projection_shelf_'+wood
        output = destination/('resource_pack/textures/blocks/'+texture+'.png')
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, output)
        textures[texture] = {'textures': 'textures/blocks/'+texture}
        for front in FRONTS:
            for direction in DIRECTIONS:
                model = body_model(reference, wood, front, direction)
                identifier = model['netease:block_geometry']['description']['identifier']
                stem = identifier.split(':', 1)[1]
                write_json(destination/('resource_pack/models/netease_block/'+stem+'.json'), model)
                write_json(destination/('behavior_pack/netease_blocks/'+stem+'.json'), {
                    'format_version': '1.10.0', 'minecraft:block': {
                        'description': {'identifier': identifier, 'register_to_creative_menu': False},
                        'components': {'netease:render_layer': {'value': 'alpha'},
                                       'netease:no_crop_face_block': {},
                                       'minecraft:block_light_absorption': {'value': 0}}}})
                blocks[identifier] = {'netease_model': identifier, 'sound': 'wood'}
    write_json(destination/'blocks.patch.json', blocks)
    write_json(destination/'terrain_texture.patch.json', textures)
    write_json(destination/'reference.json', reference)
    contract = {'schema_version': 1, 'engine_version': ENGINE_VERSION,
                'production_qualified': False, 'state_mapping_qualified': False,
                'reference_sha256': hashlib.sha256(reference_path.read_bytes()).hexdigest(),
                'native_texture_sha256': sources,
                'limits': ['Reference geometry requires matched NEMC shape, direction and texel validation.',
                           'No runtime routing, item contents or powered-state mapping is admitted.'],
                'output_sha256': {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in destination.rglob('*') if p.is_file()}}
    write_json(destination/'contract.json', contract)
    if project:
        for folder in ('behavior_pack', 'resource_pack'):
            shutil.copytree(destination/folder, project/folder, dirs_exist_ok=True)
        for relative, section, entries in (
                ('resource_pack/blocks.json', None, blocks),
                ('resource_pack/textures/terrain_texture.json', 'texture_data', textures)):
            path = project/relative
            data = json.loads(path.read_bytes())
            (data[section] if section else data).update(entries)
            write_json(path, data)
    print(json.dumps({'models': len(blocks), 'production_qualified': False,
                      'output': str(destination)}))


def inspect_atlas(native_data, destination):
    destination.mkdir(parents=True, exist_ok=False)
    rows = []
    sheet = Image.new('RGB', (640, 640), 'white')
    draw = ImageDraw.Draw(sheet)
    for index, wood in enumerate(WOODS):
        path = native_data / ('resource_packs/vanilla/textures/blocks/' + wood + '_shelf.png')
        with Image.open(path) as picture:
            if picture.size != (32, 32):
                raise ValueError('Shelf atlas dimensions changed: ' + wood)
            left, top = (index % 4) * 160, (index // 4) * 210
            sheet.paste(picture.resize((160, 160), Image.Resampling.NEAREST).convert('RGB'), (left, top + 20))
            draw.text((left + 2, top + 2), wood, fill='black')
            rows.append({'wood': wood, 'size': list(picture.size),
                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    sheet.save(destination / 'atlas-review.png')
    (destination / 'atlas-sources.json').write_text(json.dumps({
        'schema_version': 1, 'engine_version': ENGINE_VERSION,
        'shape_measurement_claimed': False, 'textures': rows}, indent=2) + '\n', encoding='ascii')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-data', type=Path, required=True)
    parser.add_argument('--inspect-atlas', type=Path)
    parser.add_argument('--stage-project', type=Path)
    parser.add_argument('--generate-body', type=Path)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--install-project', type=Path)
    args = parser.parse_args()
    if args.inspect_atlas:
        inspect_atlas(args.native_data, args.inspect_atlas)
    if args.generate_body:
        if not args.reference:
            parser.error('--generate-body requires --reference')
        generate_body(args.native_data, args.reference, args.generate_body, args.install_project)
    if args.stage_project:
        root = Path(__file__).resolve().parents[1]
        if args.stage_project.exists():
            raise ValueError('Shelf tests need a fresh isolated project')
        args.stage_project.mkdir(parents=True)
        for name in ('behavior_pack', 'resource_pack'):
            shutil.copytree(root / name, args.stage_project / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copyfile(root / '.mcdev.json', args.stage_project / '.mcdev.json')


if __name__ == '__main__':
    main()
