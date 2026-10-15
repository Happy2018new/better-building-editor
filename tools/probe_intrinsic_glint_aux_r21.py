"""Fill measured auxiliary gaps for every newly native-confirmed glint family."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from analyze_intrinsic_glint_ui_r21 import analyze
from census_intrinsic_glint_ui_r21 import (
    CONTROLS, LAYOUT, TEXTURES, commit_at_boundary, handles_at_boundary,
    resource_stop, write_json)
from freeze_intrinsic_glint_project_r21 import fingerprint
from probe_intrinsic_glint_ui_r21 import load_session, run


def requests(summary, textures):
    observed = {(row['name'], row['aux']) for page in summary['pages'] for row in page['rows']}
    positive = {row['name'] for page in summary['pages'] for row in page['rows']
                if row['classification'] == 'intrinsic_glint_native_confirmed'}
    return sorted({(row['name'], row['aux'], False) for row in textures['rows']
                   if row['name'] in positive and (row['name'], row['aux']) not in observed})


def probe(args):
    base_path = args.census / 'census.json'
    base = json.loads(base_path.read_text(encoding='ascii'))
    if not base['completed'] or not base['project_source_unchanged']:
        raise ValueError('The full restored source-bound native census must complete first')
    if hashlib.sha256(TEXTURES.read_bytes()).hexdigest() != base['binding']['textures_sha256']:
        raise ValueError('The measured auxiliary catalog changed')
    for key, name in (('sampler_sha256', 'probe_intrinsic_glint_ui_r21.py'),
                      ('analyzer_sha256', 'analyze_intrinsic_glint_ui_r21.py')):
        if hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() != base['binding'][key]:
            raise ValueError('A native classification source changed')
    cases = requests(base, json.loads(TEXTURES.read_text(encoding='utf8')))
    session = load_session(args.session, args.owner, live=True)
    project = Path(session['project'])
    frozen = json.loads(args.project_manifest.read_text(encoding='ascii'))
    if (frozen['files_sha256'] != base['binding']['project_files_sha256'] or
            fingerprint(project) != frozen['files']):
        raise ValueError('Supplemental native inputs differ from the full census')
    args.output.mkdir(parents=True, exist_ok=False)
    result = {'schema': 1, 'full_census_sha256': hashlib.sha256(base_path.read_bytes()).hexdigest(),
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'sampler_sha256': base['binding']['sampler_sha256'],
              'analyzer_sha256': base['binding']['analyzer_sha256'],
              'requests': cases, 'pages': [], 'completed': False,
              'production_qualified': False}
    path = args.output / 'summary.json'
    write_json(path, result)
    for start in range(0, len(cases), 32):
        handles = handles_at_boundary(args.session, args.owner)
        commit = commit_at_boundary()
        reason = resource_stop(handles, commit, 200000, 3.)
        if reason:
            result['stopped_at_restored_boundary'] = {
                'reason': reason, 'handles': handles, 'system_memory': commit}
            break
        directory = args.output / ('page-%03d' % (start // 32))
        report = run(args.session, args.owner, directory, args.wgc,
                     cases=CONTROLS + cases[start:start + 32], layout=LAYOUT)
        analysis = analyze(directory)
        if (not analysis['native_controls_passed'] or
                [row['classification'] for row in analysis['rows'][:4]] !=
                ['no_intrinsic_glint_in_this_probe'] * 3 + ['intrinsic_glint_native_confirmed']):
            raise RuntimeError('Supplemental native controls failed')
        result['pages'].append({'path': directory.name, 'restored': report['restoration']['restored'],
                                'report_sha256': hashlib.sha256((directory / 'report.json').read_bytes()).hexdigest(),
                                'analysis_sha256': hashlib.sha256((directory / 'analysis.json').read_bytes()).hexdigest(),
                                'handles_before': handles, 'system_memory_before': commit,
                                'handles_after': handles_at_boundary(args.session, args.owner),
                                'system_memory_after': commit_at_boundary(),
                                'rows': analysis['rows'][4:]})
        write_json(path, result)
    rows = [row for page in result['pages'] for row in page['rows']]
    result['completed'] = len(rows) == len(cases)
    result['project_source_unchanged'] = fingerprint(project) == frozen['files']
    result['coverage'] = {'observed_pairs': len(rows),
                          'classifications': dict(Counter(row['classification'] for row in rows)),
                          'intrinsic_pairs': [{'name': row['name'], 'aux': row['aux']} for row in rows
                                              if row['classification'] == 'intrinsic_glint_native_confirmed']}
    write_json(path, result)
    if not result['project_source_unchanged']:
        raise RuntimeError('Private native input files changed during the supplement')
    print(json.dumps({'completed': result['completed'], 'coverage': result['coverage']}), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--census', type=Path, required=True)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--project-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--wgc', type=Path, required=True)
    probe(parser.parse_args())
