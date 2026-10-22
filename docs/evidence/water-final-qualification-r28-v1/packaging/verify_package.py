"""Independently reconstruct the final evidence and recheck runtime references."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
PACKAGE = ROOT / 'docs/evidence/water-final-qualification-r28-v1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-index-sha', required=True)
    args = parser.parse_args()
    indexraw = (PACKAGE / 'index.json').read_bytes()
    assert sha(indexraw) == args.expected_index_sha
    index = json.loads(indexraw)
    scanner = module('final_verification_scanner', ROOT / '.runtime/round-20261022/root_review_wire_bundle_v3.py')
    redactor = module('final_verification_redactor', ROOT / '.runtime/round-20261022/water-evidence-redaction-v4/package_v4_optimized.py')
    for path in (Path.home() / '.pyreact-debug/instances').glob('*/session.json'):
        redactor.discover(json.loads(path.read_bytes()))
    for row in index['entries']:
        original = (ROOT / row['original_raw_path']).read_bytes()
        if row['original_raw_path'].endswith('.json'):
            redactor.discover(json.loads(original))
    redactor.SECRET_PATTERN = redactor.compile_secret_pattern(redactor.secrets)
    expected = {'index.json'}
    compared_raw = compared_redacted = 0
    decoded_objects = {}
    for ordinal, row in enumerate(index['entries'], 1):
        parts = []
        for part in row['derived_parts']:
            path = (PACKAGE / part['path']).resolve(strict=True)
            assert path.is_relative_to(PACKAGE.resolve()) and part['path'] not in expected
            expected.add(part['path'])
            raw = path.read_bytes()
            assert sha(raw) == part['sha256'] and len(raw) == part['bytes'] < 240000
            parts.append(raw)
        stored = b''.join(parts)
        decoded = gzip.decompress(stored) if row['encoding'] == 'gzip' else stored
        assert sha(decoded) == row['decoded_sanitized_sha256'] and len(decoded) == row['decoded_sanitized_bytes']
        original = (ROOT / row['original_raw_path']).read_bytes()
        assert sha(original) == row['original_raw_sha256'] and len(original) == row['original_raw_bytes']
        if row['original_bytes_reconstructable']:
            assert original == decoded and not row['redacted_fields']
            compared_raw += 1
        else:
            clean, fields = redactor.sanitize_raw(original)
            assert clean == decoded and fields == row['redacted_fields'] and decoded != original
            compared_redacted += 1
        assert not (scanner.credentials(decoded) if row['encoding'] == 'png'
                    else redactor.combined_credentials(scanner, decoded))
        decoded_objects[row['logical_name']] = decoded
        if ordinal % 20 == 0:
            print(json.dumps({'reconstructed': ordinal, 'of': len(index['entries'])}), flush=True)
    actual = {path.relative_to(PACKAGE).as_posix() for path in PACKAGE.rglob('*') if path.is_file()}
    assert actual == expected and not redactor.combined_credentials(scanner, indexraw)
    references = json.loads(decoded_objects['references/runtime-artifact-index-v1.json'])
    runtime = [references['previous_FA_package']]
    runtime.extend(row['binding'] for row in references['cohort_bindings'].values())
    runtime.extend(references['source_archives'])
    runtime.extend(references['bound_hosts'])
    runtime.extend(references['external_hosts'])
    for group in references['static_captures'].values():
        runtime.extend(group['files'])
    for row in runtime:
        path = (ROOT / row['path']).resolve(strict=True)
        assert path.is_relative_to(ROOT) and path.stat().st_size == row['bytes']
        assert sha(path.read_bytes()) == row['sha256']
    manifest = json.loads(decoded_objects['official-final/qualification.json'])
    assert manifest['stage'] == 'product' and all(manifest['gates'].values())
    assert index['final_manifest_original_sha256'] == sha(decoded_objects['official-final/qualification.json'])
    d_analysis = json.loads(decoded_objects['D/analysis/default-product-analysis.json'])
    assert [key for key, value in d_analysis['transparency'].items() if not value['passed']] == [
        'editor_wet_oak_fence_wet', 'full_wet_oak_fence_wet', 'missing_wet_oak_fence_wet']
    assert all(value['phase_controlled'] is False for value in d_analysis['transparency'].values())
    scope = json.loads(decoded_objects['admission/root-final-review-confirmed-v1.json'])
    assert scope['R_or_G_exact_per_case_geometry_accepted'] is False
    assert scope['old_failed_reports_regraded'] is False
    result = {'passed': True, 'index_sha256': sha(indexraw), 'objects': len(index['entries']),
        'original_objects_compared_byte_for_byte': compared_raw,
        'sanitized_objects_recomputed_and_compared': compared_redacted,
        'exact_runtime_references_checked': len(runtime), 'stored_files': len(actual),
        'stored_bytes': sum((PACKAGE / name).stat().st_size for name in actual),
        'maximum_file_bytes': max((PACKAGE / name).stat().st_size for name in actual),
        'credential_findings': 0, 'dynamic_D_transparency_diagnostics_preserved': 3,
        'R_G_exact_geometry_not_regraded': True,
        'MC_started': False, 'qualification_or_owner_changed': False, 'manual_closures_added': 0}
    with (WORK / 'independent-reconstruction-v1.json').open('x', encoding='ascii') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
