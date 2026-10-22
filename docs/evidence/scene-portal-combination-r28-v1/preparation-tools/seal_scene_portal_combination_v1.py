"""Bind the actual private combination, receipts, source guards and preparation history."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent / 'scene-portal-combination-v1'
OWNER = HERE.parent / 'scene-owner-minimal-v2'
PORTAL = HERE.parent / 'portal-anchor-candidate-v1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def write(name, data):
    target = HERE / name
    assert not target.exists(), name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


guards = []
for directory, index_name, expected_sha in [
        (OWNER, 'ready-index.json', 'dab6301625661123426e8e42b2369b623f3cf537694b904bd61ba6ad79fa89c9'),
        (PORTAL, 'index.json', '4dbe14c85741f389e168ecdb47ca9950003710243e50eb7b1596ddf803695009')]:
    index = directory / index_name
    assert sha(index.read_bytes()) == expected_sha
    manifest = read(index)
    rows = manifest.get('entries')
    if rows is None:
        rows = [dict(row, path=name) for name, row in manifest['files'].items()]
    for row in rows:
        data = (directory / row['path']).read_bytes()
        assert sha(data) == row['sha256'] and len(data) == row['bytes']
    write('inputs/' + ('owner-ready-index.json' if directory == OWNER else 'portal-index.json'), index.read_bytes())
    guards.append({'directory': str(directory), 'index': index_name, 'index_sha256': expected_sha,
                   'bound_files_rechecked': len(rows), 'all_raw_hashes_unchanged': True})

production = read(PORTAL / 'workspace-boundary-before.json')['files']
current = {name: sha((ROOT / name).read_bytes()) for name in production}
assert production == current
write('sealed-source-guards.json', (json.dumps({'sealed_candidates': guards,
    'protected_production_source_contract_metadata_files': current,
    'protected_file_count': len(current), 'all_45_original_hashes_equal': production == current,
    'MC_started': False, 'main_repository_product_written': False}, ensure_ascii=False, indent=2) + '\n').encode('utf8'))

for name in ('prepare_scene_portal_combination_v1.py', 'finish_scene_portal_combination_v1.py',
             'repair_combined_portal_driver_v2.py', 'seal_scene_portal_combination_v1.py'):
    write('preparation-tools/' + name, (HERE.parent / name).read_bytes())

owner2, owner3 = (read(HERE / name) for name in ('owner-controls-py2.json', 'owner-controls-py3.json'))
for receipt in (owner2, owner3):
    assert receipt['completed'] and len(receipt['cases']) == 58
    assert all(row['passed'] for row in receipt['cases'])
    assert receipt['executed_source'] == 'combined private source, not sealed owner-only candidate'
portal2, portal3 = (read(HERE / name) for name in ('portal-controls-py2-v2.json', 'portal-controls-py3-v2.json'))
for receipt in (portal2, portal3):
    assert receipt['passed'] and len(receipt['formula_rows']) == 8
    assert len(receipt['dispatch_rows']) == 9 and len(receipt['invalid_GUI_rejected']) == 12
    assert len(receipt['historical_V4_formula_rows']) == 21
    assert receipt['executed_source'] == 'combined private source, not sealed portal-only candidate'
assert owner2['cases'] == owner3['cases']
for key in ('formula_rows', 'dispatch_rows', 'invalid_GUI_rejected', 'historical_V4_formula_rows', 'same_callback_GUI_changes_forwarded'):
    assert portal2[key] == portal3[key]

def report(name):
    wrapper = read(HERE / name)
    return json.loads(wrapper['value']['content'][0]['text'])


baseline_review, combined_review = report('review-baseline-v2.json'), report('review-combined-v2.json')
assert baseline_review['files_scanned'] == 2 and combined_review['files_scanned'] == 3
assert baseline_review['findings_total'] == combined_review['findings_total'] == 3
review_keys = lambda result: sorted((rule['rule_id'], finding['symbol']) for rule in result['rules'] for finding in rule['findings'])
assert review_keys(baseline_review) == review_keys(combined_review)
apply = read(HERE / 'ast-and-apply.json')
assert apply['both_patches_applied'] and apply['composition_patch_replayed_byte_exactly']

files = []
for path in sorted(HERE.rglob('*')):
    if not path.is_file() or '.git' in path.relative_to(HERE).parts or path.name == 'index.json':
        continue
    data = path.read_bytes()
    files.append({'path': path.relative_to(HERE).as_posix(), 'bytes': len(data), 'sha256': sha(data)})
index = {'schema': 1, 'base_commit': 'b70ce7bf13ad6a4472f2b089ac812c162b174861',
    'purpose': 'Private five-owner plus portal-anchor combination feasibility only',
    'entries': files, 'bound_files': len(files), 'bound_bytes': sum(row['bytes'] for row in files),
    'excluded_private_scratch_metadata': ['combined/.git/**', 'replay/.git/**'],
    'actual_default_git_apply_order': ['sealed five-owner candidate.patch', 'sealed portal-anchor candidate.patch'],
    'both_patches_applied_without_conflict': True, 'combined_patch_replay_byte_identical': True,
    'combined_patch_sha256': apply['combined_patch_sha256'], 'actual_combined_sources': apply['source_files'],
    'actual_Py2_version': owner2['python'], 'actual_Py3_version': owner3['python'],
    'owner_controls_each_interpreter': 58, 'portal_formula_rows_each_interpreter': 8,
    'portal_dispatch_rows_each_interpreter': 9, 'portal_invalid_GUI_rows_each_interpreter': 12,
    'portal_historical_formula_rows_each_interpreter': 21, 'same_callback_GUI_switch_forwarded': [2, 3, 4, 2],
    'paired_interpreter_control_results_identical': True,
    'Scene_entire_AST_same_outside_approved_owner_import_portal_regions': True,
    'Git_default_EOL_transformation_retained_and_recorded': True,
    'old_three_Scene_review_findings_retained_no_new': True,
    'production_protected_files_unchanged': len(current), 'sealed_candidates_unchanged': True,
    'main_product_written': False, 'stage_commit_push_performed': False,
    'MC_started': False, 'native_qualification': False, 'water39_qualification_transferred': False,
    'manual_closed': 0, 'this_round_merge': False, 'additional_implementation_hours_counted': 0}
write('index.json', (json.dumps(index, ensure_ascii=False, indent=2) + '\n').encode('utf8'))
print(json.dumps({'ready': True, 'bound_files': len(files), 'bound_bytes': index['bound_bytes'],
    'index_sha256': sha((HERE / 'index.json').read_bytes()), 'combined_patch_sha256': index['combined_patch_sha256'],
    'combined_scene_sha256': apply['source_files']['behavior_pack/modern_projection/projection/scene.py']['sha256'],
    'guarded_production_files': len(current), 'original_sealed_candidates_unchanged': True}))
