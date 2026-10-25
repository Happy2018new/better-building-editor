"""Read back every archived original and scan only this evidence increment."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / '.runtime/lib-layout-callers-r29-v1'
CUTOVER = ROOT / 'docs/verification/LIBRARY_CUTOVER_R29.md'
OUTPUT = HERE / 'verification.json'
assert not OUTPUT.exists()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


index = json.loads((HERE / 'index.json').read_bytes())
rows, scans = [], {}
for reference in index['references']:
    storage = (HERE / reference['object']).read_bytes()
    obj = index['objects'][reference['raw_sha256']]
    assert sha(storage) == obj['stored_sha256'] and len(storage) == obj['stored_bytes']
    raw = gzip.decompress(storage)
    assert sha(raw) == reference['raw_sha256'] and len(raw) == reference['raw_bytes']
    assert raw == (SOURCE / reference['path']).read_bytes()
    target = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0, compresslevel=9) as output:
        output.write(raw)
    assert target.getvalue() == storage
    rows.append({'path': reference['path'], 'raw_sha256': sha(raw), 'stored_sha256': sha(storage),
                 'decompressed_original_equal': True, 'recompressed_bytes_equal': True})
    scans['original/' + reference['path']] = raw
assert len(rows) == 17 and {path.name for path in SOURCE.iterdir()} == {row['path'] for row in rows}
for path in HERE.iterdir():
    if path.suffix != '.gz':
        scans['package/' + path.name] = path.read_bytes()
scans['document/LIBRARY_CUTOVER_R29.md'] = CUTOVER.read_bytes()


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from strings(key)
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


patterns = {'api_token': r'\bsk-[A-Za-z0-9_-]{20,}',
            'github_token': r'\b(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,})',
            'bearer_token': r'(?i)\bbearer\s+[A-Za-z0-9._~+/-]{20,}',
            'private_key': r'-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----'}
matches = []
for name, raw in scans.items():
    values = [raw.decode('utf-8', 'replace')]
    try:
        values.extend(strings(json.loads(raw)))
    except (ValueError, UnicodeError):
        pass
    for kind, expression in patterns.items():
        if any(re.search(expression, value) for value in values):
            matches.append({'path': name, 'kind': kind})
assert not matches, matches

links = []
for path in (CUTOVER, HERE / 'README.md'):
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
        assert not re.match(r'\w+://', target), target
        destination = (path.parent / target.split('#')[0]).resolve()
        assert destination.is_file() or destination == OUTPUT
        links.append({'document': path.relative_to(ROOT).as_posix(), 'target': target})
scan_guard = json.loads((HERE / 'credential-scan.json').read_bytes())
for row in scan_guard['inputs']:
    label = row['input']
    if label.startswith('package/'):
        raw = (HERE / label[len('package/'):]).read_bytes()
    elif label.startswith('document/'):
        raw = CUTOVER.read_bytes()
    else:
        raw = (SOURCE / label).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
result = {'passed': True, 'new_process': True, 'objects_checked': len(index['objects']),
    'originals_checked': len(rows), 'rows': rows, 'links_checked': links,
    'credential_scan': {'matches': 0, 'patterns': sorted(patterns),
        'scope': '17 raw originals plus all current package metadata and cutover; this output file excluded',
        'inputs': [{'path': name, 'sha256': sha(raw), 'bytes': len(raw)} for name, raw in sorted(scans.items())]},
    'old_source_scan_and_all_original_bytes_unchanged': True,
    'gzip_deterministic_and_roundtrip_equal': True, 'raw_and_storage_sha_and_lengths_equal': True,
    'product_imported': False, 'tests_or_grid_repeated': False,
    'project_or_large_files_copied': False, 'MC_RPC_GPU_used': False, 'manual_issues_closed': 0}
OUTPUT.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + '\n', encoding='utf-8')
assert all((ROOT / row['document']).parent.joinpath(row['target'].split('#')[0]).is_file() for row in links)
print(json.dumps({'passed': True, 'originals': len(rows), 'objects': len(index['objects']),
                  'links': len(links), 'credential_scan_inputs': len(scans), 'credential_matches': 0}, sort_keys=True))
