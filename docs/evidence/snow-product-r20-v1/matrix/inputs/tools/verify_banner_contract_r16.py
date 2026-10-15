"""Freeze the measured banner shader family and compile supported variants."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from verify_biome_shader import shader_source

ROOT = Path(__file__).resolve().parents[1]
NATIVE = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data/shaders/glsl')
SHADERS = ('resource_pack/shaders/glsl/modern_projection_native_preview_banner.vertex',
           'resource_pack/shaders/glsl/modern_projection_native_preview_banner.fragment')
MEASUREMENT = 'docs/evidence/native-render-profile-r15/native-banner-depth-measurements.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contract(project):
    material = json.loads((project / 'resource_pack/materials/entity.material').read_bytes())['materials']
    return {'schema_version': 1, 'engine_version': '3.10.0.420447',
            'family': ['minecraft:standing_banner', 'minecraft:wall_banner'],
            'view_origin': 450., 'block_scale': .64, 'measurement_sha256': digest(ROOT / MEASUREMENT),
            'source_sha256': {name: digest(project/name) for name in SHADERS},
            'materials': {name: material[name] for name in ('banner', 'banner_pole:banner')},
            'native_vertex_sha256': digest(NATIVE/'banner.vertex'),
            'native_fragment_sha256': digest(NATIVE/'banner.fragment')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=ROOT)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--compile-dir', type=Path)
    args = parser.parse_args()
    data = contract(args.project)
    args.contract.parent.mkdir(parents=True, exist_ok=True)
    args.contract.write_text(json.dumps(data, sort_keys=True, indent=2)+'\n', encoding='ascii', newline='\n')
    if args.compile_dir:
        args.compile_dir.mkdir(parents=True, exist_ok=False)
        compiler = ROOT / '.runtime/renderdoc/portable/RenderDoc_1.46_64/plugins/spirv/glslangValidator.exe'
        receipts = []
        for version in (100, 300):
            for flags in ((), ('USE_SKINNING',), ('USE_SKINNING', 'LARGE_VERTEX_SHADER_UNIFORMS')):
                for relative in SHADERS:
                    stage = 'vert' if relative.endswith('.vertex') else 'frag'
                    path = args.compile_dir / ('%s-%s-%s.%s' % (Path(relative).name, version, '-'.join(flags) or 'unskinned', stage))
                    path.write_text(shader_source(args.project/relative, NATIVE, version, flags), encoding='ascii')
                    result = subprocess.run([str(compiler), '-S', stage, str(path)], capture_output=True, text=True)
                    receipt = {'name': path.name, 'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
                    if result.returncode:
                        baseline = args.compile_dir / ('baseline-' + path.name)
                        baseline.write_text(shader_source(NATIVE / ('banner.vertex' if stage == 'vert' else 'banner.fragment'),
                                                         NATIVE, version, flags), encoding='ascii')
                        original = subprocess.run([str(compiler), '-S', stage, str(baseline)], capture_output=True, text=True)
                        receipt.update(baseline_returncode=original.returncode, baseline_stdout=original.stdout,
                                       inherited_unsupported_mat3x4=bool(version == 100 and stage == 'vert' and
                                           original.returncode and 'unexpected IDENTIFIER' in original.stdout and
                                           'unexpected IDENTIFIER' in result.stdout))
                    receipts.append(receipt)
        (args.compile_dir/'compile.json').write_text(json.dumps(receipts, indent=2)+'\n', encoding='ascii')
        if any(row['returncode'] and not row.get('inherited_unsupported_mat3x4') for row in receipts):
            raise ValueError('Banner shader has a new compile failure')
    print(json.dumps({'resource_contract_sha256': digest(args.contract), 'measurement_sha256': data['measurement_sha256']}))


if __name__ == '__main__':
    main()
