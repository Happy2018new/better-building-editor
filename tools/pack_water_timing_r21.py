"""Freeze owner-bound water timing diagnostics without changing acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime/water-r20-state-v7'
PACKAGE = ROOT / 'docs/evidence/water-timing-r21-v1'
PRIOR = ROOT / 'docs/evidence/water-ui-state-r20-v1'
FILES = {
    'paired-clock.json': RUNTIME / 'ui-clock-v1.json',
    'profiler.json': RUNTIME / 'profiler-cpu-wall-v1/report.json',
    'liquid-query.json': RUNTIME / 'profiler-cpu-wall-v1/liquid-query.json',
    'hosts/paired-clock.py': ROOT / '.runtime/water-r20-ui-clock.py',
    'hosts/paired-clock-parent.py': ROOT / '.runtime/water-r20-granular.py',
    'hosts/profiler.py': ROOT / '.runtime/water-r20-profiler.py',
    'hosts/profiler-query.py': ROOT / '.runtime/water-r20-profiler-query.py',
}
FAILURES = (
    ('v2-core-timing-and-state.json', 'LiquidProjection.advance'),
    ('v7-editor-pool.json', 'LiquidPreview.advance'),
    ('v7-editor-public19.json', 'LiquidControls.update'),
    ('v7-editor-alpha4.json', 'LiquidControls.update'),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='ascii')


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert sha(source) == sha(target), 'Refusing to replace frozen bytes: ' + str(target)
    else:
        shutil.copy2(source, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=PACKAGE)
    args = parser.parse_args()
    output = args.output.resolve()
    assert (output / 'README.md').is_file() and (output / 'verify_package.py').is_file()
    assert not (output / 'manifest.json').exists()
    for name, source in FILES.items():
        copy(source, output / name)
    copy(Path(__file__), output / 'hosts/package-builder.py')
    profiler = load(output / 'profiler.json')
    paired = load(output / 'paired-clock.json')
    query = load(output / 'liquid-query.json')
    summary = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
               'source_contract_sha256': profiler['source_contract_sha256'],
               'session_binding': profiler['session_binding'],
               'paired_clock_transitions': len(paired['rows']),
               'paired_clock_stats': paired['timing']['stats'],
               'thread_cpu_supported': paired['timing']['thread_cpu_supported'],
               'profiler': {}, 'failed_formal_samples': []}
    for clock, phase in profiler['profiles'].items():
        artifact = phase['export']['structuredContent']['data']['artifact']
        source = Path(artifact['path'])
        assert source.stat().st_size == artifact['size'] and sha(source) == artifact['sha256']
        copy(source, output / ('profiler-' + clock + '.md'))
        records = [row for page in query['profiles'][clock]['hotspots']
                   for row in page['structuredContent']['data']['records']]
        selected = {row['fields']['name']['value']: {
            key: row['fields'][key]['value'] for key in ('calls', 'self_time', 'total_time')}
            for row in records if row['fields']['name']['value'] in
            ('LiquidControls.update', 'LiquidPreview.advance')}
        summary['profiler'][clock] = {'job_id': phase['job_id'], 'transitions': len(phase['rows']),
            'state': phase['status']['structuredContent']['job']['state'], 'methods': selected}
    references = {'prior_manifest': {'path': '../water-ui-state-r20-v1/manifest.json',
                                    'sha256': sha(PRIOR / 'manifest.json')}, 'failures': []}
    for name, method in FAILURES:
        source = PRIOR / name
        original = load(source)
        maximum = max(original['owner_timing_ms'][method])
        row = {'path': '../water-ui-state-r20-v1/' + name, 'sha256': sha(source),
               'method': method, 'maximum_ms': maximum}
        references['failures'].append(row)
        summary['failed_formal_samples'].append({'report': row['path'], 'method': method,
                                                 'maximum_ms': maximum})
    write(output / 'references.json', references)
    write(output / 'summary.json', summary)
    manifest = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
        'files': {path.relative_to(output).as_posix(): {'bytes': path.stat().st_size, 'sha256': sha(path)}
                  for path in sorted(output.rglob('*')) if path.is_file() and '__pycache__' not in path.parts}}
    write(output / 'manifest.json', manifest)
    print(json.dumps({'files': len(manifest['files']),
                      'bytes': sum(row['bytes'] for row in manifest['files'].values()),
                      'production_qualified': False}))


if __name__ == '__main__':
    main()
