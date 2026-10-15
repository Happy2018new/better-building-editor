"""Create an isolated native-actor PaperDoll depth candidate from installed sources."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from verify_biome_shader import shader_source

ROOT = Path(__file__).resolve().parents[1]
NATIVE = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data')

HELPER = '''
varying highp float nativePreviewClip;
// Terrain and native actors in one PaperDoll must share the same depth scale.
// This branch is restricted to the existing tagged orthographic editor packet.
void applyPreviewActorDepth(inout POS4 projected, POS4 localPosition) {
    PREVIEW_METRICS_ASSIGNMENT
    nativePreviewClip=-1.0;
    float tag = floor(CURRENT_COLOR.r*255.0+0.5);
    if (abs(PROJ[3][3]) > 0.5 && tag >= 209.0 && tag <= 222.0) {
        bool layoutPacket = fract(CURRENT_COLOR.r*255.0) > 0.125;
        float distance = layoutPacket ?
            (floor(CURRENT_COLOR.b*65536.0+0.5)-32768.0)/64.0 :
            (floor(CURRENT_COLOR.g*255.0+0.5)*256.0+
             floor(CURRENT_COLOR.b*255.0+0.5)-32768.0)/64.0;
        vec3 viewZ = vec3(WORLDVIEW[0][2], WORLDVIEW[1][2], WORLDVIEW[2][2]);
        float clip = ACTOR_DEPTH_EXPRESSION+distance;
        nativePreviewClip=clip;
        float centerDepth = PROJ[2][2]*(-350.0)+PROJ[3][2];
        projected.z = (centerDepth+clip*PROJ[2][2]*0.04)/(1.0+abs(centerDepth));
    }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--block-scale', type=float, default=1.)
    parser.add_argument('--depth-mode', choices=('local', 'worldview'), default='local')
    parser.add_argument('--view-origin', type=float, default=350.)
    parser.add_argument('--metrics', action='store_true')
    parser.add_argument('--generic-actor', action='store_true')
    parser.add_argument('--validate-dir', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError('Use an isolated production copy, not the repository')
    materials_path = output / 'resource_pack/materials/entity.material'
    materials = json.loads(materials_path.read_text(encoding='utf8'))
    sources = {}
    expression = ('dot(normalize(viewZ),localPosition.xyz)' if args.depth_mode == 'local' else
                  '((WORLDVIEW*localPosition).z+' + repr(args.view_origin) + ')/max(length(viewZ),0.00001)')
    helper = HELPER.replace('ACTOR_DEPTH_EXPRESSION', expression + '*' + repr(args.block_scale))
    metrics = ('nativePreviewMetrics=vec2(WORLDVIEW[3][2]+350.0,'
               'length(vec3(WORLDVIEW[0][2],WORLDVIEW[1][2],WORLDVIEW[2][2])));')
    helper = helper.replace('PREVIEW_METRICS_ASSIGNMENT', metrics if args.metrics else '')
    if args.metrics:
        helper = 'varying highp vec2 nativePreviewMetrics;\n' + helper
    actor = (ROOT / 'resource_pack/shaders/glsl/modern_projection_sign_body.vertex').read_text(encoding='utf8')
    actor = actor.replace('#include "entityVertexUtil.h"', '#include "entityVertexUtil.h"\n#include "uniformShaderConstants.h"', 1)
    actor = actor.replace('void main() {', helper + '\nvoid main() {', 1).replace(
        'gl_Position = projSpacePos;', 'applyPreviewActorDepth(projSpacePos, entitySpacePosition);\n    gl_Position = projSpacePos;', 1)
    banner_source = (NATIVE / 'shaders/glsl/banner.vertex').read_text(encoding='utf8')
    banner = banner_source.replace('#include "vertexVersionCentroid.h"', 'precision highp float;\n#include "vertexVersionCentroid.h"', 1)
    banner = banner.replace('#include "uniformWorldConstants.h"', '#include "uniformWorldConstants.h"\n#include "uniformShaderConstants.h"', 1)
    banner = banner.replace('void main()\n{', helper + '\nvoid main()\n{', 1)
    banner = banner.replace('POS4 pos = WORLDVIEWPROJ * BONES[int(BONEID_0)] * POSITION;',
                            'POS4 localPosition = BONES[int(BONEID_0)] * POSITION;\n    POS4 pos = WORLDVIEWPROJ * localPosition;')
    banner = banner.replace('POS4 pos = WORLDVIEWPROJ * BONE * POSITION;',
                            'POS4 localPosition = BONE * POSITION;\n    POS4 pos = WORLDVIEWPROJ * localPosition;')
    banner = banner.replace('POS4 pos = WORLDVIEWPROJ * POSITION;',
                            'POS4 localPosition = POSITION;\n    POS4 pos = WORLDVIEWPROJ * localPosition;')
    banner = banner.replace('gl_Position = pos;', 'applyPreviewActorDepth(pos,localPosition);\n    gl_Position = pos;', 1)
    for name, text in (('modern_projection_native_preview_actor.vertex', actor),
                       ('modern_projection_native_preview_banner.vertex', banner)):
        path = output / 'resource_pack/shaders/glsl' / name
        path.write_text(text, encoding='ascii')
        sources[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if args.generic_actor:
        materials['materials']['netease_block_as_entity_transparency']['vertexShader'] = 'shaders/glsl/modern_projection_native_preview_actor.vertex'
    else:
        original = json.loads((ROOT / 'resource_pack/materials/entity.material').read_text(encoding='utf8'))
        materials['materials']['netease_block_as_entity_transparency'] = original['materials']['netease_block_as_entity_transparency']
    materials['materials']['banner'] = {'vertexShader': 'shaders/glsl/modern_projection_native_preview_banner.vertex'}
    materials['materials']['banner_pole:banner'] = {'vertexShader': 'shaders/glsl/modern_projection_native_preview_banner.vertex'}
    fragment = (NATIVE / 'shaders/glsl/banner.fragment').read_text(encoding='utf8')
    fragment = fragment.replace('#include "fragmentVersionCentroid.h"',
                                'precision highp float;\n#include "fragmentVersionCentroid.h"\nvarying highp float nativePreviewClip;', 1)
    fragment = fragment.replace('void main()\n{', 'void main()\n{\n    if(nativePreviewClip>=0.0) discard;', 1)
    fragment_name = 'modern_projection_native_preview_banner.fragment'
    path = output / 'resource_pack/shaders/glsl' / fragment_name
    path.write_text(fragment, encoding='ascii')
    sources[fragment_name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for material in ('banner', 'banner_pole:banner'):
        materials['materials'][material]['fragmentShader'] = 'shaders/glsl/' + fragment_name
    if args.metrics:
        fragment = fragment.replace('varying highp float nativePreviewClip;',
                                    'varying highp float nativePreviewClip;\nvarying highp vec2 nativePreviewMetrics;', 1)
        fragment = fragment.replace('gl_FragColor = base;', '''float value = floor(clamp(nativePreviewMetrics.x*32.0+32768.0,0.0,65535.0)+0.5);
    gl_FragColor = vec4(floor(value/256.0)/255.0,mod(value,256.0)/255.0,1.0,1.0);''', 1)
        scale_fragment = fragment.replace('nativePreviewMetrics.x*32.0+32768.0', 'nativePreviewMetrics.y*64.0')
        for name, source in (('modern_projection_native_preview_banner_metrics.fragment', fragment),
                             ('modern_projection_native_preview_pole_metrics.fragment', scale_fragment)):
            path = output / 'resource_pack/shaders/glsl' / name
            path.write_text(source, encoding='ascii')
            sources[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        materials['materials']['banner']['fragmentShader'] = 'shaders/glsl/modern_projection_native_preview_banner_metrics.fragment'
        materials['materials']['banner_pole:banner']['fragmentShader'] = 'shaders/glsl/modern_projection_native_preview_pole_metrics.fragment'
    materials_path.write_text(json.dumps(materials, indent=2) + '\n', encoding='ascii')
    if args.validate_dir:
        args.validate_dir.mkdir(parents=True, exist_ok=False)
        compiler = ROOT / '.runtime/renderdoc/portable/RenderDoc_1.46_64/plugins/spirv/glslangValidator.exe'
        receipts = []
        for version in (100, 300):
            for name in sources:
                stage = 'frag' if name.endswith('.fragment') else 'vert'
                for skinning in (False, True):
                    flags = ('USE_SKINNING',) if skinning else ()
                    path = args.validate_dir / ('%s-%d-%s.%s' % (name, version, skinning, stage))
                    source = shader_source(output / 'resource_pack/shaders/glsl' / name,
                                           NATIVE / 'shaders/glsl', version, flags)
                    path.write_text(source, encoding='utf8')
                    result = subprocess.run([str(compiler), '-S', stage, str(path)], capture_output=True, text=True)
                    receipt = {'path': str(path), 'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
                    if result.returncode and version == 100 and skinning and stage == 'vert':
                        baseline_path = args.validate_dir / ('baseline-%s.vert' % name)
                        baseline_source = (ROOT / 'resource_pack/shaders/glsl/modern_projection_sign_body.vertex' if 'actor' in name
                                           else NATIVE / 'shaders/glsl/banner.vertex')
                        baseline_path.write_text(shader_source(baseline_source, NATIVE / 'shaders/glsl', version, flags), encoding='utf8')
                        baseline = subprocess.run([str(compiler), '-S', 'vert', str(baseline_path)], capture_output=True, text=True)
                        receipt['baseline_returncode'] = baseline.returncode
                        receipt['baseline_stdout'] = baseline.stdout
                        receipt['inherited_unsupported_mat3x4'] = bool(baseline.returncode and 'unexpected IDENTIFIER' in baseline.stdout and 'unexpected IDENTIFIER' in result.stdout)
                    receipts.append(receipt)
        (args.validate_dir / 'compile.json').write_text(json.dumps(receipts, indent=2) + '\n', encoding='ascii')
        if any(row['returncode'] and not row.get('inherited_unsupported_mat3x4') for row in receipts):
            raise ValueError('Candidate shader compile failed: ' + str(args.validate_dir / 'compile.json'))
    print(json.dumps({'candidate': str(output), 'block_scale': args.block_scale, 'depth_mode': args.depth_mode,
                      'view_origin': args.view_origin, 'metrics': args.metrics,
                      'generic_actor_override': args.generic_actor, 'shader_sha256': sources,
                      'banner_native_sha256': hashlib.sha256(banner_source.encode('utf8')).hexdigest(),
                      'production_admission': False}))


if __name__ == '__main__':
    main()
