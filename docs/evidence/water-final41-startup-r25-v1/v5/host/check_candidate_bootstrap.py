"""Offline positive/negative controls for the exact private bootstrap function."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS

import candidate_bootstrap as target

ENGINE = '3.10.0.420447'
NEW_OWNER = '1' * 64
OLD_OWNER = '2' * 64
NAMES = frozenset(('minecraft:water', 'minecraft:flowing_water'))


def scenario(mode='success'):
    bridge = NS(session=None, alive=True, engine_version=ENGINE)
    for field in target.BRIDGE_EMPTY_FIELDS:
        setattr(bridge, field, None)
    bridge.survey_effects = NS(active=lambda: False)
    bridge.projection_outline = NS(entity=None, effects=NS(active=lambda: False))
    system = NS(session=None, bridge=bridge, hud=None, staff_aura=None, nearby_staff_auras=None)
    original = lambda version=None: (_ for _ in ()).throw(ValueError(target.GATE_ERROR))
    deployment = NS(production_profile=original)
    qualification = NS(PRODUCT_QUALIFIED=True, GATES={'animation': True, 'default_path': True},
                       QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256=OLD_OWNER)
    owners = NS(IMPLEMENTATION_CONTRACT_SHA256=NEW_OWNER)
    candidate = NS(supported_names=NAMES, style_version='style', rules_sha256='3' * 64)
    product = NS(production_profile=original, candidate_profile=lambda frozen=False: candidate)
    markers = NS()
    calls = []

    def initialize(unused):
        calls.append('UiInitFinished')
        selected = None if mode == 'skip_selection' else deployment.production_profile(ENGINE)
        if mode == 'second_selection':
            deployment.production_profile(ENGINE)
        if mode == 'init_exception':
            raise ValueError('Injected initialization failure')
        session = NS(liquid_profile=NS() if mode == 'wrong_profile' else selected)
        if mode != 'old_bridge':
            system.bridge = NS(session=None if mode == 'wrong_bridge_session' else session)
        system.session = session

    system.UiInitFinished = initialize
    args = (system, deployment, product, qualification, owners, ENGINE, NAMES,
            NEW_OWNER, OLD_OWNER, markers)
    return args, original, calls


def run(name, mutate=None, mode='success', expect_success=False, fail_after_install=False):
    args, original, calls = scenario(mode)
    if mutate is not None:
        mutate(*args)
    qualification_before = copy.deepcopy(args[3].__dict__)
    owners_before = copy.deepcopy(args[4].__dict__)
    receipt = {}
    error = None
    try:
        target.bootstrap(*args, receipt=receipt)
    except (RuntimeError, ValueError) as caught:
        error = str(caught)
    assert args[1].production_profile is original, name
    assert args[3].__dict__ == qualification_before, name
    assert args[4].__dict__ == owners_before, name
    assert bool(receipt.get('completed')) is expect_success, name
    if expect_success:
        assert error is None and calls == ['UiInitFinished'] and receipt['original_function_restored'], name
    else:
        assert error and not receipt['completed'], name
        if fail_after_install:
            assert receipt['temporary_function_installed'] and receipt['original_function_restored'], name
        else:
            assert not calls and not receipt.get('temporary_function_installed'), name
    return {'name': name, 'passed': True, 'expected_success': expect_success,
            'error': error, 'initialization_calls': len(calls),
            'original_function_identity_retained': True, 'qualification_untouched': True}


def main():
    checks = [run('success', expect_success=True)]
    checks.append(run('existing_session', lambda s, *rest: setattr(s, 'session', NS())))
    checks.append(run('missing_bridge', lambda s, *rest: setattr(s, 'bridge', None)))
    checks.append(run('wrong_engine', lambda s, *rest: setattr(s.bridge, 'engine_version', 'wrong')))
    for field in target.BRIDGE_EMPTY_FIELDS:
        checks.append(run('pending_bridge_' + field,
                          lambda s, *rest, field=field: setattr(s.bridge, field, ['pending'])))
    checks.append(run('survey_effects', lambda s, *rest: setattr(s.bridge.survey_effects, 'active', lambda: True)))
    checks.append(run('outline_effects', lambda s, *rest: setattr(s.bridge.projection_outline.effects, 'active', lambda: True)))
    for field in ('hud', 'staff_aura', 'nearby_staff_auras'):
        checks.append(run('existing_' + field, lambda s, *rest, field=field: setattr(s, field, NS())))
    checks.append(run('existing_probe_marker', lambda *args: setattr(args[-1], target.MARKERS[0], True)))
    checks.append(run('disabled_gate', lambda s, d, p, q, *rest: setattr(q, 'PRODUCT_QUALIFIED', False)))
    checks.append(run('owner_mismatch', lambda s, d, p, q, o, *rest: setattr(o, 'IMPLEMENTATION_CONTRACT_SHA256', '4' * 64)))
    checks.append(run('qualification_changed', lambda s, d, p, q, *rest: setattr(q, 'QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256', '5' * 64)))
    checks.append(run('production_unexpectedly_admitted', lambda s, d, p, *rest: setattr(p, 'production_profile', lambda version: NS())))
    def wrong_refusal(*args):
        def fail(version):
            raise ValueError('Unrelated failure')
        args[2].production_profile = fail
    checks.append(run('different_production_failure', wrong_refusal))
    checks.append(run('incomplete_water_owner', lambda s, d, p, *rest: setattr(p, 'candidate_profile', lambda frozen: NS(supported_names=frozenset()))))
    for mode in ('skip_selection', 'second_selection', 'init_exception', 'wrong_profile', 'old_bridge', 'wrong_bridge_session'):
        checks.append(run(mode, mode=mode, fail_after_install=True))
    path = Path(__file__).with_name('bootstrap-offline-controls-v1.json')
    result = {'schema': 1, 'offline_only': True, 'MC_started': False,
              'source_sha256': hashlib.sha256(Path(target.__file__).read_bytes()).hexdigest(),
              'checks': checks, 'passed': all(x['passed'] for x in checks),
              'limitations': ['Fake objects verify control flow and function restoration; IPC availability and live UiInitFinished safety remain unverified.']}
    with path.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': result['passed'], 'checks': len(checks), 'path': str(path)}))


if __name__ == '__main__':
    main()
