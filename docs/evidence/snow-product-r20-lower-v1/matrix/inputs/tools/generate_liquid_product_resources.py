"""Generate the declared water style without changing native diagnostic assets."""
import argparse
import hashlib
import json
from pathlib import Path
import pprint
import shutil

from PIL import Image

from generate_liquid_payload_poc import source_snapshot
from generate_liquid_face_textures import DEFAULT_SOURCE as FACE_SOURCE, validate as validate_faces
from generate_liquid_skeleton_resources import (FRAGMENT, VERTEX, WORLD_BONE,
    UI_COORDINATES, mesh, top_vertex)

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'modern_projection_liquid_product_'
ASSET_PATH = 'modern_projection/liquid'
PRODUCT_STYLE_VERSION = 'java_snapshot_water_v1'
RESOURCE_STYLE_VERSION = 'nemc_artwork_water_v2'
NATIVE_CULLING_STATE = 'InvertCulling'
SIDE_TEMPLATE = 'native_water_side_nw_bottom_edges_v1'
TOP_TEMPLATE = 'candidate_water_top_center_turn256_v1'
DEFAULT_OPACITY = .45
ANIMATION_RESET_SECONDS = 3600


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_digest(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def write_json(path, data, sort_keys=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=sort_keys) + '\n', encoding='ascii', newline='\n')


def shared_json(output, relative, value):
    source = ROOT / relative
    if json.loads(source.read_bytes()) != json.loads(json.dumps(value)):
        raise ValueError('Shared liquid geometry differs from the selected product layout: ' + relative)
    destination = output / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def object_spans(source, start=0):
    """Use JSON token boundaries to retain unrelated registry formatting."""
    decoder = json.JSONDecoder()
    start = source.index('{', start) + 1
    rows = {}
    while True:
        while source[start].isspace() or source[start] == ',':
            start += 1
        if source[start] == '}':
            return rows, start
        name, start = decoder.raw_decode(source, start)
        while source[start].isspace():
            start += 1
        if source[start] != ':':
            raise ValueError('Invalid resource registry member')
        start += 1
        while source[start].isspace():
            start += 1
        _, end = decoder.raw_decode(source, start)
        rows[name] = start, end
        start = end


def merge_registry(path, values, nested=False):
    with path.open(encoding='ascii', newline='') as stream:
        source = stream.read()
    newline = '\r\n' if '\r\n' in source else '\n'
    current = json.loads(source)
    offset = 0
    if nested:
        offset = object_spans(source)[0]['materials'][0]
        current = current['materials']
    spans, close = object_spans(source, offset)
    changes, added = [], {}
    for name, value in values.items():
        if name not in current:
            added[name] = value
        elif current[name] != value:
            begin, end = spans[name]
            line = source[source.rfind('\n', 0, begin) + 1:begin]
            indent = line[:len(line) - len(line.lstrip())]
            lines = json.dumps(value, indent=2).splitlines()
            replacement = newline.join([lines[0]] + [indent + item for item in lines[1:]])
            changes.append((begin, end, replacement))
    if added:
        indent = '    ' if nested else '  '
        encoded = json.dumps(added, indent=2)[2:-2]
        if nested:
            encoded = '\n'.join('  ' + line for line in encoded.splitlines())
        insertion = ',\n' + encoded + '\n' + indent[:-2]
        insertion = insertion.replace('\n', newline)
        previous_end = max(end for _, end in spans.values())
        changes.append((previous_end, close, insertion))
    for begin, end, replacement in sorted(changes, reverse=True):
        source = source[:begin] + replacement + source[end:]
    json.loads(source)
    with path.open('w', encoding='ascii', newline='') as stream:
        stream.write(source)


