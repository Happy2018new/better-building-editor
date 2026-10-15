"""Prepare clone-only native portal attribute/sentinel material overrides.

The control is valid only after its expected pixels are observed on a real
native block. It never qualifies the projection renderer.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

from generate_liquid_product_resources import write_json

FRAGMENT = '''// __multiversion__
precision highp float;
#define main nativePortalMain
#include "r20_portal_attribute_native.h"
#undef main
void main() {
    // NATIVE_ATTRIBUTE_BODY
}
'''
ATTRIBUTE_BODY = '''float depth=encodedPlane.w*32.0;
    if(depth>31.0) { gl_FragColor=vec4(0.,0.,0.,0.); return; }
    float stripe=mod(floor(gl_FragCoord.x/4.0),32.0);
    if(abs(floor(depth+0.5)-stripe)>0.25) discard;
    gl_FragColor=vec4(vec3(0.25)+0.75*vec3(colorLookupUV,encodedPlane.w),0.);'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(native, output, mode='attributes'):
    if mode not in ('attributes', 'solid'):
        raise ValueError('Unknown native portal diagnostic mode')
    output.mkdir(parents=True, exist_ok=False)
    shader = output / 'resource_pack/shaders/glsl'
    shader.mkdir(parents=True)
    inputs = {}
    for source, destination in (
            ('shaders/glsl/end_portal.vertex', 'r20_portal_attribute.vertex'),
            ('shaders/glsl/end_portal.fragment', 'r20_portal_attribute_native.h')):
        path = native / source
        inputs[source] = sha(path)
        (shader / destination).write_bytes(path.read_bytes())
    body = ATTRIBUTE_BODY if mode == 'attributes' else 'gl_FragColor=vec4(0.75,0.,0.75,0.);'
    (shader / 'r20_portal_attribute.fragment').write_text(
        FRAGMENT.replace('// NATIVE_ATTRIBUTE_BODY', body), encoding='ascii', newline='\n')
    material_source = native / 'resource_packs/vanilla/materials/portal.material'
    inputs[material_source.relative_to(native).as_posix()] = sha(material_source)
    material = json.loads(material_source.read_bytes())
    original = deepcopy(material['materials']['portal_base'])
    material['materials']['portal_base'].update(
        vertexShader='shaders/glsl/r20_portal_attribute.vertex',
        fragmentShader='shaders/glsl/r20_portal_attribute.fragment')
    write_json(output / 'resource_pack/materials/portal.material', material)
    for name in ('common.json', 'fancy.json', 'sad.json'):
        source = native / 'resource_packs/vanilla/materials' / name
        inputs[source.relative_to(native).as_posix()] = sha(source)
        (output / 'resource_pack/materials' / name).write_bytes(source.read_bytes())
    contract = {'schema': 1, 'mode': mode, 'diagnostic_only': True, 'pixel_acceptance': False,
                'production_qualified': False, 'native_material_original': original,
                'source_sha256': inputs,
                'requires_observed_sentinel': True,
                'limits': ['A material definition does not prove the native renderer uses it.',
                           'Native attribute values are unknown until the diagnostic pixels are decoded.',
                           'No installed game asset or production profile is modified.'],
                'output_sha256': {path.relative_to(output).as_posix(): sha(path)
                                  for path in output.rglob('*') if path.is_file()}}
    write_json(output / 'contract.json', contract)
    return contract


def install(output, project):
    if (project / '.git').exists():
        raise ValueError('Native attribute overrides may only be installed in a disposable clone')
    for source in (output / 'resource_pack').rglob('*'):
        if source.is_file():
            target = project / source.relative_to(output)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=('attributes', 'solid'), default='attributes')
    parser.add_argument('--install-clone', type=Path)
    args = parser.parse_args()
    contract = generate(args.native_data, args.output, args.mode)
    if args.install_clone:
        install(args.output, args.install_clone)
    print(json.dumps({'mode': contract['mode'], 'production_qualified': False}))


if __name__ == '__main__':
    main()
