"""Compile and link local native-adapter shaders against installed headers."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def expanded_shader(path, local, native, version, flags):
    def expand(source, stack=()):
        def include(match):
            name = match.group(1)
            if name in stack:
                raise ValueError('Cyclic shader include: ' + name)
            source_path = local / name if (local / name).is_file() else native / name
            return expand(source_path.read_text(encoding='ascii'), stack + (name,))
        return re.sub(r'^\s*#include\s+"([^"]+)".*$', include, source, flags=re.M)

    source = path.read_text(encoding='ascii')
    source = source.replace('precision highp float;', 'precision highp float;\nprecision highp int;', 1)
    prefix = '#version 300 es\n' if version == 300 else '#version 100\n'
    prefix += '#define MCPE_NETEASE\n#define MAT4 highp mat4\n#define POS4 highp vec4\n#define POS3 highp vec3\n'
    return prefix + ''.join('#define ' + flag + '\n' for flag in flags) + expand(source)


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    local = args.project / 'resource_pack/shaders/glsl'
    native = args.native_data / 'shaders/glsl'
    compiler = ROOT / '.runtime/renderdoc/portable/RenderDoc_1.46_64/plugins/spirv/glslangValidator.exe'
    rows = []
    inputs = {}
    for vertex, fragment in args.pair:
        for name in (vertex, fragment):
            inputs[name] = hashlib.sha256((local / name).read_bytes()).hexdigest()
        for version in (100, 300):
            for flags in ((), ('USE_SKINNING', 'NETEASE_SKINNING'),
                          ('USE_SKINNING', 'NETEASE_SKINNING', 'USE_INSTANCE')):
                label = '%s-%d-%s' % (Path(vertex).stem, version, '-'.join(flags) or 'plain')
                paths = []
                for name, stage in ((vertex, 'vert'), (fragment, 'frag')):
                    path = args.output / (label + '.' + stage)
                    path.write_text(expanded_shader(local / name, local, native, version, flags), encoding='ascii', newline='\n')
                    paths.append(path)
                result = subprocess.run([str(compiler), '-l'] + [str(path) for path in paths], capture_output=True, text=True)
                row = {'name': label, 'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
                       'expanded_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}
                if result.returncode and version == 100 and 'USE_SKINNING' in flags:
                    baseline = args.output / (label + '-native-baseline.vert')
                    baseline.write_text(expanded_shader(native / 'netease_skeleton.vertex', local, native, version, flags), encoding='ascii', newline='\n')
                    original = subprocess.run([str(compiler), '-S', 'vert', str(baseline)], capture_output=True, text=True)
                    baseline_output = original.stdout + original.stderr
                    pair_output = result.stdout + result.stderr
                    model_header = 'neteaseModelVertexUtil.h' in (local / vertex).read_text(encoding='ascii')
                    row.update(baseline_returncode=original.returncode, baseline_stdout=original.stdout,
                               baseline_stderr=original.stderr,
                               inherited_unsupported_mat3x4=bool(original.returncode and
                                   model_header and '.frag:' not in pair_output and
                                   'unexpected IDENTIFIER' in baseline_output and 'unexpected IDENTIFIER' in pair_output))
                rows.append(row)
    passed = all(not row['returncode'] or row.get('inherited_unsupported_mat3x4') for row in rows)
    report = {'schema': 1, 'passed': passed, 'pixel_acceptance': False, 'source_sha256': inputs,
              'compiler_sha256': hashlib.sha256(compiler.read_bytes()).hexdigest(), 'cases': rows}
    (args.output / 'compile.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii', newline='\n')
    print(json.dumps({'passed': passed, 'cases': len(rows), 'pixel_acceptance': False}))
    if not passed:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--native-data', type=Path, default=Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pair', nargs=2, action='append', default=[])
    args = parser.parse_args()
    if not args.pair:
        args.pair = [('r19_native_portal_world.vertex', 'r19_native_portal_native.fragment')]
    run(args)


if __name__ == '__main__':
    main()
