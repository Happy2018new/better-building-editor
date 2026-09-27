"""Compile every project shader to HLSL/DXIL; NOT an installed RD material pack.

Host Python 3.10+. Requires glslang, SPIRV-Cross, DXC and a local game install.
No shader arithmetic is rewritten. The original GLSL remains authoritative.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import subprocess

from material_inventory import PACKS, inventory
from spirv_interface import normalize_interfaces


ROOT = Path(__file__).resolve().parents[2]
SKINNING = {
    'single': (),
    'large': ('LARGE_VERTEX_SHADER_UNIFORMS',),
    'netease': ('NETEASE_SKINNING',),
}
QUALITY = {
    'basic': (),
    'fancy': ('FANCY',),
    'fancy_aa': ('FANCY', 'TEXEL_AA_FEATURE', 'MSAA_FRAMEBUFFER_ENABLED'),
}
UNVERIFIED = [
    'ordinary_addon_material_loading', 'native_vertex_layout_and_root_signature',
    'engine_uniform_upload_and_animation_clock', 'projection_matrix_convention',
    'PBR_prepass_and_motion_vectors', 'native_render_state_application',
    'OpenGL_RenderDragon_visual_parity', 'mobile_backends',
]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def command(args, cwd):
    result = subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True,
                            encoding='utf8', errors='replace')
    if result.returncode:
        raise RuntimeError(subprocess.list2cmdline([str(a) for a in args]) + '\n' +
                           result.stdout + result.stderr)
    return result.stdout


def plan_jobs(records):
    jobs = {}
    for record in records:
        skins = SKINNING if 'USE_SKINNING' in record['defines'] else {'static': ()}
        for skin, extra in skins.items():
            for quality, flags in QUALITY.items():
                defines = sorted(set(record['defines']) | set(extra) | set(flags) |
                                 {'MCPE_NETEASE'})
                key = (record['vertex'], record['fragment'], tuple(defines))
                if key not in jobs:
                    jobs[key] = {'id': 'p%04d' % len(jobs), 'vertex': key[0],
                                 'fragment': key[1], 'defines': defines, 'uses': []}
                jobs[key]['uses'].append({k: record[k] for k in ('pack', 'material', 'variant')} |
                                         {'skinning': skin, 'quality': quality})
    return list(jobs.values())


def check_pair(vertex, fragment):
    outputs = {item['name']: item for item in vertex.get('outputs', [])}
    for item in fragment.get('inputs', []):
        previous = outputs[item['name']]
        if any(previous.get(k) != item.get(k) for k in ('type', 'location', 'array')):
            raise ValueError('Mismatched varying: ' + item['name'])


def header_manifest(game):
    folders = [game / 'data/resource_packs' / layer / 'shaders/glsl'
               for layer in ('vanilla_netease', 'vanilla', 'vanilla_base')]
    folders.append(game / 'data/shaders/glsl')
    existing = [p for p in folders if p.is_dir()]
    if not existing:
        raise ValueError('No engine GLSL headers found')
    files = {p.relative_to(game).as_posix(): sha256(p)
             for folder in existing for p in sorted(folder.rglob('*.h'))}
    return existing, files


def compile_job(job, args, headers):
    folder = args.output / job['id']
    folder.mkdir(parents=True, exist_ok=True)
    reflections = {}
    for stage, field in (('vert', 'vertex'), ('frag', 'fragment')):
        source = ROOT / job[field]
        wrapper = folder / ('source.' + stage)
        wrapper.write_text('\n'.join([
            '#version 310 es', '#extension GL_GOOGLE_include_directive : require',
            '#define POS4 vec4', '#define MAT4 mat4',
            *('#define ' + name for name in job['defines']),
            '#include "' + source.name + '"', '',
        ]), encoding='utf8')
        command([args.glslang, '-V', '-R', '--set-default-uniform-block',
                 'LegacyUniforms', '1', '0', '--auto-map-bindings', '--auto-map-locations',
                 '-I' + str(source.parent), *('-I' + str(h) for h in headers),
                 '-o', folder / (stage + '.spv'), wrapper], folder)
    locations = normalize_interfaces(folder / 'vert.spv', folder / 'frag.spv')
    for stage, prefix in (('vert', 'vs'), ('frag', 'ps')):
        binary = folder / (stage + '.spv')
        reflection = json.loads(command([args.spirv_cross, binary, '--reflect'], folder))
        reflections[stage] = reflection
        write_json(folder / (stage + '.reflection.json'), reflection)
        hlsl = folder / (stage + '.hlsl')
        command([args.spirv_cross, binary, '--hlsl', '--shader-model', '60',
                 '--output', hlsl], folder)
        # Do not silently reintroduce the mobile half-precision issue.
        if re.search(r'\b(?:half|min16float|float16_t)\b', hlsl.read_text(encoding='utf8')):
            raise ValueError('Unexpected reduced precision: ' + str(hlsl))
        for model in ('6_3', '6_5'):
            dxil = folder / (stage + '_' + model + '.dxil')
            command([args.dxc, '-T', prefix + '_' + model, '-E', 'main', '-Gis',
                     '-validator-version', '1.6', '-Fo', dxil.name, hlsl.name], folder)
            if args.validator:
                # DXV's command-line parser rejects non-ASCII absolute paths.
                command([args.validator, dxil.name], folder)
    check_pair(reflections['vert'], reflections['frag'])
    return {'id': job['id'], 'status': 'compiled', 'varying_locations': locations,
            'artifacts': {p.name: sha256(p) for p in sorted(folder.iterdir()) if p.is_file()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', required=True, type=Path)
    parser.add_argument('--glslang', required=True, type=Path)
    parser.add_argument('--spirv-cross', required=True, type=Path)
    parser.add_argument('--dxc', required=True, type=Path)
    parser.add_argument('--validator', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / '.runtime/renderdragon/translated')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--only', help='Development subset: material name substring; marks partial coverage')
    args = parser.parse_args()
    for name in ('game', 'glslang', 'spirv_cross', 'dxc', 'output', 'validator'):
        value = getattr(args, name)
        if value is not None:
            setattr(args, name, value.resolve())
    # Generated programs expand proprietary engine headers. Keep them ignored.
    runtime = (ROOT / '.runtime').resolve()
    if not args.output.is_relative_to(runtime):
        parser.error('--output must be inside the project .runtime directory')
    args.output.mkdir(parents=True, exist_ok=True)
    report_path = args.output / 'report.json'
    write_json(report_path, {'status': 'building', 'runtime_verified': False})
    records, sources, material_files = inventory(ROOT, args.game)
    if args.only:
        records = [r for r in records if args.only in r['material']]
        if not records:
            parser.error('--only matched no material')
    jobs = plan_jobs(records)
    headers, header_hashes = header_manifest(args.game)
    report = {
        'status': 'building', 'runtime_verified': False, 'visual_parity_verified': False,
        'full_inventory': not bool(args.only), 'not_ready_for_distribution': True,
        'unverified': UNVERIFIED, 'game': str(args.game),
        'sources': {name: sha256(ROOT / name) for name in sources},
        'material_sources': {p.relative_to(ROOT).as_posix(): sha256(p)
                             for pack in PACKS for p in sorted((ROOT / pack / 'materials').glob('*.material'))},
        'engine_materials': {p.relative_to(args.game).as_posix(): sha256(p) for p in material_files},
        'engine_headers': header_hashes,
        'tools': {name: {'path': str(getattr(args, name)), 'sha256': sha256(getattr(args, name))}
                  for name in ('glslang', 'spirv_cross', 'dxc', 'validator') if getattr(args, name)},
        'clip_space': 'Original OpenGL [-w,w]; native projection matrix binding is unresolved',
        'uniform_layout': 'Generated LegacyUniforms b0/space1; requires an engine upload adapter',
        'materials': records, 'jobs': jobs, 'results': [], 'errors': [],
    }
    write_json(report_path, report)
    print('Compiling %d unique pairs for %d material variants (%d source files)' %
          (len(jobs), len(records), len(sources)), flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(compile_job, job, args, headers): job['id'] for job in jobs}
        for index, future in enumerate(as_completed(pending), 1):
            try:
                report['results'].append(future.result())
            except (RuntimeError, ValueError, KeyError, OSError) as error:
                report['errors'].append({'id': pending[future], 'error': str(error)})
                print('FAILED ' + pending[future] + ': ' + str(error)[:600], flush=True)
            if index % 20 == 0 or index == len(jobs):
                print('%d/%d pairs; %d errors' % (index, len(jobs), len(report['errors'])), flush=True)
    report['results'].sort(key=lambda item: item['id'])
    report['errors'].sort(key=lambda item: item['id'])
    report['status'] = 'failed' if report['errors'] else 'compiled_not_integrated'
    report['source_integrity'] = all(sha256(ROOT / name) == digest
                                     for name, digest in report['sources'].items())
    if not report['source_integrity']:
        report['status'] = 'failed'
    write_json(report_path, report)
    print(str(report_path), flush=True)
    return 1 if report['status'] == 'failed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
