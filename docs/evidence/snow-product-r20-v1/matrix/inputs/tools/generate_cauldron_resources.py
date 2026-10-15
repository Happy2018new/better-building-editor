"""Generate finite cauldron top models from an explicit native measurement.

Uses the liquid payload and lifetimes while owning separate artwork, shaders
and model names. The installed cauldron-water atlas is never aliased to world
water. Geometry constants must be supplied by the versioned measurement file.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image

from generate_liquid_product_resources import merge_registry, write_json
from generate_liquid_skeleton_resources import FRAGMENT, VERTEX, WORLD_BONE, UI_COORDINATES, mesh

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'modern_projection_cauldron_'
ASSET_PATH = 'modern_projection/cauldron'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vertices(inset, uv_min, uv_max, preview_header, world):
    source = VERTEX.replace('point=vec3(u,mix(mix(heights.x,heights.y,u),mix(heights.w,heights.z,u),v),v);',
        'point=vec3(mix(%s,%s,u),heights.x,mix(%s,%s,v));' %
        (repr(inset), repr(1.-inset), repr(inset), repr(1.-inset)))
    source = source.replace('liquidUv=vec2(u,v);',
        'liquidUv=mix(vec2(%s),vec2(%s),vec2(u,v));' % (repr(uv_min), repr(uv_max)))
    source = source.replace('// LIQUID_PREVIEW_HEADER', '' if world else preview_header)
    source = source.replace('// LIQUID_UI_COORDINATES', '' if world else UI_COORDINATES)
    source = source.replace('// LIQUID_WORLD_BONE', WORLD_BONE if world else '')
    return source.replace('// LIQUID_PREVIEW_DEPTH', '' if world else
        'liquidUniformPreviewDepth(vec3(-localPoint.x,-localPoint.z,-localPoint.y),EXTRA_VECTOR4.x,gl_Position,liquidClip);')


def fragment(frames, pixels, ticks, blend):
    return (FRAGMENT % {'frames': repr(float(frames)), 'pixels': repr(float(pixels)),
        'ticks': repr(float(ticks)), 'diagnostic_opacity': '-1.0',
        'pixel_coordinates': 'clamp(liquidUv*FRAME_PIXELS,0.5,FRAME_PIXELS-0.5)',
        'clock': 'TOTAL_REAL_WORLD_TIME*20.0/TICKS_PER_FRAME',
        'blend': 'fract(clock)' if blend else '0.0'}).replace(
            '#include "uniformPerFrameConstants.h"', '#include "uniformInterFrameConstants.h"').replace(
            'DIAGNOSTIC_DEFAULT_OPACITY', 'CAULDRON_SOURCE_OPACITY')


def generate(native, measurement_path, output):
    if output.exists():
        raise ValueError('Choose a fresh cauldron generation directory')
    measurement = json.loads(measurement_path.read_bytes())
    if (measurement.get('engine_version') != '3.10.0.420447' or
            measurement.get('geometry_measured') is not True):
        raise ValueError('Finite cauldron geometry requires native 3.10 measurements')
    inset = measurement['inset']
    uv_min, uv_max = measurement['uv_bounds']
    if not 0. < inset < .5 or not 0. <= uv_min < uv_max <= 1.:
        raise ValueError('Invalid measured cauldron footprint or UV region')
    native_rp = native / 'resource_packs/vanilla'
    flipbook_path = native_rp / 'textures/flipbook_textures.json'
    flipbooks = json.loads(flipbook_path.read_bytes())
    entries = dict((row['atlas_tile'], row) for row in flipbooks)
    shader_dir = output / 'resource_pack/shaders/glsl'
    shader_dir.mkdir(parents=True)
    header = ROOT / 'resource_pack/shaders/glsl/modern_projection_liquid_preview_depth.h'
    for world in (False, True):
        suffix = '_world' if world else ''
        (shader_dir / (PREFIX + 'geometry' + suffix + '.vertex')).write_text(
            vertices(inset, uv_min, uv_max, header.read_text(encoding='ascii'), world),
            encoding='ascii', newline='\n')
    skeleton = json.loads((ROOT / 'resource_pack/models/modern_projection/liquid/skeleton.json').read_bytes())
    write_json(output / ('resource_pack/models/' + ASSET_PATH + '/skeleton.json'), skeleton)
    models, materials, textures = {}, {}, {}
    for family, tile, ticks in (('water', 'cauldron_water', 2), ('plain_water', 'still_water_grey', 2),
                                ('lava', 'still_lava', 16), ('snow', 'powder_snow', 1)):
        static = family == 'snow'
        entry = {'flipbook_texture': 'textures/blocks/powder_snow'} if static else entries[tile]
        if not static and (entry.get('ticks_per_frame') != ticks or entry.get('frames') is not None):
            raise ValueError('Installed cauldron cadence changed: ' + tile)
        source = native_rp / (entry['flipbook_texture'] + '.png')
        with Image.open(source) as image:
            width, height = image.size
            expected = (16, 16) if static else (16, 512)
            if (width, height) != expected:
                raise ValueError('Installed cauldron artwork dimensions changed')
            alpha = image.convert('RGBA').getextrema()[3]
        destination = output / ('resource_pack/textures/models/' + ASSET_PATH + '/' + family + '.png')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        textures[family] = {'source': source.relative_to(native).as_posix(), 'sha256': digest(source),
                            'size': [width, height], 'alpha_range': alpha, 'frames': 1 if static else 32,
                            'ticks_per_frame': ticks, 'flipbook': entry}
        mesh_name = ASSET_PATH + '/' + family + '_mesh.json'
        write_json(output / ('resource_pack/models/' + mesh_name), mesh(ASSET_PATH + '/' + family, top_only=True))
        fragment_name = PREFIX + family + '.fragment'
        (shader_dir / fragment_name).write_text(fragment(1 if static else 32, 16, ticks,
                                                       not static and entry.get('blend_frames', True)),
                                               encoding='ascii', newline='\n')
        for world in (False, True):
            suffix = '_world' if world else ''
            name = PREFIX + family + suffix
            models[name] = {'dy_load': True, 'mesh': mesh_name, 'skeleton': ASSET_PATH + '/skeleton.json',
                            'animation': {}, 'material': name, 'texture': {'tex0': ASSET_PATH + '/' + family}}
            materials[name + ':entity_for_skeleton_alpha'] = {
                'vertexShader': 'shaders/glsl/' + PREFIX + 'geometry' + suffix + '.vertex',
                'fragmentShader': 'shaders/glsl/' + fragment_name,
                '+states': ['Blending', 'DisableDepthWrite', 'InvertCulling'],
                'blendSrc': 'SourceAlpha', 'blendDst': 'OneMinusSrcAlpha',
                'samplerStates': [{'samplerIndex': 0, 'textureFilter': 'Point'}]}
    write_json(output / 'resource_pack/models/netease_models.json', models)
    write_json(output / 'resource_pack/materials/entity.material', {'materials': dict(materials, version='1.0.0')})
    contract = {'schema_version': 1, 'payload_version': 2, 'engine_version': measurement['engine_version'],
                'measurement_sha256': digest(measurement_path), 'inset': inset, 'uv_bounds': [uv_min, uv_max],
                'textures': textures, 'models': models, 'materials': materials,
                'native_flipbook_sha256': digest(flipbook_path), 'height_quantization_error': .5 / 255.,
                'clock': 'TOTAL_REAL_WORLD_TIME', 'clock_direction': 1,
                'native_opacity': 'source_texture_alpha', 'product_acceptance_claimed': False,
                'output_sha256': {p.relative_to(output).as_posix(): digest(p)
                                  for p in sorted(output.rglob('*')) if p.is_file()}}
    write_json(output / 'contract.json', contract)
    return contract


def install(output, project):
    for relative, nested in (('resource_pack/models/netease_models.json', False),
                              ('resource_pack/materials/entity.material', True)):
        values = json.loads((output / relative).read_bytes())
        if nested:
            values = dict((k, v) for k, v in values['materials'].items() if k != 'version')
        merge_registry(project / relative, values, nested=nested)
    for source in (output / 'resource_pack').rglob('*'):
        if source.is_file() and source.name not in ('netease_models.json', 'entity.material'):
            destination = project / source.relative_to(output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    shutil.copyfile(output / 'contract.json', project / 'tools/data/cauldron_resource_contract_nemc310_v1.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-data', type=Path, required=True)
    parser.add_argument('--measurement', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--install-project', type=Path)
    args = parser.parse_args()
    generate(args.native_data, args.measurement, args.output)
    if args.install_project:
        install(args.output, args.install_project)


if __name__ == '__main__':
    main()
