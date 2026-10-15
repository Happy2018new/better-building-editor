"""Prepare a disposable, exact portal-resource cross-control for water."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / '.runtime/projects/water-r20'
REFERENCE = ROOT / '.runtime/projects/portal-r20'
OUTPUT = ROOT / '.runtime/water-r20-prime-v6'
FRAGMENT = ROOT / '.runtime/water-r20-fragment-v5'
sys.path.insert(0, str(PROJECT / 'tools'))
from probe_product_water import snapshot_sources, snapshot_digest

assert not OUTPUT.exists()
baseline = json.loads((ROOT / '.runtime/water-r20-final-v2/launch-inputs.json').read_bytes())
fragment = json.loads((FRAGMENT / 'launch-inputs.json').read_bytes())
reference = json.loads((ROOT / '.runtime/water-root-cross-r20-v1/report.json').read_bytes())
assert snapshot_sources(PROJECT) == fragment['source_sha256']
OUTPUT.mkdir()
with zipfile.ZipFile(FRAGMENT / 'original-modified-inputs.zip') as archive:
    for name in archive.namelist():
        target = PROJECT / name
        assert target.is_relative_to(PROJECT)
        target.write_bytes(archive.read(name))
generated = sorted(set(fragment['source_sha256']) - set(baseline['source_sha256']))
assert len(generated) == 6 and all('/water_r20_diag_' in name for name in generated)
for name in generated:
    (PROJECT / name).unlink()
assert snapshot_sources(PROJECT) == baseline['source_sha256']

old, new = baseline['source_sha256'], reference['source_sha256']
differences = sorted(name for name in set(old) | set(new) if old.get(name) != new.get(name))
resource_delta = [name for name in differences if name.startswith('resource_pack/')]
assert all(name in new for name in resource_delta)
shared = {}
for name, container in (('resource_pack/materials/entity.material', 'materials'),
                        ('resource_pack/models/netease_models.json', None)):
    a = json.loads((PROJECT / name).read_bytes())
    b = json.loads((REFERENCE / name).read_bytes())
    a, b = (a[container], b[container]) if container else (a, b)
    shared[name] = {'shared_entries_equal': all(a[key] == b[key] for key in set(a) & set(b)),
                    'removed': sorted(set(a) - set(b)), 'added': sorted(set(b) - set(a))}
    assert shared[name]['shared_entries_equal'] and not shared[name]['removed']
    assert len(shared[name]['added']) == 12

with zipfile.ZipFile(OUTPUT / 'resource-delta.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in resource_delta:
        source = REFERENCE / name
        assert hashlib.sha256(source.read_bytes()).hexdigest() == new[name]
        target = PROJECT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        archive.write(source, name)
frozen = snapshot_sources(PROJECT)
assert all(frozen[name] == new[name] for name in resource_delta)
assert all(frozen.get(name) == value for name, value in old.items() if name not in resource_delta)

def save(directory, name, value):
    (directory / name).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='ascii')

save(OUTPUT, 'launch-inputs.json', {'schema': 1, 'project': str(PROJECT),
    'source_sha256': frozen, 'source_contract_sha256': snapshot_digest(frozen)})
save(OUTPUT, 'plan.json', {'schema': 1, 'diagnostic_only': True,
    'production_qualified': False, 'window_actions': [], 'root_product_inputs_untouched': True,
    'baseline_contract_sha256': baseline['source_contract_sha256'],
    'source_contract_sha256': snapshot_digest(frozen), 'resource_delta': resource_delta,
    'all_source_differences': differences, 'shared_entries': shared,
    'phases': ['cold_editor_three_captures', 'portal_world_priming', 'editor_three_captures']})
save(FRAGMENT, 'diagnostic-limitations.json', {'schema': 1, 'production_qualified': False,
    'color_phase_valid': False, 'color_error': 'PROJ undefined: uniformPerFrameConstants.h was omitted',
    'static_phase_valid': False, 'static_limit': 'Captured with preceding color compiler error overlay',
    'baseline_noalpha_red_visual': 'No water or constant-red surface visible',
    'root_product_inputs_untouched': True, 'clone_restored_before_v6': True})
print(json.dumps({'prepared': True, 'files': len(frozen), 'resource_delta': len(resource_delta),
    'source_contract_sha256': snapshot_digest(frozen)}))
