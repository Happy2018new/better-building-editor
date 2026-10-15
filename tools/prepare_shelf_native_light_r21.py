"""Clone-only native entity light readback without changing vertex inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from generate_shelf_resources_r17 import write_json


FRAGMENT = 'resource_pack/shaders/glsl/modern_projection_shelf_native_light.fragment'
READBACK = '''float stripe = mod(floor(gl_FragCoord.x/16.0),4.0);
    vec3 observed = vec3(1.0,0.0,1.0);
    if (stripe > 0.5 && stripe < 1.5) observed = light.rgb;
    if (stripe > 1.5 && stripe < 2.5) observed = TILE_LIGHT_COLOR.rgb;
    if (stripe > 2.5) {
        observed = vec3(0.0);
        #ifdef FANCY
        observed.r = 1.0;
        #endif
        #ifdef RNGL_UNLIT
        observed.g += 1.0/7.0;
        #endif
        #ifdef RNGL_LIGHT
        observed.g += 2.0/7.0;
        #endif
        #ifdef RNGL_LOCAL_LIGHT
        observed.g += 4.0/7.0;
        #endif
        #ifdef ALWAYS_LIT
        observed.b = 1.0;
        #endif
    }
    gl_FragColor = vec4(observed,1.0);'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source, headers, project):
    if project.exists():
        raise ValueError('Choose a fresh isolated native-light project')
    native_fragment = headers/'entity.fragment'
    original = native_fragment.read_text(encoding='utf8')
    anchor = 'gl_FragColor = color;'
    if original.count(anchor) != 1:
        raise ValueError('The installed native fragment output changed')
    for folder in ('behavior_pack', 'resource_pack'):
        shutil.copytree(source/folder, project/folder,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
    configuration = json.loads((source/'.mcdev.json').read_bytes())
    for family in ('mods', 'ui', 'materials', 'shaders'):
        configuration['auto_hot_reload_'+family] = False
    write_json(project/'.mcdev.json', configuration)
    target = project/FRAGMENT
    fragment = original.replace(anchor, READBACK).replace('// __multiversion__',
        '// __multiversion__\nprecision highp float;\nprecision highp int;', 1)
    target.write_text(fragment, encoding='utf8', newline='\n')
    material_path = project/'resource_pack/materials/entity.material'
    materials = json.loads(material_path.read_bytes())
    previous = materials['materials'].get('entity_static')
    materials['materials']['entity_static'] = {
        'fragmentShader': FRAGMENT.removeprefix('resource_pack/')}
    write_json(material_path, materials)
    native_material = headers.parents[1]/'resource_packs/vanilla/materials/entity.material'
    contract = {
        'schema': 1, 'production_qualified': False,
        'vertex_shader_or_fields_changed': False,
        'fragment_precision_declared': 'highp float and int',
        'diagnostic_base_material': 'entity_static',
        'previous_override': previous,
        'native_sources': {str(path): digest(path) for path in (
            native_fragment, headers/'entity.vertex', headers/'entityVertexUtil.h',
            headers/'entityFragmentUtil.h', native_material)},
        'fragment_sha256': digest(target),
        'stripes': {'period_pixels': 64, 'width_pixels': 16,
                    '0': 'magenta_selector', '1': 'native_light_rgb',
                    '2': 'tile_light_rgb',
                    '3': 'FANCY, (RNGL_UNLIT+2*RNGL_LIGHT+4*RNGL_LOCAL_LIGHT)/7, ALWAYS_LIT'},
        'limits': ['Native alpha testing and other fragment work remain before readback.',
                   'Material selection must be established by actual magenta stripes.',
                   'These stripes affect native entities only in this private clone.',
                   'Do not infer a shelf input from a still-textured world draw.']}
    write_json(project/'shelf-native-light-contract.json', contract)
    print(json.dumps({'prepared': True, 'fragment_sha256': contract['fragment_sha256'],
                      'production_qualified': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-project', type=Path, required=True)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source_project, args.headers, args.project)
