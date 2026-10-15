"""Freeze the measured native-layout candidate without a native material override."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from generate_liquid_product_resources import write_json
from generate_portal_native_adapter_r19 import generate, install
from probe_product_water import snapshot_digest, snapshot_sources

project = ROOT / '.runtime/projects/portal-r20-native-v4'
control = ROOT / '.runtime/portal-native-control-r20-v4'
assert not project.exists() and not control.exists()
shutil.copytree(ROOT / '.runtime/projects/portal-r20', project)
control.mkdir()
native = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data')
contract = generate(project, native, control / 'adapter', 16, native_layout=True)
install(control / 'adapter', project)
assert not (project / 'resource_pack/materials/portal.material').exists()
materials = json.loads((project / 'resource_pack/materials/entity.material').read_bytes())['materials']
assert 'portal_base' not in materials
config = json.loads((project / '.mcdev.json').read_bytes())
for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui', 'auto_hot_reload_shaders', 'auto_hot_reload_materials'):
    config[key] = False
write_json(project / '.mcdev.json', config)
for source in (ROOT / 'tools').glob('*.py'):
    shutil.copyfile(source, project / 'tools' / source.name)
sources = snapshot_sources(project)
write_json(control / 'launch-inputs.json', {'source_contract_sha256': snapshot_digest(sources), 'files': sources})
print(json.dumps({'prepared': True, 'native_layout': contract['native_layout'], 'source_contract_sha256': snapshot_digest(sources)}))
