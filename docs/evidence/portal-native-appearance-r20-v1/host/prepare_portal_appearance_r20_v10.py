"""Freeze true native starfield resources with the verified v9 candidate ray."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from generate_liquid_product_resources import write_json
from probe_product_water import snapshot_digest, snapshot_sources

native = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data')
source = ROOT / '.runtime/projects/portal-r20-native-v9'
source_control = ROOT / '.runtime/portal-native-control-r20-v9'
project = ROOT / '.runtime/projects/portal-r20-native-v10'
control = ROOT / '.runtime/portal-native-control-r20-v10'
before = json.loads((source_control / 'launch-inputs.json').read_bytes())['files']
assert snapshot_sources(source) == before
assert not project.exists() and not control.exists()
shutil.copytree(source, project)
control.mkdir()
expected = dict(before)
restores = {
    'resource_pack/materials/portal.material': native / 'resource_packs/vanilla/materials/portal.material',
    'resource_pack/shaders/glsl/r19_native_portal_native.fragment': ROOT / 'docs/evidence/portal-native-measured-r20-v1/actual-inputs/resource_pack/shaders/glsl/r19_native_portal_native.fragment'}
for relative, original in restores.items():
    shutil.copyfile(original, project / relative)
    expected[relative] = hashlib.sha256(original.read_bytes()).hexdigest()
for relative in ('tools/probe_portal_reference_r19.py', 'tools/analyze_portal_reference_appearance_r20.py',
                 'tools/census_intrinsic_glint_ui_r21.py'):
    shutil.copyfile(ROOT / relative, project / relative)
    expected[relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
for name in ('common.json', 'fancy.json', 'sad.json'):
    assert (project / 'resource_pack/materials' / name).read_bytes() == (native / 'resource_packs/vanilla/materials' / name).read_bytes()
world = 'resource_pack/shaders/glsl/r19_native_portal_world.vertex'
assert (project / world).read_bytes() == (source / world).read_bytes()
assert hashlib.sha256((project / world).read_bytes()).hexdigest() == '55a378caac27cdbb48b3075801236c2c89f133c5210cb498f8ad436bffafd88e'
assert b'parallaxPositionInWorld=t*viewRay;' in (project / world).read_bytes()
assert b'vec3 viewRay=(WORLD*entityPoint).xyz;' in (project / world).read_bytes()
header = project / 'resource_pack/shaders/glsl/r19_native_portal_original.h'
assert header.read_bytes() == (native / 'shaders/glsl/end_portal.fragment').read_bytes()
assert (project / 'resource_pack/textures/models/modern_projection/portal/r19_native_starfield.png').read_bytes() == (native / 'resource_packs/vanilla/textures/entity/end_portal.png').read_bytes()
config = (project / '.mcdev.json').read_bytes()
assert config == (source / '.mcdev.json').read_bytes()
assert all(json.loads(config)[key] is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                                       'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
after = snapshot_sources(project)
assert after == expected
write_json(control / 'launch-inputs.json', {'source_contract_sha256': snapshot_digest(after), 'files': after})
prepared = {'prepared': True, 'launched': False, 'round': 'v10', 'route_source': 'v9',
            'source_contract_sha256': snapshot_digest(after),
            'source_v9_contract_sha256': snapshot_digest(before),
            'changed_paths': sorted(path for path in after if before.get(path) != after[path]),
            'native_portal_base_restored': True,
            'native_portal_material_sha256': expected['resource_pack/materials/portal.material'],
            'candidate_native_fragment_sha256': expected['resource_pack/shaders/glsl/r19_native_portal_native.fragment'],
            'candidate_world_vertex_sha256': expected[world], 'candidate_view_ray_unchanged': True,
            'config_sha256': hashlib.sha256(config).hexdigest(),
            'exit_observer_sha256': hashlib.sha256((ROOT / 'tools/watch_intrinsic_glint_exit_r21.py').read_bytes()).hexdigest(),
            'production_qualification': False}
write_json(control / 'prepared-summary.json', prepared)
plan = {'expected_capture_count': 8, 'phase_or_exposure_fit': False,
        'runtime_gate_metric': 'CommitLimit-CommitTotal', 'minimum_commit_bytes': 6 * 1024 ** 3,
        'runs': [
            {'family': 'end_gateway', 'views': ['front', 'oblique'], 'capture_count': 4,
             'front_offset': [0., 0., -4.5], 'oblique_offset': [3.2, 2.2, -4.5], 'measured_face': 'north'},
            {'family': 'end_portal', 'views': ['front', 'oblique'], 'capture_count': 4,
             'front_offset': [0., 2.2, -4.5], 'oblique_offset': [3.2, 2.2, -4.5], 'measured_face': 'top'}],
        'native_effects': 'Beams and exterior particles are not part of the finite-surface comparison.',
        'qualification': False}
write_json(control / 'appearance-plan.json', plan)
print(json.dumps(prepared))
