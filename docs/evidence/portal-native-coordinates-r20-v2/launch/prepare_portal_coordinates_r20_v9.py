"""Freeze the single-line candidate view-origin correction over measured v8."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from generate_liquid_product_resources import write_json
from probe_product_water import snapshot_digest, snapshot_sources

source = ROOT / '.runtime/projects/portal-r20-native-v8'
source_control = ROOT / '.runtime/portal-native-control-r20-v8'
project = ROOT / '.runtime/projects/portal-r20-native-v9'
control = ROOT / '.runtime/portal-native-control-r20-v9'
before = json.loads((source_control / 'launch-inputs.json').read_bytes())['files']
assert snapshot_sources(source) == before
assert not project.exists() and not control.exists()
shutil.copytree(source, project)
control.mkdir()
shutil.copytree(source_control / 'coordinates', control / 'coordinates')
relative = 'resource_pack/shaders/glsl/r19_native_portal_world.vertex'
shader = project / relative
raw = shader.read_bytes()
old = b'vec3 parallaxPositionInWorld=t*viewRay+VIEW_POS;'
new = b'vec3 parallaxPositionInWorld=t*viewRay;'
assert raw.count(old) == 1
corrected = raw.replace(old, new)
assert b'vec3 viewRay=(WORLD*entityPoint).xyz;' in corrected
shader.write_bytes(corrected)
expected = dict(before)
expected[relative] = hashlib.sha256(corrected).hexdigest()
after = snapshot_sources(project)
assert after == expected
changed = [path for path in before if before[path] != after[path]]
assert changed == [relative]
config = (project / '.mcdev.json').read_bytes()
assert config == (source / '.mcdev.json').read_bytes()
assert all(json.loads(config)[key] is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                                       'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
write_json(control / 'launch-inputs.json', {'source_contract_sha256': snapshot_digest(after), 'files': after})
receipt = {'prepared': True, 'launched': False, 'round': 'v9', 'route_source': 'v8',
           'source_contract_sha256': snapshot_digest(after),
           'source_v8_contract_sha256': snapshot_digest(before), 'changed_paths': changed,
           'before_line': old.decode('ascii'), 'after_line': new.decode('ascii'),
           'shader_sha256': expected[relative], 'view_ray_unchanged': True,
           'config_sha256': hashlib.sha256(config).hexdigest(),
           'exit_observer_sha256': hashlib.sha256((ROOT / 'tools/watch_intrinsic_glint_exit_r21.py').read_bytes()).hexdigest(),
           'evidence_commit': 'ab541a0a', 'production_qualification': False}
write_json(control / 'prepared-summary.json', receipt)
print(json.dumps(receipt))
