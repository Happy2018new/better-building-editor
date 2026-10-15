"""Compile the opt-in native portal UI/world pair without changing shader inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

os.environ['OPENBLAS_NUM_THREADS'] = '1'

from verify_portal_native_adapter_r20 import expanded_shader

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'modern_projection_portal_native_'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(project, native, compiler, output):
    output.mkdir(parents=True, exist_ok=False)
    local = project / 'resource_pack/shaders/glsl'
    rows, sources = [], {}
    for route in ('ui', 'world'):
        vertex, fragment = PREFIX + route + '.vertex', PREFIX + 'surface.fragment'
        for name in (vertex, fragment, PREFIX + 'original.h'):
            sources[name] = sha(local / name)
        for version in (100, 300):
            for flags in ((), ('USE_SKINNING', 'NETEASE_SKINNING'),
                          ('USE_SKINNING', 'NETEASE_SKINNING', 'USE_INSTANCE'),
                          ('USE_SKINNING', 'NETEASE_SKINNING', 'FANCY', 'FOG')):
                label = route + '-' + str(version) + '-' + ('-'.join(flags) or 'plain')
                paths = []
                for name, stage in ((vertex, 'vert'), (fragment, 'frag')):
                    source = expanded_shader(local / name, local, native, version, flags)
                    first, rest = source.split('\n', 1)
                    source = first + '\nprecision highp float;\nprecision highp int;\n' + rest
                    path = output / (label + '.' + stage)
                    path.write_text(source, encoding='ascii', newline='\n')
                    paths.append(path)
                result = subprocess.run([str(compiler.resolve()), '-l'] + [path.name for path in paths],
                                        cwd=output, capture_output=True, text=True, encoding='utf8')
                row = {'route': route, 'version': version, 'flags': flags,
                       'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
                       'expanded_sha256': {path.name: sha(path) for path in paths}}
                if result.returncode and version == 100 and 'USE_SKINNING' in flags:
                    baseline = output / (label + '-installed-skeleton.vert')
                    baseline.write_text(expanded_shader(native / 'netease_skeleton.vertex', local,
                                                        native, version, flags), encoding='ascii', newline='\n')
                    original = subprocess.run([str(compiler.resolve()), '-S', 'vert', baseline.name],
                                              cwd=output, capture_output=True, text=True, encoding='utf8')
                    row.update(baseline_returncode=original.returncode,
                               baseline_stdout=original.stdout, baseline_stderr=original.stderr,
                               inherited_unsupported_mat3x4=bool(original.returncode and
                                   '.frag:' not in result.stdout + result.stderr and
                                   'unexpected IDENTIFIER' in original.stdout + original.stderr and
                                   'unexpected IDENTIFIER' in result.stdout + result.stderr))
                rows.append(row)
    report = {'passed': all(not row['returncode'] or row.get('inherited_unsupported_mat3x4') for row in rows),
              'source_sha256': sources, 'cases': rows, 'compiler_sha256': sha(compiler),
              'default_precision_is_compile_harness_only': True,
              'runtime_variant_or_uniform_observation': False, 'qualification': False}
    (output / 'compile.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii', newline='\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=ROOT)
    parser.add_argument('--native-shaders', type=Path, required=True)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.project, args.native_shaders, args.compiler, args.output)
    print(json.dumps({'passed': result['passed'], 'cases': len(result['cases']),
                      'failures': [row for row in result['cases'] if row['returncode'] and
                                   not row.get('inherited_unsupported_mat3x4')]}))
    assert result['passed']


if __name__ == '__main__':
    main()
