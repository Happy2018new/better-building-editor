"""Verify the one-line v9 route offline before its single authorized start."""
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
from census_intrinsic_glint_ui_r21 import commit_at_boundary

project = ROOT / '.runtime/projects/portal-r20-native-v9'
control = ROOT / '.runtime/portal-native-control-r20-v9'
prepared = json.loads((control / 'prepared-summary.json').read_bytes())
frozen = json.loads((control / 'launch-inputs.json').read_bytes())['files']
assert snapshot_sources(project) == frozen
assert snapshot_digest(frozen) == prepared['source_contract_sha256']
before = json.loads((ROOT / '.runtime/portal-native-control-r20-v8/launch-inputs.json').read_bytes())['files']
assert set(before) == set(frozen)
assert [p for p in before if before[p] != frozen[p]] == prepared['changed_paths']
assert not (control / 'start.stdout.json').exists(), 'Never replay a previous start'
config = (project / '.mcdev.json').read_bytes()
assert hashlib.sha256(config).hexdigest() == prepared['config_sha256']
assert all(json.loads(config)[key] is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                                       'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
watcher_sha = hashlib.sha256((ROOT / 'tools/watch_intrinsic_glint_exit_r21.py').read_bytes()).hexdigest()
assert watcher_sha == prepared['exit_observer_sha256']
assert hashlib.sha256((ROOT / 'tools/probe_portal_reference_r19.py').read_bytes()).hexdigest() == frozen['tools/probe_portal_reference_r19.py']
compiled = json.loads((ROOT / '.runtime/portal-coordinate-compile-r20-v9/compile.json').read_bytes())
assert compiled['passed'] and compiled['source_sha256']['r19_native_portal_world.vertex'] == prepared['shader_sha256']
previous = load_session('C:/Users/Happy2018new/.pyreact-debug/instances/d3ee2a7633954945b0871526eee8b75f/session.json',
                        'portal-r20-native-v8')
assert previous['state'] == 'stopped'
for kind in ('game', 'mcdk'):
    assert process_identity(previous[kind + '_pid']) != previous[kind + '_identity']
receipt = {'ready_for_authorized_launch': True, 'launched': False,
           'source_contract_sha256': prepared['source_contract_sha256'],
           'changed_paths': prepared['changed_paths'], 'view_ray_unchanged': True,
           'compiled_case_count': len(compiled['cases']), 'expected_capture_count': 2,
           'exit_observer_sha256': watcher_sha, 'old_start_replayed': False,
           'game_or_window_mutation': False, 'production_qualification': False}
memory = commit_at_boundary()
receipt['system_memory'] = memory
receipt['memory_gate'] = {'metric': 'CommitLimit-CommitTotal', 'threshold_bytes': 6 * 1024 ** 3,
                        'passed': memory['commit_available_bytes'] >= 6 * 1024 ** 3,
                        'canonical_source_sha256': hashlib.sha256((ROOT / 'tools/census_intrinsic_glint_ui_r21.py').read_bytes()).hexdigest(),
                        'physical_memory_is_a_gate': False}
assert receipt['memory_gate']['passed'], 'Available commit is below the authorized 6 GiB gate'
write_json(control / 'preflight-summary.json', receipt)
print(json.dumps(receipt))
