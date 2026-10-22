"""Independent source/byte and recursive credential review, with no runtime calls."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / '.runtime/round-20261022/books-wire-v1/review-bundle-v3-complete'
OUT = ROOT / '.runtime/round-20261022/root-wire-bundle-v3-review'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def credentials(raw, secrets=()):
    seen = set()
    findings = set()
    keys = {'token', 'api_key', 'apikey', 'authorization', 'mcp_url', 'access_token', 'refresh_token'}

    def visit(data, depth=0):
        assert depth < 48
        fingerprint = sha(data)
        if fingerprint in seen:
            return
        seen.add(fingerprint)
        if any(secret and secret in data for secret in secrets):
            findings.add('exact local credential')
        try:
            value = data.decode('utf8')
        except UnicodeDecodeError:
            return
        if re.search(r'\bsk-[A-Za-z0-9_-]{20,}|\bBearer\s+[A-Za-z0-9._-]{16,}', value):
            findings.add('credential pattern')
        try:
            decoded = json.loads(value)
        except ValueError:
            decoded = None
        if isinstance(decoded, (dict, list)):
            walk(decoded, depth + 1)
        if len(value) >= 32 and len(value) % 4 == 0 and re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', value):
            visit(base64.b64decode(value, validate=True), depth + 1)
        unescaped = re.sub(r'\\u([0-9a-fA-F]{4})|\\x([0-9a-fA-F]{2})',
                           lambda match: chr(int(match[1] or match[2], 16)), value)
        unescaped = unescaped.replace('\\"', '"').replace("\\'", "'")
        if unescaped != value:
            visit(unescaped.encode('utf8'), depth + 1)

    def walk(value, depth):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in keys and item not in (None, '', '[REDACTED]'):
                    findings.add('sensitive JSON member')
                walk(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                walk(item, depth + 1)
        elif isinstance(value, str):
            visit(value.encode('utf8'), depth + 1)

    visit(raw)
    return sorted(findings)


def main():
    OUT.mkdir(exist_ok=False)
    secrets = []
    # Read credentials only for equality detection; never emit their values.
    for path in (Path.home() / '.pyreact-debug/instances').glob('*/session.json'):
        value = json.loads(path.read_bytes())
        for key in ('token', 'mcp_url'):
            if isinstance(value.get(key), str) and value[key]:
                secrets.append(value[key].encode('utf8'))
    synthetic = json.dumps({'mcp_url': 'http://localhost/example-private'}).encode()
    assert credentials(json.dumps({'stdout': synthetic.decode()}).encode())
    assert credentials(json.dumps({'payload': base64.b64encode(synthetic).decode()}).encode())
    assert credentials(('"' + ''.join('\\u%04x' % ord(c) for c in ('sk-' + 'X' * 32)) + '"').encode())
    assert not credentials(b'{"sha256":"' + b'a' * 64 + b'","record_count":72}')
    index_raw = (PACKAGE / 'manifest.json').read_bytes()
    manifest = json.loads(index_raw)
    assert sha(index_raw) == '61437df65fdbca309d90323da4a27198db32d5993e56fff3cda6493fc3e0f728'
    expected = {'manifest.json'}
    rows = []
    for row in manifest['objects']:
        pieces = []
        for part in row['parts']:
            path = PACKAGE / part['path']
            assert path.resolve().is_relative_to(PACKAGE.resolve())
            assert part['path'] not in expected
            expected.add(part['path'])
            raw = path.read_bytes()
            assert len(raw) == part['bytes'] < 300000 and sha(raw) == part['sha256']
            pieces.append(raw)
        stored = b''.join(pieces)
        content = gzip.decompress(stored) if row['encoding'] == 'gzip' else stored
        assert len(content) == row['content_bytes'] and sha(content) == row['content_sha256']
        if row['original_source']:
            source = ROOT / row['original_source']
            assert source.read_bytes() == content
            assert sha(content) == row['original_sha256']
            assert row['content_transform'] == 'none'
        assert not credentials(content, secrets), row['object']
        rows.append({'object': row['object'], 'source_compared': bool(row['original_source']), 'passed': True})
    actual = {p.relative_to(PACKAGE).as_posix() for p in PACKAGE.rglob('*') if p.is_file()}
    assert actual == expected
    assert all((PACKAGE / p).stat().st_size < 300000 for p in actual)
    result = {'passed': True, 'manifest_sha256': sha(index_raw), 'objects': len(rows),
              'source_originals_compared': sum(row['source_compared'] for row in rows),
              'stored_files': len(actual), 'credential_findings': 0,
              'positive_credential_controls': 3, 'negative_credential_controls': 1,
              'rows': rows, 'manual_closures_added': 0}
    (OUT / 'report.json').write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({key: value for key, value in result.items() if key != 'rows'}))


if __name__ == '__main__':
    main()
