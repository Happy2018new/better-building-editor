"""Compare context output and host timings against a tracked reference revision."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.debug_blueprints import BLUEPRINTS, build, material
from projection.model import Document
from projection.render_context import prepare_context_batches

MODULE_PATH = 'behavior_pack/modern_projection/projection/render_context.py'


def reference(revision):
    source = subprocess.check_output(
        ['git', '-c', 'safe.directory=' + ROOT.as_posix(), 'show', revision + ':' + MODULE_PATH],
        cwd=ROOT)
    module = types.ModuleType('projection._context_benchmark_reference')
    module.__package__ = 'projection'
    exec(compile(source, revision + ':' + MODULE_PATH, 'exec'), module.__dict__)
    return module.prepare_context_batches, hashlib.sha256(source).hexdigest()


def compare(document, baseline, repeats=1, missing_pattern=False):
    saved = copy.deepcopy(document.to_data())
    targets = document.palette_data(lambda pos: sum(pos) % 3 == 0) if missing_pattern else document.palette_data()
    saved_targets = copy.deepcopy(targets)
    elapsed = {'reference': [], 'candidate': []}
    for number in range(repeats):
        functions = [('reference', baseline), ('candidate', prepare_context_batches)]
        if number % 2:
            functions.reverse()
        results = {}
        for label, function in functions:
            started = time.perf_counter()
            results[label] = function(document, targets)
            elapsed[label].append(time.perf_counter() - started)
            if document.to_data() != saved:
                raise AssertionError('%s mutated the document' % label)
            if targets != saved_targets:
                raise AssertionError('%s mutated the visible target palette' % label)
        if results['reference'] != results['candidate']:
            raise AssertionError('Context palettes differ from the reference')
    timings = {key: statistics.median(values) for key, values in elapsed.items()}
    return {'size': list(document.size), 'blocks': len(document.blocks),
            'selection_mode': 'missing_pattern' if missing_pattern else 'complete',
            'equivalent': True, 'document_unchanged': True, 'targets_unchanged': True,
            'batches': len(results['candidate']['_context_batches']),
            'seconds': elapsed, 'median_seconds': timings,
            'candidate_over_reference': timings['candidate'] / timings['reference']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-commit', required=True)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    report = {'schema_version': 1, 'passed': False,
              'scope': 'Host output equivalence and CPython timings; no MC visual or runtime speed acceptance.',
              'reference_dependencies': 'Current worktree dependencies; only the context module is pinned.',
              'reference_commit': args.reference_commit, 'blueprints': [], 'cubes': []}
    try:
        baseline, fingerprint = reference(args.reference_commit)
        report['reference_source_sha256'] = fingerprint
        report['candidate_source_sha256'] = hashlib.sha256((ROOT / MODULE_PATH).read_bytes()).hexdigest()
        for key, unused_category, unused_label, unused_size, unused_block in BLUEPRINTS:
            if key == 'test.registry.vanilla':
                continue
            for missing_pattern in (False, True):
                row = compare(build(key), baseline, missing_pattern=missing_pattern)
                row['blueprint_key'] = key
                report['blueprints'].append(row)
        stone = material('stone')
        for size in (16, 24, 32):
            document = Document((size, size, size), {
                (x, y, z): stone for x in range(size) for y in range(size) for z in range(size)})
            report['cubes'].append(compare(document, baseline, args.repeats))
        report['passed'] = True
    except (AssertionError, OSError, ValueError, subprocess.CalledProcessError) as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
