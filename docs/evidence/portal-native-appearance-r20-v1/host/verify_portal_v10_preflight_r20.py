"""Check the frozen native/candidate starfield route without launching it."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from generate_liquid_product_resources import write_json
from probe_product_water import snapshot_digest, snapshot_sources
from _session import load_session, process_identity

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--require-commit', action='store_true')
args = parser.parse_args()
project = ROOT / '.runtime/projects/portal-r20-native-v10'
control = ROOT / '.runtime/portal-native-control-r20-v10'
prepared = json.loads((control / 'prepared-summary.json').read_bytes())
frozen = json.loads((control / 'launch-inputs.json').read_bytes())['files']
assert snapshot_sources(project) == frozen
assert snapshot_digest(frozen) == prepared['source_contract_sha256']
assert not (control / 'start.stdout.json').exists(), 'Never replay an old start'
config = (project / '.mcdev.json').read_bytes()
assert hashlib.sha256(config).hexdigest() == prepared['config_sha256']
assert all(json.loads(config)[key] is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                                       'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
for relative in ('tools/probe_portal_reference_r19.py', 'tools/analyze_portal_reference_appearance_r20.py',
                 'tools/census_intrinsic_glint_ui_r21.py'):
    assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == frozen[relative]
assert hashlib.sha256((ROOT / 'tools/watch_intrinsic_glint_exit_r21.py').read_bytes()).hexdigest() == prepared['exit_observer_sha256']
native = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data')
assert (project / 'resource_pack/materials/portal.material').read_bytes() == (native / 'resource_packs/vanilla/materials/portal.material').read_bytes()
assert (project / 'resource_pack/shaders/glsl/r19_native_portal_original.h').read_bytes() == (native / 'shaders/glsl/end_portal.fragment').read_bytes()
compiled = json.loads((ROOT / '.runtime/portal-appearance-compile-r20-v10/compile.json').read_bytes())
assert compiled['passed']
assert compiled['source_sha256']['r19_native_portal_world.vertex'] == prepared['candidate_world_vertex_sha256']
assert compiled['source_sha256']['r19_native_portal_native.fragment'] == prepared['candidate_native_fragment_sha256']
previous = load_session('C:/Users/Happy2018new/.pyreact-debug/instances/4196e0bddbaf4b29bf6dbc412797a450/session.json',
                        'portal-r20-native-v9')
assert previous['state'] == 'stopped'
assert all(process_identity(previous[kind + '_pid']) != previous[kind + '_identity'] for kind in ('game', 'mcdk'))
memory = commit_at_boundary()
commit_passed = memory['commit_available_bytes'] >= 6 * 1024 ** 3
if args.require_commit:
    assert commit_passed, 'Available commit is below the authorized 6 GiB gate'
external = {relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() for relative in (
    '.runtime/start_portal_v10_observed_r20.py', '.runtime/run_portal_v10_appearance_guarded_r20.py',
    '.runtime/verify_portal_v10_preflight_r20.py', '.runtime/start_portal_prepared_r20.py')}
receipt = {'ready_for_authorized_launch': True, 'launched': False,
           'source_contract_sha256': prepared['source_contract_sha256'], 'external_host_sha256': external,
           'native_portal_base_restored': True, 'candidate_v9_world_vertex_retained': True,
           'compile_case_count': len(compiled['cases']), 'system_memory': memory,
           'commit_gate_required_now': args.require_commit, 'commit_gate_passed': commit_passed,
           'physical_memory_is_a_gate': False, 'production_qualification': False}
write_json(control / 'preflight-summary.json', receipt)
print(json.dumps(receipt))
