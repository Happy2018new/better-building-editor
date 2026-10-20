"""Generate a small three-axis barrier marker from a pinned native sprite."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.barrier_render import MARKER_NAME, STYLE, STYLE_VERSION, TEXTURE_KEY

SOURCE = ROOT / 'tools/data/barrier_source_r23.json'
TEXTURE_PATH = 'resource_pack/textures/blocks/modern_projection/barrier_marker.png'
REGISTRATION_PATH = 'tools/data/barrier_registration_r23.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=True, indent=2) + '\n').encode('ascii')


def uv(origin, size):
    return {'uv': origin, 'uv_size': size}


def model():
    # Explicit opposing faces preserve a readable sprite with backface culling.
    # No solid volume: three centered 12/16-block planes, each strictly in-cell.
    planes = (
        ('marker_z', [-14, 2, 8], [12, 12, 0],
         {'north': uv([0, 0], [16, 16]), 'south': uv([16, 0], [-16, 16])}),
        ('marker_x', [-8, 2, 2], [0, 12, 12],
         {'west': uv([0, 0], [16, 16]), 'east': uv([16, 0], [-16, 16])}),
        ('marker_y', [-14, 8, 2], [12, 0, 12],
         {'up': uv([0, 0], [16, 16]), 'down': uv([0, 16], [16, -16])}),
    )
    return {'format_version': '1.13.0', 'netease:block_geometry': {
        'description': {'identifier': MARKER_NAME, 'textures': [TEXTURE_KEY],
                        'item_texture': TEXTURE_KEY, 'use_ao': False},
        'bones': [{'name': name, 'pivot': [-8, 8, 8],
                   'cubes': [{'origin': origin, 'size': size, 'uv': faces}]}
                  for name, origin, size, faces in planes],
    }}


def behavior():
    return {'format_version': '1.10.0', 'minecraft:block': {
        'description': {'identifier': MARKER_NAME, 'register_to_creative_menu': False},
        'components': {'netease:render_layer': {'value': 'alpha'},
                       'netease:no_crop_face_block': {},
                       'minecraft:block_light_absorption': {'value': 0}},
    }}


def registration():
    return {
        'schema': 1, 'identifier': MARKER_NAME,
        'blocks_json': {MARKER_NAME: {'netease_model': MARKER_NAME, 'sound': 'stone'}},
        'terrain_texture_data': {TEXTURE_KEY: {
            'textures': 'textures/blocks/modern_projection/barrier_marker'}},
        'native_material': ['minecraft:barrier', 0],
        'render_only': True, 'world_identity_changed': False,
        'pixel_acceptance': False,
    }


def outputs(texture):
    return {
        'behavior_pack/netease_blocks/preview_barrier_marker.json': encoded(behavior()),
        'resource_pack/models/netease_block/preview_barrier_marker.json': encoded(model()),
        TEXTURE_PATH: texture,
        REGISTRATION_PATH: encoded(registration()),
    }


def native_sprite(native):
    blocks_path, terrain_path = native / 'blocks.json', native / 'textures/terrain_texture.json'
    blocks = json.loads(blocks_path.read_text(encoding='utf-8-sig'))
    terrain = json.loads(terrain_path.read_text(encoding='utf-8-sig'))
    key = blocks['barrier']['textures']
    relative = terrain['texture_data'][key]['textures']
    if not isinstance(key, str) or not isinstance(relative, str):
        raise ValueError('Barrier source needs one unmodified native terrain sprite')
    relative += '.png'
    path = native / relative
    image = Image.open(path)
    if image.size != (16, 16) or image.mode != 'RGBA':
        raise ValueError('Expected the reviewed 16x16 RGBA native barrier sprite')
    extrema = image.getchannel('A').getextrema()
    if extrema != (0, 255):
        raise ValueError('Barrier marker must preserve transparent and opaque native pixels')
    image.close()
    sources = {
        'blocks.json': sha(blocks_path.read_bytes()),
        'textures/terrain_texture.json': sha(terrain_path.read_bytes()),
        relative: sha(path.read_bytes()),
    }
    return path.read_bytes(), relative, sources


def capture(native, engine):
    texture, relative, sources = native_sprite(native)
    generated = outputs(texture)
    for name, data in generated.items():
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    source = {
        'schema': 1, 'style': STYLE, 'style_version': STYLE_VERSION,
        'engine_version': engine, 'resource_pack': native.name,
        'palette_version': registry.source_version(), 'palette_sha256': registry.fingerprint(),
        'native_texture_relative': relative, 'native_texture_sha256': sha(texture),
        'native_sources_sha256': sources,
        'texture_bytes': len(texture), 'texture_size': [16, 16],
        'geometry': {'planes': 3, 'explicit_faces': 6, 'size_blocks': .75,
                     'billboard': False, 'solid_cube': False, 'mesh_authority': 'authored_editor_marker'},
        'generated': {name: {'sha256': sha(data), 'bytes': len(data)}
                      for name, data in generated.items()},
        'pixel_acceptance': False, 'manual_acceptance': False,
    }
    SOURCE.write_bytes(encoded(source))
    return source


def check(native=None, registered=False):
    source = json.loads(SOURCE.read_bytes())
    if (source['schema'] != 1 or source['style'] != STYLE or
            source['style_version'] != STYLE_VERSION or
            source['palette_sha256'] != registry.fingerprint()):
        raise ValueError('Barrier source/style differs from this renderer/palette')
    texture = (ROOT / TEXTURE_PATH).read_bytes()
    if sha(texture) != source['native_texture_sha256']:
        raise ValueError('Barrier sprite differs from its pinned native source')
    expected = outputs(texture)
    if set(expected) != set(source['generated']):
        raise ValueError('Barrier generated resource set changed')
    for name, data in expected.items():
        if (ROOT / name).read_bytes() != data or source['generated'][name] != {
                'sha256': sha(data), 'bytes': len(data)}:
            raise ValueError('Stale barrier marker resource: ' + name)
    if native is not None:
        current, relative, sources = native_sprite(native)
        if (relative != source['native_texture_relative'] or
                sources != source['native_sources_sha256'] or current != texture):
            raise ValueError('Installed native barrier sources changed; review before recapture')
    if registered:
        blocks = json.loads((ROOT / 'resource_pack/blocks.json').read_bytes())
        terrain = json.loads((ROOT / 'resource_pack/textures/terrain_texture.json').read_bytes())
        fragment = registration()
        if blocks.get(MARKER_NAME) != fragment['blocks_json'][MARKER_NAME]:
            raise ValueError('Barrier model is not registered in blocks.json')
        if terrain['texture_data'].get(TEXTURE_KEY) != fragment['terrain_texture_data'][TEXTURE_KEY]:
            raise ValueError('Barrier texture is not registered in terrain_texture.json')
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-native', type=Path)
    parser.add_argument('--native-resource-root', type=Path)
    parser.add_argument('--engine-version')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--registered', action='store_true')
    args = parser.parse_args()
    if args.capture_native:
        if args.check or not args.engine_version:
            parser.error('--capture-native requires --engine-version and cannot use --check')
        capture(args.capture_native, args.engine_version)
    source = check(args.native_resource_root, args.registered)
    print(json.dumps({'checked': True, 'resources': len(source['generated']),
                      'texture_bytes': source['texture_bytes'],
                      'native_sprite_sha256': source['native_texture_sha256'],
                      'registered_checked': args.registered,
                      'pixel_acceptance': False}))


if __name__ == '__main__':
    main()
