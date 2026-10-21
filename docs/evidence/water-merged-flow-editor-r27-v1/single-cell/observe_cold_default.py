"""Observe ordinary cold-init state once; never initialize or assign a profile."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time


WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import load_session
from mcdk import Client, return_value


CODE = '''import json
import mod.client.extraClientApi as api
from modern_projection.projection import liquid_product_owner_data as owners
from modern_projection.projection import liquid_product_qualification_data as qualification
from modern_projection.projection import liquid_product_deployment as product
from modern_projection.projection.liquid_product_profile import ProductLiquidProfile
from modern_projection.projection.widgets import Theme
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
s=owner.session if owner is not None else None
b=owner.bridge if owner is not None else None
p=s.liquid_profile if s is not None else None
_result=json.dumps({'system_exists':owner is not None,'session_exists':s is not None,
 'hud_exists':owner is not None and owner.hud is not None,
 'profile_type':type(p).__module__+'.'+type(p).__name__,
 'product_type_matches':isinstance(p,ProductLiquidProfile),
 'profile_callback_is_source_function':getattr(p,'ui_offset_for_gui',None) is product.ui_offset_for_gui,
 'profile_names':sorted(p.supported_names) if p is not None else [],
 'profile_rules':p.rules_sha256 if p is not None else None,
 'engine_version':b.engine_version if b is not None else None,
 'owner_contract':owners.IMPLEMENTATION_CONTRACT_SHA256,
 'old_qualification_implementation':qualification.QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256,
 'old_qualification_flag':qualification.PRODUCT_QUALIFIED,
 'runtime_module_files':{'product':product.__file__,'owners':owners.__file__,
 'qualification':qualification.__file__},
 'cached_gui':Theme.native_gui_scale,'theme_scale':Theme.scale,'font':Theme.input_font_scale,
 'explicit_bootstrap_performed':False,'profile_assignment_performed':False})
'''


def main():
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    launch = json.loads((WORK / 'launch/launch.json').read_bytes())
    os.environ.update(MCDEV_SESSION_FILE=launch['session_file'], MCDEV_OWNER=binding['owner'], MCDEV_ALLOW_USER_FOREGROUND='0')
    session = load_session(launch['session_file'], binding['owner'], live=True)
    assert Path(session['project']).resolve() == Path(binding['project']).resolve()
    for key in ('game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity'):
        assert session[key] == launch[key]
    report = {'schema': 1, 'owner': binding['owner'], 'completed': False,
              'observations': [], 'explicit_bootstrap_performed': False,
              'qualification_or_owner_changed': False, 'profile_assignment_performed': False,
              'old_qualification_reused_as_new_A': False, 'formal_A_accepted': False,
              'default_path_evidence': False, 'production_admission_performed': False,
              'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output = WORK / 'cold-default-observation-v1.json'
    assert not output.exists()
    deadline = time.monotonic() + 35
    try:
        with Client(timeout=8) as client:
            while True:
                value = return_value(client.call('execute_code', {'code': CODE, 'is_client': True, 'direct_return': True}))
                state = json.loads(value) if isinstance(value, str) else value
                report['observations'].append({'at_utc': datetime.now(timezone.utc).isoformat(), 'state': state})
                if state['session_exists'] and state['hud_exists']:
                    assert state['product_type_matches'] and state['profile_callback_is_source_function']
                    assert state['owner_contract'] == binding['owner_contract_sha256']
                    assert state['old_qualification_implementation'] == binding['old_qualification_implementation_sha256']
                    assert state['engine_version'] == binding['engine_version']
                    assert state['profile_names'] == sorted(binding['supported_water_names'])
                    report['completed'] = True
                    return
                assert time.monotonic() < deadline, 'Ordinary Session did not initialize; no forced initialization'
                time.sleep(.5)
    finally:
        with output.open('x', encoding='utf8') as stream:
            json.dump(report, stream, indent=2)
        print(json.dumps({'completed': report['completed'], 'observations': len(report['observations']), 'explicit_bootstrap_performed': False}))


if __name__ == '__main__':
    main()