def animation_contract(frames, ticks):
    if type(frames) is not int or frames < 1 or type(ticks) is not int or ticks < 1:
        raise ValueError('Water animation needs positive integral frame count and cadence')
    reset_ticks = ANIMATION_RESET_SECONDS * 20
    if reset_ticks % (frames * ticks):
        raise ValueError('Water animation cycle must close at the supported engine clock reset')
    return {'clock_uniform': 'TOTAL_REAL_WORLD_TIME',
            'header': 'uniformInterFrameConstants.h', 'reset_seconds': ANIMATION_RESET_SECONDS,
            'ticks_per_second': 20, 'ticks_per_frame': ticks, 'frames': frames,
            'blend_frames': True, 'cycles_per_reset': reset_ticks // (frames * ticks),
            'engine_clock_observed': False, 'native_cadence_claimed': False}


def product_fragment(frames, pixels, ticks, coordinates, frozen=False):
    animation_contract(frames, ticks)
    source = FRAGMENT % {'frames': str(float(frames)), 'pixels': str(float(pixels)),
        'ticks': str(float(ticks)), 'diagnostic_opacity': str(DEFAULT_OPACITY),
        'pixel_coordinates': coordinates,
        'clock': '0.0' if frozen else 'TOTAL_REAL_WORLD_TIME*20.0/TICKS_PER_FRAME',
        'blend': '0.0' if frozen else 'fract(clock)'}
    return source.replace('#include "uniformPerFrameConstants.h"',
        '#include "uniformInterFrameConstants.h"').replace(
        'DIAGNOSTIC_DEFAULT_OPACITY', 'STYLE_DEFAULT_OPACITY')


def resource_profile(contract, frozen=False):
    if (contract.get('schema_version') != 1 or contract.get('payload_version') != 2
            or contract.get('product_style_version') != PRODUCT_STYLE_VERSION
            or contract.get('resource_style_version') != RESOURCE_STYLE_VERSION
            or contract.get('native_culling_state') != NATIVE_CULLING_STATE
            or contract.get('native_culling_accepted') is not False
            or contract.get('default_opacity') != DEFAULT_OPACITY
            or contract.get('native_parity_claimed') is not False
            or contract.get('game_acceptance_claimed') is not False):
        raise ValueError('Product water style contract needs regeneration')
    models = []
    capabilities = []
    for key, template in (('still_water_grey', None), ('flowing_water_grey', SIDE_TEMPLATE),
                          ('flowing_water_grey_top', TOP_TEMPLATE)):
        texture = 'flowing_water_grey' if key.endswith('_top') else key
        name = PREFIX + key + ('_frozen' if frozen else '')
        if name not in contract['models'] or name + '_world' not in contract['models']:
            raise ValueError('Product water requires separate UI/world resource models')
        models.append((texture, template, name, name + '_world'))
        capabilities.append((texture, template, tuple(range(256)) if key.endswith('_top') else (0,)))
    return {'schema_version': 2, 'payload_version': 2,
            'product_style_version': PRODUCT_STYLE_VERSION,
            'resource_style_version': RESOURCE_STYLE_VERSION,
            'game_version': contract['game_version'], 'palette_sha256': contract['palette_sha256'],
            'face_texture_rows_sha256': contract['face_texture_rows_sha256'],
            'models': tuple(models), 'uv_rotations': tuple(capabilities),
            'side_templates': {'flowing_water_grey': (SIDE_TEMPLATE, 0)},
            'top_templates': {'flowing_water_grey': TOP_TEMPLATE},
            'supported_names': ('minecraft:water', 'minecraft:flowing_water'),
            'world_scale': (16., 16., 16.), 'world_rotation': (0., 0., 0.),
            'max_groups': 256, 'default_opacity': DEFAULT_OPACITY,
            'animation_clock': 'frozen_frame_zero' if frozen else 'TOTAL_REAL_WORLD_TIME',
            'animation_reset_seconds': 3600,
            'single_sided': True, 'native_culling_state': NATIVE_CULLING_STATE,
            'native_culling_accepted': False, 'native_parity_claimed': False}


