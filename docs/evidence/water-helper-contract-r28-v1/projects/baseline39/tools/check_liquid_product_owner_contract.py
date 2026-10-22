"""Diagnose water owner drift without changing the generator or its outputs."""
import argparse
import json
from pathlib import Path

import generate_liquid_product_owner_contract as generator

SCOPE = ('Explicit SOURCES and generator only; not a transitive dependency closure '
         'or a runtime/GPU qualification. Unlisted helper changes are not detected.')


def source_differences(expected, actual):
    rows = []
    for name in sorted(set(expected) | set(actual)):
        before, after = expected.get(name), actual.get(name)
        if before == after:
            continue
        status = 'added' if name not in expected else 'removed' if name not in actual else 'changed'
        rows.append({'status': status, 'path': name,
                     'expected_sha256': before, 'actual_sha256': after})
    return rows


def normalized(path):
    return path.read_bytes().replace(b'\r\n', b'\n')


def label(path):
    return path.resolve().relative_to(generator.ROOT.resolve()).as_posix()


def check():
    report = {'checked': True, 'passed': False, 'sources': len(generator.SOURCES),
              'source_differences': [], 'generator_difference': None,
              'artifact_differences': [], 'errors': [], 'scope': SCOPE}
    stored = {}
    try:
        stored = json.loads(generator.CONTRACT.read_bytes())
        if not isinstance(stored, dict) or not isinstance(stored.get('source_sha256'), dict):
            raise ValueError('Contract source_sha256 must be an object')
    except (OSError, ValueError) as error:
        report['errors'].append({'path': label(generator.CONTRACT), 'reason': str(error)})
        stored = {}

    expected_outputs = ()
    try:
        contract, source = generator.generated()
        current = json.loads(contract)
        report['contract_sha256'] = generator.digest(contract)
        expected_outputs = ((generator.CONTRACT, contract), (generator.OUTPUT, source))
    except (OSError, ValueError) as error:
        # Keep partial per-file diagnostics when a missing bound source prevents
        # the unchanged generator from completing its ordinary calculation.
        report['errors'].append({'reason': str(error)})
        current = {'source_sha256': {}}
        for name in generator.SOURCES:
            try:
                current['source_sha256'][name] = generator.digest(normalized(generator.ROOT / name))
            except OSError as source_error:
                report['errors'].append({'path': name, 'reason': str(source_error)})

    report['source_differences'] = source_differences(stored.get('source_sha256', {}), current['source_sha256'])
    before = stored.get('generator_sha256')
    after = current.get('generator_sha256')
    if after is not None and before != after:
        report['generator_difference'] = {'status': 'added' if before is None else 'changed',
            'path': label(Path(generator.__file__)),
            'expected_sha256': before, 'actual_sha256': after}
    for path, expected in expected_outputs:
        actual = None
        try:
            actual = normalized(path)
        except OSError as error:
            report['errors'].append({'path': label(path), 'reason': str(error)})
        if actual != expected:
            report['artifact_differences'].append({'status': 'removed' if actual is None else 'changed',
                'path': label(path), 'expected_sha256': generator.digest(expected),
                'actual_sha256': None if actual is None else generator.digest(actual)})
    report['passed'] = not (report['source_differences'] or report['generator_difference'] or
                            report['artifact_differences'] or report['errors'])
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Compatibility flag; this tool is always read-only')
    parser.parse_args(argv)
    report = check()
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
