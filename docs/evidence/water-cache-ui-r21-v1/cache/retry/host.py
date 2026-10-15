"""One same-session operational retry; preserve the frozen host and failure."""
import argparse
import ast
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = ROOT / '.runtime/water-r21-depth-cache-v1/host.py'
FROZEN_SHA = 'c747d500464a07c93d5dc65607f1ce369965e5e0f74ce2823ac80d7d20c6e019'
RETRY_NAME = 'ab-report-runtime-hashlib-retry-v1.json'


def main(args):
    assert args.scheduled_by_root and args.session
    assert hashlib.sha256(FROZEN.read_bytes()).hexdigest() == FROZEN_SHA
    spec = importlib.util.spec_from_file_location('water_cache_frozen_retry_base', FROZEN)
    cache = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cache)
    plan, probe = cache.validate_plan()
    old = cache.read(cache.OUTPUT / 'ab-report.json')
    assert not old['completed'] and old['restored'] and old['source_unchanged']
    assert not old['cleanup_errors'] and not old['phases']
    assert 'sha256' in old['error'] and 'AttributeError' in old['error']
    assert not (HERE / 'amendment.json').exists(), 'One-use operational retry already attempted'
    assert not (cache.OUTPUT / RETRY_NAME).exists()
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve()),
                      MCDEV_OWNER=cache.OWNER, MCDEV_ALLOW_USER_FOREGROUND='1')
    from _session import load_session
    session = load_session(args.session, cache.OWNER, live=True)
    assert Path(session['project']).resolve() == cache.PROJECT.resolve()
    baseline = (cache.OUTPUT / 'baseline_viewport.py').read_bytes().decode('ascii')
    assert hashlib.sha256(baseline.encode('ascii')).hexdigest() == cache.BASELINE_SHA
    receipt = {'schema': 1, 'operational_only': True, 'same_session_only': True,
        'frozen_host_sha256': FROZEN_SHA, 'retry_host_sha256': cache.sha(__file__),
        'old_failure_report_sha256': cache.sha(cache.OUTPUT / 'ab-report.json'),
        'old_failure_preserved': True, 'frozen_project_changed': False,
        'baseline_source_sha256': cache.BASELINE_SHA,
        'source_contract_sha256': plan['source_contract_sha256'],
        'operational_amendment_sha256': cache.sha(cache.AMENDMENT),
        'session': session['id'], 'owner': cache.OWNER,
        'retry_report': str(cache.OUTPUT / RETRY_NAME),
        'launch_performed': False, 'production_qualified': False,
        'host_environment': {'OPENBLAS_NUM_THREADS': '1'}}

    def boundary(label):
        state = cache.capacity(probe, session)
        observer = cache.retained_observer(session)
        coverage = cache.watcher_coverage()
        receipt[label] = {'capacity': state, 'watcher': coverage,
                          'retained_processes': observer['processes']}
        assert state['passed'] and coverage['passed'], 'Canonical 6 GiB or exact identity/watcher gate failed'

    boundary('before_hash_probe')
    with probe.base.Client(timeout=45) as client:
        check = probe.blueprints.BlueprintCheck(client, HERE / 'amendment.json', 45.)
        raw = check.run('''import hashlib
payload=%r
try:
 digest=hashlib.new('sha256',payload).hexdigest()
 hash_result={'supported':True,'digest':digest,'error':None}
except (AttributeError,ValueError,TypeError,RuntimeError) as exc:
 hash_result={'supported':False,'digest':None,'error':repr(exc)}
compile(payload,'water-depth-baseline-probe','exec')
_result={'hashlib_new':hash_result,'compiled':True,'source_readback':payload}
''' % baseline)
    boundary('after_hash_probe')
    assert raw['compiled'] and raw['source_readback'] == baseline
    assert hashlib.sha256(raw['source_readback'].encode('ascii')).hexdigest() == cache.BASELINE_SHA
    new_supported = raw['hashlib_new']['supported']
    if new_supported:
        assert raw['hashlib_new']['digest'] == cache.BASELINE_SHA, 'Native hashlib.new digest disagrees'
    receipt['hashlib_new_probe'] = raw['hashlib_new']
    receipt['probe_source_readback_equal'] = True
    receipt['probe_source_readback_sha256_host'] = cache.BASELINE_SHA
    receipt['game_sha_computed'] = new_supported
    receipt['validation'] = ('game hashlib.new SHA256 plus exact source readback' if new_supported else
        'SHA256 computed on host only; game compiled exact source string and returned it byte-for-byte')
    original_install = cache.install_code()
    old_line = "assert hashlib.sha256(baseline_source.encode('ascii')).hexdigest()==%r" % cache.BASELINE_SHA
    assert original_install.count(old_line) == 1
    new_line = ("assert hashlib.new('sha256',baseline_source).hexdigest()==%r" % cache.BASELINE_SHA
                if new_supported else "assert baseline_source")
    revised_install = original_install.replace(old_line, new_line)
    revised_install += "\n_result['baseline_source_readback']=baseline_source\n"
    receipt['original_install_sha256_host'] = hashlib.sha256(original_install.encode('ascii')).hexdigest()
    receipt['revised_install_sha256_host'] = hashlib.sha256(revised_install.encode('ascii')).hexdigest()
    receipt['changes'] = ['Replace only unsupported native SHA invocation with probed equivalent or exact readback',
        'Return the exact compiled baseline string and verify it on the host before any phase',
        'Write the new report name; preserve every original phase, gate and restoration action']
    tree = ast.parse(inspect.getsource(cache.run))
    replacements = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == 'ab-report.json':
            node.value = RETRY_NAME
            replacements.append(node)
    assert len(replacements) == 1
    function = tree.body[0]
    for index, node in enumerate(function.body):
        if isinstance(node, ast.With):
            try_block = next(item for item in node.body if isinstance(item, ast.Try))
            for item_index, item in enumerate(try_block.body):
                if (isinstance(item, ast.Assign) and isinstance(item.value, ast.Call)
                        and any(isinstance(child, ast.Name) and child.id == 'install_code'
                                for child in ast.walk(item))):
                    extra = ast.parse("""assert report['install']['baseline_source_readback']==%r
report['baseline_transmission_sha256_host']=hashlib.sha256(report['install']['baseline_source_readback'].encode('ascii')).hexdigest()
assert report['baseline_transmission_sha256_host']==BASELINE_SHA
report['game_sha_computed']=%r
report['retry_operational_receipt']=%r
""" % (baseline, new_supported, str(HERE / 'amendment.json'))).body
                    try_block.body[item_index + 1:item_index + 1] = extra
                    break
            else:
                raise AssertionError('Exact install assignment was not found')
            break
    else:
        raise AssertionError('Frozen run context was not found')
    ast.fix_missing_locations(tree)
    with (HERE / 'amendment.json').open('x', encoding='ascii') as handle:
        handle.write(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    namespace = dict(cache.__dict__)
    namespace['__file__'] = str(Path(__file__).resolve())
    namespace['install_code'] = lambda: revised_install
    exec(compile(tree, str(Path(__file__).resolve()) + ':frozen-run', 'exec'), namespace)
    return namespace['run'](args)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--scheduled-by-root', action='store_true')
    raise SystemExit(main(parser.parse_args()))
