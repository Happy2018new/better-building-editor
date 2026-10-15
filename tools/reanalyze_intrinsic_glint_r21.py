"""Derive stricter native glint evidence without modifying acquired reports."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

import analyze_intrinsic_glint_ui_r21 as baseline

BASE_SIGNATURE = baseline.glint_signature
MAXIMUM_RATIO_ERROR = .025


def strict_signature(frames):
    result = BASE_SIGNATURE(frames)
    ratios = result['channel_ratios']
    error = (max(abs(value - expected) for value, expected in
                 zip(ratios, baseline.GLINT_COLOR[:2])) if ratios is not None else None)
    result['maximum_ratio_error'] = error
    result['detected'] = bool(result['detected'] and error is not None and
                              error <= MAXIMUM_RATIO_ERROR)
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


def derive_page(source, destination, page, source_digest):
    for name in ('report', 'analysis'):
        if digest(source / (name + '.json')) != page[name + '_sha256']:
            raise ValueError('An acquired page changed: ' + str(source))
    report = json.loads((source / 'report.json').read_text(encoding='ascii'))
    destination.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='intrinsic-glint-r21-') as directory:
        temporary = Path(directory)
        shutil.copyfile(source / 'report.json', temporary / 'report.json')
        for capture in report['captures']:
            receipt = capture['receipt']
            name = Path(receipt['path']).name
            if digest(source / name) != receipt['sha256']:
                raise ValueError('An acquired native capture changed')
            shutil.copyfile(source / name, temporary / name)
        with patch.object(baseline, 'glint_signature', strict_signature):
            analysis = baseline.analyze(temporary)
        analysis['schema'] = 4
        analysis['signature']['maximum_aggregate_channel_ratio_error'] = MAXIMUM_RATIO_ERROR
        analysis['derivation'] = {
            'original_analysis_sha256': page['analysis_sha256'],
            'strict_analyzer_source_sha256': source_digest,
            'method': 'Recomputed all pixel signatures from immutable acquired screenshots; '
                      'added aggregate red/blue and green/blue ratio gates'}
        write_json(destination / 'analysis.json', analysis)
        shutil.copyfile(temporary / 'paired-review.png', destination / 'paired-review.png')
    if not analysis['native_controls_passed'] or [row['classification'] for row in analysis['rows'][:4]] != (
            ['no_intrinsic_glint_in_this_probe'] * 3 + ['intrinsic_glint_native_confirmed']):
        raise ValueError('Stricter native controls failed at ' + str(source))
    previous = {row['index']: row for row in json.loads(
        (source / 'analysis.json').read_text(encoding='ascii'))['rows']}
    changed = [{'name': row['name'], 'aux': row['aux'],
                'before': previous[row['index']]['classification'], 'after': row['classification']}
               for row in analysis['rows']
               if previous[row['index']]['classification'] != row['classification']]
    return {'path': destination.name, 'acquisition_path': page['path'],
            'report_sha256': page['report_sha256'],
            'original_analysis_sha256': page['analysis_sha256'],
            'analysis_sha256': digest(destination / 'analysis.json'),
            'review_sha256': digest(destination / 'paired-review.png'),
            'native_controls_passed': True, 'classification_changes': changed,
            'rows': analysis['rows'][4:]}


def derive(census, output):
    raw_path = census / 'census.json'
    acquired = json.loads(raw_path.read_text(encoding='ascii'))
    if not acquired['completed'] or not acquired['project_source_unchanged']:
        raise ValueError('Complete source-bound acquisition is required')
    if digest(Path(baseline.__file__)) != acquired['binding']['analyzer_sha256']:
        raise ValueError('The original analyzer bytes must remain unchanged')
    source_digest = digest(Path(__file__))
    output.mkdir(parents=True, exist_ok=False)
    result = {'schema': 1, 'engine_version': acquired['engine_version'],
              'full_census_sha256': digest(raw_path),
              'original_analyzer_sha256': acquired['binding']['analyzer_sha256'],
              'strict_analyzer_source_sha256': source_digest,
              'ratio_error_limit': MAXIMUM_RATIO_ERROR, 'pages': [], 'supplemental_pages': [],
              'completed': False, 'production_qualified': False}
    for page in acquired['pages']:
        result['pages'].append(derive_page(census / page['path'], output / page['path'], page, source_digest))
    extra_path = census / 'supplemental-aux/summary.json'
    if extra_path.exists():
        extra = json.loads(extra_path.read_text(encoding='ascii'))
        if (not extra['completed'] or not extra['project_source_unchanged'] or
                extra['full_census_sha256'] != result['full_census_sha256']):
            raise ValueError('Complete source-bound supplement is required')
        result['supplemental_summary_sha256'] = digest(extra_path)
        for page in extra['pages']:
            result['supplemental_pages'].append(derive_page(
                extra_path.parent / page['path'], output / ('supplement-' + page['path']), page, source_digest))
    rows = [row for page in result['pages'] + result['supplemental_pages'] for row in page['rows']]
    result['coverage'] = {
        'observed_pairs': len(rows), 'observed_ids': len({row['name'] for row in rows}),
        'classifications': dict(Counter(row['classification'] for row in rows)),
        'intrinsic_pairs': [{'name': row['name'], 'aux': row['aux']} for row in rows
                            if row['classification'] == 'intrinsic_glint_native_confirmed']}
    result['classification_changes'] = [change for page in result['pages'] + result['supplemental_pages']
                                        for change in page['classification_changes']]
    result['completed'] = len(rows) == acquired['requested_pairs'] + sum(
        len(page['rows']) for page in result['supplemental_pages'])
    write_json(output / 'summary.json', result)
    print(json.dumps({'completed': result['completed'], 'pairs': len(rows),
                      'classifications': result['coverage']['classifications'],
                      'changed': result['classification_changes']}), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--census', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    derive(args.census, args.output)
