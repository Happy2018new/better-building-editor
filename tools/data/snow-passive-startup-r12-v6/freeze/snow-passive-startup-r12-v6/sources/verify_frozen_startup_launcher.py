"""Run upstream readiness tests against exact frozen launcher/client/helper bytes."""
import argparse
from contextlib import ExitStack
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
import unittest
from unittest.mock import patch
import urllib.request


def load_source(name, record):
    path = Path(record['path']).resolve(strict=True)
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != record['sha256']:
        raise ValueError('Frozen offline source changed: ' + name)
    module = ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(payload, str(path), 'exec'), module.__dict__)
    return module


def verify(manifest_path, output):
    output = Path(output)
    if output.exists():
        raise ValueError('Offline launcher verification output must be fresh')
    sources = json.loads(Path(manifest_path).read_bytes())
    modules = {name: load_source(name, sources['modules'][name])
               for name in ('_session', '_window', 'setup_mcdk', 'mcdk', 'instances')}
    if modules['instances'].Client is not modules['mcdk'].Client:
        raise ValueError('Launcher did not bind the frozen planned MCP client')
    tests = [load_source(name, record) for name, record in sources['tests'].items()]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(module)
                               for module in tests)
    log = io.StringIO()
    with ExitStack() as stack:
        for target, name in ((subprocess, 'Popen'), (subprocess, 'run'),
                             (urllib.request.OpenerDirector, 'open'),
                             (modules['_session'], 'process_identity'),
                             (modules['_session'], 'terminate_owned'),
                             (modules['_window'], 'foreground_snapshot'),
                             (modules['_window'], '_list_windows_windows'),
                             (modules['_window'], '_process_name_windows'),
                             (modules['_window'], '_activate_window')):
            stack.enter_context(patch.object(target, name,
                side_effect=AssertionError('Unmocked host operation in offline launcher test')))
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    report = {'schema': 1, 'passed': result.wasSuccessful(), 'tests_run': result.testsRun,
              'modules': sources['modules'], 'tests': sources['tests'],
              'exact_planned_client_bound': True, 'native_launches': 0,
              'sdk_requests': 0, 'wgc_captures': 0, 'test_log': log.getvalue()}
    with output.open('x', encoding='ascii') as handle:
        handle.write(json.dumps(report, ensure_ascii=True, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'tests_run': result.testsRun,
                      'receipt': str(output.resolve()), 'native_launches': 0}))
    return 0 if result.wasSuccessful() else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    return verify(args.manifest, args.output)


if __name__ == '__main__':
    raise SystemExit(main())
