"""One bound host invocation of the private candidate bootstrap, with no retry."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import load_session
from mcdk import Client, return_value


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_sources(binding):
    project = Path(binding['project'])
    actual = {name: sha(project / name) for name in binding['source_sha256']}
    if actual != binding['source_sha256']:
        raise RuntimeError('Frozen private source binding changed')
    return actual


def main():
    binding_path = WORK / 'final-source-binding-v1.json'
    binding = json.loads(binding_path.read_bytes())
    launch = json.loads((WORK / 'launch/launch.json').read_bytes())
    output = WORK / 'candidate-bootstrap-execution-v1.json'
    source_path = WORK / 'candidate_bootstrap.py'
    assert not output.exists(), 'Retain first attempt; do not replay initialization'
    assert sha(source_path) == binding['bootstrap_sha256']
    assert sha(Path(binding['archive']['path'])) == binding['archive']['sha256']
    assert sha(Path(binding['project']) / binding['qualification_path']) == binding['qualification_sha256']
    assert binding['owner_contract_sha256'] != binding['old_qualification_implementation_sha256']
    os.environ.update(MCDEV_SESSION_FILE=launch['session_file'], MCDEV_OWNER=binding['owner'],
                      MCDEV_ALLOW_USER_FOREGROUND='0')
    session = load_session(launch['session_file'], binding['owner'], live=True)
    assert Path(session['project']).resolve() == Path(binding['project']).resolve()
    for name in ('game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity'):
        assert session[name] == launch[name]
    before = checked_sources(binding)
    receipt = {'schema': 1, 'owner': binding['owner'], 'session_binding': {
        key: session[key] for key in ('id', 'owner', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')},
        'source_contract_sha256': binding['source_contract_sha256'],
        'host_sha256': sha(Path(__file__)), 'bootstrap_sha256': sha(source_path),
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'production_admission_performed': False, 'default_path_evidence': False,
        'execution_dispatched': False, 'completed': False}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2)
    code = source_path.read_text(encoding='utf-8') + '''
import json,sys,traceback
import mod.client.extraClientApi as api
from modern_projection.projection import liquid_deployment as deployment
from modern_projection.projection import liquid_product_deployment as product
from modern_projection.projection import liquid_product_qualification_data as qualification
from modern_projection.projection import liquid_product_owner_data as owners
system=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
bootstrap_receipt={}
try:
    bootstrap(system,deployment,product,qualification,owners,%r,%r,%r,%r,sys,bootstrap_receipt)
except Exception as bootstrap_error:
    bootstrap_receipt.update(error_type=type(bootstrap_error).__name__,error=str(bootstrap_error),
                             traceback=traceback.format_exc())
_result=json.dumps(bootstrap_receipt)
''' % (binding['engine_version'], tuple(binding['supported_water_names']),
       binding['owner_contract_sha256'], binding['old_qualification_implementation_sha256'])
    try:
        with Client(timeout=35) as client:
            state_deadline = time.monotonic() + 20.
            receipt['read_only_state_samples'] = []
            while True:
                remaining = state_deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError('No bridge observed within20s; no initialization forced')
                client.timeout = min(3., remaining)
                state_value = return_value(client.call('execute_code', {
                    'code': "import json\nimport mod.client.extraClientApi as api\ns=api.GetSystem('ModernProjection','ModernProjectionClientSystem')\n_result=json.dumps({'system_exists':s is not None,'bridge_exists':s is not None and s.bridge is not None,'session_exists':s is not None and s.session is not None,'hud_exists':s is not None and s.hud is not None,'ui_init_bridge_observed':s is not None and s.bridge is not None})",
                    'is_client': True, 'direct_return': True}))
                state = json.loads(state_value) if isinstance(state_value, str) else state_value
                receipt['read_only_state_samples'].append({'at_utc': datetime.now(timezone.utc).isoformat(), 'state': state})
                output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
                if not state['system_exists'] or state['session_exists']:
                    raise RuntimeError('Unexpected client system/session state before one-shot bootstrap')
                if state['bridge_exists']:
                    break
                if time.monotonic() >= state_deadline:
                    raise RuntimeError('No bridge observed within20s; UiInitFinished not observed; no initialization forced')
                time.sleep(min(1., max(0., state_deadline - time.monotonic())))
            client.timeout = 35
            receipt['execution_dispatched'] = True
            value = return_value(client.call('execute_code', {
                'code': code, 'is_client': True, 'direct_return': True}))
            runtime = json.loads(value) if isinstance(value, str) else value
            receipt['runtime'] = runtime
            receipt['completed'] = bool(runtime.get('completed'))
    except Exception as error:
        receipt['host_error'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
        raise
    finally:
        receipt['source_unchanged'] = checked_sources(binding) == before
        receipt['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    if not receipt['completed']:
        raise RuntimeError('Private bootstrap failed; inspect first receipt and ordinary-stop, no retry')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
