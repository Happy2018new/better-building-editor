"""Expose the measured normal-TIME portal adapter behind a separate false gate."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

from generate_liquid_product_resources import merge_registry, write_json

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence/portal-native-appearance-r20-v1'
PREFIX = 'modern_projection_portal_native_'
ASSET = 'modern_projection/portal/native_'
SHADERS = 'resource_pack/shaders/glsl/'
FAMILIES = ('end_gateway', 'end_portal')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ui_vertex(world, original_ui):
    """Retain the established preview geometry and depth clip without ray fitting."""
    first = original_ui.index('#ifndef MODERN_PROJECTION_LIQUID_PREVIEW_DEPTH_H')
    last = original_ui.index('varying highp vec2 portalUv;', first)
    header = original_ui[first:last]
    marker = '#include "uniformExtraVectorConstants.h"\n'
    assert world.count(marker) == 1
    source = world.replace(marker, marker + header)
    first = source.index('    #if defined(USE_SKINNING) && defined(NETEASE_SKINNING)')
    last = source.index('    gl_Position=WORLDVIEWPROJ*entityPoint;', first)
    source = source[:first] + '    entityPoint=vec4(-localPoint.x,-localPoint.z+1.5,-localPoint.y,1.0);\n\n' + source[last:]
    marker = '    vec3 planeNormal=NORMAL.xyz;\n    vec3 viewRay=(WORLD*entityPoint).xyz;'
    assert source.count(marker) == 1
    source = source.replace(marker, '''    // Keep native axis-mask planes in the preview entity basis.
    vec3 planeNormal=vec3(-NORMAL.x,-NORMAL.z,-NORMAL.y);
    vec3 viewPoint=(WORLDVIEW*entityPoint).xyz;
    vec3 basisX=WORLDVIEW[0].xyz;
    vec3 basisY=WORLDVIEW[1].xyz;
    vec3 basisZ=WORLDVIEW[2].xyz;
    vec3 cofactorX=cross(basisY,basisZ);
    float basisDeterminant=dot(basisX,cofactorX);
    // Invert the linear map, retaining its view-origin translation.
    vec3 viewRay=vec3(0.0);
    if(abs(basisDeterminant)>0.000000000001) {
        viewRay=vec3(dot(cofactorX,viewPoint),
                     dot(cross(basisZ,basisX),viewPoint),
                     dot(cross(basisX,basisY),viewPoint))/basisDeterminant;
    } else portalVisible=0.0;''')
    marker = '    portalClip=-1.0;'
    assert source.count(marker) == 1
    return source.replace(marker, marker + '\n    portalUniformPreviewDepth(vec3(-localPoint.x,-localPoint.z,-localPoint.y),EXTRA_VECTOR4.x,gl_Position,portalClip);')


def generate(project, output):
    if output.exists():
        raise ValueError('Use a fresh native portal candidate directory')
    manifest = json.loads((EVIDENCE / 'manifest.json').read_bytes())
    for name, expected in manifest.items():
        assert sha(EVIDENCE / name) == expected, name
    frozen = EVIDENCE / 'frozen'
    world_path = SHADERS + 'r19_native_portal_world.vertex'
    world_bytes = (frozen / world_path).read_bytes()
    world = world_bytes.decode('ascii')
    assert 'parallaxUV.y+=TIME/256.0;' in world
    assert 'vec3 viewRay=(WORLD*entityPoint).xyz;' in world
    assert 'vec3 parallaxPositionInWorld=t*viewRay;' in world
    assert '64.0/256.0' not in world
    original_ui_path = SHADERS + 'modern_projection_portal_geometry.vertex'
    original_ui = (project / original_ui_path).read_text(encoding='ascii')
    shader_dir = output / SHADERS
    shader_dir.mkdir(parents=True)
    (shader_dir / (PREFIX + 'world.vertex')).write_bytes(world_bytes)
    (shader_dir / (PREFIX + 'ui.vertex')).write_text(ui_vertex(world, original_ui), encoding='ascii', newline='\n')
    original_header = SHADERS + 'r19_native_portal_original.h'
    (shader_dir / (PREFIX + 'original.h')).write_bytes((frozen / original_header).read_bytes())
    fragment_path = SHADERS + 'r19_native_portal_native.fragment'
    fragment = (frozen / fragment_path).read_bytes()
    fragment = fragment.replace(b'r19_native_portal_original.h', (PREFIX + 'original.h').encode('ascii'))
    (shader_dir / (PREFIX + 'surface.fragment')).write_bytes(fragment)
    registry = json.loads((frozen / 'resource_pack/models/netease_models.json').read_bytes())
    old_materials = json.loads((frozen / 'resource_pack/materials/entity.material').read_bytes())['materials']
    models, materials, copied_inputs = {}, {}, {}
    for family in FAMILIES:
        old_name = 'r19_native_portal_' + family + '_world'
        original = registry[old_name]
        mesh_relative = 'resource_pack/models/' + original['mesh']
        target_mesh = 'resource_pack/models/' + ASSET + family + '_mesh.json'
        target = output / target_mesh
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(frozen / mesh_relative, target)
        copied_inputs[mesh_relative] = sha(frozen / mesh_relative)
        for mode in ('ui', 'world'):
            name = PREFIX + family + ('_world' if mode == 'world' else '')
            model = deepcopy(original)
            model.update(material=name, mesh=target_mesh.removeprefix('resource_pack/models/'))
            model['texture']['tex0'] = ASSET + 'starfield'
            models[name] = model
            material = deepcopy(old_materials[old_name + ':entity_for_skeleton_alpha'])
            material.update(vertexShader='shaders/glsl/' + PREFIX + mode + '.vertex',
                            fragmentShader='shaders/glsl/' + PREFIX + 'surface.fragment')
            materials[name + ':entity_for_skeleton_alpha'] = material
    starfield = 'resource_pack/textures/models/modern_projection/portal/r19_native_starfield.png'
    target = output / ('resource_pack/textures/models/' + ASSET + 'starfield.png')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(frozen / starfield, target)
    copied_inputs[starfield] = sha(frozen / starfield)
    closure = json.loads((EVIDENCE / 'launch/launch-inputs.json').read_bytes())['files']
    dependencies = ('resource_pack/models/modern_projection/portal/skeleton.json',
                    'resource_pack/textures/models/modern_projection/portal/end_portal_colors.png')
    for relative in dependencies:
        assert sha(project / relative) == closure[relative], relative
    write_json(output / 'resource_pack/models/netease_models.json', models)
    write_json(output / 'resource_pack/materials/entity.material', {'materials': dict(materials, version='1.0.0')})
    contract = {'schema': 1, 'engine': '3.10.0.420447', 'stage': 'candidate_only',
                'native_product_qualified': False, 'old_default_profile_changed': False,
                'normal_time': True, 'clock': 'TIME / 256.0', 'world_vertex_verbatim': True,
                'world_vertex_source_sha256': sha(frozen / world_path),
                'native_header_verbatim': True, 'native_header_source_sha256': sha(frozen / original_header),
                'fragment_only_include_path_renamed': True,
                'ui_geometry_and_depth_source_sha256': sha(project / original_ui_path),
                'ui_plane_basis': 'preview_entity_axes_P_normal',
                'ui_ray_basis': 'inverse_WORLDVIEW_linear_times_WORLDVIEW_entity_point',
                'ui_world_identity_assumed': False,
                'world_only_fixed_time_reference': 'portal-r21-fixed-time-v11 north/front',
                'models': models, 'materials': materials, 'copied_inputs': copied_inputs,
                'unchanged_dependencies': {name: closure[name] for name in dependencies},
                'limits': ['Native UI matrix bindings and orthographic appearance have not been qualified.',
                           'Native FOG varying remains neutral; distant fog is not qualified.',
                           'Normal-TIME animation, editor/full/missing and lifecycle remain open.',
                           'The legacy PRODUCT_QUALIFIED flag does not close the reopened appearance issue.'],
                'output_sha256': {p.relative_to(output).as_posix(): sha(p)
                                  for p in output.rglob('*') if p.is_file()}}
    write_json(output / 'contract.json', contract)
    return contract


def install(output, project):
    for relative, nested in (('resource_pack/models/netease_models.json', False),
                             ('resource_pack/materials/entity.material', True)):
        values = json.loads((output / relative).read_bytes())
        if nested:
            values = {key: value for key, value in values['materials'].items() if key != 'version'}
        merge_registry(project / relative, values, nested=nested)
    for source in (output / 'resource_pack').rglob('*'):
        if source.is_file() and source.name not in ('netease_models.json', 'entity.material'):
            target = project / source.relative_to(output)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    target = project / 'tools/data/portal_native_candidate_r21.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(output / 'contract.json', target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    contract = generate(args.project, args.output)
    if args.install:
        install(args.output, args.project)
    print(json.dumps({'models': len(contract['models']), 'normal_time': True,
                      'native_product_qualified': False, 'old_default_profile_changed': False}))


if __name__ == '__main__':
    main()
