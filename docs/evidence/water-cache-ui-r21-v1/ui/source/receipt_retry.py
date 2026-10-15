"""Bind the unchanged S/SE runner to the successful preserved cache retry."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
HERE = Path(__file__).resolve().parent
RUNTIME = HERE / 'runtime.py'
RUNTIME_SHA = '0d8004c32eb247fc6ebf401bdb51e8c23ee5ece765d3c508387516c5e7911353'
RETRY_NAME = 'ab-report-runtime-hashlib-retry-v1.json'


def main(args):
    assert args.scheduled_by_root and args.session
    assert hashlib.sha256(RUNTIME.read_bytes()).hexdigest() == RUNTIME_SHA
    tree = ast.parse(RUNTIME.read_bytes())
    changed = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == 'ab-report.json':
            node.value = RETRY_NAME
            changed.append(node)
    assert len(changed) == 2
    ast.fix_missing_locations(tree)
    namespace = {'__file__': str(RUNTIME.resolve()), '__name__': 'water_ui_receipt_retry'}
    exec(compile(tree, str(RUNTIME.resolve()) + ':receipt-only-amendment', 'exec'), namespace)
    cache = namespace['cache_module']()
    prior = cache.read(cache.OUTPUT / 'ab-report.json')
    retry = cache.read(cache.OUTPUT / RETRY_NAME)
    assert not prior['completed'] and prior['restored'] and prior['source_unchanged']
    assert all(retry[key] for key in ('completed', 'restored', 'source_unchanged'))
    receipt = {'schema': 1, 'operational_only': True, 'same_session_only': True,
        'unchanged_runtime_sha256': RUNTIME_SHA,
        'outer_runner_sha256': cache.sha(__file__),
        'candidate_sha256': cache.sha(HERE / 'candidate.py'),
        'engine_sha256': cache.sha(HERE / 'runtime_engine.py'),
        'old_ab_failure_sha256': cache.sha(cache.OUTPUT / 'ab-report.json'),
        'successful_ab_retry_sha256': cache.sha(cache.OUTPUT / RETRY_NAME),
        'ast_constant_replacements': 2,
        'changes': ['Only the two A/B receipt-path constants: gate read and provenance hash'],
        'original_files_changed': False, 'extra_launch': False,
        'extra_fixture_or_capture': False, 'production_qualified': False}
    with (HERE / 'runtime-ab-receipt-amendment.json').open('x', encoding='ascii') as handle:
        handle.write(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    original_save = namespace['save']
    def save_with_source(report):
        report['execution_outer_runner'] = {'path': str(Path(__file__).resolve()),
            'sha256': receipt['outer_runner_sha256'],
            'receipt': str(HERE / 'runtime-ab-receipt-amendment.json'),
            'receipt_sha256': cache.sha(HERE / 'runtime-ab-receipt-amendment.json')}
        original_save(report)
    namespace['save'] = save_with_source
    return namespace['run'](args)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--scheduled-by-root', action='store_true')
    args = parser.parse_args()
    args.action = 'run'
    raise SystemExit(main(args))
