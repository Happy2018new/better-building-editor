"""Verify every archived file and native-to-derived glint evidence binding."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import runpy


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='ascii'))


def verify(package):
    package = package.resolve(strict=True)
    index = read(package / 'index.json')
    for entry in index['files']:
        path = package / entry['path']
        if package not in path.resolve(strict=True).parents:
            raise ValueError('An indexed file escaped the evidence directory')
        if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ValueError('An indexed file changed: ' + entry['path'])
    census_path = package / 'census/census.json'
    census = read(census_path)
    strict = read(package / 'strict-analysis/summary.json')
    if (not census['completed'] or not census['project_source_unchanged'] or not strict['completed'] or
            digest(census_path) != strict['full_census_sha256'] or
            index['coverage'] != strict['coverage'] or index['production_qualified'] or
            index['original_acquisition_coverage'] != census['coverage'] or
            strict['original_analyzer_sha256'] != census['binding']['analyzer_sha256'] or
            len(census['pages']) != census['requested_pages']):
        raise ValueError('The archive coverage or source-bound completion claim changed')
    for field, path in (
            ('sampler_sha256', 'sources/tools/probe_intrinsic_glint_ui_r21.py'),
            ('analyzer_sha256', 'sources/tools/analyze_intrinsic_glint_ui_r21.py'),
            ('census_source_sha256', 'sources/tools/census_intrinsic_glint_ui_r21.py'),
            ('basic_sha256', 'basic-catalog.json'), ('textures_sha256', 'textures-catalog.json')):
        if digest(package / path) != census['binding'][field]:
            raise ValueError('A source used during native acquisition changed')
    if digest(package / 'sources/tools/reanalyze_intrinsic_glint_r21.py') != strict['strict_analyzer_source_sha256']:
        raise ValueError('The stricter analyzer source changed')
    extra_path = package / 'census/supplemental-aux/summary.json'
    extra = read(extra_path)
    if (digest(extra_path) != strict['supplemental_summary_sha256'] or not extra['completed'] or
            not extra['project_source_unchanged'] or extra['full_census_sha256'] != digest(census_path) or
            extra['source_sha256'] != digest(package / 'sources/tools/probe_intrinsic_glint_aux_r21.py')):
        raise ValueError('The auxiliary supplement changed')
    rows = []
    for native, derived, source in (
            (census['pages'], strict['pages'], package / 'census'),
            (extra['pages'], strict['supplemental_pages'], extra_path.parent)):
        if len(native) != len(derived):
            raise ValueError('Native and derived page counts differ')
        for page, derivative in zip(native, derived):
            directory = source / page['path']
            report = read(directory / 'report.json')
            if (not page['restored'] or not report['completed'] or report['cleanup_errors'] or
                    not report['restoration']['restored'] or
                    digest(directory / 'report.json') != page['report_sha256'] or
                    digest(directory / 'analysis.json') != page['analysis_sha256'] or
                    derivative['report_sha256'] != page['report_sha256'] or
                    derivative['original_analysis_sha256'] != page['analysis_sha256']):
                raise ValueError('An original page or restoration claim changed')
            for capture in report['captures']:
                receipt = capture['receipt']
                if not receipt['reliable'] or digest(directory / Path(receipt['path']).name) != receipt['sha256']:
                    raise ValueError('An original native capture changed')
            analysis_path = package / 'strict-analysis' / derivative['path'] / 'analysis.json'
            analysis = read(analysis_path)
            if (digest(analysis_path) != derivative['analysis_sha256'] or
                    not analysis['native_controls_passed'] or analysis['production_qualified'] or
                    analysis['rows'][4:] != derivative['rows']):
                raise ValueError('A derived native page changed')
            rows.extend(derivative['rows'])
    coverage = strict['coverage']
    positives = {(row['name'], row['aux']) for row in rows
                 if row['classification'] == 'intrinsic_glint_native_confirmed'}
    rules = runpy.run_path(str(package / 'sources/behavior_pack/modern_projection/projection/intrinsic_item_glint.py'))
    if (len(rows) != coverage['observed_pairs'] or
            len({row['name'] for row in rows}) != coverage['observed_ids'] or
            dict(Counter(row['classification'] for row in rows)) != coverage['classifications'] or
            positives != {(row['name'], row['aux']) for row in coverage['intrinsic_pairs']} or
            rules['CONFIRMED_PAIRS'] != positives):
        raise ValueError('Archived rendering rules differ from strict native positives')
    exited = read(package / 'exact-process-exit.json')
    identity = census['pages'][-1]['handles_after']
    if (not exited['completed'] or
            any(row['state'] != 'exited' for row in exited['processes'].values()) or
            exited['processes']['game']['pid'] != identity['pid'] or
            exited['processes']['game']['identity'] != identity['identity'] or
            exited['processes'] != index['exact_process_exit']):
        raise ValueError('Exact process exit observations changed')
    return {'verified_files': len(index['files']), 'observed_pairs': len(rows),
            'intrinsic_families': len({name for name, aux in positives}),
            'classifications': coverage['classifications'],
            'production_qualified': False, 'game_exit_code_hex': exited['processes']['game']['exit_code_hex']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', nargs='?', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(verify(args.package), sort_keys=True))
