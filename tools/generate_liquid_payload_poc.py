"""Generate an isolated resource overlay for native liquid carrier experiments."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from liquid_payload_poc import ACTOR_TAG, PAYLOAD_TEXTURE, levels, proxy_name
from generate_shulker_proxies import behavior

ROOT = Path(__file__).resolve().parents[1]
POSE_BLOCK = 'modern_projection:liquid_payload_pose_poc'
STATIC_CONTROL = 'modern_projection:liquid_payload_static_control_poc'
ENTITY_CONTROL = 'modern_projection:liquid_payload_entity_control_poc'
NATIVE_KEYS = ('still_water_grey', 'flowing_water_grey', 'still_lava', 'flowing_lava')
VERTEX = '''
void main() {
    if (abs(EXTRA_ACTOR_UNIFORM4.x - 39683.0) > 0.25) {
        liquidPayloadFallback();
        return;
    }
    vec3 encoded = POSITION.xyz + vec3(0.5);
    vec3 carrier = floor(encoded);
    float u = step(0.5, fract(encoded.x));
    float v = step(0.5, fract(encoded.z));
    float index = mod(carrier.y, 64.0);
    float kind = floor(carrier.y / 64.0);
    vec3 cell = vec3(mod(index, 4.0), floor(index / 16.0), mod(floor(index / 4.0), 4.0));
    vec2 payloadUV = (TEXCOORD_0 - EXTRA_ACTOR_UNIFORM3.xy) / EXTRA_ACTOR_UNIFORM3.zw;
    vec2 code = floor(payloadUV * 64.0 + vec2(0.5));
    float third = code.x + code.y * 64.0;
    float denominator = EXTRA_ACTOR_UNIFORM4.y;
    vec3 point;
    vec2 sampleUV;
    if (kind < 1.5) {
        if (u < 0.5) point = vec3(0.0, third / denominator, 0.0);
        else if (v < 0.5) point = vec3(1.0, carrier.x / denominator, kind);
        else point = vec3(1.0 - kind, carrier.z / denominator, 1.0);
        sampleUV = point.xz;
    } else if (kind > 5.5) {
        point = vec3(1.0-u, 0.0, v);
        sampleUV = point.xz;
    } else {
        float height = v * mix(carrier.x, carrier.z, u) / denominator;
        if (kind < 2.5) point = vec3(u, height, 0.0);
        else if (kind < 3.5) point = vec3(1.0-u, height, 1.0);
        else if (kind < 4.5) point = vec3(0.0, height, 1.0-u);
        else point = vec3(1.0, height, u);
        sampleUV = vec2(u, 1.0-height);
    }
    liquidPayloadDecoded = cell + point;
    gl_Position = WORLDVIEWPROJ * vec4(liquidPayloadDecoded - vec3(0.5), 1.0);
    gl_PointSize = 1.0;
    if (denominator < 1.0 || kind > 6.5 || third < 0.0 || third > denominator ||
        carrier.x > denominator || carrier.z > denominator) {
        gl_Position = vec4(0.0, 0.0, 2.0, 1.0);
    }
    uv0 = EXTRA_ACTOR_UNIFORM2.xy + sampleUV * EXTRA_ACTOR_UNIFORM2.zw;
    uv1 = vec2(0.0);
    color = vec4(1.0);
    light = vec4(1.0);
    previewClip = -1.0;
    gridPosition = point.xz;
    outlineHue = 0.0;
    renderContext = vec4(0.0);
    #ifdef FOG
    fogColor = vec4(0.0);
    #endif
}
'''
FRAGMENT = '''
void main() {
    if (abs(EXTRA_ACTOR_UNIFORM4.x - 39683.0) > 0.25) {
        liquidPayloadFallback();
        return;
    }
    if (EXTRA_ACTOR_UNIFORM4.z > 0.5) {
        gl_FragColor = vec4(liquidPayloadDecoded / 4.0, 1.0);
        return;
    }
    vec4 sampleColor = texture2D(TEXTURE_0, uv0);
    gl_FragColor = sampleColor * vec4(EXTRA_ACTOR_UNIFORM1.rgb, EXTRA_ACTOR_UNIFORM4.w);
}
'''


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def model(code):
    name = proxy_name(code)
    return {'format_version': '1.13.0', 'netease:block_geometry': {
        'description': {'identifier': name, 'textures': [PAYLOAD_TEXTURE],
                        'textures_descriptions': [{'width': 64, 'length': 64}], 'use_ao': False},
        'bones': [{'name': 'payload', 'pivot': [0, 0, 0], 'cubes': [
            {'origin': [-12, 7, 4], 'size': [8, 1, 8],
             'uv': {'up': {'uv': [code % 64, code // 64], 'uv_size': [0, 0]}}}]}]}}


def wrapped_shader(path, appended, vertex=False):
    source = path.read_text(encoding='utf8')
    source, count = re.subn(r'void\s+main\s*\(\s*\)', 'void liquidPayloadFallback()', source)
    if count != 1:
        raise ValueError('The source shader must contain exactly one main: ' + str(path))
    missing = ('2', '3') if vertex else ('1',)
    declarations = ''.join('uniform highp vec4 EXTRA_ACTOR_UNIFORM' + value + ';\n' for value in missing)
    return source + '\n' + declarations + 'varying highp vec3 liquidPayloadDecoded;\n' + appended


def pose_resources():
    entity = {'format_version': '1.10.0', 'minecraft:client_entity': {'description': {
        'identifier': POSE_BLOCK, 'materials': {'default': 'entity_alphatest'},
        'textures': {'default': 'textures/blocks/liquid_payload_poc'},
        'geometry': {'default': 'geometry.modern_projection.liquid_payload_pose_poc'},
        'render_controllers': ['controller.render.modern_projection.anchor']}}}
    geometry = {'format_version': '1.12.0', 'minecraft:geometry': [{
        'description': {'identifier': 'geometry.modern_projection.liquid_payload_pose_poc',
                        'texture_width': 16, 'texture_height': 16,
                        'visible_bounds_width': 4, 'visible_bounds_height': 4},
        'bones': [{'name': 'root', 'pivot': [0, 0, 0],
                   'cubes': [{'origin': [-8, 0, -8], 'size': [16, 1, 16],
                              'uv': dict((face, {'uv': [0, 0], 'uv_size': [16, 16] if face in ('up', 'down') else [16, 1]})
                                         for face in ('north', 'south', 'east', 'west', 'up', 'down'))}]}]}]}
    block = behavior(POSE_BLOCK, 'blend')
    block['minecraft:block']['components']['netease:block_entity'] = {
        'tick': False, 'client_tick': False, 'movable': False}
    return block, entity, geometry


def source_snapshot(native):
    atlas_path = native / 'resource_packs/vanilla/textures/terrain_texture.json'
    flipbook_path = native / 'resource_packs/vanilla/textures/flipbook_textures.json'
    atlas, flipbook = json.loads(atlas_path.read_bytes()), json.loads(flipbook_path.read_bytes())
    native_entries = {key: atlas['texture_data'][key] for key in NATIVE_KEYS}
    animations = [entry for entry in flipbook if entry.get('atlas_tile') in NATIVE_KEYS]
    if {entry['atlas_tile'] for entry in animations} != set(NATIVE_KEYS):
        raise ValueError('The supplied game does not animate all four declared native liquid tiles')
    files = {str(path.relative_to(native)): digest(path.read_bytes()) for path in (atlas_path, flipbook_path)}
    return {'native_atlas_entries': native_entries, 'native_flipbook_entries': animations,
            'native_source_sha256': files, 'atlas_references_verified': True,
            'animated_sampling_accepted': False}


def generate(destination, native, height_bits=8):
    from PIL import Image

    if destination.exists():
        raise ValueError('The experiment output must be a fresh directory')
    count = levels(height_bits)
    source = source_snapshot(native)
    vertex_source = ROOT / 'resource_pack/shaders/glsl/modern_projection_biome_blocks.vertex'
    fragment_source = ROOT / 'resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment'
    blocks, files = {'format_version': [1, 1, 0]}, {}
    for code in range(count):
        identifier = proxy_name(code)
        filename = identifier.split(':')[1] + '.json'
        files['behavior_pack/netease_blocks/' + filename] = behavior(identifier, 'blend')
        files['resource_pack/models/netease_block/' + filename] = model(code)
        blocks[identifier] = {'netease_model': identifier, 'sound': 'stone'}
    block, entity, geometry = pose_resources()
    files['behavior_pack/netease_blocks/liquid_payload_pose_poc.json'] = block
    entity_behavior = json.loads((ROOT / 'behavior_pack/entities/modern_projection_anchor.json').read_bytes())
    entity_behavior['minecraft:entity']['description']['identifier'] = POSE_BLOCK
    files['behavior_pack/entities/liquid_payload_pose_poc.json'] = entity_behavior
    files['resource_pack/entity/liquid_payload_pose_poc.entity.json'] = entity
    files['resource_pack/models/entity/liquid_payload_pose_poc.geo.json'] = geometry
    static_control = model(0)
    static_description = static_control['netease:block_geometry']['description']
    static_description['identifier'] = STATIC_CONTROL
    static_control['netease:block_geometry']['bones'][0]['cubes'][0]['uv']['up']['uv_size'] = [64, 64]
    files['behavior_pack/netease_blocks/liquid_payload_static_control_poc.json'] = behavior(STATIC_CONTROL, 'blend')
    files['resource_pack/models/netease_block/liquid_payload_static_control_poc.json'] = static_control
    blocks[STATIC_CONTROL] = {'netease_model': STATIC_CONTROL, 'sound': 'stone'}
    control_entity = json.loads(json.dumps(entity))
    control_entity['minecraft:client_entity']['description']['identifier'] = ENTITY_CONTROL
    control_entity['minecraft:client_entity']['description']['geometry']['default'] = 'geometry.modern_projection.liquid_payload_entity_control_poc'
    control_geometry = json.loads(json.dumps(geometry))
    control_geometry['minecraft:geometry'][0]['description']['identifier'] = 'geometry.modern_projection.liquid_payload_entity_control_poc'
    control_geometry['minecraft:geometry'][0]['bones'][0]['cubes'][0]['size'] = [16, 16, 16]
    control_behavior = json.loads(json.dumps(entity_behavior))
    control_behavior['minecraft:entity']['description']['identifier'] = ENTITY_CONTROL
    files['behavior_pack/entities/liquid_payload_entity_control_poc.json'] = control_behavior
    files['resource_pack/entity/liquid_payload_entity_control_poc.entity.json'] = control_entity
    files['resource_pack/models/entity/liquid_payload_entity_control_poc.geo.json'] = control_geometry
    blocks[POSE_BLOCK] = {'sound': 'stone', 'client_entity': {
        'identifier': POSE_BLOCK, 'hand_model_use_client_entity': True,
        'block_icon': 'quartz_block_top'}}
    files['resource_pack/blocks.json'] = blocks
    files['resource_pack/textures/terrain_texture.json'] = {
        'resource_pack_name': 'modern_projection_liquid_payload_poc', 'texture_name': 'atlas.terrain',
        'texture_data': {PAYLOAD_TEXTURE: {'textures': 'textures/blocks/liquid_payload_poc'}}}
    material = {'vertexShader': 'shaders/glsl/liquid_payload_poc.vertex',
                'fragmentShader': 'shaders/glsl/liquid_payload_poc.fragment',
                '+states': ['DisableCulling']}
    files['resource_pack/materials/terrain.material'] = {'materials': {'version': '1.0.0'}}
    for key in ('netease_block_as_mesh_blend:netease_block_as_entity_mesh',
                'netease_block_as_mesh_blend_far:netease_block_as_mesh_blend',
                'netease_block_as_mesh_blend_no_culling:netease_block_as_mesh_blend',
                'netease_block_as_mesh_blend_enable_transparency:netease_block_as_mesh_blend'):
        files['resource_pack/materials/terrain.material']['materials'][key] = dict(material)
    for path, data in files.items():
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    shaders = destination / 'resource_pack/shaders/glsl'
    shaders.mkdir(parents=True)
    (shaders / 'liquid_payload_poc.vertex').write_text(wrapped_shader(vertex_source, VERTEX, True), encoding='ascii')
    (shaders / 'liquid_payload_poc.fragment').write_text(wrapped_shader(fragment_source, FRAGMENT), encoding='ascii')
    texture = destination / 'resource_pack/textures/blocks/liquid_payload_poc.png'
    texture.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGBA', (64, 64), (255, 255, 255, 255)).save(texture)
    report = dict(source, schema_version=1, actor_tag=ACTOR_TAG, height_bits=height_bits,
                  static_height_proxies=count, max_cells_per_batch=64, max_carriers_per_batch=448,
                  max_quantization_error_blocks=0.5 / (count - 1),
                  max_native_volume=(count, count, 448),
                  max_native_volume_indices=count * count * 448,
                  fallback_shader_sha256={'vertex': digest(vertex_source.read_bytes()),
                                          'fragment': digest(fragment_source.read_bytes())},
                  native_geometry_accepted=False, accuracy_accepted=False, production_memory_accepted=False,
                  scope='Isolated carrier and custom-actor pose experiment; no native height rule or production integration')
    report['output_sha256'] = {path.relative_to(destination).as_posix(): digest(path.read_bytes())
                               for path in sorted(destination.rglob('*')) if path.is_file()}
    (destination / 'contract.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    return report


def install_overlay(overlay, project, backup):
    """Apply only the generated experiment; preserve original tracked bytes."""
    import shutil

    if backup.exists():
        raise ValueError('The backup path must be fresh')
    patches = ('resource_pack/blocks.json', 'resource_pack/textures/terrain_texture.json',
               'resource_pack/materials/terrain.material')
    contract = json.loads((overlay / 'contract.json').read_text(encoding='ascii'))
    plans = []
    for relative, expected in contract['output_sha256'].items():
        source, target = overlay / relative, project / relative
        if digest(source.read_bytes()) != expected:
            raise ValueError('The generated overlay changed: ' + relative)
        if relative in patches:
            current = json.loads(target.read_bytes())
            patch = json.loads(source.read_bytes())
            if relative.endswith('blocks.json'):
                for key, value in patch.items():
                    if key != 'format_version':
                        if key in current:
                            raise ValueError('The experiment block already exists: ' + key)
                        current[key] = value
            elif relative.endswith('terrain_texture.json'):
                for key, value in patch['texture_data'].items():
                    if key in current['texture_data']:
                        raise ValueError('The experiment texture already exists: ' + key)
                    current['texture_data'][key] = value
            else:
                for key, value in patch['materials'].items():
                    if key == 'version':
                        continue
                    name = key.split(':')[0]
                    previous = [item for item in current['materials'] if item.split(':')[0] == name]
                    if len(previous) != 1:
                        raise ValueError('Expected one already validated native descendant: ' + name)
                    definition = current['materials'][previous[0]]
                    for field, item in value.items():
                        if field.startswith('+'):
                            definition[field] = list(dict.fromkeys(definition.get(field, []) + item))
                        else:
                            definition[field] = item
            plans.append((target, json.dumps(current, indent=2) + '\n', True))
        else:
            if target.exists():
                raise ValueError('Refusing to overwrite an existing experiment resource: ' + relative)
            plans.append((target, source.read_bytes(), False))
    backup.mkdir(parents=True)
    for target, data, changed in plans:
        if changed:
            original = backup / target.relative_to(project)
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(target, original)
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            target.write_text(data, encoding='ascii')
        else:
            target.write_bytes(data)
    report = {'schema_version': 1, 'project': str(project), 'overlay': str(overlay),
              'backup': str(backup), 'installed_sha256': {
                  target.relative_to(project).as_posix(): digest(target.read_bytes()) for target, _, _ in plans},
              'native_geometry_accepted': False, 'scope': 'Uncommitted isolated experiment resource installation'}
    (backup / 'installation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-data', type=Path, required=True)
    parser.add_argument('--height-bits', type=int, default=8, choices=(6, 8))
    parser.add_argument('--install-project', type=Path)
    parser.add_argument('--backup', type=Path)
    args = parser.parse_args()
    if bool(args.install_project) != bool(args.backup):
        parser.error('--install-project and --backup must be supplied together')
    report = generate(args.output.resolve(), args.native_data.resolve(), args.height_bits)
    if args.install_project:
        install_overlay(args.output.resolve(), args.install_project.resolve(), args.backup.resolve())
    print(json.dumps({key: report[key] for key in ('static_height_proxies', 'max_native_volume_indices',
                                                 'native_geometry_accepted', 'production_memory_accepted')}))


if __name__ == '__main__':
    main()
