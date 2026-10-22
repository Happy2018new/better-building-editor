"""Small cold-pool proof with exact raw/sanitized hashes and no source archive."""
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
ROUND = WORK.parent
OUT = ROOT / 'docs/evidence/water-pool-geometry-cold-r28-v1'
LIMIT = 240000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    assert not OUT.exists()
    inputs = {}

    def add(label, path):
        path = path.resolve()
        assert label not in inputs and path.is_file() and path.is_relative_to(ROOT)
        inputs[label] = path

    for label, folder in (
            ('cold', 'water-pool-geometry-cold-v1'),
            ('preflight', 'water-pool-geometry-preflight-v1'),
            ('analysis', 'water-pool-geometry-analysis-v1'),
            ('shared-validation', 'water-shared-hook-validation-v1')):
        directory = ROUND / folder
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.suffix in ('.py', '.json', '.txt', '.png'):
                add(label + '/' + path.name, path)
    cold = ROUND / 'water-pool-geometry-cold-v1'
    for name in ('launch/launch.json', 'launch/exact-exit.json'):
        add('cold/' + name, cold / name)
    for path in sorted((ROUND / 'water-pool-geometry-analysis-v1/result-v1').glob('*.json')):
        add('analysis/result-v1/' + path.name, path)
    binding = json.loads((cold / 'final-source-binding-v1.json').read_bytes())
    for name in ('liquid_product_deployment.py', 'scene.py'):
        path = Path(binding['project']) / 'behavior_pack/modern_projection/projection' / name
        assert sha(path.read_bytes()) == binding['source_sha256']['behavior_pack/modern_projection/projection/' + name]
        add('private-cold-source/' + name, path)
    validation = json.loads((ROUND / 'water-shared-hook-validation-v1/validation-v1.json').read_bytes())
    for name, expected in validation['source_sha256'].items():
        path = ROOT / name
        assert sha(path.read_bytes()) == expected
        add('shared-source/' + name, path)
    previous = ROOT / 'docs/evidence/water-A-replay-F-pool-r28-v1/index.json'
    reference = {'index_path': previous.relative_to(ROOT).as_posix(), 'index_sha256': sha(previous.read_bytes()),
                 'scope': 'Preserved original failure, exact state, reviewed algebra and negative controls.',
                 'old_original_report_sha256': '84a0365844b2a9b7564b2a3b91241f29380e88fcd5ff76f5fb9937f2dc2e53c2'}
    reference_path = WORK / 'previous-evidence-reference-v1.json'
    reference_path.write_text(json.dumps(reference, sort_keys=True, indent=2) + '\n', encoding='ascii')
    add('packaging/previous-evidence-reference-v1.json', reference_path)
    add('packaging/package.py', Path(__file__))
    scanner_path = ROOT / '.runtime/round-20261022/root_review_wire_bundle_v3.py'
    redactor_path = ROOT / '.runtime/round-20261022/water-evidence-redaction-v4/package_v4_optimized.py'
    assert sha(scanner_path.read_bytes()) == '6c5bbd86dcf5fdcbf36ab709806beff4cb0230cbc0dad1d505b8fc172f95429e'
    scanner = module('pool_independent_scanner', scanner_path)
    redactor = module('pool_recursive_redactor', redactor_path)
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
        for number, piece in enumerate(pieces, 1):
            name = stem + ('.%03d' % number if len(pieces) > 1 else '')
            target = OUT / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(piece)
            entry['derived_parts'].append({'path': name, 'bytes': len(piece), 'sha256': sha(piece)})
        entries.append(entry)
    index = {'schema': 3, 'created_at_utc': datetime.now(timezone.utc).isoformat(), 'entries': entries,
             'entry_count': len(entries), 'single_file_limit_bytes': LIMIT,
             'scope': 'One private cold editor pool geometry candidate, wet/dry and actual canvas/clip; shared minimal hook regressions.',
             'previous_failure_reference': reference, 'original_PNG_count': 2,
             'geometry_candidate_native_pool_passed': True, 'complete_water_product_qualified': False,
             'manual_closures_added': 0, 'large_source_archives_included': False,
             'credential_findings': 0, 'full_frozen_matrix_completed': False,
             'private_cold_scene_has_new_book_hook': False,
             'actual_exit_codes': {'game': '0xC0000409', 'mcdk': '0x00000000'}}
    index_bytes = (json.dumps(index, sort_keys=True, indent=2) + '\n').encode('ascii')
    assert len(index_bytes) <= LIMIT and not redactor.combined_credentials(scanner, index_bytes)
    (OUT / 'index.json').write_bytes(index_bytes)
    stored = [path for path in OUT.rglob('*') if path.is_file()]
    assert max(path.stat().st_size for path in stored) <= LIMIT
    result = {'passed': True, 'package': OUT.relative_to(ROOT).as_posix(),
              'index_sha256': sha(index_bytes), 'entries': len(entries), 'stored_files': len(stored),
              'stored_bytes': sum(path.stat().st_size for path in stored),
              'max_file_bytes': max(path.stat().st_size for path in stored),
              'original_PNG_count': 2, 'credential_findings': 0, 'source_archives_included': False}
    (WORK / 'package-review-v1.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
