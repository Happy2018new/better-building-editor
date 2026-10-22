"""Independent object-level checks against separately fetched exact Git blobs."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / '.runtime/round-20261023/render-resource-boundary-v2'
read = lambda p: json.loads(Path(p).read_bytes())
report = read(HERE / 'map.json')
commit = report['source_commit']
blobs = {}
for path, pin in report['read_source_pins'].items():
    data = subprocess.check_output(['git', 'cat-file', 'blob', commit + ':' + path], cwd=ROOT)
    oid = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
    assert oid == pin['git_blob_sha1'] and len(data) == pin['bytes']
    assert hashlib.sha256(data).hexdigest() == pin['sha256']
    blobs[path] = data
models = json.loads(blobs['resource_pack/models/netease_models.json'])
materials = json.loads(blobs['resource_pack/materials/entity.material'])['materials']
rows = report['resources']['model_rows']
assert len(rows) == len({r['identifier'] for r in rows}) == 28
assert {f: sum(r['family'] == f for r in rows) for f in ('water','cauldron','portal','book')} == {
    'water':12, 'cauldron':8, 'portal':4, 'book':4}
for row in rows:
    contract = json.loads(blobs[row['contract']])
    assert row['definition_equal_to_contract']
    assert models[row['identifier']] == contract['models'][row['identifier']]
    for local in row['local_files']:
        assert local['in_exact_commit'] and local['path'] in blobs
    for material in row['material_chain']:
        assert material['matches_declared_contract'] is True
        assert materials[material['key']] == contract['materials'][material['key']]
assert report['resources']['unresolved_edges'] == []
diffs = report['resources']['whole_output_hash_differences']
assert len(diffs) == 8 and all(row['shared_registry'] for row in diffs)
assert {r['path'] for r in diffs} == {'resource_pack/models/netease_models.json',
                                    'resource_pack/materials/entity.material'}
for row in diffs:
    assert hashlib.sha256(blobs[row['path']]).hexdigest() == row['actual_raw_sha256']
    assert row['actual_raw_sha256'] != row['expected_sha256']
effects = report['owner_input_boundary']['effects']
assert len(effects) == 5 and all(r['late_cleanup_has_identity_guard'] for r in effects)
for row in effects:
    assert len(row['cleanup_call_order_syntax']) == 2
    assert row['cleanup_call_order_syntax'][0].endswith('_controls.close')
    assert row['cleanup_call_order_syntax'][1].endswith('.close')
assert all(r['external_material_parents'] == ['entity_for_skeleton_alpha'] for r in rows)
result = {'passed':True, 'different_Git_fetch_method':'one git cat-file blob COMMIT:path per pin',
    'source_files':len(blobs), 'model_rows':len(rows), 'models_per_family':{'water':12,'cauldron':8,'portal':4,'book':4},
    'local_resource_files':len({p['path'] for r in rows for p in r['local_files']}),
    'shared_registry_whole_hash_differences':8, 'unique_shared_registries':2,
    'model_and_material_entry_mismatches':0, 'missing_local_resources':0,
    'external_engine_parent':'entity_for_skeleton_alpha',
    'shader_include_paths_runtime_unproven':True, 'owner_effects_syntax_checked':5,
    'first_analysis_attempt': {'path':str(HERE.with_name('render-resource-boundary-v1')/'map.json'),
        'sha256':hashlib.sha256((HERE.with_name('render-resource-boundary-v1')/'map.json').read_bytes()).hexdigest(),
        'error':'Analyzer v1 incorrectly applied CRLF normalization to raw output hashes, including PNG. Its reported 21 differences included 13 false differences. Raw-byte v2 leaves only 8 shared-registry differences. V1 source/output retained; no product file or generation contract changed.'},
    'MC_started':False, 'runtime_qualification_created':False, 'manual_issues_closed':0}
target = HERE / 'independent-review.json'
assert not target.exists()
target.write_text(json.dumps(result, sort_keys=True, indent=2)+'\n', encoding='utf8')
print(json.dumps(result))
