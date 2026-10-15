"""Prepare clone-only GPU input readback for shelf and stone actor geometry."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from probe_product_water import snapshot_sources


MARKER = 19491.
VERTEX_NAME = 'shaders/glsl/modern_projection_shelf_inputs.vertex'
FRAGMENT_NAME = 'shaders/glsl/modern_projection_shelf_inputs.fragment'
MODES = {1: 'raw_normal', 2: 'entity_normal', 3: 'world_normal',
         4: 'light_rgb', 5: 'tile_light_rgb', 6: 'vertex_rgb', 7: 'flags'}

DECLARATIONS = '''
uniform highp vec4 EXTRA_ACTOR_UNIFORM4;
varying highp vec4 shelfInput;
'''
READBACK = '''
    shelfInput = vec4(1.0, 0.0, 1.0, 1.0);
    if (abs(EXTRA_ACTOR_UNIFORM4.x-19491.0) < 0.25) {
        float mode = EXTRA_ACTOR_UNIFORM4.y;
        if (mode < 1.5) shelfInput = vec4(NORMAL.xyz*0.5+0.5, 1.0);
        else if (mode < 2.5) shelfInput = vec4(normalize(entitySpaceNormal.xyz)*0.5+0.5, 1.0);
        else if (mode < 3.5) shelfInput = vec4(normalize((WORLD*entitySpaceNormal).xyz)*0.5+0.5, 1.0);
        else if (mode < 4.5) shelfInput = vec4(light.rgb, 1.0);
        else if (mode < 5.5) shelfInput = vec4(TILE_LIGHT_COLOR.rgb, 1.0);
        else if (mode < 6.5) {
            #ifdef COLOR_BASED
            shelfInput = vec4(COLOR.rgb, 1.0);
            #endif
        } else {
            // R: FANCY, G: RNGL_UNLIT/LOCAL_LIGHT/LIGHT, B: COLOR_BASED/skinning.
            vec3 flags = vec3(0.0);
            #ifdef FANCY
            flags.r = 1.0;
            #endif
            #ifdef RNGL_UNLIT
            flags.g += 1.0/7.0;
            #endif
            #ifdef RNGL_LOCAL_LIGHT
            flags.g += 2.0/7.0;
            #endif
            #ifdef RNGL_LIGHT
            flags.g += 4.0/7.0;
            #endif
            #ifdef COLOR_BASED
            flags.b += 1.0/7.0;
            #endif
            #ifdef USE_SKINNING
            flags.b += 2.0/7.0;
            #endif
            #ifdef NETEASE_SKINNING
            flags.b += 4.0/7.0;
            #endif
            shelfInput = vec4(flags, 1.0);
        }
    }
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vertex_wrapper(source):
    anchor = 'void main() {'
    end = source.rfind('}')
    if source.count(anchor) != 1 or end < 0:
        raise ValueError('Unexpected native entity vertex structure')
    source = source[:end] + READBACK + source[end:]
    return source.replace(anchor, DECLARATIONS + '\n' + anchor, 1)


def fragment_wrapper(source):
    anchor = 'void main() {'
    if source.count(anchor) != 1 or source.count('uniform highp vec4 EXTRA_ACTOR_UNIFORM4;') != 1:
        raise ValueError('Unexpected product actor fragment structure')
    return source.replace(anchor, '''varying highp vec4 shelfInput;

void main() {
    if (abs(EXTRA_ACTOR_UNIFORM4.x-19491.0) < 0.25) {
        gl_FragColor = shelfInput;
        return;
    }''', 1)


def prepare(source, output, native_root):
    before = snapshot_sources(source)
    if output.exists():
        raise ValueError('Use a fresh private shelf input clone')
    output.mkdir(parents=True)
    for name in ('behavior_pack', 'resource_pack'):
        shutil.copytree(source/name, output/name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
    shutil.copyfile(source/'.mcdev.json', output/'.mcdev.json')
    config = json.loads((output/'.mcdev.json').read_bytes())
    assert all(config.get('auto_hot_reload_'+family) is False
               for family in ('mods', 'ui', 'materials', 'shaders'))
    vertex = native_root/'shaders/glsl/entity.vertex'
    fragment = source/'resource_pack/shaders/glsl/modern_projection_native_actor.fragment'
    (output/'resource_pack'/VERTEX_NAME).write_text(
        vertex_wrapper(vertex.read_text(encoding='utf8')), encoding='utf8', newline='\n')
    (output/'resource_pack'/FRAGMENT_NAME).write_text(
        fragment_wrapper(fragment.read_text(encoding='utf8')), encoding='utf8', newline='\n')
    material_path = output/'resource_pack/materials/entity.material'
    materials = json.loads(material_path.read_bytes())
    entry = materials['materials']['netease_block_as_entity_transparency']
    entry.update(vertexShader=VERTEX_NAME, fragmentShader=FRAGMENT_NAME)
    material_path.write_text(json.dumps(materials, indent=2)+'\n', encoding='ascii', newline='\n')
    assert snapshot_sources(source) == before
    contract = {'production_qualified': False, 'source_unchanged': True,
                'native_vertex_sha256': sha(vertex), 'actor_fragment_sha256': sha(fragment),
                'marker': MARKER, 'modes': MODES,
                'scope': 'Private actor transparency material; product routing unchanged',
                'limits': ['RGB values quantized to capture bytes; no absolute HDR measurement',
                           'Missing COLOR_BASED is magenta in mode 6',
                           'Native world shelf does not use this actor diagnostic',
                           'Input readback alone cannot qualify appearance or item contents']}
    (output/'shelf-input-contract.json').write_text(
        json.dumps(contract, indent=2)+'\n', encoding='ascii', newline='\n')
    return contract


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-root', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output, args.native_root)))
