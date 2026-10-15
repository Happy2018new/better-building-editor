"""Preserve pre-workspace failure; correct owned assertion-helper invocation."""
import argparse
import ast
import hashlib
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
    old = json.loads((HERE / 'result/report.json').read_bytes())
    assert not old['completed'] and old['restored'] and old['source_unchanged']
    assert not old['phases'] and not old['captures'] and 'assertion_dialogs()' in old['error']
    tree = ast.parse(RUNTIME.read_bytes())
    replacements = {'ab_report_paths': 0, 'output_directory': 0, 'assertion_helper': 0}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == 'ab-report.json':
            node.value = RETRY_NAME
            replacements['ab_report_paths'] += 1
        elif isinstance(node, ast.Constant) and node.value == 'result':
            node.value = 'result-v2'
            replacements['output_directory'] += 1
        elif (isinstance(node, ast.Assert) and isinstance(node.test, ast.UnaryOp)
              and isinstance(node.test.operand, ast.Call)
              and isinstance(node.test.operand.func, ast.Attribute)
              and node.test.operand.func.attr == 'assertion_dialogs'):
            node.test.operand = ast.parse(
                "[row for row in probe.assertion_dialogs() if row['pid']==session['game_pid']]",
                mode='eval').body
            replacements['assertion_helper'] += 1
    assert replacements == {'ab_report_paths': 2, 'output_directory': 1, 'assertion_helper': 1}
    ast.fix_missing_locations(tree)
    namespace = {'__file__': str(RUNTIME.resolve()), '__name__': 'water_ui_receipt_retry_v2'}
    exec(compile(tree, str(RUNTIME.resolve()) + ':receipt-and-helper-amendment-v2', 'exec'), namespace)
    cache = namespace['cache_module']()
    retry = cache.read(cache.OUTPUT / RETRY_NAME)
    assert all(retry[key] for key in ('completed', 'restored', 'source_unchanged'))
    receipt = {'schema': 1, 'operational_only': True, 'same_session_only': True,
        'unchanged_runtime_sha256': RUNTIME_SHA, 'outer_runner_sha256': cache.sha(__file__),
        'candidate_sha256': cache.sha(HERE / 'candidate.py'),
        'engine_sha256': cache.sha(HERE / 'runtime_engine.py'),
        'prior_precapture_failure_sha256': cache.sha(HERE / 'result/report.json'),
        'old_ab_failure_sha256': cache.sha(cache.OUTPUT / 'ab-report.json'),
        'successful_ab_retry_sha256': cache.sha(cache.OUTPUT / RETRY_NAME),
        'ast_replacements': replacements, 'original_files_changed': False,
        'changes': ['Use successful preserved A/B receipt for gate and hash',
            'New result-v2 output preserves pre-workspace failure',
            'Call zero-argument assertion_dialogs then filter exact owned game PID'],
        'extra_launch': False, 'extra_fixture_or_capture': False, 'production_qualified': False}
    receipt_path = HERE / 'runtime-operational-amendment-v2.json'
    with receipt_path.open('x', encoding='ascii') as handle:
        handle.write(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    original_save = namespace['save']
    def save_with_source(report):
        report['execution_outer_runner'] = {'path': str(Path(__file__).resolve()),
            'sha256': receipt['outer_runner_sha256'], 'receipt': str(receipt_path),
            'receipt_sha256': cache.sha(receipt_path)}
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
