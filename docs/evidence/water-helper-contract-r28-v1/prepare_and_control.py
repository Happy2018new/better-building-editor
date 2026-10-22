"""One-shot isolated owner-source extension controls; never runs a qualifier."""
import ast
import difflib
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
COMBINED = ROOT / '.runtime/round-20261023/scene-portal-combination-v1/combined'
PREFIX = 'behavior_pack/modern_projection/projection/'
HELPER = PREFIX + 'scene_owner.py'
GENERATOR = 'tools/generate_liquid_product_owner_contract.py'
CHECKER = 'tools/check_liquid_product_owner_contract.py'
CONTRACT = 'tools/data/liquid_product_owner_contract_v1.json'
OUTPUT = PREFIX + 'liquid_product_owner_data.py'
CUTOFF = datetime(2026, 10, 22, 23, 0, tzinfo=timezone.utc)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def dump(path, value):
    assert not path.exists(), 'Never overwrite an existing evidence record'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')


def require_time():
    assert datetime.now(timezone.utc) < CUTOFF, 'Root offline-preparation cutoff reached'


def snapshot(folder):
    return {p.relative_to(folder).as_posix(): sha(p.read_bytes()) for p in folder.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}


def main():
    require_time()
    assert not (HERE / 'projects').exists()
    contract = read(ROOT / CONTRACT)
    assert len(contract['source_sha256']) == 39
    guard_paths = set(contract['source_sha256']) | {
        GENERATOR, CHECKER, CONTRACT, OUTPUT, PREFIX + 'liquid_product_qualification_data.py',
        'tools/qualify_water_product_r16.py', 'tools/probe_product_water.py',
        'tools/audit_water_source_closure_r15.py',
    }
    protected = {name: sha((ROOT / name).read_bytes()) for name in sorted(guard_paths)}
    combined_guard = {p.relative_to(COMBINED).as_posix(): sha(p.read_bytes())
                      for p in COMBINED.rglob('*.py')}
    dump(HERE / 'boundary-before.json', {'workspace': protected, 'combined': combined_guard})
    original_generator = (ROOT / GENERATOR).read_bytes()
    old = b"'liquid_projection', 'liquid_viewport', 'liquid_scene', 'scene', 'world_projection',"
    new = b"'liquid_projection', 'liquid_viewport', 'liquid_scene', 'scene', 'scene_owner', 'world_projection',"
    assert original_generator.count(old) == 1
    changed_generator = original_generator.replace(old, new, 1)
    patch = ''.join(difflib.unified_diff(original_generator.decode('utf8').splitlines(True),
                                        changed_generator.decode('utf8').splitlines(True),
                                        fromfile='a/' + GENERATOR, tofile='b/' + GENERATOR))
    (HERE / 'generator.patch').write_text(patch, encoding='utf8', newline='\n')
    for label, code in [('baseline39', original_generator), ('candidate40', changed_generator)]:
        project = HERE / 'projects' / label
        for name in contract['source_sha256']:
            source = COMBINED / name if name == PREFIX + 'scene.py' else ROOT / name
            target = project / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        for name in (HELPER, PREFIX + 'portal_profile.py'):
            target = project / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((COMBINED / name).read_bytes())
        (project / 'tools/data').mkdir(parents=True, exist_ok=True)
        (project / GENERATOR).write_bytes(code)
        (project / CHECKER).write_bytes((ROOT / CHECKER).read_bytes())
        assert not (project / PREFIX / 'liquid_product_qualification_data.py').exists()

    calls = []

    def run(label, project, tool, extra, expected):
        require_time()
        command = [sys.executable, '-B', '-X', 'utf8', str(project / tool)] + extra
        result = subprocess.run(command, cwd=project, capture_output=True, text=True, encoding='utf8',
                                timeout=20, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        receipt = {'label': label, 'command': command, 'cwd': str(project),
                   'returncode': result.returncode, 'expected_returncode': expected,
                   'stdout': result.stdout, 'stderr': result.stderr,
                   'at_utc': datetime.now(timezone.utc).isoformat()}
        dump(HERE / 'calls' / (label + '.json'), receipt)
        calls.append(receipt)
        assert result.returncode == expected, label
        return receipt

    baseline = HERE / 'projects/baseline39'
    candidate = HERE / 'projects/candidate40'
    run('baseline-generate39', baseline, GENERATOR, [], 0)
    run('baseline-check39', baseline, GENERATOR, ['--check'], 0)
    old_contract = (baseline / CONTRACT).read_bytes()
    helper_original = (baseline / HELPER).read_bytes()
    (baseline / HELPER).write_bytes(helper_original + b'\n# deliberate private helper drift\n')
    leak = run('baseline-helper-drift-not-detected', baseline, GENERATOR, ['--check'], 0)
    leak_checker = run('baseline-checker-helper-drift-not-detected', baseline, CHECKER, ['--check'], 0)
    assert (baseline / CONTRACT).read_bytes() == old_contract
    (baseline / HELPER).write_bytes(helper_original)

    run('candidate-generate40', candidate, GENERATOR, [], 0)
    before_check = snapshot(candidate)
    run('candidate-check40', candidate, GENERATOR, ['--check'], 0)
    good_checker = run('candidate-checker40', candidate, CHECKER, ['--check'], 0)
    assert snapshot(candidate) == before_check
    generated = read(candidate / CONTRACT)
    baseline_generated = read(baseline / CONTRACT)
    assert len(generated['source_sha256']) == 40 and len(baseline_generated['source_sha256']) == 39
    assert set(generated['source_sha256']) - set(baseline_generated['source_sha256']) == {HELPER}
    assert all(generated['source_sha256'][name] == value for name, value in baseline_generated['source_sha256'].items())
    assert generated['source_sha256'][HELPER] == sha(helper_original.replace(b'\r\n', b'\n'))
    assert generated['generator_sha256'] == sha(changed_generator.replace(b'\r\n', b'\n'))
    assert generated['schema_version'] == baseline_generated['schema_version'] == 1
    assert generated['normalization'] == baseline_generated['normalization'] == 'CRLF_to_LF_only'

    original_outputs = {name: (candidate / name).read_bytes() for name in (CONTRACT, OUTPUT)}
    (candidate / HELPER).write_bytes(helper_original + b'\n# deliberate private helper drift\n')
    drift = run('candidate-helper-drift-rejected', candidate, GENERATOR, ['--check'], 1)
    drift_checker = run('candidate-checker-helper-drift-rejected', candidate, CHECKER, ['--check'], 1)
    changed = json.loads(drift_checker['stdout'])
    assert [row['path'] for row in changed['source_differences']] == [HELPER]
    assert all((candidate / name).read_bytes() == data for name, data in original_outputs.items())
    (candidate / HELPER).write_bytes(helper_original)
    run('candidate-helper-restored', candidate, GENERATOR, ['--check'], 0)

    # Actual line-ending normalization remains exactly the existing contract.
    (candidate / HELPER).write_bytes(helper_original.replace(b'\r\n', b'\n'))
    run('candidate-helper-LF-normalization', candidate, GENERATOR, ['--check'], 0)
    (candidate / HELPER).write_bytes(helper_original)
    held = candidate / (HELPER + '.held-private-input')
    (candidate / HELPER).rename(held)
    missing = run('candidate-missing-helper-rejected', candidate, GENERATOR, ['--check'], 1)
    missing_checker = run('candidate-checker-missing-helper-rejected', candidate, CHECKER, ['--check'], 1)
    missing_json = json.loads(missing_checker['stdout'])
    assert any(row['path'] == HELPER and row['status'] == 'removed' for row in missing_json['source_differences'])
    assert all((candidate / name).read_bytes() == data for name, data in original_outputs.items())
    held.rename(candidate / HELPER)
    run('candidate-final-check40', candidate, GENERATOR, ['--check'], 0)

    # Execute only the actual pure snapshot functions, never the host imports.
    source = (ROOT / 'tools/probe_product_water.py').read_bytes()
    tree = ast.parse(source)
    names = {'fingerprint', 'snapshot_sources', 'snapshot_digest'}
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(selected) == len(names)
    namespace = {'hashlib': hashlib, 'json': json}
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<actual-water-source-snapshot-functions>', 'exec'), namespace)
    actual_snapshot = namespace['snapshot_sources'](candidate)
    assert actual_snapshot[HELPER] == sha(helper_original)

    # Existing historical audit is not the admission tool: it assumes every
    # current owner path was already present in each old source archive.
    audit = (ROOT / 'tools/audit_water_source_closure_r15.py').read_text(encoding='utf8')
    assert 'frozen=normalized(archive.read(relative))' in audit
    require_time()
    assert protected == {name: sha((ROOT / name).read_bytes()) for name in protected}
    assert combined_guard == {p.relative_to(COMBINED).as_posix(): sha(p.read_bytes()) for p in COMBINED.rglob('*.py')}
    dump(HERE / 'boundary-after.json', {'workspace': protected, 'combined': combined_guard,
        'unchanged': True, 'production_modified': False, 'old_metadata_modified': False})
    summary = {
        'passed': True, 'python': list(sys.version_info[:3]), 'interpreter': sys.executable,
        'interpreter_sha256': sha(Path(sys.executable).read_bytes()),
        'actual_CLI_calls': len(calls), 'baseline_sources': 39, 'candidate_sources': 40,
        'only_added_source': HELPER, 'existing_39_source_hashes_unchanged_between_private_projects': True,
        'generator_patch_sha256': sha((HERE / 'generator.patch').read_bytes()),
        'baseline_unbound_helper_false_negative_demonstrated': True,
        'candidate_helper_drift_rejected': True, 'candidate_missing_helper_rejected': True,
        'candidate_CRLF_to_LF_normalization_unchanged': True,
        'actual_snapshot_sources_includes_helper': True,
        'source_schema_version_unchanged': 1,
        'candidate_contract_sha256': sha((candidate / CONTRACT).read_bytes()),
        'candidate_owner_module_sha256': sha((candidate / OUTPUT).read_bytes()),
        'all_checks_read_only_to_generated_outputs': True,
        'workspace_protected_files': len(protected), 'combined_source_files': len(combined_guard),
        'qualifier_executed': False, 'qualification_copied': False,
        'MC_started': False, 'production_modified': False, 'old_metadata_modified': False,
        'water_gates_requalified': 0, 'all_16_water_gates_still_pending_for_new_source': True,
        'completed_at_utc': datetime.now(timezone.utc).isoformat(),
    }
    dump(HERE / 'controls-summary.json', summary)
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
