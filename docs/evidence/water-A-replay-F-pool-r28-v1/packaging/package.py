"""Small selected evidence: reused A originals, preserved failed F, geometry proposal."""
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
OUT = ROOT / 'docs/evidence/water-A-replay-F-pool-r28-v1'
ROUND = WORK.parent
F = ROUND / 'water-formal-f-editor-v2'
A = ROUND / 'water-r27-A-product-replay-v1'
GEOMETRY = ROUND / 'water-geometry-readiness-v1'
LIMIT = 240000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    assert not OUT.exists()
    inputs = {}

    def add(label, path):
        path = Path(path).resolve()
        assert label not in inputs and path.is_file() and path.is_relative_to(ROOT)
        inputs[label] = path

    for path in A.glob('*'):
        if path.is_file() and path.suffix in ('.py', '.json'):
            add('A-replay/' + path.name, path)
    add('A-replay/root-water-A-review-v1.json', ROUND / 'root-water-A-review-v1.json')
    for name in ('product-v2-f-editor-v1.json', 'product-v2-f-editor-v1-host.json',
                 'product-v2-f-editor-v1-handles.json', 'final-source-binding-v1.json',
                 'prelaunch-host-binding-v1.json', 'plan-v1.json', 'root-grant-v1.json',
                 'cold-default-observation-v1.json', 'resize-background-v1.json', 'world-baseline-v1.json',
                 'independent-restore-v1.json', 'continuous-handle-guard-v1.json', 'helper-retirement-v1.json',
                 'group-execution-v1.json', 'host-changes-v1.patch', 'F-editor.stdout.txt',
                 'F-editor.stderr.txt', 'launch/launch.json', 'launch/exact-exit.json'):
        add('F-failure/' + name, F / name)
    for path in sorted(F.glob('*.py')):
        add('F-host/' + path.name, path)
    capture = json.loads((F / 'product-v2-f-editor-v1.json').read_bytes())
    assert capture['completed'] is False and capture['restored'] is True and len(capture['captures']) == 14
    assert 'Liquid skeleton model ID did not become ready' in capture['error']
    for label, row in sorted(capture['captures'].items()):
        path = Path(row['path'])
        assert sha(path.read_bytes()) == row['sha256'] and path.stat().st_size == row['bytes']
        add('F-PNG/' + label + '.png', path)
        add('F-PNG/' + label + '.capture.json', path.with_suffix('.capture.json'))
    for path in sorted(GEOMETRY.iterdir()):
        if path.is_file() and path.suffix in ('.py', '.json', '.patch'):
            add('geometry-proposal/' + path.name, path)
    for path in sorted((ROUND / 'water-formal-f-editor-preflight-v2').iterdir()):
        if path.is_file() and path.suffix in ('.py', '.json', '.txt'):
            add('F-preflight/' + path.name, path)
    old_index_path = ROOT / 'docs/evidence/water-fullA-flow-r27-v2/index.json'
    old_index = json.loads(old_index_path.read_bytes())
    a_report_path = ROOT / '.runtime/round-20261022/water-merged-fullA-v2/product-v2-a-v1.json'
    a_report = json.loads(a_report_path.read_bytes())
    references = []
    for label, row in sorted(a_report['captures'].items()):
        matches = [entry for entry in old_index['entries'] if entry['original_raw_sha256'] == row['sha256']
                   and entry['encoding'] == 'png' and entry['original_bytes_reconstructable']]
        assert len(matches) == 1, label
        references.append({'capture_label': label, 'original_PNG_sha256': row['sha256'],
                           'existing_bundle_logical_name': matches[0]['logical_name']})
    assert len(references) == 30
    reference = {'schema': 1, 'existing_index_path': old_index_path.relative_to(ROOT).as_posix(),
                 'existing_index_sha256': sha(old_index_path.read_bytes()),
                 'original_A_report_sha256': sha(a_report_path.read_bytes()),
                 'static_PNG_count': len(references), 'PNG_bytes_duplicated': 0, 'captures': references,
                 'original_bursts_and_source_archive': 'Retained in R27 runtime; selected originals and replay manifests already retained in referenced R27 bundle.'}
    reference_path = WORK / 'A-original-reference-v1.json'
    reference_path.write_text(json.dumps(reference, sort_keys=True, indent=2) + '\n', encoding='ascii')
    add('A-replay/A-original-reference-v1.json', reference_path)
    add('packaging/package.py', Path(__file__))
    scanner_path = ROOT / '.runtime/round-20261022/root_review_wire_bundle_v3.py'
    redactor_path = ROOT / '.runtime/round-20261022/water-evidence-redaction-v4/package_v4_optimized.py'
    assert sha(scanner_path.read_bytes()) == '6c5bbd86dcf5fdcbf36ab709806beff4cb0230cbc0dad1d505b8fc172f95429e'
    scanner = load('reviewed_independent_scanner', scanner_path)
    redactor = load('reviewed_recursive_redactor', redactor_path)
    add('packaging/reviewed_recursive_redactor.py', redactor_path)
    add('packaging/original_independent_scanner.py', scanner_path)
    original = {label: path.read_bytes() for label, path in inputs.items()}
    for label, raw in original.items():
        if inputs[label].suffix == '.json':
            redactor.discover(json.loads(raw))
    for path in (Path.home() / '.pyreact-debug/instances').glob('*/session.json'):
        redactor.discover(json.loads(path.read_bytes()))
    redactor.SECRET_PATTERN = redactor.compile_secret_pattern(redactor.secrets)
    OUT.mkdir()
    entries = []
    for label, path in sorted(inputs.items()):
        raw = original[label]
        clean, locations = (raw, []) if path.suffix == '.png' else redactor.sanitize_raw(raw)
        assert not (scanner.credentials(clean) if path.suffix == '.png'
                    else redactor.combined_credentials(scanner, clean)), label
        encoding = 'png' if path.suffix == '.png' else ('gzip' if len(clean) > 100000 else 'utf8')
        encoded = gzip.compress(clean, mtime=0) if encoding == 'gzip' else clean
        entry = {'logical_name': label, 'original_raw_path': path.relative_to(ROOT).as_posix(),
                 'original_raw_sha256': sha(raw), 'original_raw_bytes': len(raw),
                 'decoded_sanitized_sha256': sha(clean), 'decoded_sanitized_bytes': len(clean),
                 'original_bytes_reconstructable': clean == raw, 'encoding': encoding,
                 'redacted_fields': locations, 'derived_parts': []}
        pieces = [encoded[i:i + LIMIT] for i in range(0, len(encoded), LIMIT)] or [b'']
        stem = label + ('.gz' if encoding == 'gzip' else '')
        for index, piece in enumerate(pieces, 1):
            name = stem + ('.%03d' % index if len(pieces) > 1 else '')
            target = OUT / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(piece)
            entry['derived_parts'].append({'path': name, 'bytes': len(piece), 'sha256': sha(piece)})
        entries.append(entry)
    index = {'schema': 3, 'created_at_utc': datetime.now(timezone.utc).isoformat(), 'entries': entries,
             'entry_count': len(entries), 'single_file_limit_bytes': LIMIT,
             'scope': 'R27 A original-PNG visible-animation replay; new R28 F pool readiness failure and proposed geometry diagnosis.',
             'existing_A_original_reference': reference, 'new_F_original_PNG_count': len(capture['captures']),
             'A_passed': True, 'F_passed': False, 'geometry_proposal_native_tested': False,
             'complete_water_product_qualified': False, 'manual_closures_added': 0,
             'large_source_archives_included': False, 'credential_findings': 0}
    index_bytes = (json.dumps(index, sort_keys=True, indent=2) + '\n').encode('ascii')
    assert len(index_bytes) <= LIMIT and not redactor.combined_credentials(scanner, index_bytes)
    (OUT / 'index.json').write_bytes(index_bytes)
    stored = list(path for path in OUT.rglob('*') if path.is_file())
    assert max(path.stat().st_size for path in stored) <= LIMIT
    result = {'passed': True, 'package': str(OUT.relative_to(ROOT)), 'index_sha256': sha(index_bytes),
              'entries': len(entries), 'stored_files': len(stored), 'stored_bytes': sum(path.stat().st_size for path in stored),
              'max_file_bytes': max(path.stat().st_size for path in stored), 'original_PNG_count': 14,
              'A_static_PNG_references': 30, 'credential_findings': 0, 'source_archives_included': False}
    (WORK / 'package-review-v1.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
