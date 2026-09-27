"""Compile the Windows RenderDragon pixel-stage pilot, without installing it.

Requires host Python 3 and lazurite 0.11.0. The native templates must be supplied
from the developer's own client; generated binaries must not be redistributed.
This is an experiment, not a supported addon material-registration mechanism.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from lazurite.material import Material
from lazurite.material.stage import ShaderStage
from lazurite.material.uniform import Uniform, UniformType
from lazurite.material.shader_pass.bgfx_shader import BgfxUniform

MATERIALS = ('Actor', 'ActorForwardPBR', 'ActorPrepass')

def compile_material(template, dxc, output, solid=False, validator=None):
    material = Material.load_bin_file(str(template))
    if material.version != 22 or material.name not in MATERIALS:
        raise ValueError('Expected a v22 Actor/PBR template from the pilot client')
    if output.resolve() == template.parent.resolve():
        raise ValueError('Build output must not overwrite installed native templates')
    output.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).with_name('staff_probe.hlsl')
    definitions = []
    if material.name != 'Actor':
        definitions += ['-D', 'MP_PBR=1']
    if material.name == 'ActorPrepass':
        definitions += ['-D', 'MP_PREPASS=1']
    if solid:
        definitions += ['-D', 'MP_SOLID_PROBE=1']
    if not any(u.name == 'Time' for u in material.uniforms):
        uniform = Uniform()
        uniform.name = 'Time'
        uniform.type = UniformType.vec4
        uniform.count = 1
        material.uniforms.append(uniform)
    programs = {}
    profiles = {'Direct3D_SM60': 'ps_6_3', 'Direct3D_SM65': 'ps_6_5'}
    count = 0
    signatures = set()
    for shader_pass in material.passes:
        if 'Depth' in shader_pass.name:
            continue
        for variant in shader_pass.variants:
            for shader in variant.shaders:
                if shader.stage != ShaderStage.Fragment or shader.platform.name not in profiles:
                    continue
                signatures.add(tuple(i.semantic.get_name() for i in shader.inputs))
                sampler = next(u for u in shader.bgfx_shader.uniforms if u.name == 's_MatTexture')
                expected_slot = {'Actor': 0, 'ActorForwardPBR': 2, 'ActorPrepass': 1}[material.name]
                if sampler.reg_index != expected_slot:
                    raise ValueError('Unexpected native texture register; inspect template before compiling')
                clock = next((u for u in shader.bgfx_shader.uniforms if u.name == 'Time'), None)
                if clock is None:
                    offset = (shader.bgfx_shader.size + 15) // 16 * 16
                    clock = BgfxUniform().load({'name': 'Time', 'type_bits': 18,
                        'count': 0, 'reg_index': offset, 'reg_count': 1})
                    shader.bgfx_shader.uniforms.append(clock)
                    shader.bgfx_shader.size = offset + 16
                if clock.reg_index % 16:
                    raise ValueError('Time is not aligned to a float4 register')
                register = clock.reg_index // 16
                key = (shader.platform.name, register)
                if key not in programs:
                    profile = profiles[shader.platform.name]
                    target = output / (material.name + '_' + profile + '_c' + str(register) + '.dxil')
                    args = [str(dxc), '-T', profile, '-validator-version', '1.6',
                            '-E', 'main', '-Fo', str(target), str(source),
                            '-D', 'MP_TIME_REGISTER=c' + str(register)] + definitions
                    subprocess.run(args, check=True)
                    if validator is not None:
                        subprocess.run([str(validator), target.name], cwd=output, check=True)
                    programs[key] = target.read_bytes()
                shader.bgfx_shader.shader_bytes = programs[key]
                # Retain original offsets and samplers; append Time when absent.
                # Keep every varying, in original order, even when unused by the PS.
                # Reducing this signature caused E_INVALIDARG in this native pipeline.
                shader.hash = int.from_bytes(hashlib.sha256(shader.bgfx_shader.shader_bytes).digest()[:8], 'little')
                count += 1
    expected = ('COLOR1', 'COLOR0', 'COLOR2', 'COLOR3', 'TEXCOORD0', 'TEXCOORD3')
    if material.name != 'Actor':
        expected = ('BITANGENT', 'COLOR1', 'COLOR0', 'NORMAL', 'TEXCOORD4', 'TANGENT', 'TEXCOORD0', 'TEXCOORD3')
    if signatures != {expected} or count == 0:
        raise ValueError('Native varying layout does not match this pilot adapter')
    target = output / (material.name + '.material.bin')
    with target.open('wb') as stream:
        material.write(stream)
    check = Material.load_bin_file(str(target))
    if check.version != 22 or check.name != material.name:
        raise ValueError('Compiled material did not round-trip')
    return {'material': material.name, 'variants': count, 'mode': 'solid' if solid else 'starfield',
            'file': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--templates', required=True, type=Path)
    parser.add_argument('--dxc', required=True, type=Path)
    parser.add_argument('--validator', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--solid', action='store_true')
    args = parser.parse_args()
    report = [compile_material(args.templates / (name + '.material.bin'),
                args.dxc.resolve(), args.output.resolve(), args.solid,
                args.validator.resolve() if args.validator else None) for name in MATERIALS]
    (args.output / 'build.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