def runtime_source(contract_path):
    contract = json.loads(contract_path.read_bytes())
    return ('"""Generated product water style; game acceptance is tracked separately."""\n'
            'PRODUCT_RESOURCE_CONTRACT_SHA256 = %r\nPRODUCT_RESOURCES = %s\n'
            'FROZEN_PRODUCT_MODELS = %s\n' %
            (digest(contract_path), pprint.pformat(resource_profile(contract), width=100, sort_dicts=True),
             pprint.pformat(resource_profile(contract, frozen=True)['models'], width=100)))


def verify_contract(contract, assets, sources=ROOT, native=None):
    resource_profile(contract)
    for relative, expected in contract['project_source_sha256'].items():
        if text_digest(sources / relative) != expected:
            raise ValueError('Product water source changed: ' + relative)
    for relative, expected in contract['output_sha256'].items():
        path = assets / relative
        if relative == 'resource_pack/models/netease_models.json':
            values = json.loads(path.read_bytes())
            if any(values.get(name) != value for name, value in contract['models'].items()):
                raise ValueError('Product water model registry changed')
        elif relative == 'resource_pack/materials/entity.material':
            values = json.loads(path.read_bytes())['materials']
            if any(values.get(name) != value for name, value in contract['materials'].items() if name != 'version'):
                raise ValueError('Product water material registry changed')
        elif digest(path) != expected:
            raise ValueError('Product water resource changed: ' + relative)
    if native is not None:
        for relative, expected in contract['native_source_sha256'].items():
            if digest(native / relative) != expected:
                raise ValueError('Installed water source changed; generate a new profile: ' + relative)


