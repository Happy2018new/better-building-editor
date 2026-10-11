"""Build an isolated native skeleton fixture for per-model vec4 diagnostics."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from generate_liquid_payload_poc import install_overlay

MODEL = 'modern_projection_liquid_skeleton_r9'
MATERIAL = 'modern_projection_liquid_skeleton_r9'
VERTEX = '''// __multiversion__
precision highp float;
#include "neteaseModelVertexUtil.h"
#include "uniformExtraVectorConstants.h"
varying highp vec3 liquidSkeletonDiagnostic;
void main() {
    float slot = floor((POSITION.x + 2.15) / 1.1);
    vec2 payloadCodes;
    if (slot < 0.5) payloadCodes = EXTRA_VECTOR2.xy;
    else if (slot < 1.5) payloadCodes = EXTRA_VECTOR2.zw;
    else if (slot < 2.5) payloadCodes = EXTRA_VECTOR3.xy;
    else payloadCodes = EXTRA_VECTOR3.zw;
    liquidSkeletonDiagnostic = vec3(mod(payloadCodes.x,256.0),floor(payloadCodes.x/256.0),
                                    mod(payloadCodes.y,256.0)) / 255.0;
    gl_Position = WORLDVIEWPROJ * vec4(POSITION.xyz,1.0);
    gl_PointSize = 1.0;
}
'''
FRAGMENT = '''// __multiversion__
precision highp float;
#include "fragmentVersionCentroidUV.h"
varying highp vec3 liquidSkeletonDiagnostic;
void main() { gl_FragColor = vec4(liquidSkeletonDiagnostic,1.0); }
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(output, native):
    if output.exists():
        raise ValueError('Choose a fresh fixture output')
    example = native / 'resource_packs/vanilla_netease/models/for_developer'
    sources = [example / 'mesh/ceshi_rightlegdown_mesh.json',
               example / 'skeleton/ceshi_rightlegdown_skeleton.json',
               native / 'resource_packs/vanilla_netease/models/netease_models.json',
               native / 'resource_packs/vanilla_netease/materials/entity.material',
               native / 'shaders/glsl/neteaseModelVertexUtil.h',
               native / 'shaders/glsl/uniformExtraVectorConstants.h']
    # Match installed dictionary-form mesh/skeleton fields; use only one static root.
    mesh_example = json.loads(sources[0].read_bytes())['mesh'][0]
    skeleton_example = json.loads(sources[1].read_bytes())
    if not {'material','indices','vertices'} <= set(mesh_example):
        raise ValueError('Installed mesh example has a different format')
    if not {'skeleton','boundingbox'} <= set(skeleton_example):
        raise ValueError('Installed skeleton example has a different format')
    vertices, indices = [], []
    for slot in range(4):
        offset = len(vertices)
        for x,z,u,v in ((-.4,-.4,0.,0.),(.4,-.4,1.,0.),(.4,.4,1.,1.),(-.4,.4,0.,1.)):
            vertices.append({'pos':[slot*1.1-1.65+x,0.,z], 'normal':[0.,1.,0.],
                             'uvcoord':[u,v], 'weight':[['root',1.]]})
        indices.extend([[offset,offset+1,offset+2],[offset,offset+2,offset+3]])
    bounds = [[-2.05,-.01,-.4],[2.05,.01,.4]]
    files = {
        'resource_pack/models/netease_models.json': {MODEL:{'dy_load':True,
            'mesh':'liquid_skeleton_r9/mesh.json','skeleton':'liquid_skeleton_r9/skeleton.json',
            'material':MATERIAL,'texture':{'tex0':'liquid_skeleton_r9/white'},'animation':{}}},
        'resource_pack/models/liquid_skeleton_r9/mesh.json': {'mesh':[
            {'material':'liquid_skeleton_r9/white','indices':indices,'vertices':vertices}]},
        'resource_pack/models/liquid_skeleton_r9/skeleton.json': {'boundingbox':bounds,'skeleton':[
            {'name':'root','parent':'root','initpos':[0.,0.,0.],'initquaternion':[0.,0.,0.,1.],
             'initscale':[1.,1.,1.], 'offmtx':[[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.]],
             'boundingbox':bounds}]},
        'resource_pack/materials/entity.material': {'materials':{'version':'1.0.0',
            MATERIAL+':entity_for_skeleton':{
                'vertexShader':'shaders/glsl/liquid_skeleton_r9.vertex',
                'fragmentShader':'shaders/glsl/liquid_skeleton_r9.fragment',
                '+states':['DisableCulling']}}}}
    for relative,value in files.items():
        path=output/relative
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,indent=2)+'\n',encoding='ascii')
    for extension,text in (('vertex',VERTEX),('fragment',FRAGMENT)):
        path=output/('resource_pack/shaders/glsl/liquid_skeleton_r9.'+extension)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding='ascii')
    Image.new('RGBA',(1,1),(255,255,255,255)).save(output/'resource_pack/models/liquid_skeleton_r9/white.png')
    report={'schema_version':1,'model':MODEL,'material':MATERIAL,
            'generator_sha256':digest(Path(__file__)),
            'source_sha256':{str(path.resolve()):digest(path) for path in sources},
            'output_sha256':{path.relative_to(output).as_posix():digest(path)
                             for path in sorted(output.rglob('*')) if path.is_file()},
            'scope':'Static four-plane native skeleton uniform diagnostic only',
            'editor_uniforms_accepted':False,'native_geometry_accepted':False,
            'animated_sampling_accepted':False,'production_memory_accepted':False}
    (output/'contract.json').write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--native-data',required=True,type=Path)
    parser.add_argument('--install-project',type=Path)
    parser.add_argument('--backup',type=Path)
    args=parser.parse_args()
    if bool(args.install_project)!=bool(args.backup):
        parser.error('--install-project and --backup must be supplied together')
    report=generate(args.output.resolve(),args.native_data.resolve())
    if args.install_project:
        install_overlay(args.output.resolve(),args.install_project.resolve(),args.backup.resolve())
    print(json.dumps({'files':len(report['output_sha256']),'editor_uniforms_accepted':False}))


if __name__=='__main__':
    main()
