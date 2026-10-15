"""Verify the waiting v8 coordinate pair without launching or contacting a game."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from generate_liquid_product_resources import write_json
from probe_product_water import snapshot_digest, snapshot_sources
from _session import load_session, process_identity

project = ROOT / '.runtime/projects/portal-r20-native-v8'
control = ROOT / '.runtime/portal-native-control-r20-v8'
launch = json.loads((control / 'launch-inputs.json').read_bytes())
prepared = json.loads((control / 'prepared-summary.json').read_bytes())
assert snapshot_sources(project) == launch['files']
assert snapshot_digest(launch['files']) == prepared['source_contract_sha256']
assert not (control / 'start.stdout.json').exists(), 'Do not replay an old start'
config = json.loads((project / '.mcdev.json').read_bytes())
assert all(config[key] is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                          'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
assert hashlib.sha256((project / '.mcdev.json').read_bytes()).hexdigest() == prepared['config_sha256']
host_paths = ('tools/probe_portal_reference_r19.py', 'tools/analyze_portal_coordinates_r20.py',
              'tools/watch_intrinsic_glint_exit_r21.py', 'tools/probe_intrinsic_glint_ui_r21.py',
              '.agents/skills/pyreact-debugging/scripts/instances.py',
              '.agents/skills/pyreact-debugging/scripts/_session.py',
              '.runtime/start_portal_prepared_r20.py')
host_sha256 = {}
for relative in host_paths:
    raw = (ROOT / relative).read_bytes()
    compile(raw, relative, 'exec')
    host_sha256[relative] = hashlib.sha256(raw).hexdigest()
assert host_sha256['tools/watch_intrinsic_glint_exit_r21.py'] == prepared['exit_observer_sha256']
assert host_sha256['tools/probe_portal_reference_r19.py'] == launch['files']['tools/probe_portal_reference_r19.py']
old = load_session('C:/Users/Happy2018new/.pyreact-debug/instances/59d11648f93b4e908b68ed4711c72ba8/session.json',
                   'portal-r20-native-v1')
assert process_identity(old['game_pid']) is None and process_identity(old['mcdk_pid']) is None
guard_verified = {}
for kind in ('mcdk', 'dll'):
    guard = old['noactivation'][kind]
    actual = hashlib.sha256(Path(guard['path']).read_bytes()).hexdigest()
    assert actual == guard['sha256']
    guard_verified[kind] = actual
receipt = {'verified_at': datetime.now(timezone.utc).isoformat(), 'ready_for_authorized_launch': True,
           'launched': False, 'old_start_replayed': False, 'game_or_window_mutation': False,
           'source_contract_sha256': prepared['source_contract_sha256'],
           'host_sha256': host_sha256, 'guard_sha256': guard_verified,
           'pair_arguments': ['--project', str(project), '--owner', 'portal-r20-native-v8',
                              '--output', str(ROOT / '.runtime/portal-coordinate-readback-r20-v8'),
                              '--native-adapter', '--adapter-prefix', 'r19_native_portal_',
                              '--families', 'end_gateway', '--views', 'front',
                              '--near-player', '--record-absent'],
           'expected_capture_count': 2, 'production_qualification': False}
write_json(control / 'preflight-summary.json', receipt)
print(json.dumps({'ready_for_authorized_launch': True, 'launched': False,
                  'source_contract_sha256': prepared['source_contract_sha256'],
                  'expected_capture_count': 2, 'exit_observer_unchanged': True,
                  'approved_guards_verified': True, 'production_qualification': False}))
