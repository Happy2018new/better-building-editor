"""Verify exact timing reports, clocks, owner binding, and retained failures."""
import hashlib
import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parent
CONTRACT = 'cb2b32de68b69f435d69b59cf296d8492d88984ddb96e10f020d7fdbd0aef806'


def load(name):
    return json.loads((PACKAGE / name).read_bytes())


def sha(name):
    return hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest()


def main():
    manifest = load('manifest.json')
    assert manifest['diagnostic_only'] and manifest['production_qualified'] is False
    actual = {path.relative_to(PACKAGE).as_posix() for path in PACKAGE.rglob('*')
              if path.is_file() and path.name != 'manifest.json' and '__pycache__' not in path.parts}
    assert actual == set(manifest['files'])
    for name, row in manifest['files'].items():
        assert (PACKAGE / name).stat().st_size == row['bytes'] and sha(name) == row['sha256'], name
    paired, profiler, query = (load(name) for name in
                               ('paired-clock.json', 'profiler.json', 'liquid-query.json'))
    for report in (paired, profiler, query):
        assert report['diagnostic_only'] and report['production_qualified'] is False
        assert report['source_contract_sha256'] == CONTRACT
        assert report['window_actions'] == []
    for report in (paired, profiler):
        assert report['completed'] and report['restored'] and report['source_unchanged']
        assert report['cleanup_errors'] == [] and report['screenshots'] == []
    assert paired['session_binding'] == profiler['session_binding']
    assert paired['host_sha256'] == sha('hosts/paired-clock.py')
    assert paired['parent_host_sha256'] == sha('hosts/paired-clock-parent.py')
    assert profiler['host_sha256'] == sha('hosts/profiler.py')
    assert query['host_sha256'] == sha('hosts/profiler-query.py')
    assert query['capture_started'] is False
    assert len(paired['rows']) == 36
    timing = paired['timing']
    assert timing['thread_cpu_supported'] is False and 'not CPU time' in timing['clock_semantics']
    assert all(row['thread_cpu_ms'] is None for row in timing['outliers'])
    assert timing['stats']['LiquidControls.update']['calls'] == 10338
    assert 10.9 < timing['stats']['LiquidControls.update']['maximum_wall_ms'] < 11.1
    assert 11.8 < timing['stats']['LiquidControls.update']['maximum_high_resolution_wall_ms'] < 11.9
    expected = {'cpu': (3747, 0.265625, 0.09375), 'wall': (5775, 0.5607786, 0.1117812)}
    for clock, values in expected.items():
        phase = profiler['profiles'][clock]
        assert len(phase['rows']) == 6 and phase['status']['structuredContent']['job']['state'] == 'completed'
        assert phase['status']['structuredContent']['job']['partial'] is False
        assert query['profiles'][clock]['job_id'] == phase['job_id']
        artifact = phase['export']['structuredContent']['data']['artifact']
        assert artifact['sha256'] == sha('profiler-' + clock + '.md')
        methods = {}
        for view in ('hotspots', 'calls'):
            pages = query['profiles'][clock][view]
            for index, page in enumerate(pages):
                assert page['isError'] is False and page['structuredContent']['ok'] is True
                data = page['structuredContent']['data']
                assert bool(data.get('next_cursor')) == (index < len(pages) - 1)
                assert data['returned'] == len(data['records'])
                if view == 'hotspots':
                    for record in data['records']:
                        fields = record['fields']
                        assert 'liquid_' in fields['module']['value'] or 'liquid_' in fields['name']['value']
                        methods[fields['name']['value']] = fields
        for name, total in (('LiquidControls.update', values[1]), ('LiquidPreview.advance', values[2])):
            assert methods[name]['calls']['value'] == values[0]
            assert abs(methods[name]['total_time']['value'] - total) < 1e-10
    refs = load('references.json')
    assert sha(refs['prior_manifest']['path']) == refs['prior_manifest']['sha256']
    maxima = []
    for row in refs['failures']:
        assert sha(row['path']) == row['sha256']
        maximum = max(load(row['path'])['owner_timing_ms'][row['method']])
        assert maximum == row['maximum_ms']
        maxima.append(round(maximum))
    assert maxima == [169, 230, 435, 370]
    summary = load('summary.json')
    assert summary['production_qualified'] is False and summary['source_contract_sha256'] == CONTRACT
    assert summary['session_binding'] == profiler['session_binding']
    assert summary['paired_clock_stats'] == timing['stats']
    print(json.dumps({'verified': True, 'paired_clock_transitions': 36,
                      'profiler_jobs': 2, 'preserved_failure_maxima_ms': maxima,
                      'production_qualified': False}))


if __name__ == '__main__':
    main()
