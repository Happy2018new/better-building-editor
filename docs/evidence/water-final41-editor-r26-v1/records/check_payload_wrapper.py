"""Exercise the actual retained-receipt payload with fake SDK/module imports."""
import builtins
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS

import bootstrap_payload as payload
import check_candidate_bootstrap as core_controls


def exercise(mode):
    args, original, calls = core_controls.scenario(mode)
    system, deployment, product, qualification, owners, engine, names, new, old, private_sys = args
    initialize = system.UiInitFinished

    def initialize_with_hud(unused):
        initialize(unused)
        system.hud = NS()

    system.UiInitFinished = initialize_with_hud
    modules = NS(liquid_deployment=deployment, liquid_product_deployment=product,
                 liquid_product_qualification_data=qualification, liquid_product_owner_data=owners)
    api = NS(GetSystem=lambda namespace, name: system)
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'sys':
            return private_sys
        if name == 'mod.client.extraClientApi':
            return NS(client=NS(extraClientApi=api))
        if name == 'modern_projection.projection':
            return modules
        return real_import(name, globals, locals, fromlist, level)

    binding = {'bootstrap_receipt_marker': '_offline_unique_receipt', 'engine_version': engine,
               'supported_water_names': list(names), 'owner_contract_sha256': new,
               'old_qualification_implementation_sha256': old}
    core = Path(core_controls.target.__file__).read_text(encoding='utf-8')
    namespace = {'__builtins__': dict(vars(builtins), __import__=fake_import)}
    code = payload.dispatch_code(core, binding)
    exec(compile(code, '<actual-dispatch-payload>', 'exec'), namespace)
    direct = json.loads(namespace['_result'])
    assert deployment.production_profile is original
    assert direct['adapter_finally_reached'] and direct['adapter_original_function_restored']
    exec(compile(payload.readback_code(binding['bootstrap_receipt_marker']), '<actual-readback>', 'exec'), namespace)
    observed = json.loads(namespace['_result'])
    assert payload.accepted_runtime(observed) is (mode == 'success')
    assert calls == ['UiInitFinished']
    try:
        exec(compile(code, '<duplicate-dispatch-refused>', 'exec'), namespace)
    except RuntimeError as error:
        assert 'never replay' in str(error)
    else:
        raise AssertionError('Existing marker did not reject duplicate dispatch')
    assert calls == ['UiInitFinished'] and deployment.production_profile is original
    exec(compile(payload.readback_code(binding['bootstrap_receipt_marker'], retire=True), '<retire-terminal-marker>', 'exec'), namespace)
    retired = json.loads(namespace['_result'])
    assert retired['marker_retired'] and not hasattr(private_sys, binding['bootstrap_receipt_marker'])
    return {'mode': mode, 'passed': True, 'initialization_calls': len(calls),
            'terminal_readback_accepted': payload.accepted_runtime(observed),
            'duplicate_dispatch_refused': True, 'original_identity_retained': True,
            'terminal_marker_retired': True}


def main():
    checks = [exercise('success'), exercise('init_exception'), exercise('second_selection')]
    result = {'schema': 1, 'offline_only': True, 'MC_started': False, 'checks': checks,
              'all_passed': True,
              'original_core_sha256': hashlib.sha256(Path(core_controls.target.__file__).read_bytes()).hexdigest(),
              'payload_sha256': hashlib.sha256(Path(payload.__file__).read_bytes()).hexdigest(),
              'limitations': ['Fake SDK control proves wrapper and marker flow, not actual game lifecycle or IPC completion.']}
    path = Path(__file__).with_name('payload-wrapper-controls-v1.json')
    with path.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
