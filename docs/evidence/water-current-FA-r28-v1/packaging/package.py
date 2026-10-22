"""Compact same-source F/A proof; retain every original and burst in runtime."""
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
COHORT = WORK.with_name('water-final-matrix-v1')
BRG = WORK.with_name('water-final-brg-v3')
OUT = ROOT / 'docs/evidence/water-current-FA-r28-v1'
LIMIT = 239000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def file_ref(path):
    path = path.resolve(strict=True)
    assert path.is_relative_to(ROOT)
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}


def main():
    assert not OUT.exists()
    inputs = {}

    def add(label, path):
        assert label not in inputs and path.is_file()
        inputs[label] = path.resolve()

    report_names = ('product-v2-f-editor-v1.json', 'product-v2-f-full-v2.json',
                    'product-v2-f-missing-v2.json', 'product-v2-a-v1.json')
    originals = {}
    references = {'schema': 1, 'source_cohort_sha256':
        '4e4eb7fff2b3dd8d6519ce70c7290c911f6c54ff2c9dbd0e7d3cf160a6b54749',
        'scope': 'Exact original paths/hashes only; all burst bytes and unselected PNGs remain in runtime.',
        'static_captures': {}, 'bursts': {}, 'large_archives': [], 'external_capture_oracles': []}
    for name in report_names:
        path = COHORT / name
        add('captures/' + name, path)
        for suffix in ('-host.json', '-handles.json'):
            add('captures/' + path.stem + suffix, path.with_name(path.stem + suffix))
        row = json.loads(path.read_bytes())
        assert row['completed'] and row['restored'] and row['source_unchanged']
        assert not row['cleanup_errors']
        originals[name] = row
        references['static_captures'][name] = {
            'original_report': file_ref(path), 'rows': len(row['rows']),
            'captures': {label: {'png': file_ref(Path(capture['path'])),
                'receipt': file_ref(Path(capture['path']).with_suffix('.capture.json'))}
                for label, capture in sorted(row['captures'].items())}}
        for label, burst in sorted(row['flow_bursts'].items()):
            capture = burst['capture']
            directory = Path(capture['output_directory'])
            paths = sorted(path for path in directory.rglob('*') if path.is_file())
            for expected in capture['artifacts']:
                assert file_ref(Path(expected['path']))['sha256'] == expected['sha256']
                assert Path(expected['path']).stat().st_size == expected['bytes']
            manifest = file_ref(Path(capture['native_manifest_file']['path']))
            assert manifest['sha256'] == capture['native_manifest_file']['sha256']
            references['bursts'][label] = {'report': name, 'route': burst['row']['route'],
                'case': burst['row']['case'], 'wrapper': file_ref(Path(capture['wrapper_receipt'])),
                'native_manifest': manifest, 'planned_duration_ms': capture['request']['planned_duration_ms'],
                'maximum_gap_ms': capture['request']['max_gap_ms'],
                'files': [file_ref(path) for path in paths],
                'png_count': sum(path.suffix == '.png' for path in paths),
                'attempted_receipts': sum(path.name.endswith('.capture.json') for path in paths),
                'PNG_bytes_copied_to_package': 0}
    binding = json.loads((COHORT / 'final-source-binding-v1.json').read_bytes())
    for key in ('base', 'overlay'):
        value = binding['source_provenance'][key]
        ref = file_ref(Path(value['path']))
        assert ref['sha256'] == value['sha256']
        references['large_archives'].append(dict(ref, included_in_package=False))
    for path in (
            ROOT / '.runtime/round-20261022/water-camera-extractor-seam-candidate-v1/candidate_extractor.py',
            ROOT / '.runtime/round-20261022/water-camera-extractor-seam-candidate-v1/controls-v1/report.json',
            ROOT / '.runtime/round-20261021/water-startup-protocol-v2/host-contract-v1.json'):
        references['external_capture_oracles'].append(file_ref(path))
    references.update(static_PNGs=sum(len(value['captures']) for value in references['static_captures'].values()),
                      burst_count=len(references['bursts']),
                      burst_PNG_count=sum(value['png_count'] for value in references['bursts'].values()))
    reference_path = WORK / 'runtime-artifact-index-v1.json'
    with reference_path.open('x', encoding='ascii') as stream:
        json.dump(references, stream, indent=2, sort_keys=True)
        stream.write('\n')
    add('references/runtime-artifact-index-v1.json', reference_path)
    for path in sorted((COHORT / 'analysis-F-A-v3').glob('*.json')):
        add('analysis/' + path.name, path)
    add('preserved-refusal/analysis-after-F-full-v1-summary.json',
        COHORT / 'analysis-after-F-full-v1/summary.json')
    for name in ('B.stderr.txt', 'B.stdout.txt', 'group-execution-v1.json',
                 'independent-restore-after-camera.json', 'independent-restore-after-F-editor.json',
                 'independent-restore-after-F-full.json', 'independent-restore-after-F-missing.json',
                 'independent-restore-after-A.json', 'independent-restore-v1.json',
                 'helper-retirement-v1.json', 'precise-release-audit-v1.json',
                 'precise-release-audit-v2.json', 'continuous-handle-guard-v1.json',
                 'cold-default-observation-v1.json', 'resize-background-v1.json',
                 'world-baseline-v1.json', 'launch/launch.json', 'launch/exact-exit.json',
                 'final-source-binding-v1.json', 'source-synthesis-v1.json',
                 'prelaunch-host-binding-v1.json', 'prelaunch-host-extension-v2.json',
                 'plan-v2.json', 'root-grant-v1.json', 'product-v2-camera-seam-v1.json',
                 'host-transform-preflight-v1.json'):
        add('cohort/' + name, COHORT / name)
    for name in ('analyze_matrix.py', 'analyze_matrix_v2.py', 'calibration_host.py',
                 'run_flow.py', 'run_group_v2.py', 'run_camera.py', 'run_frozen_editor.py',
                 'run_product_v2_f_world_v2.py', 'run_f_world_cutoff_v2.py',
                 'flow_restore.py', 'world_readback.py', 'source_provenance.py'):
        add('hosts/' + name, COHORT / name)
    for name in ('plan-v3.json', 'stage-mapping-preflight-v3.json', 'host-changes-v3.patch',
                 'prepare_brg.py'):
        add('BRG-static-only/' + name, BRG / name)
    selected = (
        ('product-v2-f-editor-v1.json', 'editor_source_wet'),
        ('product-v2-f-editor-v1.json', 'editor_pool_wet'),
        ('product-v2-f-full-v2.json', 'full_source_wet'),
        ('product-v2-f-missing-v2.json', 'missing_pool_wet'),
        ('product-v2-a-v1.json', 'editor_flow_east_wet'))
    for name, label in selected:
        path = Path(originals[name]['captures'][label]['path'])
        add('selected-original-PNG/' + label + '.png', path)
        add('selected-original-PNG/' + label + '.capture.json', path.with_suffix('.capture.json'))
    scanner_path = ROOT / '.runtime/round-20261022/root_review_wire_bundle_v3.py'
    redactor_path = ROOT / '.runtime/round-20261022/water-evidence-redaction-v4/package_v4_optimized.py'
    assert sha(scanner_path.read_bytes()) == '6c5bbd86dcf5fdcbf36ab709806beff4cb0230cbc0dad1d505b8fc172f95429e'
    scanner = load_module('water_FA_original_scanner', scanner_path)
    redactor = load_module('water_FA_reviewed_redactor', redactor_path)
    add('packaging/package.py', Path(__file__))
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
        if ordinal % 10 == 0:
            print(json.dumps({'packaged': ordinal, 'of': len(inputs)}), flush=True)
    index = {'schema': 3, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
             'scope': 'Current shared-source three-route F and A; first B host-path refusal and exact release. BRG is static preparation only.',
             'entries': entries, 'entry_count': len(entries), 'single_file_limit_bytes': LIMIT,
             'current_source_F_passed': True, 'current_source_A_passed': True,
             'complete_water_product_qualified': False, 'manual_closures_added': 0,
             'production_admission_performed': False, 'B_capture_started': False,
             'original_PNG_count': len(selected), 'all_static_PNG_count': references['static_PNGs'],
             'burst_PNGs_referenced_only': references['burst_PNG_count'],
             'large_source_archives_included': False, 'credential_findings': 0,
             'source_contract_sha256': binding['source_contract_sha256'],
             'root_head': binding['root_head'], 'source_files': binding['source_count'],
             'auxiliary_files': binding['auxiliary_count'],
             'actual_exit_codes': {'game': '0xC0000409', 'mcdk': '0x00000000'}}
    raw = (json.dumps(index, sort_keys=True, indent=2) + '\n').encode('ascii')
    assert len(raw) < 240000 and not redactor.combined_credentials(scanner, raw)
    (OUT / 'index.json').write_bytes(raw)
    files = [path for path in OUT.rglob('*') if path.is_file()]
    result = {'passed': True, 'package': OUT.relative_to(ROOT).as_posix(),
              'index_sha256': sha(raw), 'entries': len(entries), 'stored_files': len(files),
              'stored_bytes': sum(path.stat().st_size for path in files),
              'max_file_bytes': max(path.stat().st_size for path in files),
              'original_PNG_count': len(selected), 'burst_PNGs_referenced_only': references['burst_PNG_count'],
              'credential_findings': 0, 'source_archives_included': False,
              'qualification_or_owner_mutation_performed': False, 'manual_closures_added': 0}
    assert result['max_file_bytes'] < 240000 and result['stored_bytes'] < 8 * 1024 * 1024
    with (WORK / 'package-review-v1.json').open('x', encoding='ascii') as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
