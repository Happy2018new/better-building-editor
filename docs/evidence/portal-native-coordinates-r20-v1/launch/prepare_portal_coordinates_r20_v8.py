"""Clone the frozen v5 coordinate route without regenerating its resources."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from generate_liquid_product_resources import write_json
from probe_product_water import snapshot_digest, snapshot_sources

source = ROOT / '.runtime/projects/portal-r20-native-v5'
source_control = ROOT / '.runtime/portal-native-control-r20-v5'
project = ROOT / '.runtime/projects/portal-r20-native-v8'
control = ROOT / '.runtime/portal-native-control-r20-v8'
expected = json.loads((source_control / 'launch-inputs.json').read_bytes())
assert snapshot_sources(source) == expected['files']
assert not project.exists() and not control.exists()
shutil.copytree(source, project)
control.mkdir()
shutil.copytree(source_control / 'coordinates', control / 'coordinates')
shutil.copyfile(source_control / 'launch-inputs.json', control / 'launch-inputs.json')
actual = snapshot_sources(project)
assert actual == expected['files']
config = json.loads((project / '.mcdev.json').read_bytes())
assert all(config[key] is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                          'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
watcher = ROOT / 'tools/watch_intrinsic_glint_exit_r21.py'
receipt = {'prepared': True, 'launched': False, 'round': 'v8', 'route_source': 'v5',
           'source_contract_sha256': snapshot_digest(actual),
           'identical_to_frozen_v5': True,
           'config_sha256': hashlib.sha256((project / '.mcdev.json').read_bytes()).hexdigest(),
           'exit_observer_sha256': hashlib.sha256(watcher.read_bytes()).hexdigest(),
           'production_qualification': False}
write_json(control / 'prepared-summary.json', receipt)
print(json.dumps(receipt))