def generate(output, native, face_source=FACE_SOURCE):
    if output.exists():
        raise ValueError('Choose a fresh product water resource directory')
    snapshot = source_snapshot(native)
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_bytes())
    face_textures = validate_faces(json.loads(face_source.read_bytes()), manifest)
    block_source = native / 'resource_packs/vanilla' / face_textures['native_path']
    if digest(block_source) != face_textures['native_sha256']:
        raise ValueError('Installed liquid faces differ from their versioned source table')
    header = native / 'shaders/glsl/uniformInterFrameConstants.h'
    text = header.read_text(encoding='ascii')
    if 'TOTAL_REAL_WORLD_TIME' not in text or '3600' not in text:
        raise ValueError('Installed engine no longer declares the supported hour animation clock')
    material_source = native / 'resource_packs/vanilla_netease/materials/entity.material'
    source_files = (Path(__file__), ROOT / 'tools/generate_liquid_skeleton_resources.py', face_source,
                    ROOT / 'tools/generate_liquid_face_textures.py',
                    ROOT / 'tools/generate_liquid_payload_poc.py',
                    ROOT / 'resource_pack/shaders/glsl/modern_projection_liquid_preview_depth.h')
    sources = {p.relative_to(ROOT).as_posix(): text_digest(p) for p in source_files}
    native_sources = {Path(p).as_posix(): value for p, value in snapshot['native_source_sha256'].items()}
    native_sources[header.relative_to(native).as_posix()] = digest(header)
    native_sources[material_source.relative_to(native).as_posix()] = digest(material_source)
    native_sources[block_source.relative_to(native).as_posix()] = digest(block_source)
    registry, materials, options, textures = {}, {'version': '1.0.0'}, {}, {}
    shader_dir = output / 'resource_pack/shaders/glsl'
    shader_dir.mkdir(parents=True)
    preview_header = source_files[-1].read_text(encoding='ascii')
    ui_vertex = VERTEX.replace('    // LIQUID_WORLD_BONE\n', '').replace(
        '// LIQUID_UI_COORDINATES', UI_COORDINATES).replace(
        '// LIQUID_PREVIEW_HEADER', preview_header).replace('// LIQUID_PREVIEW_DEPTH',
        'liquidUniformPreviewDepth(vec3(-localPoint.x,-localPoint.z,-localPoint.y),EXTRA_VECTOR4.x,gl_Position,liquidClip);')
    world_vertex = VERTEX.replace('// LIQUID_WORLD_BONE', WORLD_BONE).replace(
        '    // LIQUID_UI_COORDINATES\n', '')
    for suffix, source in (('', ui_vertex), ('_world', world_vertex),
                           ('_top', top_vertex(ui_vertex)), ('_top_world', top_vertex(world_vertex))):
        (shader_dir / (PREFIX + 'geometry' + suffix + '.vertex')).write_text(source, encoding='ascii', newline='\n')
    bounds = [[-2., -2., -2.], [2., 2., 2.]]
    skeleton = {'boundingbox': bounds, 'skeleton': [{'name': 'root', 'parent': 'root',
        'initpos': [0., 0., 0.], 'initquaternion': [0., 0., 0., 1.], 'initscale': [1., 1., 1.],
        'offmtx': [[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.]], 'boundingbox': bounds}]}
    shared_json(output, 'resource_pack/models/' + ASSET_PATH + '/skeleton.json', skeleton)
    animations = {row['atlas_tile']: row for row in snapshot['native_flipbook_entries']}
    for key in ('still_water_grey', 'flowing_water_grey'):
        entry = animations[key]
        if (entry.get('frames') is not None or entry.get('replicate', 1) !=
                (2 if key.startswith('flowing_') else 1)):
            raise ValueError('Installed water layout requires a new versioned sampling profile')
        source = native / 'resource_packs/vanilla' / (entry['flipbook_texture'] + '.png')
        with Image.open(source) as image:
            width, height = image.size
            if height % width or height // width != 32:
                raise ValueError('Installed water artwork requires a new versioned frame profile')
            alpha = image.convert('RGBA').getextrema()[3]
        frames = height // width
        ticks = entry.get('ticks_per_frame', 1)
        animation = animation_contract(frames, ticks)
        animation['cadence_source'] = 'installed_metadata' if 'ticks_per_frame' in entry else 'product_style_default'
        target = output / ('resource_pack/textures/models/' + ASSET_PATH + '/' + key + '.png')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        native_sources[source.relative_to(native).as_posix()] = digest(source)
        textures[key] = {'source': source.relative_to(native).as_posix(), 'sha256': digest(source),
                         'size': [width, height], 'alpha_range': alpha, 'animation': animation,
                         'flipbook': entry}
        top_choices = (False, True) if key == 'flowing_water_grey' else (False,)
        for top in top_choices:
            stem = key + ('_top' if top else '')
            name = PREFIX + stem
            coordinates = ('liquidUv*FRAME_PIXELS' if top else
                'clamp(liquidUv,0.0,1.0)*(FRAME_PIXELS*0.5-1.0)+0.5' if key.startswith('flowing_') else
                'clamp(liquidUv,0.0,1.0)*(FRAME_PIXELS-1.0)+0.5')
            mesh_name = ASSET_PATH + '/' + stem + '_mesh.json'
            shared_json(output, 'resource_pack/models/' + mesh_name, mesh(ASSET_PATH + '/' + key, top_only=top))
            for frozen in (False, True):
                variant = name + ('_frozen' if frozen else '')
                fragment_name = variant + '.fragment'
                (shader_dir / fragment_name).write_text(
                    product_fragment(frames, width, ticks, coordinates, frozen), encoding='ascii', newline='\n')
                for suffix in ('', '_world'):
                    model = variant + suffix
                    vertex_name = PREFIX + 'geometry' + ('_top' if top else '') + suffix + '.vertex'
                    registry[model] = {'dy_load': True, 'mesh': mesh_name, 'skeleton': ASSET_PATH + '/skeleton.json',
                        'animation': {}, 'material': model, 'texture': {'tex0': ASSET_PATH + '/' + key}}
                    materials[model + ':entity_for_skeleton_alpha'] = {
                        'vertexShader': 'shaders/glsl/' + vertex_name,
                        'fragmentShader': 'shaders/glsl/' + fragment_name,
                        '+states': ['Blending', 'DisableDepthWrite', NATIVE_CULLING_STATE],
                        'blendSrc': 'SourceAlpha', 'blendDst': 'OneMinusSrcAlpha',
                        '+samplerStates': [{'samplerIndex': 0, 'textureFilter': 'Point'}]}
                    options[model] = {'texture': key, 'top_only': top, 'frozen': frozen,
                        'uv_template': TOP_TEMPLATE if top else SIDE_TEMPLATE if key.startswith('flowing_') else None,
                        'vertex_shader': vertex_name, 'fragment_shader': fragment_name,
                        'pixel_coordinates': coordinates, 'preview_depth': not bool(suffix),
                        'single_sided': True, 'outward_winding': True,
                        'native_culling_state': NATIVE_CULLING_STATE}
    write_json(output / 'resource_pack/models/netease_models.json', registry)
    write_json(output / 'resource_pack/materials/entity.material', {'materials': materials})
    contract = {'schema_version': 1, 'payload_version': 2,
        'product_style_version': PRODUCT_STYLE_VERSION, 'resource_style_version': RESOURCE_STYLE_VERSION,
        'game_version': manifest['game_version'], 'palette_sha256': manifest['source_sha256'],
        'face_texture_rows_sha256': face_textures['rows_sha256'],
        'generator_sha256': digest(Path(__file__)), 'project_source_sha256': sources,
        'project_source_fingerprint': 'sha256_utf8_text_with_lf',
        'native_source_sha256': native_sources, 'textures': textures,
        'models': registry, 'materials': materials, 'model_options': options,
        'default_opacity': DEFAULT_OPACITY,
        'opacity_contract': 'Explicit biome opacity overrides the product default; projection and UI alpha multiply it',
        'draw_contract': 'Opaque scene bodies first; physical outward winding with native InvertCulling, source-alpha blend, no liquid depth writes',
        'native_culling_state': NATIVE_CULLING_STATE,
        'native_culling_accepted': False,
        'native_parity_claimed': False, 'game_acceptance_claimed': False,
        'output_sha256': {p.relative_to(output).as_posix(): digest(p) for p in sorted(output.rglob('*')) if p.is_file()}}
    write_json(output / 'contract.json', contract)
    return contract


