"""Generate a clone-only bridge to the installed native End portal fragment.

No product shader, registry entry, profile or qualification is overwritten.
The world adapter keeps the native fragment and its additive blend factors.
Layer-count/color assignment remain hypotheses pending real-block comparison.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from generate_liquid_product_resources import merge_registry, write_json

PREFIX = 'r19_native_portal_'
FAMILIES = ('end_portal', 'end_gateway')
FRAGMENT = '''// __multiversion__
precision highp float;
#define main nativePortalMain
#include "r19_native_portal_original.h"
#undef main
#include "uniformExtraVectorConstants.h"
#include "uniformWorldConstants.h"
varying highp float portalVisible;
varying highp float portalClip;
void main() {
    if(portalVisible<0.5 || portalClip>0.0 || EXTRA_VECTOR4.w<=0.0) discard;
    nativePortalMain();
    float opacity=EXTRA_VECTOR4.w;
    // Native One/SourceAlpha clears once, then adds the colored star planes.
    if(encodedPlane.w*MAX_LAYER_DEPTH>MAX_LAYER_DEPTH-1.0) gl_FragColor.a=1.0-opacity;
    else gl_FragColor.rgb*=opacity;
}
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def layered_mesh(source, layers, first_layer=0):
    """Encode plane distance in unused Z, clear plane preceding star layers."""
    if not 1 <= layers <= 31 or first_layer < 0 or first_layer+layers > 32:
        raise ValueError('Star plane distances must precede the clear plane')
    result = deepcopy(source)
    for part in result['mesh']:
        vertices, indices = [], []
        for layer in (32,) + tuple(range(first_layer, first_layer+layers)):
            offset = len(vertices)
            for original in part['vertices']:
                vertex = deepcopy(original)
                vertex['pos'][2] = float(layer)
                vertices.append(vertex)
            indices.extend([[index + offset for index in triangle] for triangle in part['indices']])
        part['vertices'], part['indices'] = vertices, indices
    return result


def world_vertex(source, native_layout=False):
    """Decode our payload, then provide native fragment varyings explicitly."""
    old = '''varying highp vec2 portalUv;
varying highp float portalVisible;
varying highp float portalClip;'''
    new = old + '''
varying vec2 colorLookupUV;
varying highp vec2 parallaxUV;
varying lowp vec4 encodedPlane;
#ifdef FOG
varying vec4 fogColor;
#endif'''
    if source.count(old) != 1:
        raise ValueError('The frozen portal vertex interface changed')
    source = source.replace(old, new)
    end = '''    gl_Position=WORLDVIEWPROJ*entityPoint;
    portalClip=-1.0;'''
    replacement = '''    gl_Position=WORLDVIEWPROJ*entityPoint;
    // The native block renderer supplies these through COLOR/UV attributes.
    // Our mesh supplies the same logical fields through its decoded payload.
    float planeDistance=POSITION.z;
    vec3 planeNormal=NORMAL.xyz;
    vec3 viewRay=(WORLD*entityPoint).xyz;
    float denominator=dot(viewRay,planeNormal);
    // Only an exactly edge-on face needs a finite diagnostic guard.
    if(abs(denominator)<0.00001) denominator=denominator<0.0 ? -0.00001 : 0.00001;
    float t=dot(viewRay-planeDistance*planeNormal,planeNormal)/denominator;
    vec3 parallaxPositionInWorld=t*viewRay+VIEW_POS;
    vec3 normalMask=floor(abs(planeNormal)+vec3(0.5));
    vec2 raycastUV=parallaxPositionInWorld.yz*normalMask.x+
                   parallaxPositionInWorld.xz*normalMask.y+
                   parallaxPositionInWorld.xy*normalMask.z;
    raycastUV/=16.0;
    const float rotor=3.1415926535897*(5.0/7.0);
    float rotS=sin(planeDistance*rotor);
    float rotC=cos(planeDistance*rotor);
    parallaxUV=mat2(vec2(rotC,rotS),vec2(-rotS,rotC))*raycastUV;
    parallaxUV+=vec2(rotC,rotS)*planeDistance;
    parallaxUV.y+=TIME/256.0;
    colorLookupUV=(vec2(mod(planeDistance,4.0),mod(floor(planeDistance/4.0),4.0))+0.5)/4.0;
    encodedPlane=vec4((planeNormal+vec3(1.0))*0.5,planeDistance/32.0);
    #ifdef FOG
    fogColor=vec4(0.0);
    #endif
    if(portalVisible<0.5) gl_Position=vec4(2.0,2.0,2.0,1.0);
    portalClip=-1.0;'''
    if source.count(end) != 1:
        raise ValueError('The frozen portal world transform changed')
    if native_layout:
        # Real native attributes encode 16 planes in 8-bit COLOR, two units apart.
        replacement = replacement.replace('float planeDistance=POSITION.z;', '''float layerIndex=POSITION.z;
    float planeDistance=layerIndex>31.0 ? 32.0 : floor(layerIndex*(255.0/16.0))*(32.0/255.0);''')
        replacement = replacement.replace(
            'colorLookupUV=(vec2(mod(planeDistance,4.0),mod(floor(planeDistance/4.0),4.0))+0.5)/4.0;',
            '''float colorIndex=15.0-layerIndex;
    colorLookupUV=(vec2(mod(colorIndex,4.0),mod(floor(colorIndex/4.0),4.0))+0.5)/4.0;''')
    return source.replace(end, replacement)


def generate(project, native, output, layers, first_layer=0, native_layout=False):
    if not 1 <= layers <= 31 or first_layer < 0 or first_layer+layers > 32:
        raise ValueError('Native plane distances must precede the clear plane')
    if native_layout and (layers != 16 or first_layer != 0):
        raise ValueError('Observed native layout requires all 16 indexed planes')
    output.mkdir(parents=True, exist_ok=False)
    sources = ('shaders/glsl/end_portal.vertex', 'shaders/glsl/end_portal.fragment',
               'resource_packs/vanilla/materials/portal.material',
               'resource_packs/vanilla/textures/entity/end_portal.png')
    inputs = {name: sha(native / name) for name in sources}
    installed = json.loads((project / 'resource_pack/models/netease_models.json').read_bytes())
    current_materials = json.loads((project / 'resource_pack/materials/entity.material').read_bytes())['materials']
    vertex = world_vertex((project / 'resource_pack/shaders/glsl/modern_projection_portal_geometry_world.vertex').read_text(encoding='ascii'), native_layout)
    vertex_path = 'resource_pack/shaders/glsl/' + PREFIX + 'world.vertex'
    (output / vertex_path).parent.mkdir(parents=True, exist_ok=True)
    (output / vertex_path).write_text(vertex, encoding='ascii', newline='\n')
    native_fragment = native / 'shaders/glsl/end_portal.fragment'
    bundled_fragment = output / 'resource_pack/shaders/glsl/r19_native_portal_original.h'
    bundled_fragment.write_bytes(native_fragment.read_bytes())
    starfield_path = 'modern_projection/portal/r19_native_starfield'
    starfield = output / ('resource_pack/textures/models/' + starfield_path + '.png')
    starfield.parent.mkdir(parents=True, exist_ok=True)
    starfield.write_bytes((native / sources[-1]).read_bytes())
    fragment_path = 'resource_pack/shaders/glsl/' + PREFIX + 'native.fragment'
    (output / fragment_path).write_text(FRAGMENT, encoding='ascii', newline='\n')
    models, materials = {}, {}
    for family in FAMILIES:
        original = 'modern_projection_portal_' + family + '_world'
        model = deepcopy(installed[original])
        name = PREFIX + family + '_world'
        mesh_path = 'modern_projection/portal/' + PREFIX + family + '_mesh.json'
        source_mesh = json.loads((project / 'resource_pack/models' / model['mesh']).read_bytes())
        write_json(output / 'resource_pack/models' / mesh_path, layered_mesh(source_mesh, layers, first_layer))
        model.update(mesh=mesh_path, material=name)
        model['texture']['tex0'] = starfield_path
        models[name] = model
        material = deepcopy(current_materials[original + ':entity_for_skeleton_alpha'])
        material.update(vertexShader=vertex_path.removeprefix('resource_pack/'),
                        fragmentShader=fragment_path.removeprefix('resource_pack/'),
                        blendSrc='One', blendDst='SourceAlpha', depthFunc='LessEqual')
        materials[name + ':entity_for_skeleton_alpha'] = material
    write_json(output / 'resource_pack/models/netease_models.json', models)
    write_json(output / 'resource_pack/materials/entity.material', {'materials': dict(materials, version='1.0.0')})
    contract = {'schema': 1, 'stage': 'diagnostic_only', 'production_qualified': False,
                'native_source_sha256': inputs, 'models': models, 'materials': materials,
                'layers': layers, 'first_layer': first_layer, 'native_fragment_used_verbatim': True,
                'native_layout': native_layout,
                'layout_observation': ('portal-native-attributes-r20-v3' if native_layout else None),
                'bundled_native_fragment_sha256': sha(bundled_fragment),
                'limits': ['World only; preview clipping remains unadapted.',
                           'Native fog varying is neutral in this near-field diagnostic.',
                           'Native layout readback does not qualify model-to-native ray coordinates or appearance.',
                           'No native appearance equivalence or qualification is asserted.'],
                'output_sha256': {p.relative_to(output).as_posix(): sha(p)
                                  for p in output.rglob('*') if p.is_file()}}
    write_json(output / 'contract.json', contract)
    return contract


def install(output, project):
    for path, nested in (('resource_pack/models/netease_models.json', False),
                         ('resource_pack/materials/entity.material', True)):
        value = json.loads((output / path).read_bytes())
        if nested:
            value = {key: entry for key, entry in value['materials'].items() if key != 'version'}
        merge_registry(project / path, value, nested=nested)
    for source in (output / 'resource_pack').rglob('*'):
        if source.is_file() and source.name not in ('netease_models.json', 'entity.material'):
            target = project / source.relative_to(output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--native-data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--layers', type=int, default=16)
    parser.add_argument('--first-layer', type=int, default=0)
    parser.add_argument('--native-layout', action='store_true',
                        help='Use the observed 16 native depth bytes and reverse 4x4 color order')
    parser.add_argument('--install-clone', action='store_true')
    args = parser.parse_args()
    if args.install_clone and (args.project / '.git').exists():
        parser.error('Diagnostic aliases may only be installed in a disposable clone')
    result = generate(args.project, args.native_data, args.output, args.layers, args.first_layer, args.native_layout)
    if args.install_clone:
        install(args.output, args.project)
    print(json.dumps({'models': len(result['models']), 'layers': result['layers'],
                      'production_qualified': False}))


if __name__ == '__main__':
    main()
