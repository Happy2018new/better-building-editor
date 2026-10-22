"""Package BRG, cold D and official final admission without copying big archives."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
BRG = WORK.with_name('water-final-brg-v3')
D = WORK.with_name('water-default-final-v1')
ADMISSION = WORK.with_name('water-default-admission-v1')
OUT = ROOT / 'docs/evidence/water-final-qualification-r28-v1'
LIMIT = 239000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ref(path):
    path = path.resolve(strict=True)
    assert path.is_relative_to(ROOT)
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final-output', required=True, type=Path)
    args = parser.parse_args()
    final_output = args.final_output.resolve(strict=True)
    manifest = json.loads((final_output / 'qualification.json').read_bytes())
    receipt = json.loads((final_output / 'reviewed-final-host-receipt-v1.json').read_bytes())
    assert manifest['stage'] == 'product' and all(manifest['gates'].values())
    assert receipt['shared_admission_performed'] is True
    assert not OUT.exists()
    inputs = {}

    def add(label, path):
        assert label not in inputs and path.is_file(), (label, str(path))
        inputs[label] = path.resolve(strict=True)

    references = {'schema': 1, 'scope': 'Exact runtime paths/bytes/SHA; unselected PNGs and all source ZIPs remain in runtime.',
        'static_captures': {}, 'cohort_bindings': {}, 'source_archives': [],
        'bound_hosts': [], 'external_hosts': [], 'previous_FA_package': ref(ROOT / 'docs/evidence/water-current-FA-r28-v1/index.json')}
    originals = {}
    for label, cohort, names in (
        ('BRG', BRG, ('product-v2-b-v1.json', 'product-v2-r-v1.json', 'product-v2-g-v1.json')),
        ('D', D, ('default-r28-d.json',))):
        for name in names:
            report_path = cohort / name
            row = json.loads(report_path.read_bytes())
            assert row['completed'] and row['restored'] and row['source_unchanged'] and not row['cleanup_errors']
            originals[label + '/' + name] = row
            for path in (report_path, report_path.with_name(report_path.stem + '-host.json'),
                         report_path.with_name(report_path.stem + '-handles.json')):
                add(label + '/captures/' + path.name, path)
        # Camera PNGs are included in the same exact runtime reference inventory.
        references['static_captures'][label] = {
            'files': [ref(path) for path in sorted(cohort.glob('*.png'))] +
                     [ref(path) for path in sorted(cohort.glob('*.capture.json'))]}
        binding = json.loads((cohort / 'final-source-binding-v1.json').read_bytes())
        hosts = json.loads((cohort / 'prelaunch-host-binding-v1.json').read_bytes())
        references['cohort_bindings'][label] = {
            'binding': ref(cohort / 'final-source-binding-v1.json'),
            'source_contract_sha256': binding['source_contract_sha256'],
            'source_files': len(binding['source_sha256']), 'auxiliary_files': len(binding['auxiliary_sha256'])}
        for key in ('base', 'overlay'):
            archive = binding['source_provenance'][key]
            reference = ref(Path(archive['path']))
            assert reference['sha256'] == archive['sha256']
            references['source_archives'].append(dict(reference, cohort=label, included_in_package=False))
        for name, expected in hosts['host_sha256'].items():
            path = cohort / name
            reference = ref(path)
            assert reference['sha256'] == expected
            references['bound_hosts'].append(dict(reference, cohort=label))
            if path.suffix != '.zip':
                add(label + '/bound-hosts/' + name, path)
        for name, expected in hosts['external_host_sha256'].items():
            reference = ref(ROOT / name)
            assert reference['sha256'] == expected
            references['external_hosts'].append(dict(reference, cohort=label))
        for name in ('final-source-binding-v1.json', 'prelaunch-host-binding-v1.json',
            'group-execution-v1.json', 'cold-default-observation-v1.json',
            'world-baseline-v1.json', 'independent-restore-after-camera.json',
            'independent-restore-v1.json', 'helper-retirement-v1.json', 'precise-release-audit-v1.json',
            'continuous-handle-guard-v1.json', 'resize-background-v1.json',
            'launch/launch.json', 'launch/exact-exit.json', 'product-v2-camera-seam-v1.json',
            'product-v2-camera-seam-v1-host.json', 'product-v2-camera-seam-v1-handles.json'):
            add(label + '/cohort/' + name, cohort / name)
    for name in ('independent-restore-after-B.json', 'independent-restore-after-R.json',
                 'root-grant-brg-v1.json', 'root-static-review-v1.json',
                 'original-brg-gates-v1.json', 'editor-geometry-diagnosis-v1.json',
                 'gallery-F-shape-comparison-v1.json', 'offline-centering-controls-v1.json',
                 'analyze_matrix_v2.py', 'inspect_original_brg_gates_v1.py'):
        add('BRG/results/' + name, BRG / name)
    for path in sorted((BRG / 'analysis-BRG-v1').glob('*.json')):
        add('BRG/analysis/' + path.name, path)
    for name in ('root-grant-D-v1.json', 'root-static-review-v1.json'):
        add('D/cohort/' + name, D / name)
    for name in ('disposable-preparation-v1.json', 'prepare-failure-v1.json',
        'prepare_disposable.py', 'prepare_disposable_v2.py', 'prepare_final_host.py',
        'qualify_provisional.py', 'qualify_provisional_v2.py',
        'provisional-static-inspection-v1.json', 'provisional-static-inspection-v2.json',
        'root-scope-review-draft-v1.json', 'root-scope-review-confirmed-v1.json',
        'static-admission-contract-v1.json', 'actual-prelaunch-audit-D-v1.json',
        'qualify_final_v1.py', 'final-static-inspection-v1.json', 'root-final-review-confirmed-v1.json',
        'analyze_default.py', 'audit_release_D.py',
        'provisional-output-v1/qualification.json', 'provisional-output-v1/reviewed-host-receipt-v1.json'):
        add('admission/' + name, ADMISSION / name)
    for path in sorted((ADMISSION / 'default-analysis-v1').glob('*.json')):
        add('D/analysis/' + path.name, path)
    for path in sorted(final_output.glob('*.json')):
        add('official-final/' + path.name, path)
    for name in ('tools/generate_liquid_product_owner_contract.py', 'tools/qualify_water_product_r16.py',
        'tools/data/liquid_product_owner_contract_v1.json',
        'behavior_pack/modern_projection/projection/liquid_product_owner_data.py',
        'behavior_pack/modern_projection/projection/liquid_product_qualification_data.py'):
        add('official-shared/' + name, ROOT / name)
    selected = [
        ('BRG', 'product-v2-b-v1.json', 'missing_pool_wet'),
        ('BRG', 'product-v2-r-v1.json', 'editor_neighbor_stone_wet'),
        ('BRG', 'product-v2-r-v1.json', 'full_transparent_overlap_wet'),
        ('BRG', 'product-v2-g-v1.json', 'editor_gallery_wet')]
    selected += [('D', 'default-r28-d.json', route + '_' + case + '_wet')
        for route in ('editor', 'full', 'missing') for case in ('source', 'pool', 'wet_oak_fence')]
    selected += [('D', 'default-r28-d.json', 'missing_pool_wet_occupied'),
                 ('D', 'default-r28-d.json', 'missing_pool_wet_restored')]
    for cohort, name, label in selected:
        path = Path(originals[cohort + '/' + name]['captures'][label]['path'])
        add('selected-original-PNG/' + cohort + '/' + label + '.png', path)
        add('selected-original-PNG/' + cohort + '/' + label + '.capture.json', path.with_suffix('.capture.json'))
    references['static_PNG_count'] = sum(sum(row['path'].endswith('.png') for row in group['files'])
                                       for group in references['static_captures'].values())
    references['new_burst_directories_copied'] = 0
    reference_path = WORK / 'runtime-artifact-index-v1.json'
    with reference_path.open('x', encoding='ascii') as stream:
        json.dump(references, stream, indent=2, sort_keys=True)
        stream.write('\n')
    add('references/runtime-artifact-index-v1.json', reference_path)
    scanner_path = ROOT / '.runtime/round-20261022/root_review_wire_bundle_v3.py'
    redactor_path = ROOT / '.runtime/round-20261022/water-evidence-redaction-v4/package_v4_optimized.py'
    assert sha(scanner_path.read_bytes()) == '6c5bbd86dcf5fdcbf36ab709806beff4cb0230cbc0dad1d505b8fc172f95429e'
    scanner = load('final_original_scanner', scanner_path)
    redactor = load('final_reviewed_redactor', redactor_path)
    add('packaging/package.py', Path(__file__))
    add('packaging/verify_package.py', WORK / 'verify_package.py')
    add('packaging/reviewed_recursive_redactor.py', redactor_path)
    add('packaging/original_independent_scanner.py', scanner_path)
    raw_inputs = {label: path.read_bytes() for label, path in inputs.items()}
    for label, raw in raw_inputs.items():
        if inputs[label].suffix == '.json':
            redactor.discover(json.loads(raw))
    for path in (Path.home() / '.pyreact-debug/instances').glob('*/session.json'):
        redactor.discover(json.loads(path.read_bytes()))
    redactor.SECRET_PATTERN = redactor.compile_secret_pattern(redactor.secrets)
    OUT.mkdir()
    entries = []
    for ordinal, (label, path) in enumerate(sorted(inputs.items()), 1):
        raw = raw_inputs[label]
        clean, locations = (raw, []) if path.suffix == '.png' else redactor.sanitize_raw(raw)
        findings = (scanner.credentials(clean) if path.suffix == '.png'
                    else redactor.combined_credentials(scanner, clean))
        assert not findings, (label, findings)
        encoding = 'png' if path.suffix == '.png' else ('gzip' if len(clean) > 100000 else 'utf8')
        encoded = gzip.compress(clean, compresslevel=9, mtime=0) if encoding == 'gzip' else clean
        entry = {'logical_name': label, 'original_raw_path': path.relative_to(ROOT).as_posix(),
            'original_raw_sha256': sha(raw), 'original_raw_bytes': len(raw),
            'decoded_sanitized_sha256': sha(clean), 'decoded_sanitized_bytes': len(clean),
            'original_bytes_reconstructable': clean == raw, 'encoding': encoding,
            'redacted_fields': locations, 'derived_parts': []}
        pieces = [encoded[i:i + LIMIT] for i in range(0, len(encoded), LIMIT)] or [b'']
        stem = label + ('.gz' if encoding == 'gzip' else '')
        for number, piece in enumerate(pieces, 1):
            name = stem + ('.%03d' % number if len(pieces) > 1 else '')
            target = OUT / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(piece)
            entry['derived_parts'].append({'path': name, 'bytes': len(piece), 'sha256': sha(piece)})
        entries.append(entry)
        if ordinal % 15 == 0:
            print(json.dumps({'packaged': ordinal, 'of': len(inputs)}), flush=True)
    index = {'schema': 3, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'BRG original scoped gates, disposable provisional admission, cold D and official final shared qualification; historical F/A retained by exact package reference.',
        'entries': entries, 'entry_count': len(entries), 'single_file_limit_bytes': LIMIT,
        'complete_water_product_qualified': True, 'manual_closures_added': 0,
        'production_admission_performed_by': '/root', 'packaging_mutated_products_or_gates': False,
        'FA_BRG_source_contract_sha256': references['cohort_bindings']['BRG']['source_contract_sha256'],
        'D_source_contract_sha256': references['cohort_bindings']['D']['source_contract_sha256'],
        'historical_source_contracts_relabelled': False,
        'R_or_G_exact_per_case_geometry_accepted': False, 'old_failed_reports_regraded': False,
        'preserved_R_geometry_failures': 5, 'preserved_G_geometry_failures': 1,
        'preserved_dynamic_D_transparency_diagnostics': 3,
        'final_manifest_original_sha256': ref(final_output / 'qualification.json')['sha256'],
        'original_PNG_count': len(selected), 'all_static_PNG_count': references['static_PNG_count'],
        'all_burst_PNGs_retained_in_prior_FA_runtime_only': True,
        'large_source_archives_included': False, 'credential_findings': 0,
        'actual_exit_codes': {'BRG': {'game': '0xC0000409', 'mcdk': '0x00000000'},
                              'D': {'game': '0xC0000409', 'mcdk': '0x00000000'}}}
    raw = (json.dumps(index, indent=2, sort_keys=True) + '\n').encode('ascii')
    assert len(raw) < 240000 and not redactor.combined_credentials(scanner, raw)
    (OUT / 'index.json').write_bytes(raw)
    files = [path for path in OUT.rglob('*') if path.is_file()]
    result = {'passed': True, 'package': OUT.relative_to(ROOT).as_posix(),
        'index_sha256': sha(raw), 'entries': len(entries), 'stored_files': len(files),
        'stored_bytes': sum(path.stat().st_size for path in files),
        'max_file_bytes': max(path.stat().st_size for path in files),
        'original_PNG_count': len(selected), 'credential_findings': 0,
        'source_archives_included': False, 'qualification_or_owner_mutation_performed': False,
        'manual_closures_added': 0}
    assert result['max_file_bytes'] < 240000
    with (WORK / 'package-review-v1.json').open('x', encoding='ascii') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
