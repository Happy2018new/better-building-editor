"""Verify an offline build is complete and current, without claiming runtime parity."""
import argparse
from collections import Counter
import json
from pathlib import Path

from material_inventory import inventory
from translate_all import ROOT, check_pair, header_manifest, plan_jobs, sha256


def verify(report_path):
    report = json.loads(report_path.read_text(encoding='utf8'))
    if report['status'] != 'compiled_not_integrated' or report['errors']:
        raise ValueError('Build did not compile successfully')
    if not report['full_inventory']:
        raise ValueError('Partial --only builds are not full coverage')
    if 'validator' not in report['tools']:
        raise ValueError('This report did not use an external DXIL validator')
    game = Path(report['game'])
    materials, sources, engine_materials = inventory(ROOT, game)
    if materials != report['materials'] or plan_jobs(materials) != report['jobs']:
        raise ValueError('Material inheritance or compile settings changed; rebuild required')
    if set(sources) != set(report['sources']):
        raise ValueError('Source coverage changed')
    for category, base in (('sources', ROOT), ('material_sources', ROOT),
                           ('engine_materials', game), ('engine_headers', game)):
        for name, expected in report[category].items():
            if sha256(base / name) != expected:
                raise ValueError('Build input changed: ' + name)
    if {p.relative_to(game).as_posix() for p in engine_materials} != set(report['engine_materials']):
        raise ValueError('Engine material layers changed')
    if header_manifest(game)[1] != report['engine_headers']:
        raise ValueError('Engine header search paths changed')
    jobs = {j['id']: j for j in report['jobs']}
    results = {r['id']: r for r in report['results']}
    if len(results) != len(report['results']) or set(results) != set(jobs):
        raise ValueError('Missing or duplicate compilation results')
    required = {s + extension for s in ('vert', 'frag') for extension in
                ('.spv', '.hlsl', '.reflection.json', '_6_3.dxil', '_6_5.dxil')}
    per_source = {}
    for identifier, result in results.items():
        if result['status'] != 'compiled' or not required.issubset(result['artifacts']):
            raise ValueError('Incomplete artifacts: ' + identifier)
        folder = report_path.parent / identifier
        for name, expected in result['artifacts'].items():
            if sha256(folder / name) != expected:
                raise ValueError('Artifact hash mismatch: ' + identifier + '/' + name)
        reflections = [json.loads((folder / (s + '.reflection.json')).read_text('utf8'))
                       for s in ('vert', 'frag')]
        check_pair(*reflections)
        for field in ('vertex', 'fragment'):
            source = jobs[identifier][field]
            per_source.setdefault(source, []).append(identifier)
    if set(per_source) != set(sources):
        raise ValueError('Not every source produced artifacts')
    return {
        'status': 'offline_build_verified_not_runtime_integrated',
        'runtime_verified': False, 'visual_parity_verified': False,
        'files': len(sources), 'materials': len({(m['pack'], m['material']) for m in materials}),
        'material_variants': len(materials), 'program_pairs': len(jobs),
        'hlsl_files': len(jobs) * 2, 'dxil_files': len(jobs) * 4,
        'source_sha256': report['sources'],
        'family_pairs': dict(sorted(Counter(Path(j['vertex']).stem for j in jobs.values()).items())),
        'programs_by_source': {name: sorted(ids) for name, ids in sorted(per_source.items())},
        'unverified': report['unverified'],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--summary', type=Path)
    args = parser.parse_args()
    summary = verify(args.report.resolve())
    if args.summary:
        args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ('source_sha256', 'programs_by_source')}, ensure_ascii=False, indent=2))