def install(output, project):
    shared_paths = []
    for path in (output / 'resource_pack').rglob('*'):
        if path.is_file() and path.relative_to(output).as_posix() not in (
                'resource_pack/models/netease_models.json', 'resource_pack/materials/entity.material'):
            destination = project / path.relative_to(output)
            if destination.exists() and 'product_' not in path.name and destination.read_bytes() != path.read_bytes():
                raise ValueError('Product resource would modify shared diagnostic bytes: ' + str(destination))
            shared_paths.append((path, destination))
    for relative in ('resource_pack/models/netease_models.json', 'resource_pack/materials/entity.material'):
        path = project / relative
        generated = json.loads((output / relative).read_bytes())
        if relative.endswith('entity.material'):
            merge_registry(path, {k: v for k, v in generated['materials'].items() if k != 'version'}, nested=True)
        else:
            merge_registry(path, generated)
    for path, destination in shared_paths:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-data', type=Path, required=True)
    parser.add_argument('--face-textures', type=Path, default=FACE_SOURCE)
    parser.add_argument('--install-project', type=Path)
    args = parser.parse_args()
    generate(args.output, args.native_data, args.face_textures)
    if args.install_project:
        install(args.output, args.install_project)
        contract_path = args.install_project / 'tools/data/liquid_product_resource_contract_v1.json'
        shutil.copyfile(args.output / 'contract.json', contract_path)
        module = args.install_project / 'behavior_pack/modern_projection/projection/liquid_product_resource_data.py'
        module.write_text(runtime_source(contract_path), encoding='ascii', newline='\n')
    print(json.dumps({'product_style_version': PRODUCT_STYLE_VERSION,
                      'native_parity_claimed': False, 'game_acceptance_claimed': False}))


if __name__ == '__main__':
    main()
