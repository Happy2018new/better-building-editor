"""Seal offline candidate controls and verify protected workspace bytes."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCENE = 'behavior_pack/modern_projection/projection/scene.py'
WATER_GATES = ('animation', 'biome', 'budgets', 'default_path', 'editor', 'geometry',
               'lifecycle', 'neighbors', 'occupancy', 'projection_full', 'projection_missing',
               'public_gallery', 'side_uv', 'transparency', 'transparent_overlap', 'visibility')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def dump(path, value):
    assert not path.exists(), 'Never replace a sealed result'
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')


def main():
    before = read(HERE / 'workspace-boundary-before.json')
    actual = {name: sha((ROOT / name).read_bytes()) for name in before['files']}
    assert before['files'] == actual, 'Protected production/metadata changed'
    dump(HERE / 'workspace-boundary-after.json', {'files': actual, 'unchanged': True,
        'production_modified': False, 'metadata_modified': False, 'water39_contract_modified': False})
    provenance = read(HERE / 'provenance.json')
    for major in (2, 3):
        controls = read(HERE / ('controls-py%d.json' % major))
        assert controls['passed'] and controls['python'][0] == major
        assert controls['candidate_cold_tested'] is False and controls['MC_started'] is False
        assert len(controls['actual_files_compiled']) == 4
        assert len(controls['formula_rows']) == 8 and len(controls['dispatch_rows']) == 9
        assert len(controls['invalid_GUI_rejected']) == 12
        assert len(controls['historical_V4_formula_rows']) == 21
        for entry in controls['actual_files_compiled']:
            assert sha((HERE / entry['path']).read_bytes()) == entry['sha256']
        assert sha(Path(controls['interpreter']).read_bytes()) == controls['interpreter_sha256']

    reviews = {}
    for variant in ('baseline', 'candidate'):
        result = read(HERE / ('review-' + variant + '-v1.json'))['result']
        review = json.loads(next(c['text'] for c in result['content'] if c['type'] == 'text'))
        assert review['files_scanned'] == 2 and review['parse_health'] == {'failed': 0, 'ok': 2, 'recovered': 0}
        reviews[variant] = {f['finding_key'] for rule in review['rules'] for f in rule['findings']}
    assert reviews['baseline'] == reviews['candidate'] and len(reviews['candidate']) == 3

    baseline = (HERE / 'baseline' / SCENE).read_bytes()
    candidate = (HERE / 'candidate' / SCENE).read_bytes()
    # Replacing the candidate's exact changed callback with the original node
    # must recover the entire unchanged Scene AST (no other owner branch edits).
    base_tree, candidate_tree = ast.parse(baseline), ast.parse(candidate)
    base_callback = next(n for n in ast.walk(base_tree) if isinstance(n, ast.FunctionDef) and n.name == 'portal_view')
    changed_callback = next(n for n in ast.walk(candidate_tree) if isinstance(n, ast.FunctionDef) and n.name == 'portal_view')
    changed_callback.__dict__.clear()
    changed_callback.__dict__.update(base_callback.__dict__)
    assert ast.dump(base_tree) == ast.dump(candidate_tree)
    contract = read(ROOT / 'tools/data/liquid_product_owner_contract_v1.json')
    assert len(contract['source_sha256']) == 39
    proposed = {name: sha((HERE / 'candidate' / name).read_bytes().replace(b'\r\n', b'\n'))
                if name == SCENE else sha((ROOT / name).read_bytes().replace(b'\r\n', b'\n'))
                for name in contract['source_sha256']}
    differences = [{'path': name, 'current': expected, 'proposed': proposed[name]}
                   for name, expected in contract['source_sha256'].items() if proposed[name] != expected]
    assert len(differences) == 1 and differences[0]['path'] == SCENE
    dump(HERE / 'requalification-preview.json', {
        'hypothetical_only': True, 'generator_write_executed': False, 'qualifier_executed': False,
        'normalization': 'CRLF_to_LF_only', 'water_source_entries': 39,
        'source_differences_if_merged': differences,
        'water_gates_for_candidate': {gate: 'pending_new_source_evidence_and_official_qualification' for gate in WATER_GATES},
        'old_product_qualification_modified': False, 'candidate_cold_tested': False,
        'V4_actual_native_reuse_claimed': False,
    })
    dump(HERE / 'review-scope-first-zero-v1.json', {
        'attempts': ['modern_projection/projection/portal_profile', 'modern_projection/projection/scene'],
        'files_each': 0, 'accepted_as_review': False,
        'correction': 'Review both and only candidate files with no scope in fallback-directory mode; 2 files scanned',
        'baseline_candidate_final_findings_equal': sorted(reviews['candidate']),
    })
    dump(HERE / 'validation-invocations.json', {
        'workdir': ROOT.as_posix(),
        'calls': [
            {'interpreter': 'D:/Program/Python27/python.exe', 'arguments': ['-B', '.runtime/round-20261023/portal-anchor-candidate-v1/verify_candidate.py', '--output', '.runtime/round-20261023/portal-anchor-candidate-v1/controls-py2.json'], 'returncode': 0},
            {'interpreter': read(HERE / 'controls-py3.json')['interpreter'], 'arguments': ['-B', '-X', 'utf8', '.runtime/round-20261023/portal-anchor-candidate-v1/verify_candidate.py', '--output', '.runtime/round-20261023/portal-anchor-candidate-v1/controls-py3.json'], 'returncode': 0},
            {'command': 'git apply --check --directory=.runtime/round-20261023/portal-anchor-candidate-v1/baseline .runtime/round-20261023/portal-anchor-candidate-v1/candidate.patch', 'returncode': 0, 'filesystem_mutation': False},
        ], 'MC_started': False, 'candidate_native_tested': False,
    })
    entries = []
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            data = path.read_bytes()
            entries.append({'path': path.relative_to(HERE).as_posix(), 'bytes': len(data), 'sha256': sha(data)})
    dump(HERE / 'index.json', {
        'schema': 1, 'source_commit': provenance['source_commit'], 'entries': entries,
        'files': len(entries), 'bytes': sum(e['bytes'] for e in entries),
        'patch_sha256': provenance['patch_sha256'], 'protected_workspace_files': len(actual),
        'actual_Py2_Py3_controls_passed': True, 'production_modified': False,
        'metadata_modified': False, 'water39_contract_modified': False,
        'merge_authorized': False, 'MC_started': False, 'candidate_cold_tested': False,
        'qualification_awarded': False, 'manual_issues_closed': 0,
    })
    print(json.dumps({'sealed': True, 'files_excluding_index': len(entries),
        'bytes_excluding_index': sum(e['bytes'] for e in entries), 'protected_files_unchanged': len(actual),
        'water_source_differences_if_merged': len(differences), 'water_gates_pending': len(WATER_GATES),
        'new_review_findings': 0, 'index_sha256': sha((HERE / 'index.json').read_bytes()),
        'production_modified': False, 'MC_started': False, 'candidate_cold_tested': False}))


if __name__ == '__main__':
    main()
